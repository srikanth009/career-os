---
name: scout-jds
description: Open-web, boolean-driven job scout. The broad front of the funnel — finds job postings across the internet that match the user's profile. Reads memory/booleans.yaml (the engineered boolean/X-ray query set built by generate-booleans) and runs its active google-xray / linkedin-guest / linkedin-posts-xray strings via WebSearch + scripts/linkedin_search.py, fetches full JD text with scripts/fetch_jd.py, de-dupes on canonical jobId, scores relevance, writes a ranked-list.md that triage-jds consumes, and writes per-boolean yield stats (results/fetched) back to booleans.yaml to fuel the evolution loop. SELF-EXPANDS memory/role-taxonomy.yaml: when a real posting carries a genuinely-matching new title, it asks the user to add it. Parallel to discover-jds (Naukri + curated career pages). Triggers on "scout jobs", "find all jobs for me", "search the web for roles", "sweep for openings", or `/scout-jds`.
---

# Skill: scout-jds

## What this skill does
The widest mouth of the discover → triage → tailor funnel. Where `discover-jds` pulls from
Naukri + a curated `target-companies.yaml` list, **scout-jds searches the open internet** for
every title the user's role is known by, then narrows to a ranked shortlist.

1. Reads `memory/booleans.yaml` — the engineered boolean/X-ray query set (built by
   `generate-booleans`) — and runs the `active` booleans for scout's platforms (google-xray,
   linkedin-guest, linkedin-posts-xray). Naukri booleans are discover-jds' job.
2. Reads `memory/search-defaults.yaml` for exclusion / comp filters + the archetype lens, and
   `memory/role-taxonomy.yaml` for excluded-title drops + the self-expansion check.
3. Sweeps the open web (WebSearch) + LinkedIn guest API by executing each boolean's query.
4. Fetches full JD text for each candidate URL via `scripts/fetch_jd.py` (ATS-agnostic).
5. De-dupes on a canonical job key (jobId / ATS id), then against `jds/_cache/web-seen.json`.
5b. Writes per-boolean yield stats (`runs`/`results`/`fetched`) back to `booleans.yaml` — the
   fuel for the boolean-evolution loop (triage adds `on_profile` later).
6. **Self-expands the taxonomy**: when a real posting carries a title not yet in the taxonomy
   but the JD content matches the profile, it surfaces it and asks the user to confirm/add.
7. Scores relevance against the resolved archetype → STRONG / MEDIUM / WEAK buckets.
8. Writes `ranked-list.md` in the **exact format `triage-jds` Mode A expects**, so the handoff
   `triage [1], [3], [7]` just works.

## What this skill does NOT do
- Does NOT log into LinkedIn or scrape authenticated pages (that risks the user's account).
  It DOES use LinkedIn's **public guest endpoints** — the same anonymous job pages LinkedIn
  serves to search engines and logged-out visitors — via `scripts/linkedin_search.py` (discovery)
  and `fetch_jd.py`'s `linkedin-guest` tier (bodies). No login, no account, no flag risk.
- Does NOT pull from Naukri via this skill. Naukri's `jobapi/v3` is gated by a JS-computed
  reCAPTCHA token (returns `406 recaptcha required` to any plain HTTP client) and its pages are
  fully client-side rendered (no JSON-LD, no embedded job data), so it cannot be fetched headlessly.
  Naukri is `discover-jds`' job — that skill drives a real logged-in browser (Chrome MCP) where the
  page's own JS produces the token. WebSearch can surface Naukri JD *URLs*, but their bodies won't
  fetch without the browser, so they'd only ever land in NEEDS-FETCH here — leave Naukri to discover-jds.
- Does NOT deep-evaluate each JD against memory or give a go/no-go — that's `triage-jds`.
- Does NOT tailor a resume — that's `tailor-resume`.
- Does NOT auto-apply to anything. It discovers; application is a human decision.
- Does NOT fabricate a posting, a URL, a company, or a title variant. A title only enters the
  taxonomy's `confirmed` list with a real, cited posting. (Same never-invent rule as the suite.)
- Does NOT silently edit `role-taxonomy.yaml`. New titles are proposed to the user, never auto-added.

## Pre-flight: required artifacts + tools
Verify these exist; if any is missing, STOP and report:
- `career-os/memory/booleans.yaml`  (the QUERY SOURCE — run generate-booleans first if empty)
- `career-os/memory/role-taxonomy.yaml`  (excluded-title drops + self-expansion check)
- `career-os/memory/profile.yaml`
- `career-os/memory/search-defaults.yaml`
- `career-os/memory/narratives/*.md`  (archetype context for ranking)
- `career-os/scripts/fetch_jd.py`  (to pull full JD text from result URLs)
- `career-os/scripts/linkedin_search.py`  (LinkedIn public-guest discovery)

Tool check: the **WebSearch** tool must be available (this skill is WebSearch-first). If it is
not, STOP and tell the user — do NOT silently fall back to inventing results. (Chrome MCP is an
optional fallback only for JS-heavy / fetch-failing URLs, exactly as in `tailor-resume` Step 1.)

## Pre-flight: rate-limit check
WebSearch is far lower-risk than logged-in scraping, but stay polite and bounded. Read the
directory listing of `career-os/jds/_runs/`. Count entries with today's date prefix whose name
ends in `-scout`. If that count ≥ `safety.max_runs_per_day` (default 3 from search-defaults.yaml),
STOP and tell the user. Total WebSearch calls per run are capped in Step 2.

## Step 0 — Load the boolean set + filters
1. Read `memory/booleans.yaml` — **this is now the query source** (replaces ad-hoc query
   building from titles). Collect every `active` boolean whose `platform` is one scout drives:
   - `google-xray` → run as a WebSearch query (Step 2).
   - `linkedin-guest` → run via `linkedin_search.py` (Step 2b).
   - `linkedin-posts-xray` → run as a WebSearch query, but its hits are hiring-sourcing leads
     (feed `find-hiring-manager`), often not JD URLs — handle in Step 3.
   - `naukri-browser` booleans are **NOT scout's job** — skip them (discover-jds runs those).
   Also pull any `candidate` booleans the user opted into for this run (default: skip candidates).
   Carry each boolean's `id` forward — every candidate it surfaces must be tagged with it so
   Step 8b can write yield back.
2. Read `role-taxonomy.yaml` for `excluded` titles (to drop false positives in Step 5) and for
   the self-expansion check (Step 6). It is NO LONGER the query source — booleans.yaml is.
3. Read `search-defaults.yaml`. Resolve: `exclusions` (titles + companies), `comp_handling`,
   and `default_search.archetype_target` (the ranking lens; default `platform-staff-pm`).
   (Themes/locations are already baked into each boolean's `query`/params.)
4. Apply any user overrides from the invocation (e.g. "scout jobs but only run the ATS booleans",
   or "include the candidate booleans this run"). Note overrides in the run config.
5. Echo the resolved config back to the user in one short block before searching: which boolean
   `id`s are being run, on which platforms, and the archetype lens. Cheap confirmation, avoids a
   wasted run. If `booleans.yaml` has zero active scout-platform entries, STOP and tell the user
   to run `generate-booleans` first.

## Step 1 — Create run directory
Create: `career-os/jds/_runs/<YYYY-MM-DD-HHMMSS>-scout/`
Write `search-config.yaml` (the fully resolved config used this run — for reproducibility),
including which taxonomy titles were swept and any one-off overrides.

## Step 2 — Run the `google-xray` + `linkedin-posts-xray` booleans (WebSearch)
For each `active` boolean whose `platform` is `google-xray` or `linkedin-posts-xray`, run its
`query` string **verbatim** through the WebSearch tool — the boolean IS the engineered query
(site:-operators, OR-groups, exclusions already in it). Do NOT rewrite it on the fly; if a
boolean is weak, that's the evolution loop's job (`generate-booleans` Mode B), not an ad-hoc
patch here. Tag every hit with the `boolean_id` that produced it.

Hard caps (politeness + cost + signal-to-noise):
- **≤ 24 WebSearch calls total per run.** With ~5 google-xray + 1 posts-xray booleans that's
  comfortably inside budget; if you ever exceed it, run the highest-`yield` booleans first
  (read `stats.yield`; nulls — never-run — get one slot each before repeats).
- Stop early if you already have ~30+ distinct candidate URLs — more is noise, not signal.

Record, per boolean, the **count of result URLs it surfaced** (`results`) into `search-config.yaml`
and the per-boolean tally — Step 8b writes these back to `booleans.yaml`.

## Step 2b — Run the `linkedin-guest` booleans (public guest endpoint)
For each `active` boolean whose `platform` is `linkedin-guest`, run `linkedin_search.py` using its
`query` as `--keywords` and its `li_params` block for the rest:
```bash
python3 career-os/scripts/linkedin_search.py --keywords "<boolean.query>" \
    --location "<li_params.location>" --pages 3 --recent-days <li_params.recent_days> \
    [--experience <li_params.experience>] [--remote] --json
```
This returns up to ~25 cards/page (jobId, title, company, location, posted, url) with no auth.
Caps mirror the safety budget: **≤ 3 pages per boolean**, default 4s throttle between pages.
Tag every card with its `boolean_id`. Each card's `url` (or `/jobs/view/<jobId>`) is fetchable in
Step 4 — `fetch_jd.py`'s `linkedin-guest` tier resolves the full body. Treat cards exactly like
WebSearch candidates from here on.

## Step 3 — Collect + de-dupe candidates (canonical jobId)
Merge WebSearch hits and LinkedIn guest cards into one candidate set. Per hit capture: `url`,
`result_title`, `snippet`/none, `domain`, and the `boolean_id` that surfaced it. Keep hits whose
domain is a fetchable ATS / company-careers source (greenhouse.io, lever.co, ashbyhq.com,
myworkdayjobs.com, smartrecruiters.com, recruitee.com, linkedin.com guest job URLs, or a company
careers page).
**Drop**: pure aggregator/SEO-spam domains, Naukri URLs (bodies won't fetch headlessly — see "does
NOT do"), and anything whose result title clearly matches an `excluded` title.

**De-dupe on a canonical job key, not the raw URL** (the same posting arrives via several
booleans with different tracking params). Derive the key per source:
- LinkedIn → the numeric `jobId` (from the card or the `/jobs/view/<id>` / `currentJobId=` URL).
- Greenhouse/Lever/Ashby/SmartRecruiters/Workday → the ATS job id in the path (strip query string).
- Other careers pages → normalized URL (lowercase host, drop query/fragment, strip trailing slash).
When two candidates collapse to the same key, keep one but **record ALL `boolean_id`s that found
it** (a `found_by: [..]` list) — every contributing boolean gets `results` credit in Step 8b.

The **same-job-across-booleans collisions are themselves signal** for the evolution loop: a boolean
that only ever finds jobs other booleans already found is redundant. Note collision counts in
`search-config.yaml`.

Never invent a posting from a search snippet alone — a snippet is a lead, not a JD. The JD text
comes from Step 4. If a promising hit can't be fetched, it stays flagged `unfetched`, not confirmed.

`linkedin-posts-xray` hits are a special case: they're usually a person's hiring POST, not a JD
URL. Don't try to fetch them as JDs. Set them aside in a `hiring-leads.jsonl` (url, poster if
visible, snippet, boolean_id) for `find-hiring-manager`, and don't count them toward `fetched`.

**Recency caveat (learned 2026-06-02).** `site:linkedin.com/posts` X-ray has **no date operator** —
Google ranks high-pagerank *old viral* posts, so a posts-xray boolean tends to return stale 2-4-yr-old
posts with zero live leads. If every hit a posts-xray boolean returns is clearly old, that's a
structural limitation, not a wording bug: record `results` honestly (likely all stale), and flag the
boolean for `generate-booleans` Mode B (retire / rebuild with current-year + "this week"/"immediate"
anchors). The only reliably recency-capable LinkedIn path is `linkedin_search.py --recent-days` (jobs,
Step 2b) — prefer it for fresh HM discovery if posts-xray keeps returning stale results.

## Step 4 — Fetch full JD text
For each surviving candidate URL, pull clean text:
```bash
python3 career-os/scripts/fetch_jd.py "<url>" --debug
```
`fetch_jd.py` is tiered (Greenhouse/Lever/Ashby/SmartRecruiters/Workday/Recruitee JSON APIs →
JSON-LD → readability → headless Chrome). Rules:
- On success, carry the fetched text forward as the JD body, compute `hash = sha256(text)[:16]`,
  and mark the candidate `fetched: true` (every `boolean_id` in its `found_by` earns `fetched`
  credit in Step 8b).
- If it exits non-zero or returns < 120 words, the candidate is **`unfetched`**: move it to the
  NEEDS-FETCH backlog (Step 8), **do not score it, do not list it in the ranked shortlist**. Record the
  URL so it's not lost — but make no match/fit claim about a JD you never read. Never backfill with
  invented text, never score on "company/domain priors". Unfetched candidates earn `results` credit
  for their booleans but NOT `fetched` credit.
- Chrome MCP is an optional last resort for a JS-heavy URL the fetcher couldn't render; only use it
  if connected. Otherwise leave the candidate `unfetched`.

**Ashby / Lever postings — `fetch_jd.py` handles these natively (built in 2026-06-02).** Both ATSs
are JS-heavy SPAs where the old readability + headless-Chrome path returned 0 / timed out at 60s.
`fetch_jd.py`'s Tier-0 API handlers now resolve them without a browser:
- **Ashby**: isolates the posting by the UUID in the URL against the board API
  (`api.ashbyhq.com/posting-api/job-board/<org>`) and returns `descriptionPlain`. Works on live UUIDs.
- **Lever**: tries the per-posting endpoint; on 404 (expired id) it falls back to the live board and
  re-matches by id, then by a title hint.
- **Title hint**: pass `--title "<the search-result title>"` so a stale-id candidate can be re-matched
  to the same role on the board by title. The hint must be the REAL title from the search hit — never
  invented. Without a hint, an unmatched posting is reported as closed (below).
- **Closed/expired postings**: if the board API is reachable but the posting isn't listed, the role has
  **closed**. `fetch_jd.py` short-circuits (no wasted Chrome render) and **exits 4** with a `CLOSED:`
  message. Treat exit 4 as "role gone" — drop it or, if you have a live replacement title on the same
  board, re-fetch with `--title`. Never carry a dead URL as if it were fetched, and never invent a body.

## Step 5 — De-dupe + drop exclusions
Load `jds/_cache/web-seen.json` (create `[]` if absent; schema mirrors the other seen-caches:
`url, hash, title, company, first_seen, last_seen, last_triaged`).
- URL not in cache → new; add it.
- URL in cache AND hash matches → SKIP (count it as cache-skip).
- URL in cache AND hash differs → re-process as "edited JD", update the cached hash, flag it.
Then drop any posting whose **actual fetched title** matches an `excluded` taxonomy title or a
`search-defaults.exclusions.titles/companies` entry (the result-title check in Step 3 is coarse;
this is the authoritative pass on real JD text).
Append every kept posting to `web-pulled.jsonl` in the run dir.

## Step 6 — Title self-expansion (the distinguishing step)
For every kept posting, look at its **actual title** on the fetched JD:
- If the title (or a close normalization of it) is already in `confirmed` → fine.
- If it's in `excluded` → already dropped in Step 5.
- If it's a known `hypothesis` → bump confidence: record this posting as a real `seen_on`
  citation for that hypothesis.
- **If it's a NEW title not in the taxonomy at all**, judge whether the JD *content* genuinely
  matches the profile (archetype themes, seniority, scope — not just the words). If yes, it's a
  candidate to add.

Batch ALL new/seen-on candidates into ONE message and invoke the **capture-memory** skill
(`skills/capture-memory.md`) to ask the user, e.g.:
```
Found 2 titles I don't have in your role-taxonomy. Add them? (each cites a real posting)
1. "AI Solutions Lead" — <Company>, <City>. JD is roadmap-ownership for an AI platform (matches your AI-platform narrative).
   [add as confirmed · keep as hypothesis · exclude · skip]   src: <url> (2026-06-01)
2. "Principal PM, Platform" — confirms an existing hypothesis ("Platform Product Manager"). Promote to confirmed?
   src: <url> (2026-06-01)
```
On the user's answer, write back to `role-taxonomy.yaml` per the capture-memory routing rules:
- `add as confirmed` → new `confirmed` entry **with the real posting as `evidence`** (source_url + date).
- `keep as hypothesis` → new `hypotheses` entry, `status: unverified`, `seen_on` = this posting.
- `promote` a hypothesis → move it to `confirmed`, fill `evidence` from the cited posting.
- `exclude` → new `excluded` entry with a one-line `why_not`.
- `skip` → record nothing (but don't re-propose the same title next run if the user already skipped it).
Add a dated provenance comment on every write. **Never auto-add without the user's answer**, and
**never fabricate the evidence URL** — only the posting actually fetched this run counts.

## Step 7 — Rank
Score every kept posting against the resolved archetype using the **same rubric as `discover-jds`
Step 6** (keep the two skills consistent so triage sees comparable buckets):
- Title match (Senior/Lead/Staff/Principal/Group PM): +3
- Required themes present (AI, platform): +2 each
- Optional themes (FinTech, SaaS, GenAI, LLM, agentic): +1 each
- Seniority match (3–7 yrs for the user's 5+): +2 · Seniority mismatch (>8 yrs / Director+ required): −3
- Location match: +2 primary / +1 secondary
- Domain alignment (HR Tech / FinTech / conversational AI / fraud / KYC / agentic): +2
- Excluded company (not auto-dropped — e.g. a competitor): −2
- Comp (per `search-defaults.comp_handling`): ≥ floor +2 · below floor −1 · not listed 0
- **`unfetched` ⇒ NOT SCORED.** If you could not fetch and read the JD body, you may not assign a
  fit score or match claim of any kind — scoring an unread JD on "company/domain priors" is fabrication.
  Unfetched candidates go in a separate **NEEDS-FETCH backlog** (unscored, no fit %), never in the ranked list.

Normalize to 0–100 and bucket: `STRONG` (≥70), `MEDIUM` (40–69), `WEAK` (<40). One-line rationale
per JD (≤20 words, top 2 reasons).

**Theme tagging must be tight literal-text matching — not loose keyword priors (learned 2026-06-02).**
The theme tags that drive the rubric (`ai`, `platform`, `fintech`, `fraud`, `saas`, `health`, …) come
from matching the **fetched body text** against domain-specific regexes, and loose patterns silently
inflate scores. Two over-fires that bit us and the fix:
- **`fraud` (renamed from `kyc`)** must require real fraud/identity terms —
  `\bKYC\b|\bAML\b|anti-money|\bfraud\b|liveness|identity verification|sanctions|chargeback` — NOT
  generic "compliance / onboarding / identity", which fire on half of all enterprise JDs.
- **`health`** must require real healthcare terms —
  `healthcare|clinical|patient|hospital|\bpayer\b|medicare|medicaid|life sciences` — so it does NOT
  match marketing phrases like Salesforce's "Customer **Health** Platform".
Keep abbreviations (`\bAI\b`, `\bML\b`, `\bAPI\b`) case-sensitive so they don't match inside words.
A tag is only valid if the term is **literally present in the body you fetched** — never tag from the
company name, the domain, or a snippet. Re-tag from body text, not from a prior run's tags.

## Step 8 — Write the ranked shortlist (triage-compatible)
Write to `<run-dir>/ranked-list.md` in the **same numbered format triage-jds Mode A reads**:

```markdown
# JD Scout Run — <YYYY-MM-DD HH:MM>

**Resolved config**: archetype=<name>, booleans run=<id list>, archetype lens=<name>
**Swept**: <B> booleans · <Q> web queries · <C> candidate URLs (<X> collisions de-duped)
**Pulled**: <N> postings (<M> new, <K> edited, <S> cache-skips, <U> unfetched, <L> LinkedIn dropped)
**Taxonomy**: <A> titles added · <P> hypotheses promoted · <H> still pending (see role-taxonomy.yaml)
**Hiring leads**: <Z> (linkedin-posts-xray → hiring-leads.jsonl, for find-hiring-manager)

---

## STRONG MATCHES (recommend triage)

### [1] <Title> @ <Company> · <Location>
- Source: web (<domain>) · Posted: <date or N/A> · Match: STRONG (<score>)
- Rationale: <one line>
- URL: <link>
- Boolean: <boolean_id(s) that found it>   ← triage credits these on the fit-gate
- Status: NEW | EDITED-SINCE-LAST-PULL | UNFETCHED

### [2] ...

## MEDIUM MATCHES (your call)
### [N] ...

## WEAK MATCHES (probably skip)
### [N] ...

---

## SKIPPED FROM CACHE
- <count>: unchanged JDs already pulled in prior runs.

## NEEDS FETCH — body NOT retrieved (UNSCORED, no match claim)
- <count>: <one line each — title @ company, url, why-unfetched>
- These are NOT ranked and carry NO fit score. Fetch the body first, then they earn assessment.

## DETECTION / ERRORS
- WebSearch: <OK | partial — reason>
- fetch_jd failures: <count>
```

## Step 8b — Write yield stats back to booleans.yaml (the evolution loop's fuel)
For every boolean run this cycle, update its `stats` block in `memory/booleans.yaml` from the
REAL run tallies (never invent counts):
- `runs` += 1
- `results` += the number of distinct candidates it surfaced (via `found_by` credit; a candidate
  found by 3 booleans gives +1 `results` to each)
- `fetched` += the number of those candidates whose body actually fetched (≥120 words)
- `on_profile` — **leave unchanged here.** Scout does not know fit yet; `triage-jds` writes
  `on_profile` after the fit-gate (a fetched JD isn't "on profile" until triage says so).
- `yield` — leave `null` if `results` is still the only thing populated; it's recomputed as
  `on_profile / results` by triage once `on_profile` exists. Don't fake a yield from fetch rate.

Write a dated note in `booleans.meta.last_updated`. This is a numeric stats update only — do NOT
prune, retire, or add booleans here (that's `generate-booleans` Mode B, user-confirmed). If a
boolean returned zero results this run, still bump `runs` and record `results: 0` — a persistent
zero-yield boolean is exactly what the evolution loop needs to see to prune it.

## Step 9 — Report to user
```
Scout complete — see jds/_runs/<dir>-scout/ranked-list.md

STRONG: <N> | MEDIUM: <N> | WEAK: <N>
New: <N> | Edited: <N> | Cache-skips: <N> | Unfetched: <N>
Taxonomy: <A> titles added, <P> promoted — role-taxonomy.yaml now sweeps <X> titles.

Top 3 STRONG matches:
1. <Title> @ <Company> — <one-line>
2. ...
3. ...

Next step: reply with the JD numbers to triage, e.g.
"triage [1], [3], [7]"
```

## Hard safety rules — NEVER violate
1. **WebSearch-first; never invent a result.** Every listed posting must come from a real search
   hit that was actually fetched (or explicitly flagged `unfetched`). No snippet-only fabrication.
2. **LinkedIn: public guest endpoint ONLY — never log in or scrape authenticated pages.** The guest
   API is unauthenticated public data, so there is no account-flag risk; logged-in scraping is what
   gets accounts flagged, and this skill never does that. Don't bypass `linkedin_search.py`'s throttle.
3. **Respect the caps** (≤24 WebSearch calls/run, ≤3 LinkedIn pages/title, ≤3 runs/day). Don't hammer.
4. **Never auto-apply.** This skill discovers; the user applies.
5. **Never silently modify role-taxonomy.yaml.** Propose, get the user's answer, then write with a
   dated provenance comment. A title enters `confirmed` only with a real cited posting.
6. **Stop and report** on persistent WebSearch errors rather than degrading into guesses.

## How this differs from discover-jds (don't confuse them)
| | discover-jds | scout-jds |
|---|---|---|
| Sources | Naukri + curated `target-companies.yaml` | the open web via WebSearch |
| Driver | Chrome MCP (logged-in) | WebSearch tool + `fetch_jd.py` |
| Titles | `search-defaults.query_terms` (fixed) | `role-taxonomy.yaml` (living, self-expanding) |
| Account risk | real (LinkedIn-style flagging) | low (no logged-in scraping) |
| Output | `ranked-list.md` | `ranked-list.md` (same format → same triage handoff) |

Both feed `triage-jds`. Run whichever fits: scout for broad open-web coverage across title
variants, discover for deep pulls on a known shortlist of target companies. They are complementary.

## Anti-patterns — do NOT do these
- Don't score, rank, or claim a match for a posting you couldn't fetch. Unfetched ⇒ NEEDS-FETCH
  backlog, unscored. Scoring an unread JD on "company/domain priors" is fabrication — never do it.
- Don't add a title to the taxonomy without a real cited posting and the user's OK.
- Don't sweep `search: false` hypotheses (Program Manager / Product Owner / etc.) without the user
  opting them in for the run — they're high-false-positive on purpose.
- Don't treat a result-title match as proof; the authoritative title is on the fetched JD.
- Don't re-propose a title the user already chose to `skip`.
- Don't widen the query cap to chase volume. One page of strong matches beats four pages of noise.
- Don't produce go/no-go calls or tailored resumes here — those are the next two stages.
