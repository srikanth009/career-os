#!/usr/bin/env python3
"""
fetch_jd.py — ATS-agnostic job-description fetcher.

Turns a job-posting URL into clean text, regardless of the ATS or website.

Strategy (tiered, cheapest/most-reliable first):
  Tier 0  API-first  : detect the ATS from the URL and hit its public JSON API
                       (Greenhouse, Lever, Ashby, SmartRecruiters, Workday,
                       Recruitee). Cleanest data, no browser, no bot-detection.
  Tier 1  JSON-LD    : any page that ships a schema.org JobPosting block
                       (Google-for-Jobs requires this — covers most career sites).
  Tier 2  Readability: static HTML, pick the densest text block.
  Tier 3  Headless   : render JS with the local Chrome (--dump-dom), then re-run
                       Tiers 1+2 on the rendered DOM. No Selenium / chromedriver.

Dependencies: requests + lxml  (already present). Chrome optional, only for Tier 3.

Usage:
  python3 fetch_jd.py "<url>"                  # prints clean text to stdout
  python3 fetch_jd.py "<url>" --out jd.txt     # also writes to a file
  python3 fetch_jd.py "<url>" --json           # emit structured JSON
  python3 fetch_jd.py "<url>" --no-browser     # disable Tier 3 fallback
  python3 fetch_jd.py "<url>" --title "..."    # title hint for ATS board re-match
  python3 fetch_jd.py "<url>" --debug          # log which tier won, to stderr

Exit codes: 0 ok, 2 fetch failed, 3 bad usage, 4 posting closed/expired.
"""

import argparse
import html as _html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse, parse_qs, unquote

import requests
from lxml import html as lxml_html

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 25


def log(debug, *a):
    if debug:
        print("[fetch_jd]", *a, file=sys.stderr)


# ---------------------------------------------------------------------------
# HTML -> text  (structure-preserving, dependency-free)
# ---------------------------------------------------------------------------
def html_to_text(fragment):
    """Convert an HTML fragment/string to readable plain text."""
    if not fragment or not fragment.strip():
        return ""
    # Some ATS APIs (e.g. Greenhouse) return HTML with entity-encoded tags
    # (&lt;div&gt;). Decode those first so the markup becomes parseable.
    if "&lt;" in fragment or "&gt;" in fragment:
        fragment = _html.unescape(fragment)
    # If it doesn't look like HTML, return as-is (already plain).
    if "<" not in fragment:
        return _html.unescape(fragment).strip()
    try:
        node = lxml_html.fromstring(fragment)
    except Exception:
        return re.sub(r"<[^>]+>", " ", _html.unescape(fragment)).strip()

    for bad in node.xpath(".//script | .//style | .//noscript"):
        bad.getparent().remove(bad)

    lines = []

    def walk(el):
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag == "li":
            txt = " ".join(el.text_content().split())
            if txt:
                lines.append("- " + txt)
            return
        if tag in ("br",):
            lines.append("")
            return
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section"):
            # Recurse but force a line break around block elements.
            before = len(lines)
            if el.text and el.text.strip():
                lines.append(el.text.strip())
            for child in el:
                walk(child)
                if child.tail and child.tail.strip():
                    lines.append(child.tail.strip())
            if len(lines) > before:
                lines.append("")
            return
        # inline / other: flatten text
        if el.text and el.text.strip():
            lines.append(el.text.strip())
        for child in el:
            walk(child)
            if child.tail and child.tail.strip():
                lines.append(child.tail.strip())

    walk(node)
    text = "\n".join(lines)
    # Collapse 3+ blank lines to 1 blank line; trim trailing space per line.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _html.unescape(text).strip()


# Sentinel: an ATS board API was reachable (HTTP 200) but the specific posting
# is NOT listed on it — i.e. the role has closed/expired. Distinct from None
# ("this handler doesn't apply / API unreachable"). When a handler returns this,
# the orchestrator short-circuits: no point rendering a dead SPA page in headless
# Chrome (it just times out at 60s and fails anyway).
CLOSED = "__POSTING_CLOSED__"


def result(source, title=None, company=None, location=None, body="", url=""):
    return {
        "source": source,
        "title": (title or "").strip() or None,
        "company": (company or "").strip() or None,
        "location": (location or "").strip() or None,
        "url": url,
        "text": (body or "").strip(),
    }


def _norm_title(s):
    """Lowercase + collapse non-alphanumerics — for fuzzy title matching."""
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _best_title_match(items, hint, field="title"):
    """Find the board posting whose title best matches a caller-provided hint.
    Caller supplies the hint (e.g. the search-result title) — never invented here.
    Ordered: exact normalized match; then the hint contained in a fuller board
    title (board titles often add a dept prefix like 'Product Management - ...');
    then a board title contained in the hint, but only if it is specific enough
    (>= 4 words) so a generic 1-word title like 'Manager' can't false-match."""
    h = _norm_title(hint)
    if not h:
        return None
    for it in items:
        if _norm_title(it.get(field)) == h:
            return it
    for it in items:
        t = _norm_title(it.get(field))
        if t and h in t:
            return it
    for it in items:
        t = _norm_title(it.get(field))
        if t and len(t.split()) >= 4 and t in h:
            return it
    return None


# ---------------------------------------------------------------------------
# Tier 0 — ATS-specific JSON APIs
# ---------------------------------------------------------------------------
def try_greenhouse(url, debug, title_hint=None):
    # boards.greenhouse.io/{board}/jobs/{id}
    # job-boards.greenhouse.io/{board}/jobs/{id}
    # boards.greenhouse.io/embed/job_app?for={board}&token={id}
    u = urlparse(url)
    if "greenhouse.io" not in u.netloc:
        return None
    board = job_id = None
    m = re.search(r"/([^/]+)/jobs/(\d+)", u.path)
    if m:
        board, job_id = m.group(1), m.group(2)
    else:
        q = parse_qs(u.query)
        board = (q.get("for") or [None])[0]
        job_id = (q.get("token") or [None])[0]
    if not (board and job_id):
        return None
    api = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}?content=true"
    log(debug, "greenhouse api", api)
    r = requests.get(api, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    d = r.json()
    return result("greenhouse-api", d.get("title"),
                  (d.get("company_name") or board),
                  (d.get("location") or {}).get("name"),
                  html_to_text(d.get("content", "")), url)


def _lever_result(d, company, url):
    parts = [d.get("descriptionPlain") or html_to_text(d.get("description", ""))]
    for blk in d.get("lists", []):
        parts.append((blk.get("text") or "").strip())
        parts.append(html_to_text(blk.get("content", "")))
    parts.append(d.get("additionalPlain") or html_to_text(d.get("additional", "")))
    loc = (d.get("categories") or {}).get("location")
    return result("lever-api", d.get("text"), company, loc,
                  "\n\n".join(p for p in parts if p), url)


def try_lever(url, debug, title_hint=None):
    u = urlparse(url)
    if "lever.co" not in u.netloc:
        return None
    m = re.search(r"/([^/]+)/([0-9a-f\-]{8,})", u.path)
    if not m:
        return None
    company, job_id = m.group(1), m.group(2)
    api = f"https://api.lever.co/v0/postings/{company}/{job_id}?mode=json"
    log(debug, "lever api", api)
    r = requests.get(api, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code == 200:
        return _lever_result(r.json(), company, url)
    # Per-posting endpoint failed (404 = expired/closed id). Fall back to the
    # live board and re-match by id, then by caller-provided title hint.
    if r.status_code not in (400, 404, 410):
        return None
    board = f"https://api.lever.co/v0/postings/{company}?mode=json"
    log(debug, "lever per-posting", r.status_code, "-> board", board)
    rb = requests.get(board, headers=HEADERS, timeout=TIMEOUT)
    if rb.status_code != 200:
        return None
    postings = rb.json() or []
    for p in postings:
        if p.get("id") == job_id:
            log(debug, "lever matched by id on board")
            return _lever_result(p, company, url)
    if title_hint:
        m2 = _best_title_match(postings, title_hint, field="text")
        if m2:
            log(debug, "lever matched by title hint:", m2.get("text"))
            return _lever_result(m2, company, url)
    # Board reachable but this posting isn't on it -> role closed/expired.
    log(debug, "lever posting not on board (closed/expired):", job_id)
    return CLOSED


def _ashby_result(job, org, url):
    return result("ashby-api", job.get("title"), org, job.get("location"),
                  html_to_text(job.get("descriptionHtml")
                               or job.get("descriptionPlain", "")), url)


def try_ashby(url, debug, title_hint=None):
    u = urlparse(url)
    if "ashbyhq.com" not in u.netloc:
        return None
    m = re.search(r"/([^/]+)/([0-9a-f\-]{8,})", u.path)
    if not m:
        return None
    org, job_id = m.group(1), m.group(2)
    api = f"https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true"
    log(debug, "ashby api", api)
    r = requests.get(api, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    jobs = r.json().get("jobs", [])
    for job in jobs:
        if job.get("id") == job_id or job_id in (job.get("jobUrl") or ""):
            return _ashby_result(job, org, url)
    # No UUID match. Try a caller-provided title hint before giving up.
    if title_hint:
        m2 = _best_title_match(jobs, title_hint, field="title")
        if m2:
            log(debug, "ashby matched by title hint:", m2.get("title"))
            return _ashby_result(m2, org, url)
    # Board reachable but this UUID isn't listed -> role closed/expired.
    log(debug, "ashby posting not on board (closed/expired):", job_id)
    return CLOSED


def try_smartrecruiters(url, debug, title_hint=None):
    u = urlparse(url)
    if "smartrecruiters.com" not in u.netloc:
        return None
    # jobs.smartrecruiters.com/{company}/{numericid}-{slug}
    m = re.search(r"/([^/]+)/(\d{6,})", u.path)
    if not m:
        return None
    company, posting_id = m.group(1), m.group(2)
    api = f"https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting_id}"
    log(debug, "smartrecruiters api", api)
    r = requests.get(api, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    d = r.json()
    secs = ((d.get("jobAd") or {}).get("sections")) or {}
    parts = []
    for key in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"):
        s = secs.get(key) or {}
        if s.get("title"):
            parts.append(s["title"])
        parts.append(html_to_text(s.get("text", "")))
    loc = d.get("location") or {}
    loc_s = ", ".join(x for x in [loc.get("city"), loc.get("country")] if x)
    return result("smartrecruiters-api", d.get("name"), company, loc_s,
                  "\n\n".join(p for p in parts if p), url)


def try_recruitee(url, debug, title_hint=None):
    u = urlparse(url)
    if "recruitee.com" not in u.netloc:
        return None
    sub = u.netloc.split(".")[0]
    m = re.search(r"/o/([^/]+)", u.path)
    if not m:
        return None
    slug = m.group(1)
    api = f"https://{sub}.recruitee.com/api/offers/{slug}"
    log(debug, "recruitee api", api)
    r = requests.get(api, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    d = r.json().get("offer", {})
    return result("recruitee-api", d.get("title"), sub, d.get("location"),
                  html_to_text(d.get("description", "")), url)


def try_workday(url, debug, title_hint=None):
    u = urlparse(url)
    if "myworkdayjobs.com" not in u.netloc and "workday.com" not in u.netloc:
        return None
    # External: https://{tenant}.{dc}.myworkdayjobs.com/{lang}/{site}/job/{loc}/{title}_{reqid}
    # CXS API : https://{host}/wday/cxs/{tenant}/{site}/job/{the-path-after-site}
    host = u.netloc
    tenant = host.split(".")[0]
    parts = [p for p in u.path.split("/") if p]
    if "job" not in parts:
        return None
    ji = parts.index("job")
    # site name is the segment right before "job" (skip optional lang code).
    site = parts[ji - 1] if ji >= 1 else None
    tail = "/".join(parts[ji:])  # job/.../req
    if not site:
        return None
    api = f"https://{host}/wday/cxs/{tenant}/{site}/{tail}"
    log(debug, "workday cxs api", api)
    try:
        r = requests.get(api, headers={**HEADERS, "Accept": "application/json"}, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        d = r.json().get("jobPostingInfo", {})
        return result("workday-api", d.get("title"), tenant,
                      d.get("location"), html_to_text(d.get("jobDescription", "")), url)
    except Exception as e:
        log(debug, "workday api failed", e)
        return None


def try_linkedin(url, debug, title_hint=None):
    # LinkedIn job pages are JS-walled, but the *guest* (anonymous) endpoint
    # serves the full posting as static HTML — no login, no account, no OAuth:
    #   https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jobId}
    # Accept any LinkedIn job URL form and the 10-digit job id embedded in it.
    u = urlparse(url)
    if "linkedin.com" not in u.netloc:
        return None
    job_id = None
    q = parse_qs(u.query)
    if q.get("currentJobId"):
        job_id = q["currentJobId"][0]
    if not job_id:
        m = re.search(r"/jobPosting/(\d{6,})", u.path) or \
            re.search(r"/jobs/view/(?:.*-)?(\d{6,})", u.path) or \
            re.search(r"(\d{10})", u.path)
        if m:
            job_id = m.group(1)
    if not job_id:
        return None
    api = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    log(debug, "linkedin guest api", api)
    r = requests.get(api, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200 or len(r.text) < 200:
        return None
    doc = lxml_html.fromstring(r.text)

    def _first_text(xpaths):
        for xp in xpaths:
            els = doc.xpath(xp)
            if els:
                t = els[0].text_content().strip()
                if t:
                    return t
        return None

    title = _first_text(['//h2[contains(@class,"top-card-layout__title")]',
                          '//*[contains(@class,"topcard__title")]'])
    company = _first_text(['//*[contains(@class,"topcard__org-name-link")]',
                           '//a[contains(@class,"topcard__org-name-link")]',
                           '//*[contains(@class,"top-card-layout__entity-info")]//a'])
    location = _first_text(['//*[contains(@class,"topcard__flavor--bullet")]',
                            '//*[contains(@class,"top-card-layout__second-subline")]//span'])
    body_els = doc.xpath('//*[contains(@class,"show-more-less-html__markup")]') or \
               doc.xpath('//*[contains(@class,"description__text")]')
    body = html_to_text(lxml_html.tostring(body_els[0], encoding="unicode")) if body_els else ""
    if len((body or "").split()) < 40:
        return None
    return result("linkedin-guest", title, company, location, body, url)


ATS_HANDLERS = [try_greenhouse, try_lever, try_ashby,
                try_smartrecruiters, try_recruitee, try_workday, try_linkedin]


# ---------------------------------------------------------------------------
# Tier 1 — schema.org JobPosting (JSON-LD)
# ---------------------------------------------------------------------------
def extract_jsonld_jobposting(doc, url, debug):
    for script in doc.xpath('//script[@type="application/ld+json"]'):
        raw = script.text_content()
        if not raw or "JobPosting" not in raw:
            continue
        for cand in _iter_json_objects(raw):
            t = cand.get("@type")
            types = t if isinstance(t, list) else [t]
            if "JobPosting" not in types:
                continue
            log(debug, "json-ld JobPosting found")
            org = cand.get("hiringOrganization") or {}
            company = org.get("name") if isinstance(org, dict) else None
            loc = cand.get("jobLocation")
            loc_s = _jsonld_location(loc)
            return result("jsonld", cand.get("title"), company, loc_s,
                          html_to_text(cand.get("description", "")), url)
    return None


def _iter_json_objects(raw):
    """Yield dicts from a JSON-LD blob (handles single obj, list, @graph)."""
    try:
        data = json.loads(raw)
    except Exception:
        # Some sites concatenate or trail commas; try a lenient salvage.
        try:
            data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        except Exception:
            return
    stack = [data]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if "@graph" in cur and isinstance(cur["@graph"], list):
                stack.extend(cur["@graph"])
            yield cur
        elif isinstance(cur, list):
            stack.extend(cur)


def _jsonld_location(loc):
    if isinstance(loc, list):
        return ", ".join(filter(None, (_jsonld_location(x) for x in loc)))
    if isinstance(loc, dict):
        addr = loc.get("address") or {}
        if isinstance(addr, dict):
            return ", ".join(x for x in [addr.get("addressLocality"),
                                         addr.get("addressRegion"),
                                         addr.get("addressCountry")] if x)
    return None


# ---------------------------------------------------------------------------
# Tier 2 — readability (densest text block)
# ---------------------------------------------------------------------------
def extract_readability(doc, url, debug):
    for bad in doc.xpath("//script | //style | //noscript | //nav | //header | //footer | //form | //aside"):
        bad.getparent().remove(bad)
    best, best_score = None, 0
    for el in doc.xpath("//main | //article | //section | //div"):
        txt = el.text_content()
        words = len(txt.split())
        # density: prefer blocks with many words and several list items / paragraphs
        bonus = len(el.xpath(".//li")) * 8 + len(el.xpath(".//p")) * 4
        score = words + bonus
        if score > best_score and words > 80:
            best, best_score = el, score
    if best is None:
        body = doc.xpath("//body")
        best = body[0] if body else doc
    log(debug, "readability score", best_score)
    title = None
    h = doc.xpath("//h1")
    if h:
        title = h[0].text_content().strip()
    elif doc.xpath("//title"):
        title = doc.xpath("//title")[0].text_content().strip()
    text = html_to_text(lxml_html.tostring(best, encoding="unicode"))
    return result("readability", title, None, None, text, url)


# ---------------------------------------------------------------------------
# Tier 3 — headless Chrome --dump-dom (renders JS, no Selenium)
# ---------------------------------------------------------------------------
def render_with_chrome(url, debug):
    chrome = _find_chrome()
    if not chrome:
        log(debug, "no chrome binary for Tier 3")
        return None
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--hide-scrollbars", "--mute-audio",
               f"--user-data-dir={tmp}",
               "--virtual-time-budget=9000",
               f"--user-agent={UA}", "--dump-dom", url]
        log(debug, "chrome dump-dom")
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if out.stdout and len(out.stdout) > 500:
                return out.stdout
        except Exception as e:
            log(debug, "chrome failed", e)
    return None


def _find_chrome():
    for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"),
              shutil.which("chrome")):
        if c and shutil.which(c) or (c and c.startswith("/") and __import__("os").path.exists(c)):
            return c
    return None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def fetch_static(url, debug):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and r.text:
            return r.text
        log(debug, "static fetch status", r.status_code)
    except Exception as e:
        log(debug, "static fetch error", e)
    return None


def from_html(raw_html, url, debug):
    try:
        doc = lxml_html.fromstring(raw_html)
    except Exception:
        return None
    res = extract_jsonld_jobposting(doc, url, debug)
    if res and len(res["text"]) > 200:
        return res
    res2 = extract_readability(doc, url, debug)
    if res2 and len(res2["text"]) > 200:
        return res2
    return res or res2


def fetch_jd(url, allow_browser=True, debug=False, title_hint=None):
    # Tier 0
    for handler in ATS_HANDLERS:
        try:
            res = handler(url, debug, title_hint)
        except Exception as e:
            log(debug, handler.__name__, "error", e)
            res = None
        if res is CLOSED:
            # ATS confirmed the posting is gone — don't burn 60s on a headless
            # Chrome render of a dead SPA page that will fail anyway.
            log(debug, handler.__name__, "posting closed/expired; skipping remaining tiers")
            return CLOSED
        if res and len(res["text"]) > 150:
            return res

    # Tier 1 + 2 on static HTML
    raw = fetch_static(url, debug)
    if raw:
        res = from_html(raw, url, debug)
        if res and len(res["text"]) > 200:
            return res

    # Tier 3 — render JS then re-run 1+2
    if allow_browser:
        rendered = render_with_chrome(url, debug)
        if rendered:
            res = from_html(rendered, url, debug)
            if res and res["text"]:
                res["source"] += "+chrome"
                return res

    # Last resort: whatever static gave us
    if raw:
        res = from_html(raw, url, debug)
        if res:
            return res
    return None


def main():
    ap = argparse.ArgumentParser(description="ATS-agnostic JD fetcher")
    ap.add_argument("url")
    ap.add_argument("--out", help="write clean text to this file")
    ap.add_argument("--json", action="store_true", help="emit structured JSON")
    ap.add_argument("--no-browser", action="store_true", help="disable headless fallback")
    ap.add_argument("--title", help="title hint for ATS board re-match (e.g. the search-result title)")
    ap.add_argument("--debug", action="store_true", help="log tier decisions to stderr")
    args = ap.parse_args()

    res = fetch_jd(args.url, allow_browser=not args.no_browser, debug=args.debug,
                   title_hint=args.title)
    if res is CLOSED:
        print("CLOSED: this posting is no longer listed on the ATS board "
              "(role closed/expired). No body to fetch.", file=sys.stderr)
        sys.exit(4)
    if not res or not res["text"]:
        print("ERROR: could not extract a job description from that URL.", file=sys.stderr)
        sys.exit(2)

    if args.json:
        payload = json.dumps(res, ensure_ascii=False, indent=2)
        print(payload)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(payload)
        return

    header = []
    if res["title"]:
        header.append(res["title"])
    meta = " | ".join(x for x in [res["company"], res["location"]] if x)
    if meta:
        header.append(meta)
    header.append(f"Source: {res['source']}  ({res['url']})")
    body = "\n".join(header) + "\n" + "=" * 60 + "\n\n" + res["text"] + "\n"

    sys.stdout.write(body)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"\n[written to {args.out}]", file=sys.stderr)


if __name__ == "__main__":
    main()
