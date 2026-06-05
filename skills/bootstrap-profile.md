---
name: bootstrap-profile
description: First-run onboarding. Turns an uploaded resume (PDF / DOCX / Markdown / plain text) into the career-os memory layer — profile.yaml, education.yaml, roles/*.yaml, projects/*.yaml, and seeded stories/frameworks/open-questions. Triggers when a new user says "set me up", "bootstrap my profile", "here's my resume, build my memory", or runs `/bootstrap-profile`. Run this ONCE before using discover-jds / triage-jds / tailor-resume.
---

# Skill: bootstrap-profile

## What this does
Reads a resume the user uploads and populates `memory/` so the rest of career-os
has a source of truth to tailor from. It is the on-ramp for a brand-new clone of
this template. It does NOT tailor a resume — it builds the memory the tailoring
engine reads.

## Golden rule
**Extract, don't invent.** A resume is a lossy, sometimes-stale artifact. Pull only
what's stated. Everything ambiguous (attribution, provenance, dates, scope) goes to
`open-questions.yaml`, NOT into a confident memory field. When something blocks a
core field (e.g. you can't tell which company an award belongs to), ASK — use the
batched-question protocol in `capture-memory.md`.

## Process

### 1. Locate + read the resume
Accept a file path or pasted text. Supported: `.pdf`, `.docx`, `.md`, `.txt`.
- PDF/DOCX: extract text (use the host's document tooling). If extraction is messy,
  show the user what you got and confirm before proceeding.
- If no resume is provided, ask for one — do not fabricate a profile from chat alone
  unless the user explicitly wants to build from scratch.

### 2. Confirm memory isn't already populated
If `memory/profile.yaml` already exists (not the `.example`), STOP and ask whether
to overwrite, merge, or abort. Never silently clobber an existing memory layer.

### 3. Create the core files from the examples
Copy each `*.example.yaml` to its live name and fill from the resume:
- `profile.example.yaml` → `profile.yaml` — name, location, contact, links, YOE,
  recognition. Quote postal codes. Set `source_confidence` honestly.
- `education.example.yaml` → `education.yaml` — base degree(s) in `default`; any
  advanced/secondary credential in `conditional` with sensible `include_when`.

### 4. One file per role
For each job on the resume, create `roles/<company-slug>.yaml` from
`roles/_example-role.yaml`. Fill `scope`, `metrics` (with `attribution` +
`source_confidence`), `tech_stack` (only tools actually mentioned), and the
`projects` list. Resume metrics are usually unattributed — default
`attribution: personal` ONLY if the resume clearly frames it as the user's own;
otherwise mark it and add an open-question.

### 5. One file per significant project / achievement
For each substantial accomplishment, create `projects/<slug>.yaml` from
`projects/_example-project.yaml`. Write `summary`, `problem_space`, `actions`,
`outcomes` (with confidence), `tags`, and — critically — pre-composed `bullets` at
2-3 altitudes. These bullets are what stops the tailoring engine from hallucinating
later, so write them truthfully now.

### 6. Seed the supporting files
- `stories.yaml` (from `stories.example.yaml`): draft 1-3 interview stories if the
  resume implies them (a 0-to-1, a hard call, an AI eval). Leave `prompt_match`
  honest. If you can't ground a story, leave the file as the scaffold and note it.
- `frameworks.yaml` (from `frameworks.example.yaml`): only if the resume names a
  framework the user owns. Otherwise keep just `frameworks_borrowed`.
- `search-defaults.yaml`, `target-companies.yaml` (copy from `.example`): fill what
  you can infer (level, location, domains); leave the rest for the user.
- `open-questions.yaml`, `outcomes.yaml`: already scaffolded — append questions as
  you hit them in steps 3-5.

### 7. Pick a default archetype
Read the three `narratives/*.md`. Based on the resume's center of gravity
(generalist / AI-ML / platform-staff), tell the user which archetype fits best and
set it as `archetype_target` in `search-defaults.yaml`. The user can override.

### 8. Batch the clarifying questions
Collect every gap you flagged into ONE message (per `capture-memory.md` — never
one-at-a-time). Prioritize anything that blocks attribution or a headline metric.
Persist the answers back to the right files; record genuine unknowns in
`open-questions.yaml`.

### 9. Confirm what was built
Report concisely:
```
Memory bootstrapped from <resume file>.
  profile.yaml ............ <name>, <location>, <YOE>
  education.yaml .......... <N> default, <N> conditional
  roles/ .................. <N> roles
  projects/ ............... <N> projects (<total> pre-composed bullets)
  stories.yaml ............ <N> stories seeded
  open-questions.yaml ..... <N> gaps to resolve

Default archetype: <name>
Next: resolve the <N> open questions above, then run /tailor-resume on a JD.
```

## Anti-patterns — do NOT do these
- Don't invent metrics, dates, attribution, or tools not in the resume.
- Don't mark everything `source_confidence: high` — a resume claim you can't verify
  is `medium` at best.
- Don't overwrite an existing populated memory layer without explicit confirmation.
- Don't ask questions one message at a time. Batch them.
- Don't skip the pre-composed bullets — they're the anti-hallucination layer.
