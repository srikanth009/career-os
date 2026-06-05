---
name: tailor-resume
description: Tailor the candidate's resume (identity read from memory/profile.yaml) to a specific job description using the career-os memory layer. Triggers when user provides a JD (URL or pasted text) and asks for a tailored resume, OR when user runs `/tailor-resume`. Accepts a job URL directly and fetches it via scripts/fetch_jd.py (Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Recruitee, JSON-LD career pages, JS-rendered sites); only asks for a paste if the fetch fails.
---

# Skill: tailor-resume

## What this skill does
Takes a job description as input. Produces:
1. A tailored resume (markdown, rendered from `templates/resume.md`)
2. A `decisions.md` defensibility log (which bullet was chosen, why, what evidence backs it)
3. A `gaps.md` list (JD requirements with no matching evidence — surfaced to user, never invented)

**Never invents metrics, projects, or claims not present in memory.** When evidence is missing, asks the user instead.

## Pre-flight: memory check
Before doing anything, verify these files exist:
- `career-os/memory/profile.yaml`
- `career-os/memory/education.yaml`
- `career-os/memory/roles/*.yaml`
- `career-os/memory/projects/*.yaml`
- `career-os/memory/frameworks.yaml`
- `career-os/memory/stories.yaml`
- `career-os/memory/open-questions.yaml`
- `career-os/memory/narratives/*.md`
- `career-os/templates/resume.md`

If any are missing, stop and tell the user. Don't proceed with partial memory.

## Step 1 — Receive the JD

A URL is the default, expected input. Do NOT ask the user to paste JD text by hand — that is the failure mode this step exists to remove. Use the bundled fetcher:

```bash
python3 career-os/scripts/fetch_jd.py "<url>" --out /tmp/career-os-jd.txt --debug
```

`fetch_jd.py` is ATS-agnostic and tiered (run it for ANY job URL):
- **Tier 0** — public JSON APIs for Greenhouse, Lever, Ashby, SmartRecruiters, **Workday**, Recruitee (cleanest, no browser).
- **Tier 1** — schema.org JobPosting (JSON-LD) on most company career pages.
- **Tier 2** — readability extraction from static HTML.
- **Tier 3** — headless local Chrome render for JS-heavy sites, then re-runs Tiers 1+2.

Rules:
- For Greenhouse / Lever / Ashby / SmartRecruiters / **Workday** / Recruitee / company career pages → just run the fetcher. These used to be refused; they are now supported. Do not refuse them.
- Capture the fetcher's stdout/`/tmp/career-os-jd.txt` as the JD text and carry it forward. In Step 11 it becomes `jd.txt` verbatim.
- **Fallback, not first resort**: only ask the user to paste if the fetcher exits non-zero OR returns < 120 words (it prints the winning tier to stderr with `--debug`, so you can see what happened). LinkedIn job URLs are the main case that still needs a paste, because they are auth-walled — try the fetcher first anyway, and only fall back when it genuinely returns nothing usable.
- Never fabricate a JD from a title or search snippet. If the fetch truly fails, ask for a paste — that is the ONLY time you ask.

If pasted/fetched JD text is < 200 words, ask the user to confirm it's complete. Short JDs often hide requirements.

### When a fuller JD replaces an earlier blurb
If you already tailored against a short recruiter blurb and the user later provides the **full JD** (a longer paste or a PDF), treat it as a fresh tailoring, not a touch-up:
1. Overwrite `jd.txt` with the full text and re-run Step 2 analysis from scratch.
2. Re-run the structure-mirroring pass (Step 7) — a full JD usually exposes named pillars the blurb didn't.
3. Re-score (Step 11a) and record the delta in `ats-score.md` as a dated revision note.
4. A fuller JD often *raises* the bar (more explicit hands-on / credential asks) rather than lowering it — re-read for new disqualifiers before assuming the job got "easier."

## Step 2 — Extract requirements (deterministic structure)
Parse the JD into a structured `analysis.md` with these sections:

```
## Role
- Title: <exact title>
- Company: <name>
- Location: <city / remote>
- Seniority: <Junior | Mid | Senior | Staff | Director> (your inference)

## Domain
- Industry: <e.g., FinTech, HR Tech, AI Platforms>
- Sub-domain: <e.g., KYC, conversational AI>

## Must-have requirements
- <bulleted list, verbatim where possible>

## Nice-to-have requirements
- <bulleted list>

## Tech stack signals
- <explicit technologies named in JD>

## Soft signals
- <e.g., "thrive in ambiguity", "executive presence", "0-to-1 builder">

## Explicit credential asks
- MBA: <yes / no / preferred>
- Masters CS/AI/ML: <yes / no / preferred>
- Specific certifications: <list>
```

## Step 3 — Select narrative archetype
Read all three `narratives/*.md` files. For each, check `## When to use` against the JD analysis. Pick the strongest match.

Output the selection with rationale:
```
Selected archetype: <generic-pm | ai-ml-pm | platform-staff-pm>
Rationale: <2-3 sentences citing specific JD signals>
Alternatives considered: <other archetypes + why rejected>
```

**If two archetypes seem equally strong, ASK the user before proceeding.** Don't silently pick.

## Step 4 — Retrieve relevant memory
Read all `projects/*.yaml` files. For each project, compute a relevance score against the JD by checking:
- Tag overlap with JD must-haves / nice-to-haves / tech stack
- Domain alignment
- Whether the selected archetype emphasizes or de-emphasizes this project

Produce a ranked list:
```
High relevance (full bullet treatment, 2-3 bullets each):
- <project-slug>: <one-line why>

Medium relevance (1 bullet each):
- <project-slug>: <one-line why>

Low relevance (consider dropping):
- <project-slug>: <one-line why>
```

## Step 5 — Surface gaps BEFORE composing
For every JD must-have that has no matching project / bullet / framework in memory, write a gap entry:

```
GAP: <JD requirement>
Closest evidence: <whatever's nearest, with confidence>
Action: <one of: "ASK USER", "USE CLOSEST WITH CAVEAT", "OMIT FROM RESUME">
```

If any gap action is "ASK USER", invoke the **capture-memory** skill (`skills/capture-memory.md`): batch ALL blocking gaps into ONE chat message, get the user's answers, and **write each answer back into the correct memory file before composing** (new evidence → its project/role file; a confirmed "I don't have that" → `open-questions.yaml` as a resolved-gap so it's never re-asked). Do not proceed to composition until the user has answered or explicitly said "skip."

This step is non-negotiable. The system's job is to refuse to invent — and to *persist* whatever it learns so the same question is never asked twice.

## Step 6 — Check open-questions.yaml
Cross-reference the JD requirements against `open-questions.yaml`. If the JD requires evidence from a low-confidence area (e.g., +35% HR case resolution, attribution-uncertain), flag it:

```
LOW-CONFIDENCE EVIDENCE USED:
- <metric>: <current source-confidence>
- Recommendation: <whether to use with caveat or ask user to verify>
```

If a low-confidence metric is load-bearing for this resume, fold its provenance question into the same **capture-memory** batch from Step 5 (one message, not a second round). When the user confirms provenance/attribution, write it back to the metric's source file and bump `source_confidence` — so the next tailoring treats it as confirmed.

## Step 7 — Compose bullets
For each project selected in Step 4, retrieve the bullets from its `projects/<slug>.yaml` file at the `altitude` recommended by the selected archetype.

Rules:
- Prefer pre-composed bullets verbatim. They were written carefully and are defensible.
- If a bullet needs JD-language alignment (e.g., JD says "agent orchestration" and bullet says "agentic workflows"), do a minimal rewrite that swaps terminology WITHOUT changing the underlying claim.
- NEVER invent a metric. If the bullet doesn't have a number, don't add one.
- NEVER claim a tech the project file doesn't list.
- Aim for 3-5 bullets per role. Quality over quantity.

### Structure-mirroring (do this, not just keyword-swapping)
When the JD enumerates its own **named responsibility pillars** (e.g. "substrate / runtime / interface / observability", or "discovery / delivery / growth"), **regroup and reorder the lead role's bullets so each bullet maps to one of those pillars, in the JD's order.** This beats swapping vocabulary:
- Keyword-swapping raises only the literal keyword-coverage component of the ATS score.
- Restructuring raises **cosine similarity** (semantic fit) — the resume mirrors the JD's own architecture, so a human reviewer sees their mental model reflected back.
- It uses ONLY reordering/reframing of existing true facts. Nothing new is claimed.

Tell that you skipped this: if after a "re-tailor" the resume still reads "mostly like the previous version," you almost certainly only swapped words. Go back and mirror the JD's pillar structure.

### Title-anchor vs. role-coding (when the JD is coded for a different function than the true title)
Some JDs carry a title that doesn't match the candidate's real title (e.g. an "...Engineer" req for a candidate who is honestly a builder-leaning PM). Do NOT restyle the candidate into the JD's title.
- **Keep the true title** as the resume's role anchor. Overclaiming a function the candidate can't defend in interview (especially on a former-employer req) is the failure mode.
- **Surface genuine builder/edge evidence truthfully** — the most hands-on tooling/systems work the candidate actually did — woven into bullets and summary. Do not invent depth.
- **Route unbridgeable gaps to interview prep, not the resume** — pedigree asks, "code that raises the engineering floor," house-vocabulary terms. Log them as INTERVIEW PREP in `ats-score.md` and lean on any explicit "or something untraditional that trumps all of the above" clause. Never paper a hard credential gap onto the resume.

## Step 8 — Compose summary + headline + competencies
Use the selected archetype's templates as the base. Customize:
- Headline: use the archetype default OR a minor variant aligned to JD language.
- Professional summary: rewrite the archetype's summary substituting JD-vocabulary where it doesn't change the facts. Keep length within the archetype's word target.
- Core competencies: pick 8-12 from the archetype list, prioritizing those that match JD requirements verbatim.

## Step 9 — Resolve education
Per `education.yaml` and its `conditional` rules:
- Default: include only the primary/base degree.
- Add any additional credential (e.g., MBA, Masters) only when the JD explicitly requires/prefers it AND the archetype permits it, per the `conditional` block in `education.yaml`.
- NEVER include all credentials by default — surface them conditionally. If a JD would trigger including two optional credentials at once and you're unsure, STOP and ask the user.

## Step 10 — Render
Load `templates/resume.md`. Substitute every `{{PLACEHOLDER}}` with the composed content.

If any placeholder remains unfilled, STOP and report which one. Do not output a half-rendered resume.

## Step 11 — Write outputs
Create directory: `career-os/jds/<YYYY-MM-DD>-<company-slug>-<role-slug>/`

Write these files:
- `jd.txt` — the original JD text (verbatim)
- `analysis.md` — Step 2 output
- `tailored-resume.md` — the rendered resume (markdown, ATS-clean)
- `decisions.md` — for each bullet on the resume, log: (a) source project file + bullet altitude, (b) any wording change made and why, (c) confidence flag from memory
- `gaps.md` — Step 5 output (even if empty, write the file)
- `ats-score.md` — Step 11a output (deterministic score + reviewer commentary + apply verdict)

Also append a new entry to `career-os/memory/outcomes.yaml` (copy the schema from an existing entry): `jd` slug, company, role, `tailored_date`, the `ats_score` / `ats_band` from Step 11a, and the `apply_verdict` from the rubric. Leave the funnel fields (`applied`, `callback`, `interview`, `offer`, `rejected`) as `null` — the `log-outcome` skill fills them later. This is what makes the gate self-calibrating over time.

## Step 11a — Score the resume against the JD (ATS match)

Every tailored artifact MUST ship with an ATS match score. Compute it two ways — deterministic number + LLM commentary — and write both to `ats-score.md` in the per-JD directory.

### Deterministic score (reproducible, no LLM)
Run the bundled scorer on the markdown resume + the verbatim JD:
```bash
python3 career-os/scripts/ats_score.py \
  --resume career-os/jds/<dir>/tailored-resume.md \
  --jd career-os/jds/<dir>/jd.txt \
  --out career-os/jds/<dir>/ats-score.md
```
This produces: an overall % (0.70·keyword-coverage + 0.30·cosine), the matched JD keywords, and the **missing** JD keywords.

### LLM commentary (qualitative, appended to the same file)
Below the deterministic block in `ats-score.md`, append a short `## Reviewer commentary` section that explains what the number misses:
- **Literal-vs-conceptual gap**: the deterministic score is literal keyword overlap (what an ATS sees). Note where the resume is a strong *conceptual* fit that an ATS under-counts because the vocabulary differs (e.g., resume says "distributed tracing", JD says "telemetry"). This is the single most useful thing you can add.
- **Truthful keyword lifts**: for each *missing* keyword, say whether memory already supports it (→ weave the literal term in, then re-score) or whether it's a genuine gap (→ leave out, route to interview prep). NEVER recommend adding a keyword the candidate can't truthfully support.
- **Verdict**: one line — is the deterministic score misleadingly low/high, and what (if anything) to change in the markdown before export.

### Apply recommendation (combined-signal judgment)
The ATS number alone is NOT the decision — it's literal keyword overlap and can be misleadingly low for a strong conceptual fit (e.g., resume says "distributed tracing", JD says "telemetry"). The apply verdict is a judgment over THREE signals:

1. **Deterministic ATS score** (`ats_score.py`) — literal overlap.
2. **Hard gaps** (from `gaps.md` Step 5) — JD must-haves with *zero* supporting evidence in memory. This is the real disqualifier.
3. **Conceptual fit** (your read of the memory files vs the JD's core) — does the candidate actually do this kind of work, ignoring vocabulary? Rate HIGH / MEDIUM / LOW.

Decision rubric → write one verdict at the top of `ats-score.md` and lead the Step 12 report with it:

| Verdict | When |
|---|---|
| **APPLY** | 0 hard gaps AND conceptual fit HIGH. (ATS number secondary — even a low number is just a keyword-lift away.) |
| **APPLY WITH CAVEATS** | ≤1 hard gap AND conceptual fit ≥ MEDIUM, OR low ATS driven by vocabulary not substance. Note exactly what to shore up (lift truthful keywords; prep interview answers for the soft gaps). |
| **RECOMMEND AGAINST** | ≥2 hard gaps, OR (≥1 hard gap AND conceptual fit LOW). The profile is genuinely divergent from the JD — shortlist odds are below baseline. **Still produce the tailored resume** (the user may apply anyway), but say plainly: this is a stretch, here's why, and here's the honest probability read. |

Never fire RECOMMEND AGAINST on a low ATS number alone — only when hard gaps AND weak conceptual fit coincide. That's the difference between "winnable longshot" and "truly divergent."

State the verdict, the three signals it's based on, and (for caveats/against) the specific gaps driving it.

### Iterate if cheap
If the commentary identifies missing keywords that memory genuinely supports, update `tailored-resume.md` to use the literal JD vocabulary (only where truthful), re-run the scorer, and note the before/after in `decisions.md`. Do NOT chase the number past what memory supports.

## Step 11b — Render styled HTML for PDF export

### Deliverable filename (what the recruiter actually sees) — DO NOT ship `tailored-resume.pdf`
The internal pipeline files keep their canonical names (`tailored-resume.md` is the source of truth, `tailored-resume.html` is the styled render). But the **PDF the candidate emails/uploads is seen by the recruiter, and its filename is visible before they open it.** A file literally named `tailored-resume.pdf` (or `resume-final-v3.pdf`, `<company>-resume.pdf`, etc.) signals "this was customized for you" / looks unpolished. Never hand the candidate a deliverable with a name like that.

Rule: **export the recruiter-facing PDF as `<Full Name> - <Role Anchor>.pdf`** — e.g. `Jordan Lee - Product Manager.pdf`. The role anchor is the candidate's TRUE resume title, NOT the JD's title (don't encode the target company/role into the filename — that re-introduces the "tailored-for-you" tell). Keep the clean-named PDF in the same per-JD directory alongside the internal `tailored-resume.*` working files.

Concretely: still render/print to `tailored-resume.pdf` as the working artifact if convenient (e.g. for the page-count check), then produce the deliverable copy:
```bash
cp "career-os/jds/<dir>/tailored-resume.pdf" "career-os/jds/<dir>/<Full Name> - <Role Anchor>.pdf"
```
— or print-to-pdf directly to the clean name (see "How to convert to PDF" below). In the Step 12 report, point the candidate at the clean-named PDF as the file to send.

User cannot apply via .md file. ATSes accept PDF/DOCX. We use HTML+CSS as the styled rendering format because:
- It mimics the user's preferred two-column "v4" layout (peach left column + white right column)
- It converts to PDF via Chrome's built-in print dialog — no toolchain to install
- It is editable in any text editor if the user wants to tweak

### Visual spec (matches resume v4 from the original corpus)

- **Page**: A4, zero margins (content controls its own padding so the peach column bleeds to the edge)
- **Layout**: CSS grid, 33% left / 67% right
- **Left column**: background `#f6d8d3` (peach), contains:
  - Name (large, 30pt, light-weight, two lines: FIRSTNAME / LASTNAME from profile.yaml)
  - Horizontal divider (50% width, 1pt black)
  - Contact block (email, phone, location, LinkedIn, Medium — with unicode glyph "icons" `✉ ☎ ⌖ in M` in `#b94f47`)
  - SKILLS section (bulleted list, 9pt, ~12 items)
  - EDUCATION section (school name bold, italic date, italic degree, bulleted details)
  - PUBLICATIONS section (only when JD asks for "thought leader" preferred qual)
- **Right column**: white, contains:
  - PROFESSIONAL SUMMARY (12pt header, 1pt grey divider, 9.5pt paragraph)
  - RECOGNITION & CREDENTIALS
  - WORK HISTORY (one block per role: title bold 11pt, meta italic 9pt, bulleted list 9.5pt, plus a final italic grey "Environment:" line listing tech/domain)
- **Fonts**: Calibri / Helvetica Neue fallback. ASCII-safe characters; HTML entities for em-dash (`&mdash;`), en-dash (`&ndash;`), ₹ (`&#8377;`), bullet (`&bull;`), times (`&times;`).

### Environment: line (per role)
Each role bullet list ends with an italicized "Environment:" line listing the tech stack + domain tags relevant to that role. Pulled from `roles/<role>.yaml.tech_stack` and the `tags` field of linked project files. Strict rule: never list a tech the user hasn't actually worked with.

### Page-break control (CRITICAL — without this, roles split mid-content)
The template MUST include these CSS print-control rules to avoid awkward mid-role page breaks:

```css
/* RIGHT COLUMN: keep each role together across pages */
.role {
  page-break-inside: avoid;
  break-inside: avoid;
  -webkit-column-break-inside: avoid;
}
/* Never end a page right after a header/meta line */
.role-title, .role-meta { page-break-after: avoid; break-after: avoid; }
/* Never orphan the Environment line at the top of next page */
.role-bullets li.environment { page-break-before: avoid; break-before: avoid; }
/* Never orphan a section header */
.right-section-header { page-break-after: avoid; break-after: avoid; }
.right-section-divider { page-break-after: avoid; break-after: avoid; }
/* Don't strand 1 bullet at top/bottom of page */
.role-bullets li { orphans: 2; widows: 2; }

/* LEFT COLUMN: same treatment for education + publications blocks */
.edu-block {
  page-break-inside: avoid;
  break-inside: avoid;
  -webkit-column-break-inside: avoid;
}
.edu-school, .edu-date, .edu-degree {
  page-break-after: avoid;
  break-after: avoid;
}
.edu-detail-list li { orphans: 2; widows: 2; }

/* CRITICAL: left section headers (SKILLS / EDUCATION / PUBLICATIONS) must
   travel with their first content block. Without this, if the next .edu-block
   doesn't fit, the header gets orphaned at the bottom of the previous page. */
.left-section-header {
  page-break-after: avoid;
  break-after: avoid;
}
```

### Page-break debug protocol (when output looks wrong)

If after rendering you see ANY of these symptoms, the fix is in the rules above — re-verify they're present in the HTML:
- **Role split mid-content** → `.role { page-break-inside: avoid }` missing
- **Single bullet orphaned at top of next page** → `.role-bullets li { orphans: 2; widows: 2 }` missing OR Chrome ignoring it; check if the entire role is large enough to fit only when split
- **Section header (EDUCATION / SKILLS / PUBLICATIONS) alone at bottom of page** → `.left-section-header { page-break-after: avoid }` missing
- **Environment: line alone at top of next page** → `.role-bullets li.environment { page-break-before: avoid }` missing
- **Education school/degree line separated from its bullets** → `.edu-block { page-break-inside: avoid }` missing

Always re-verify by reading the PDF after CSS changes — Chrome's print algorithm can be surprising and a single missing rule can cascade.

**Tradeoff**: with `page-break-inside: avoid`, if a role doesn't fit on the remaining page, the browser pushes the entire role to the next page — leaving some whitespace at the bottom of the previous page. This is the lesser evil vs splitting a role across pages.

**If a role + leftover space is awkward**: shorten that role's bullets in the markdown source (don't fight CSS, fight content). Aim for the most recent / lead role at 4-5 bullets, others at 2-3.

### One-page fit protocol (when the recruiter asks for one page)
Fitting to one page is a two-lever job — cut content first, then tune density — and you must **verify**, not eyeball. Apply levers in order (least-destructive first), re-rendering after each until it fits:
1. **Content cuts first:** competencies 12 → ~9; education sub-bullets → 1; drop per-role "Environment:" lines; merge a 4-bullet supporting role to 3.
2. **Move blocks across columns:** the left column usually has slack — move short sections (e.g. Recognition) there to relieve the right column.
3. **Density knobs last (CSS):** nudge `.role-bullets li` font 9.5pt → 9pt and `line-height` to ~1.32; trim `.role { margin-bottom }` and column `padding`.

**Verify with a page count, don't guess** — after rendering the PDF:
```bash
grep -c "/Type *. *Page[^s]" career-os/jds/<dir>/tailored-resume.pdf   # expect 1; if 2+, apply next lever
```
If it renders 2 pages with only a few overflow lines, prefer one more content cut over shrinking font again — readability is the constraint that matters to the human reader.

### Render procedure
1. Read `career-os/templates/resume.html.template` (the canonical template with `{{VARIABLES}}`).
2. Substitute:
   - `{{NAME_HTML}}` — e.g., `FIRSTNAME<br>LASTNAME` (from profile.yaml)
   - `{{CONTACT_ITEMS}}` — 4-5 `<div class="contact-item">` lines
   - `{{SKILLS_ITEMS}}` — `<li>` for each competency from the tailored markdown
   - `{{EDUCATION_BLOCKS}}` — one `<div class="edu-block">` per credential included (per `education.yaml.conditional` rules)
   - `{{SUMMARY}}` — the same prose from the markdown's summary section
   - `{{RECOGNITION}}` — recognition line
   - `{{ROLES}}` — one `<div class="role">` per role, with Environment: line appended as final `<li class="environment">`
3. Write to `career-os/jds/<dir>/tailored-resume.html`.

### IMPORTANT: HTML is NOT the source of truth
The markdown (`tailored-resume.md`) is canonical. The HTML is a stylized rendering. If you iterate on bullets, update the markdown first, then re-render the HTML. Don't edit the HTML directly without also updating the markdown — drift will silently break consistency.

## Step 12 — Report to user
Output a short summary:
```
>>> VERDICT: <APPLY | APPLY WITH CAVEATS | RECOMMEND AGAINST> <<<
   Based on: ATS <overall>% (<band>) · hard gaps: <count> · conceptual fit: <HIGH/MED/LOW>
   <one line — if caveats/against, the specific gaps driving it and the honest shortlist read>

Tailored resume written to: career-os/jds/<dir>/tailored-resume.md
Send this file to the recruiter: career-os/jds/<dir>/<Full Name> - <Role Anchor>.pdf

Archetype selected: <name>
Projects emphasized: <list>
Education included: <list>
Frameworks surfaced: <candidate-specific frameworks from frameworks.yaml / none>

ATS match score: <overall>% (<band>) — keyword coverage <x>%, cosine <y>% — see ats-score.md
  Top missing keywords: <list> (<which are truthfully addable vs genuine gaps>)

GAPS surfaced: <count> — see gaps.md
LOW-CONFIDENCE evidence used: <count> — see decisions.md
MEMORY captured this run: <count> answers persisted (or "none")

Anticipated objections for this resume (from stories.yaml):
- <list any matched objections>
```

## Anti-patterns — do NOT do these

- Don't paraphrase the professional summary into something the archetype doesn't authorize.
- Don't add bullets to satisfy length. Better to ship a 4-bullet role than to pad.
- Don't surface candidate-specific frameworks or credentials (from frameworks.yaml / education.yaml) unless the archetype explicitly permits.
- Don't blend archetypes. If you can't decide, ask.
- Don't add a "References available on request" line. It's noise.
- Don't include the GitHub link unless its active/presentable status is confirmed — either `open-questions.yaml` records it, OR the user explicitly confirms it in-session. When the user confirms verbally, write that back to `open-questions.yaml`/`profile.yaml` so it's not re-asked.
- Don't auto-fetch LinkedIn URLs.
- Don't add color, columns, or images to the rendered **markdown** — the markdown is ATS-clean for a reason. (The HTML render is a separate, styled artifact — see Step 11b.)

## When the user wants iteration

If user says "make bullet 3 more technical" or "swap X for Y":
- Re-read the relevant project file
- Find a bullet at a different altitude OR re-word within the same factual claims
- Update `decisions.md` to log the change
- Never silently strengthen claims to satisfy iteration pressure

## How to convert to PDF / DOCX after tailoring

### Recommended: Chrome print-to-PDF (uses the styled HTML)

The HTML render (Step 11b) is designed for this path.

```bash
# Open the styled HTML in Chrome
open -a "Google Chrome" career-os/jds/<dir>/tailored-resume.html
```

Then in Chrome:
1. `Cmd+P` (Print)
2. Destination → **Save as PDF**
3. Layout: **Portrait**
4. Pages: **All**
5. Paper size: **A4**
6. Margins: **None** (the HTML controls its own padding so the peach left-column bleeds to the edge — this is intentional)
7. Options: ✅ **Background graphics** (CRITICAL — without this the peach column will print white)
8. Save as `<Full Name> - <Role Anchor>.pdf` (the recruiter-facing deliverable name — see "Deliverable filename" in Step 11b; do NOT save as `tailored-resume.pdf`).

Headless alternative (no GUI, scriptable) — print straight to the clean deliverable name:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless --disable-gpu \
  --print-to-pdf="career-os/jds/<dir>/<Full Name> - <Role Anchor>.pdf" \
  --no-pdf-header-footer \
  --print-to-pdf-no-header \
  file://$PWD/career-os/jds/<dir>/tailored-resume.html
```
(If you rendered to `tailored-resume.pdf` first for the page-count check, just `cp` it to the clean name afterward — see Step 11b.)

### Fallback: pandoc from markdown (plain, no two-column styling)

Only use if you want the plain ATS-clean version (no peach column, single column):
```bash
pandoc career-os/jds/<dir>/tailored-resume.md \
  -o career-os/jds/<dir>/tailored-resume-plain.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=0.6in \
  -V fontsize=11pt
```

### DOCX (for ATSes that prefer Word)
```bash
pandoc career-os/jds/<dir>/tailored-resume.md \
  -o career-os/jds/<dir>/tailored-resume.docx
```
(Plain styling — pandoc doesn't translate the HTML CSS to DOCX styles. If you need a styled DOCX, open the HTML in Word — `File → Open` works in modern Word and approximates the layout.)

### Which to send?
- **Most ATSes (Greenhouse, Lever, Workday, custom)**: PDF from styled HTML.
- **Large-corp / enterprise ATSes**: try PDF first; if they reject or strip formatting, send the pandoc-DOCX fallback.
- **Direct email to recruiter**: PDF from styled HTML always.
- **Workday-style parsers**: some Workday instances mangle two-column layouts during parsing. If the role is high-stakes, also submit the plain pandoc PDF as a backup so the parser gets clean text.
