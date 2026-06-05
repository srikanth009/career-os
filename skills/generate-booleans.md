---
name: generate-booleans
description: Stage 0 of the job-search pipeline — the boolean/X-ray query engine that feeds scout-jds and discover-jds. Reads memory/role-taxonomy.yaml (every title the user's role goes by) x memory/search-defaults.yaml (themes, locations, exclusions) and composes 10-15 platform-aware boolean search strings into memory/booleans.yaml. Also runs the boolean-EVOLUTION loop — after a scout run populates per-boolean yield stats, it prunes the queries that returned mostly noise and proposes sharper replacements (user confirms every change). Triggers on "generate booleans", "make search strings", "refresh my booleans", "prune the booleans", or `/generate-booleans`.
---

# Skill: generate-booleans

## What this skill does
The most upstream stage of the pipeline: it turns the user's role taxonomy and search
defaults into a small, sharp set of **boolean / X-ray search strings**, and then keeps that
set healthy over time by retiring the ones that don't pay off. It writes to one living file —
`memory/booleans.yaml` — which `scout-jds` (open web + LinkedIn guest) and `discover-jds`
(Naukri browser) consume directly.

The whole point is **signal-to-noise**: a few queries that reliably return on-profile,
fetchable postings beat a pile of broad ones that return aggregator spam. The evolution loop
is what gets us there — booleans earn their place by yield, not by looking clever.

## What this skill does NOT do
- Does NOT run any search itself. It only AUTHORS and CURATES query strings. `scout-jds` and
  `discover-jds` are what execute them and write back the yield stats.
- Does NOT fetch JDs, score them, or rank anything. Downstream stages do that.
- Does NOT invent yield numbers. A boolean's `stats` change ONLY when a real run reports real
  counts. Until then, `yield: null`.
- Does NOT silently add/retire booleans or silently edit `role-taxonomy.yaml`. Every prune,
  promote, or new-title proposal is shown to the user first (human-in-the-loop on every step).

## Pre-flight
Verify these exist; if any is missing, STOP and report:
- `career-os/memory/role-taxonomy.yaml`  (title source)
- `career-os/memory/search-defaults.yaml`  (themes / locations / exclusions / comp)
- `career-os/memory/booleans.yaml`  (the library — create from the seed schema if absent)

---

## MODE A — GENERATE / REFRESH  (default)

Use when the user wants to (re)build the active boolean set, or seed the library the first time.

### Step 1 — Load the inputs
- From `role-taxonomy.yaml`: collect `confirmed` entries with `search: true` and `hypotheses`
  with `search: true`. These are the **only** titles allowed into generated booleans. Titles
  with `search: false` (Program Manager, Product Owner, TPM, Solutions PM) and everything in
  `excluded` are OFF-LIMITS unless the user explicitly opts one in for this refresh.
- From `search-defaults.yaml`: `keyword_filters.required_themes` (AI, platform),
  `optional_themes` (FinTech, SaaS, GenAI, LLM, agentic), `location.primary/secondary`,
  `exclusions.titles/companies`, and `default_search.archetype_target` (the lens).

### Step 2 — Compose booleans across the four platforms
Aim for the **target band in `booleans.meta.target_active_count` (10-15 active)**. Spread them
so no single platform dominates. Each platform has its own syntax — respect it:

**`google-xray`** — Google search with `site:` operators. Highest fetch yield because the
results land on ATS/careers domains that `fetch_jd.py` can pull. Shapes:
- ATS X-ray (preferred): `(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:jobs.smartrecruiters.com OR site:*.myworkdayjobs.com) ("Senior Product Manager" OR "Lead Product Manager") (<themes>) (<locations>)`
- Use `"quoted phrases"` for multi-word titles, `OR` (caps) inside `( )` groups, `-term` /
  `-site:naukri.com` to exclude noise, and at most ~3 OR-groups (title group, theme group,
  location group) so Google doesn't truncate.

**`linkedin-guest`** — executed by `scripts/linkedin_search.py`. Its `keywords` param does NOT
handle big OR-booleans well, so make these **one title (+ maybe one theme word) per boolean**
and push the rest into `li_params`: `{ location, recent_days, experience: mid-senior, remote }`.

**`naukri-browser`** — executed by `discover-jds` in the logged-in Chrome session. `query` is
the Naukri search-UI keyword string (a title); put theme + cities + pages in `naukri_params`.
Naukri's SEO URL pattern is `<title-slug>-jobs-in-<city>` and pages append `-<n>`.

**`linkedin-posts-xray`** — `site:linkedin.com/posts ("we're hiring" OR "hiring a") ("Product
Manager") (<themes>) (<locations>)`. Intent is **hiring-sourcing**, not always a JD URL — it
surfaces hiring managers posting roles directly, feeding `find-hiring-manager`.

### Step 3 — Tag every boolean
Each entry carries: `id` (stable, kebab — `b-<platform-short>-<lens>`), `platform`, `intent`
(`ats-fetchable | title-coverage | theme-narrow | hiring-sourcing`), `query`, the platform
param block where relevant, `derived_from` (titles/themes/locations it was built from),
`stats` (all zero, `yield: null`), `status` (`active | candidate | retired`), `created`, `note`.

Mark anything experimental — a title variant NOT yet in the taxonomy (e.g. "Category Manager"
for GCC PM roles) — as `status: candidate`, not `active`, with a note on the false-positive risk.

### Step 4 — Echo the set to the user, then write
Show the proposed active set as a compact table (id · platform · intent · the query) and the
candidates separately. Get the user's OK / edits. Then write `memory/booleans.yaml`, preserving
any existing `stats` for booleans whose `id` already exists (a refresh must NOT wipe earned
yield). Add a dated provenance note in `meta.last_updated`.

---

## MODE B — EVOLVE / PRUNE  (the feedback loop)

Use after one or more scout runs have written real yield stats back into `booleans.yaml`
(the user says "prune the booleans", "refresh based on results", or it's the natural next step
after a scout run). This is what keeps the set sharp.

### Step 1 — Read the stats
For each `active` boolean read `stats: { runs, results, fetched, on_profile, yield }`.
Recompute `yield = on_profile / results` if results > 0 (defensive — scout should have set it).

### Step 2 — Classify each boolean
Using thresholds in `booleans.meta`:
- **PRUNE candidate**: `runs >= prune_min_runs` (default 2) AND `yield < prune_threshold_yield`
  (default 0.10). It's burning budget on noise.
- **KEEPER**: `yield >= keeper_threshold_yield` (default 0.25). Consider cloning its shape for a
  nearby theme/location to mine the vein.
- **WATCH**: everything else — too few runs to judge, or middling. Leave it.
- **fetched but zero on_profile** across >=2 runs → the query finds real JDs but they're the
  wrong roles: the title/theme mix is off, not the platform. Re-aim, don't just kill.

### Step 3 — Propose changes (NEVER auto-apply)
Present one batched message:
```
Boolean evolution — based on <N> run(s):

PRUNE (low yield, propose retiring):
  b-ats-fintech-pm   yield 0.04 (1 on-profile / 23 results, 2 runs)
    → replace with: b-ats-fintech-pm-v2  '(site:jobs.lever.co OR site:boards.greenhouse.io) ("Senior Product Manager") (payments OR "risk platform") (<your-city> OR <secondary-city>)'
    (narrower theme, dropped the noisy KYC/lending OR-terms, tightened to 2 cities)

KEEPERS (high yield, propose cloning):
  b-ats-platform-pm  yield 0.31 → clone for AI theme as b-ats-platform-pm-ai?

WATCH (leave as-is): b-li-staff-pm (1 run), b-posts-hiring-pm (1 run)
```
For each replacement, say **WHY the original underperformed** and **what the new shape changes**
(narrower theme, fewer OR-terms, different platform, tighter location). This rationale is the
evolution — a v2 that doesn't diagnose the v1 failure is just a reshuffle.

### Step 4 — Apply on the user's answer
- `retire` → move the boolean to the `retired:` list (keep it for the audit trail; do NOT delete),
  preserving its final stats, add `retired: <date>` and a one-line reason.
- `replace` → retire the old one AND add the v2 to `active` (fresh zero stats, `created: <date>`).
- `clone` → add the new variant to `active`.
- `keep` → no change.
Keep the active set inside `target_active_count`. Re-write `booleans.yaml`, bump `last_updated`.

### Step 5 — Taxonomy co-evolution
If a `candidate` boolean (e.g. `b-gcc-category-manager`) earned `on_profile >= 1` from a real
fetched posting, that's evidence the title variant maps to the profile. Flag it:
```
"Category Manager" returned a real on-profile posting (<url>, <date>).
Promote it: candidate boolean → active, AND propose adding "Category Manager" to role-taxonomy.yaml?
```
Promoting the TITLE into the taxonomy is `scout-jds`/`capture-memory`'s job (it owns taxonomy
writes) — this skill just raises the flag with the cited posting. Never write the taxonomy here.

---

## Report to user
```
Booleans <generated|evolved> — memory/booleans.yaml

Active: <N> (<google-xray> / <linkedin-guest> / <naukri-browser> / <posts-xray>)
Candidates: <N>   Retired this cycle: <N>

<MODE A>  New/updated booleans ready for the next scout + discover run.
<MODE B>  Pruned <P>, cloned <C>, <X> taxonomy-promotion flag(s) raised.

Next step: run the scout — "scout jobs" (open web + LinkedIn) and/or "discover jobs"
(Naukri, logged-in Chrome). They'll consume the active set and write yield back here.
```

## Anti-patterns — do NOT do these
- Don't generate booleans from `search: false` or `excluded` titles without an explicit per-run opt-in.
- Don't pack a `linkedin-guest` boolean with OR-heavy keywords — its API ignores them; one title each.
- Don't exceed ~3 OR-groups in a `google-xray` query — Google truncates and yield drops.
- Don't fabricate or hand-edit `stats`/`yield`. They change only from a real scout run's report.
- Don't retire or add a boolean without showing the user and getting an answer.
- Don't write to `role-taxonomy.yaml` from here — only flag promotions; the scout owns that write.
- Don't chase volume. The target band is 10-15 active; a sharp 10 beats a noisy 15.
