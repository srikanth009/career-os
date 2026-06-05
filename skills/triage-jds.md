---
name: triage-jds
description: Stage 2 of the discover → triage → tailor funnel. Takes a subset of JDs (chosen by user from a discover-jds ranked list, OR pasted manually) and produces a deep triage report per JD — archetype, match strength, evidence matches, gaps, anticipated objections, tailoring effort, go/no-go recommendation. Does NOT tailor a resume. Triggers when user says "triage [N], [N], ..." after a discover run, or "triage this JD" with pasted text.
---

# Skill: triage-jds

## What this skill does
For each JD provided, produces a structured triage report. The report is decision-support: "should I spend the energy to tailor this?" It does NOT produce a resume.

## What this skill does NOT do
- Does NOT pull JDs from the internet (that's `discover-jds`).
- Does NOT produce a tailored resume (that's `tailor-resume`).
- Does NOT modify memory *by default* — triage is a fast pass across several JDs, so it surfaces gaps rather than stopping to interview the user on each one. Exception: if the user chooses to resolve a verifiable gap on the spot, invoke `capture-memory` to persist the answer (see Step 4).

## Inputs accepted
**Mode A — From a discover-jds run:**
User says: `triage [1], [3], [7]` (numbers refer to entries in the most recent `ranked-list.md`).
Or: `triage [1], [3], [7] from <run-dir>` to target a specific run.

**Mode B — JD URLs or pasted text:**
User provides 1+ job URLs and/or pasted JD text. For each URL, fetch with the bundled scraper before triaging — do NOT ask the user to paste unless the fetch fails:
```bash
python3 career-os/scripts/fetch_jd.py "<url>" --debug
```
This handles Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Recruitee, JSON-LD career pages, and JS-rendered sites. Only LinkedIn auth-walled URLs typically need a paste — try the fetcher first. Skill creates a transient run dir under `jds/_runs/<YYYY-MM-DD-HHMMSS>-manual/` with the fetched/pasted JD text saved per JD.

## Pre-flight: memory check
Verify the same memory files as `tailor-resume`:
- `memory/profile.yaml`
- `memory/projects/*.yaml`
- `memory/narratives/*.md`
- `memory/frameworks.yaml`
- `memory/stories.yaml`
- `memory/open-questions.yaml`

If missing, STOP and report.

## Per-JD process

### Step 1 — Parse the JD
Extract the same structured fields as `tailor-resume.md` Step 2 (Role, Domain, Must-haves, Nice-to-haves, Tech stack, Soft signals, Credential asks). Store as a JSON-ish block in the per-JD output.

### Step 2 — Select archetype
Read all three `narratives/*.md`. Match `## When to use` criteria. Pick best fit.
- If two archetypes tie, list both as "primary / alternative" with rationale.

### Step 3 — Evidence matching
Traverse `projects/*.yaml`. For each project:
- Compare `tags` against JD must-haves + nice-to-haves + tech stack.
- Compute coverage: which JD requirements have ≥1 matching project, which have none.

Bucket projects into:
- **Direct match** (covers a must-have)
- **Adjacent match** (covers a nice-to-have or related theme)
- **Not relevant**

### Step 4 — Gap detection
List every JD must-have that has NO direct or adjacent match in memory.

For each gap:
- Identify closest evidence (if any), with confidence flag.
- Cross-reference `open-questions.yaml.missing_evidence_categories` — is this a known gap?
- Classify gap severity:
  - **Hard gap** — JD must-have, no evidence, no nearby story → likely DQ
  - **Soft gap** — JD must-have, weak evidence, can be framed → tailoring challenge
  - **Verifiable gap** — JD must-have, evidence exists but in low-confidence layer → surface it. If the user answers on the spot, invoke `capture-memory` to write it back so the later tailoring run treats it as confirmed.

### Step 5 — Anticipated objections
Read `stories.yaml.anticipated_objections`. For each, check `surfaces_when` against the JD requirements / archetype choice. List any that would surface for this JD.

### Step 6 — Tailoring effort estimate
Heuristic:
- 0 hard gaps + ≥3 direct matches → **LOW** (~10-15 min tailoring)
- ≤1 hard gap OR <3 direct matches → **MEDIUM** (~25-35 min tailoring + 1 round of user clarification)
- ≥2 hard gaps OR archetype mismatch → **HIGH** (substantial framing work; consider whether worth pursuing)

### Step 7 — Recommendation
Compose a go / no-go / borderline call:
- **GO** — strong archetype fit, few gaps, defensible. Tailor it.
- **BORDERLINE** — defensible but with caveats. Tailor only if the role itself is highly desirable.
- **NO-GO** — too many hard gaps OR archetype is too far from any narrative. Skipping is the rational choice.

The recommendation is a recommendation, NOT a decision. User decides.

## Output format

Write to: `<run-dir>/triage-<jd-slug>.md` for each JD.

```markdown
# Triage: <Title> @ <Company>

**Source**: <board/pasted>
**URL**: <link or N/A>
**Triaged**: <YYYY-MM-DD HH:MM>

## Parsed requirements
<analysis block>

## Archetype
- **Recommended**: <name>
- **Rationale**: <2 sentences>
- **Alternative**: <name or "none">

## Evidence matching
**Direct matches** (covers must-haves):
- <project-slug> — <one-line why>

**Adjacent matches** (covers nice-to-haves):
- <project-slug> — <one-line why>

## Gaps
**Hard gaps** (no evidence in memory):
- <requirement> — <closest-available or "nothing close">

**Soft gaps** (weak evidence, can be framed):
- <requirement> — <approach to framing>

**Verifiable gaps** (low-confidence, ask user):
- <requirement> — <which open-question to resolve>

## Anticipated objections (from stories.yaml)
- <prompt> — <risk_level>
- ...

## Tailoring effort
**Estimate**: <LOW | MEDIUM | HIGH>
**Reason**: <one sentence>

## Recommendation
**<GO | BORDERLINE | NO-GO>**
<2-sentence rationale>

## If GO
- Frameworks to surface: <candidate-specific frameworks from frameworks.yaml | none>
- Education to include: <which credentials per education.yaml conditional rules>
- Top 5 bullets to retrieve: <project-slug : altitude>
- Stories to prep for interview: <story-slug from stories.yaml>
```

## Summary report
After processing all JDs, write a summary to `<run-dir>/triage-summary.md`:

```markdown
# Triage Summary — <timestamp>

| # | Company | Title | Archetype | Effort | Recommendation |
|---|---------|-------|-----------|--------|----------------|
| 1 | ... | ... | ... | LOW | GO |
| 2 | ... | ... | ... | HIGH | NO-GO |

## GO list (recommend tailoring):
1. ...

## BORDERLINE (your call):
1. ...

## NO-GO (recommend skipping):
1. ...
```

## Report to user
```
Triaged <N> JDs — see jds/_runs/<dir>/triage-summary.md

GO: <count> | BORDERLINE: <count> | NO-GO: <count>

GO list:
1. <Title> @ <Company> — LOW effort
2. ...

Next step: reply with the JD numbers to tailor, e.g.
"tailor [1], [3]"
```

## Anti-patterns

- Don't recommend GO just because the archetype matches. Hard gaps matter more.
- Don't recommend NO-GO based on tailoring effort alone. A high-effort tailoring for a dream role is still worth it. The recommendation reflects defensibility, not laziness.
- Don't silently treat low-confidence evidence as confirmed. Surface it.
- Don't invent matches. If a project doesn't have a relevant tag, it doesn't match — even if "logically it kind of does."
- Don't produce a tailored resume in this skill. That's the next stage's job.
