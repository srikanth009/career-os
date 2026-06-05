#!/usr/bin/env python3
"""
linkedin_search.py — discover LinkedIn job cards via the public *guest* endpoint.

Uses LinkedIn's anonymous job-search API (the same one LinkedIn serves to search
engines and logged-out visitors):
    https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
No login, no account, no OAuth, no cookies. Because nothing is authenticated,
there is NO risk to the user's LinkedIn account — the only limit is IP-level
rate limiting, which we respect with a human-paced throttle.

Each card yields: jobId, title, company, location, posted, url. To get the full
JD body, pass the url (or https://www.linkedin.com/jobs/view/{jobId}) to fetch_jd.py
— its `linkedin-guest` tier resolves the body from the same anonymous endpoint.

Usage:
  python3 linkedin_search.py --keywords "product manager" --location "India" \
      --pages 3 --recent-days 7 --json
  # filters: --recent-days N (f_TPR), --remote, --experience mid-senior

Exit codes: 0 ok, 2 fetch failed, 3 bad usage.
"""
import argparse
import json
import re
import sys
import time
from urllib.parse import urlencode, urlparse

import requests
from lxml import html as lxml_html

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
TIMEOUT = 25
EXPERIENCE = {"internship": "1", "entry": "2", "associate": "3",
              "mid-senior": "4", "director": "5", "executive": "6"}


def fetch_page(keywords, location, start, recent_days, remote, experience, debug):
    params = {"keywords": keywords, "location": location, "start": start}
    if recent_days:
        params["f_TPR"] = f"r{int(recent_days) * 86400}"
    if remote:
        params["f_WT"] = "2"
    if experience and experience in EXPERIENCE:
        params["f_E"] = EXPERIENCE[experience]
    url = f"{SEARCH}?{urlencode(params)}"
    if debug:
        print("[li_search]", url, file=sys.stderr)
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        if debug:
            print(f"[li_search] HTTP {r.status_code}", file=sys.stderr)
        return None
    return r.text


def parse_cards(html_text):
    doc = lxml_html.fromstring(html_text)
    out = []
    for card in doc.xpath('//li'):
        urn = card.xpath('.//*[@data-entity-urn]/@data-entity-urn')
        job_id = None
        if urn:
            m = re.search(r"jobPosting:(\d+)", urn[0])
            job_id = m.group(1) if m else None
        title = card.xpath('.//*[contains(@class,"base-search-card__title")]/text()')
        company = card.xpath('.//*[contains(@class,"base-search-card__subtitle")]//text()')
        loc = card.xpath('.//*[contains(@class,"job-search-card__location")]/text()')
        posted = card.xpath('.//time/@datetime')
        link = card.xpath('.//a[contains(@class,"base-card__full-link")]/@href')
        title = title[0].strip() if title else None
        if not (job_id or title):
            continue
        out.append({
            "jobId": job_id,
            "title": title,
            "company": "".join(company).strip() or None,
            "location": loc[0].strip() if loc else None,
            "posted": posted[0] if posted else None,
            "url": (link[0].split("?")[0] if link else
                    (f"https://www.linkedin.com/jobs/view/{job_id}" if job_id else None)),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", required=True)
    ap.add_argument("--location", default="India")
    ap.add_argument("--pages", type=int, default=3, help="pages of ~25 cards each")
    ap.add_argument("--recent-days", type=int, default=0, help="only last N days")
    ap.add_argument("--remote", action="store_true")
    ap.add_argument("--experience", default=None, choices=list(EXPERIENCE))
    ap.add_argument("--throttle", type=float, default=4.0, help="seconds between pages")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()

    seen, results = set(), []
    for p in range(a.pages):
        html_text = fetch_page(a.keywords, a.location, p * 25, a.recent_days,
                               a.remote, a.experience, a.debug)
        if html_text is None:
            if p == 0:
                print("fetch failed", file=sys.stderr)
                sys.exit(2)
            break
        cards = parse_cards(html_text)
        if not cards:
            break
        for c in cards:
            key = c["jobId"] or c["url"]
            if key and key not in seen:
                seen.add(key)
                results.append(c)
        if p < a.pages - 1:
            time.sleep(a.throttle)

    if a.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for c in results:
            print(f"{c['title']} @ {c['company']} · {c['location']} · {c['url']}")
    print(f"[li_search] {len(results)} unique cards", file=sys.stderr)


if __name__ == "__main__":
    main()
