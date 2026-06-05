---
name: discover-jds
description: Pull job descriptions from Naukri + a curated list of target-company career pages via Chrome MCP, de-dupe against cache, and produce a ranked one-line-per-JD shortlist. Stage 1 of a 3-stage funnel (discover → triage → tailor). LinkedIn is intentionally NOT scraped here — use LinkedIn's saved-search email alerts (see memory/notes/linkedin-alerts.md). Triggers when user says "find jobs", "pull JDs", "discover jobs", or runs `/discover-jds`.
---

# Skill: discover-jds

## ⚠️ ENVIRONMENT REQUIREMENTS — READ FIRST

This skill requires a Chrome MCP that can navigate to arbitrary career-page domains. There are two viable MCP modes; **most environments fail without explicit setup**.

### Mode A — Control Chrome (RECOMMENDED for full career-page scraping)
Connects to a running Chrome instance via Chrome DevTools Protocol. Sees your existing logged-in sessions. Works with any domain Chrome can reach.

**Setup**:
1. Quit any running Chrome instance (Cmd+Q on macOS), OR plan to use a separate user-data-dir.
2. Launch Chrome with the remote-debugging-port flag:

   **macOS — full restart of main Chrome** (quit Chrome first):
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222
   ```

   **macOS — separate debugging instance** (keep main Chrome open):
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 \
     --user-data-dir=/tmp/chrome-debug
   ```
   (Note: the separate instance starts with no saved logins; you'll re-login to LinkedIn / Naukri in it once. The session persists for the lifetime of that user-data-dir.)

3. Log in to: LinkedIn (if you ever scrape there), Naukri, and any company career sites that need auth.
4. Verify Control Chrome can reach content by running a `get_page_content` on any tab. If it returns content, you're good.

### Mode B — Claude in Chrome
Runs in an isolated tab group with its own session (no inherited logins). Has a per-domain allowlist that must be granted explicitly per origin. Cannot read tabs outside its group.

**Reality check**: Most company career pages will be blocked unless they're on a previously-granted domain. `jobs.lever.co` is commonly approved. Greenhouse, Workday, LinkedIn, Naukri, and most custom-ATS domains are typically blocked.

**When to use Mode B**: Only when Mode A is unavailable AND you're scraping Lever-hosted JDs (or another domain you've explicitly granted in the Claude in Chrome extension UI).

### If neither mode works for a given domain
- Do NOT pretend the scrape worked.
- Skip that company, log it in the run output, tell the user.
- Fall back to manual paste workflow (user pastes the JD text or URL → use `triage-jds` directly).

### Pre-flight tool detection (skill MUST run this first)
1. Call any Control Chrome metadata tool (`list_tabs`). If it returns tabs AND `get_page_content` on any tab returns text, Mode A is live — prefer it.
2. Else call `mcp__Claude_in_Chrome__list_connected_browsers`. If that returns a browser, Mode B is live with limited reach.
3. Else STOP and tell user neither MCP is connected. Suggest one of the setup paths above.

## What this skill does
1. Reads `memory/booleans.yaml` for the `active` **`naukri-browser`** booleans (the Naukri
   query source, built by generate-booleans) and `memory/search-defaults.yaml` for filters +
   safety limits.
2. Reads `memory/target-companies.yaml` for company-specific career-page targets.
3. Drives a Chrome MCP (Claude in Chrome OR Control Chrome — use whichever is connected).
4. Pulls up to N JDs from **Naukri** (one search per naukri-browser boolean) AND from each entry
   in **target-companies.yaml** (company-page-based), throttled to human-paced.
5. De-dupes against `jds/_cache/<source>-seen.json` using URL + JD-text-hash.
6. Produces a single ranked Markdown shortlist with one line per JD (tagging each with the
   `boolean_id` that surfaced it).
7. Writes per-boolean yield stats (`runs`/`results`/`fetched`) back to `booleans.yaml` — same
   evolution-loop contract as scout-jds (triage adds `on_profile` later).
8. User picks the ones they want → next stage is `triage-jds`.

## What this skill does NOT do
- Does NOT scrape LinkedIn. (Use LinkedIn's own job-alert system — see `memory/notes/linkedin-alerts.md`.)
- Does NOT deep-evaluate each JD against memory (that's `triage-jds`).
- Does NOT tailor a resume (that's `tailor-resume`).
- Does NOT auto-apply to any job.
- Does NOT bypass safety limits even if user asks.
- Does NOT retry on detection signals.

## What this skill does NOT do
- Does NOT deep-evaluate each JD against memory (that's `triage-jds`).
- Does NOT tailor a resume (that's `tailor-resume`).
- Does NOT auto-apply to any job.
- Does NOT bypass safety limits even if user asks.
- Does NOT retry on detection signals.

## Pre-flight: required artifacts
- `career-os/memory/booleans.yaml` (the Naukri query source — run generate-booleans first if it has no active naukri-browser entries)
- `career-os/memory/search-defaults.yaml` (config)
- `career-os/memory/target-companies.yaml` (company list — may be empty; that's fine, skill skips company loop)
- `career-os/memory/narratives/*.md` (for the archetype context used in ranking)
- A Chrome MCP available at runtime. Discover by tool prefix: `mcp__Claude_in_Chrome__*` OR `mcp__Control_Chrome__*`. Prefer Claude in Chrome (richer API). If neither is connected, STOP and tell user to enable a Chrome MCP.

## Pre-flight: rate-limit check
Read directory listing of `career-os/jds/_runs/`. Count entries with today's date prefix (`YYYY-MM-DD`). If count >= `safety.max_runs_per_day` (default 3), STOP and tell user. Explain: rate limit is intentional, prevents LinkedIn account flagging.

## Step 1 — Load config + the Naukri booleans
Read `memory/booleans.yaml` and collect the `active` entries with `platform: naukri-browser`.
Each gives a `query` (the Naukri search keyword/title) plus a `naukri_params` block
(`keyword_theme`, `locations`, `pages`). These define the Naukri searches to run in Step 4 —
carry each boolean's `id` forward so Step 4b can write yield back. If there are zero active
naukri-browser booleans, tell the user to run `generate-booleans` first (don't invent searches).
Also read `memory/search-defaults.yaml` for `exclusions`, `comp_handling`, safety limits, and the
archetype lens. Accept user overrides passed in the invocation message (e.g., "discover jobs but
only Bangalore, only AI roles") — apply on top of file defaults. Echo the resolved config
(boolean ids being run + filters) back to the user before proceeding.

## Step 2 — Create run directory
Create: `career-os/jds/_runs/<YYYY-MM-DD-HHMMSS>/`
Write: `search-config.yaml` (the resolved config used for this run — for reproducibility).

## Step 3 — Load cache
Read `jds/_cache/linkedin-seen.json` and `jds/_cache/naukri-seen.json` if they exist. Cache schema:
```json
[
  {
    "url": "https://...",
    "hash": "sha256-prefix-16-chars",
    "title": "...",
    "company": "...",
    "first_seen": "YYYY-MM-DD",
    "last_seen": "YYYY-MM-DD",
    "last_triaged": null
  }
]
```
If cache files don't exist, create empty arrays.

## Step 4 — Pull from Naukri (if enabled)

### Navigation — loop over the naukri-browser booleans
Run each `active` naukri-browser boolean from Step 1 as its own Naukri search:
1. Build the SEO search URL from the boolean's `query` (title) + `naukri_params`:
   `https://www.naukri.com/<title-slug>-jobs-in-<city>` (e.g. `senior-product-manager-jobs-in-bengaluru`),
   one per city in `naukri_params.locations`. Paginate by appending `-<n>` up to `naukri_params.pages`.
   Apply `keyword_theme` (e.g. "AI", "platform") via the Naukri keyword box / `&keyword=` where possible.
2. Wait 3-5s for page load.
3. Detection-signal check (see below).
Tag every card harvested from a given search with that boolean's `id`. The per-platform JD cap and
all safety limits apply across the WHOLE run, not per boolean — don't let multiple booleans blow the
cap. De-dupe cards on the Naukri job URL across booleans; record ALL boolean ids that found a card
(`found_by`) so each gets `results` credit in Step 4b.

### Detection-signal checks (run after every page interaction)
Check page text/HTML for any of `safety.detection_signals`. If matched → STOP IMMEDIATELY. Do NOT retry. Save partial results. Tell user. Mark this source as "skipped due to detection" in the run output.

### Verified extraction recipe (Claude in Chrome, logged-in session — confirmed working 2026-06-01)
Naukri is fully client-side rendered and Akamai/reCAPTCHA-gated, so a plain HTTP fetch (incl.
`fetch_jd.py`) returns `406 recaptcha required` and no job data. It only works inside a **real
logged-in browser** where the page's own JS runs. Don't click each card (slow + detection-prone) —
read the whole result page in one DOM query, then navigate straight to JD URLs.

**a. Harvest the search-results page** (after navigating to the search URL), via `javascript_tool`:
```js
[...document.querySelectorAll('div.srp-jobtuple-wrapper')].map(c=>{const q=s=>c.querySelector(s);
  const t=q('a.title');return {title:t?.innerText?.trim(), url:t?.href?.split('?')[0],
  company:q('a.comp-name')?.innerText?.trim(), exp:q('span.expwdth')?.innerText?.trim(),
  loc:q('span.locWdth')?.innerText?.trim(), sal:q('span.sal-wrap span')?.innerText?.trim()};}).filter(x=>x.title)
```
Gives ~20 cards/page with the real JD `url`. Filter to on-profile titles client-side to keep output small.

**b. Pull each JD body** — `navigate` to the card's `url`, then:
```js
(()=>{const q=s=>document.querySelector(s);return {title:q('h1')?.innerText?.trim(),
  comp:q('.styles_jd-header-comp-name__MvqAI a')?.innerText?.trim(),
  exp:q('.styles_jhc__exp__k_giM')?.innerText?.trim(),
  loc:q('.styles_jhc__location__W_pVs')?.innerText?.trim(),
  body:q('.styles_JDC__dang-inner-html__h0K4t, section.job-desc, div.dang-inner-html')?.innerText?.trim()};})()
```
(Naukri rotates hashed class suffixes periodically; if a selector misses, fall back to `h1` + the
densest `div`/`section` text block. The `dang-inner-html` substring is the stable JD-body marker.)

**Browser robustness (learned 2026-06-02 — these failure modes WILL recur):**
- **Renderer freeze / CDP timeout.** `javascript_tool` sometimes returns `Runtime.evaluate timed out
  after 45000ms` and a follow-up errors with "page may be loading / unresponsive". Recovery: issue a
  `navigate` to the next JD URL (this resets the renderer), then re-run the extraction. A light probe
  (`get_page_text`) confirms the page is responsive again before retrying the heavier JS. Don't sit in
  a retry loop on a frozen tab — navigate away and continue.
- **Return-string truncation.** `javascript_tool` truncates returned strings at ~1000 chars, so a full
  JD body won't survive the round-trip. Don't pass raw bodies back through the tool. Instead **compute
  what you need inside the page** (e.g. word count + theme tags) and return only the compact result.
- **Theme tagging in-browser (mirror scout-jds Step 7's tight regexes).** Tag from the body's
  `innerText`, requiring real domain terms — `fraud:/\bKYC\b|\bAML\b|anti-money|\bfraud\b|liveness|
  identity verification|sanctions|chargeback/i`, `health:/healthcare|clinical|patient|hospital|\bpayer\b|
  medicare|medicaid|life sciences/i` — so generic "compliance" / "customer health" wording does NOT
  fire. Keep `\bAI\b`/`\bML\b`/`\bAPI\b` case-sensitive. Same never-invent rule: a tag is valid only if
  the term is literally in the body you read.
- **localStorage as a cross-navigation accumulator.** `window` vars are wiped on every navigation, but
  `localStorage` persists across same-origin (`naukri.com`) page loads. To collect results across the
  per-JD navigation loop, read-modify-write a single `localStorage` key (e.g. `nk_themes`) each page,
  then read the whole accumulated object once at the end.

### Result extraction loop
For each JD in the result list, until `safety.per_platform_jd_cap` (default 20) reached:
1. Sleep random 3-5s between JD navigations (human-paced; protects the user's real account).
2. Navigate to the JD `url` from step (a) and extract via the step (b) query.
3. Extract: `url`, `title`, `company`, `location`, `posted_date`, `jd_text` (full description), `seniority_signal` (years required), `salary_range` (if shown).
4. Compute `hash = sha256(jd_text)[:16]`.
5. Check cache (`jds/_cache/naukri-seen.json`):
   - If URL not in cache → new JD, add to results, append to cache.
   - If URL in cache AND hash matches → SKIP (note count).
   - If URL in cache AND hash differs → re-process as "edited JD", update cache entry hash, mark in output.
6. Append to `naukri-pulled.jsonl` in the run directory.

### Exit conditions
- Cap reached
- No more results on page (and no pagination obvious)
- Detection signal hit (STOP immediately)
- Tool error (STOP, save partial, report)

## Step 4b — Write Naukri yield stats back to booleans.yaml
For every naukri-browser boolean run this cycle, update its `stats` in `memory/booleans.yaml` from
the REAL tallies (never invent): `runs` += 1, `results` += distinct cards it surfaced (via
`found_by` credit), `fetched` += those whose JD body actually extracted (≥120 words via the Step 4b
DOM recipe). Leave `on_profile` and `yield` for `triage-jds` to fill — discover doesn't know fit
yet. If a detection signal stopped a boolean early, still bump `runs` and record whatever `results`
it got before stopping (note the early stop). Same contract as scout-jds Step 8b — do NOT prune or
add booleans here (that's generate-booleans Mode B, user-confirmed).

## Step 5 — Pull from target-company career pages

Read `memory/target-companies.yaml`. For each company entry:

### Per company
1. Open `careers_url`.
2. Wait 3-5s.
3. Detection-signal check.
4. Parse listings according to `platform` hint:
   - `greenhouse` → typical structure: list of `<a href="/companies/<slug>/jobs/<id>">` under main content.
   - `lever` → list of `<a href="https://jobs.lever.co/<company>/<uuid>">` under postings.
   - `workday` → JavaScript-heavy; look for `[data-automation-id="jobTitle"]` elements.
   - `smartrecruiters` → list under `[data-test="job-title-link"]`.
   - `custom`/`other` → use accessibility tree extraction (`read_page` with `filter: interactive`) and find job-list-like patterns.
5. For each listing:
   - Apply `keywords` filter if specified (title must contain at least one keyword).
   - Apply `safety.per_platform_jd_cap` per company (default 20 — most career pages won't exceed this anyway).
   - Click into the JD page. Sleep 3-5s.
   - Extract: `url`, `title`, `company` (from entry name), `location`, `posted_date` (if available), `jd_text`.
   - Compute hash, check `jds/_cache/companies-seen.json`, dedupe/edit logic same as Naukri.
   - Append to `companies-pulled.jsonl` with a `tier` field copied from the company entry.

### Cross-company safety
- Sleep 5-10s BETWEEN companies (more conservative than within-company).
- If 3 consecutive companies return zero new JDs, STOP (likely cache-warm; nothing new).
- If a single company throws a detection signal, skip that company but continue with the rest.

### If `companies: []` is empty
Skip Step 5 entirely. Log: "No target companies configured — skipping company-page pull."

## Step 6 — Rank
For every JD pulled in this run (new OR edited; SKIP the unchanged):
1. Apply `exclusions` from config (drop matching titles / companies).
2. Score relevance against the resolved archetype target (default: platform-staff-pm) using these signals from the JD text:
   - **Title match** (Senior/Lead/Staff/Principal/Group PM): +3
   - **Required themes** present (AI, platform): +2 each
   - **Optional themes** present (FinTech, SaaS, GenAI, LLM, agentic): +1 each
   - **Seniority match** (years required overlaps your YoE band, e.g. 3-7y for a 5+y candidate): +2
   - **Seniority mismatch** (>8 years required, or "Director+ required"): -3
   - **Location match**: +2 primary / +1 secondary
   - **Domain alignment** (mentions HR Tech / FinTech / conversational AI / fraud / KYC / agentic): +2
   - **Excluded company** (but not auto-dropped — e.g., direct competitor): -2
   - **Target-company tier bonus**:
     - `tier: must-apply` → +3
     - `tier: interested` → +1
     - `tier: watch` → 0
   - **Compensation signal** (from `search-defaults.yaml.default_search.comp_handling`):
     - JD lists comp AND comp >= `floor_for_bonus_ranking_lpa` → +2
     - JD lists comp AND comp < floor → -1 (not auto-dropped)
     - JD does NOT list comp → 0 (no penalty for absence — most ATSes don't publish)

   Normalize scores into 0-100 scale for display. Don't pretend false precision: report as buckets — `STRONG` (>=70), `MEDIUM` (40-69), `WEAK` (<40).

3. Generate a one-line rationale per JD: ≤ 20 words, citing the top 2 reasons for the bucket.

## Step 7 — Write the ranked shortlist
Write to: `<run-dir>/ranked-list.md`

Format:
```markdown
# JD Discovery Run — <YYYY-MM-DD HH:MM>

**Resolved config**: archetype=<name>, query=<terms>, location=<list>
**Pulled**: <N> from LinkedIn, <N> from Naukri (<M> new, <K> edited, <L> skipped from cache)

---

## STRONG MATCHES (recommend triage)

### [1] <Title> @ <Company> · <Location>
- Source: Naukri | <company-careers> · Posted: <date> · Match: STRONG (score)
- Rationale: <one line>
- URL: <link>
- Boolean: <boolean_id(s) that found it, or "company-page" for target-company pulls>
- Status: NEW | EDITED-SINCE-LAST-PULL

### [2] ...

## MEDIUM MATCHES (your call)

### [N] ...

## WEAK MATCHES (probably skip)

### [N] ...

---

## SKIPPED FROM CACHE
- <count>: unchanged JDs already pulled in prior runs.

## DETECTION / ERRORS
- LinkedIn: <OK | STOPPED at JD #N due to <signal>>
- Naukri: <OK | ...>
```

## Step 8 — Report to user

Output a concise summary in chat:
```
Discovery complete — see jds/_runs/<dir>/ranked-list.md

STRONG: <N> | MEDIUM: <N> | WEAK: <N>
New: <N> | Edited: <N> | Skipped from cache: <N>

Top 3 STRONG matches:
1. <Title> @ <Company> — <one-line>
2. ...
3. ...

Next step: reply with the JD numbers you want to triage, e.g.
"triage [1], [3], [7]"
```

## Hard safety rules — NEVER violate

1. **Stop on first detection signal.** Never retry. Never "try a different approach to get around it." The signal is the system telling you to stop. Respect it.
2. **Never exceed per-platform JD cap in a single run.** If user says "pull 50", remind them of the limit. Suggest spreading across days.
3. **Never run more than `max_runs_per_day` times.** Check `jds/_runs/` directory listing for today's runs first.
4. **Never bypass cache.** Cache exists to reduce request volume, which reduces detection risk. The only legitimate cache-bypass is `safety.cache.invalidation.force_reprocess: true`, set explicitly.
5. **Never paginate aggressively.** Stop at page 1-2 of results unless explicitly asked for "more". One page of 20 strong results beats four pages of mediocre ones.
6. **Never click "Easy Apply" or any apply button.** This skill discovers, it does not act.
7. **Never store the user's LinkedIn cookies or session tokens.** The browser handles this. The skill only reads what the rendered page exposes.

## When the Chrome MCP is unavailable
Tell the user clearly:
```
This skill requires an active Chrome MCP (Claude in Chrome OR Control Chrome).
I checked and neither appears connected to this session.

To enable:
1. Make sure Claude in Chrome (or equivalent) is installed and authorized.
2. Confirm the MCP shows up in your tool list.
3. Re-invoke this skill.

Until then, paste JDs manually and use the triage-jds skill directly.
```

## What "edited JD" means and why we care
When a posted JD's text changes (company tweaked requirements, added "must have GenAI experience" two weeks in), the relevance scoring and triage recommendations may change. Re-evaluating those is high-signal. The cache catches this via the hash diff.

## Tuning over time
After a few runs, you'll discover that the default scoring weights either over-recommend or under-recommend. When that pattern is clear:
1. Don't silently tweak weights — open `search-defaults.yaml` and adjust deliberately.
2. Or, log the misclassification in `open-questions.yaml` for later attention.
The system improves by being honest about what it gets wrong.
