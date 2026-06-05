# career-os (template)

A file-based career-intelligence system. Point it at a job description and it
produces a tailored resume that preserves your real narrative, never invents
claims, attaches a deterministic ATS match score, and logs a defensibility trail
for every bullet — plus an honest "should you even apply?" verdict.

This is the **blank template**. It ships with no personal data. You bring a resume;
the `bootstrap-profile` skill turns it into your memory layer; everything else
tailors from that.

## Architecture in one paragraph
Memory is plain YAML / Markdown — no database, no vector store. The "engine" is a
set of skill prompts. Two dependency-light Python scripts handle the mechanical
edges: `fetch_jd.py` (job URL → clean text) and `ats_score.py` (deterministic
resume-vs-JD match score). Both are optional; the memory + skill layer works
without them. The same files run in Claude Code (skills auto-load, scripts run
locally) and in Claude.ai (upload the directory to a Project; paste JDs if you
can't run scripts).

## Quick start
1. **Clone / copy this directory.**
2. **Bootstrap from your resume.** In Claude Code, drop your resume into the
   directory and run:
   ```
   /bootstrap-profile
   ```
   or *"here's my resume, build my memory."* It reads the resume and writes
   `memory/profile.yaml`, `education.yaml`, one file per role and project, and
   seeds stories/frameworks/open-questions. It will ask you a batched set of
   clarifying questions for anything ambiguous — answer them in chat.
3. **Review your memory.** Open `memory/open-questions.yaml` and resolve the gaps
   it flagged. The engine never invents — it asks — so the more you fill in, the
   richer the tailoring.
4. **Edit the narratives.** The three `memory/narratives/*.md` files are scaffolds;
   replace the `<placeholders>` with your real positioning.
5. **Tailor.** Give it a JD URL: *"tailor my resume for this JD: &lt;url&gt;"*.

## The `*.example` convention
Files ending in `.example.yaml` are templates you copy to the live name:
`profile.example.yaml` → `profile.yaml`, etc. `bootstrap-profile` does this for you.
The live files are git-ignored by default (see `.gitignore`) so your personal data
doesn't get committed if you fork this publicly. The `.example` files stay tracked.

## Directory map
```
career-os-template/
├── README.md                    ← you are here
├── memory/                      ← the durable layer (you fill this)
│   ├── profile.example.yaml     ← identity + contact + recognition
│   ├── education.example.yaml   ← with conditional-display rules per credential
│   ├── frameworks.example.yaml  ← named frameworks you own / apply
│   ├── stories.example.yaml     ← interview stories + anticipated objections
│   ├── search-defaults.yaml     ← query + safety limits for discover-jds
│   ├── target-companies.example.yaml ← your prioritized employer list
│   ├── open-questions.yaml      ← gaps the engine must ask about, not invent
│   ├── outcomes.yaml            ← per-application funnel: score + verdict → result
│   ├── roles/_example-role.yaml      ← one file per employer
│   ├── projects/_example-project.yaml ← one file per project (evidence + bullets)
│   ├── notes/                   ← scratch
│   └── narratives/              ← positioning archetypes (scaffolds — edit these)
│       ├── generic-pm.md
│       ├── ai-ml-pm.md
│       └── platform-staff-pm.md
├── templates/
│   ├── resume.md                ← ATS-clean markdown template (canonical)
│   └── resume.html.template     ← styled two-column HTML (for PDF export)
├── scripts/
│   ├── fetch_jd.py              ← ATS-agnostic JD fetcher (URL → clean text)
│   └── ats_score.py             ← deterministic resume-vs-JD ATS match scorer
├── jds/                         ← one folder per JD (created at tailoring time)
└── skills/
    ├── bootstrap-profile.md     ← FIRST RUN: resume → memory layer
    ├── discover-jds.md          ← Stage 1: pull + rank JDs (needs browser MCP)
    ├── triage-jds.md            ← Stage 2: deep triage on a chosen subset
    ├── tailor-resume.md         ← Stage 3: full tailored resume per winner
    ├── capture-memory.md        ← in-flow: ask in chat + write answers to memory
    ├── ingest-update.md         ← explicit/batch memory maintenance
    └── log-outcome.md           ← record results → outcomes.yaml (calibrates the gate)
```

## The funnel
```
   bootstrap-profile  →  discover-jds  →  triage-jds  →  tailor-resume
   (once)                (Stage 1)        (Stage 2)       (Stage 3)
   resume → memory       pull + rank      go/no-go        tailored resume
                                                          + ATS score + verdict
```
- **Stage 1 — discover** (optional, needs a Chrome MCP logged into your job
  boards): pulls and ranks many JDs into `jds/_runs/<timestamp>/ranked-list.md`.
  Rate-limited by design (max 20 JDs/run, 3 runs/day). Skip it and paste JDs if you
  don't have browser MCP.
- **Stage 2 — triage**: deep go/no-go on a chosen subset. Accepts URLs or pasted text.
- **Stage 3 — tailor**: produces, per JD, in `jds/<date>-<company>-<role>/`:
  `tailored-resume.md` (+ styled `.html`/`.pdf`), `decisions.md` (defensibility
  log), `gaps.md` (what it refused to invent), and `ats-score.md`.

## The apply-gate
`ats-score.md` carries an **apply verdict**: `APPLY` / `APPLY WITH CAVEATS` /
`RECOMMEND AGAINST`. It's a judgment over **three** signals — the deterministic ATS
number, hard gaps (must-haves with zero evidence in your memory), and conceptual
fit — *not* the keyword number alone. A low ATS score driven by vocabulary
mismatch (you say "distributed tracing", the JD says "telemetry") is a keyword-lift
opportunity, not a real gap, and the gate knows the difference. It only says
`RECOMMEND AGAINST` when the profile is genuinely divergent (hard gaps **and** weak
conceptual fit), so it won't talk you out of a winnable longshot. The resume is
produced regardless — you decide.

Close the loop: report what happens (*"got a callback from &lt;company&gt;"*,
*"&lt;company&gt; rejected me"*) and the `log-outcome` skill records it in
`outcomes.yaml`. After ~10+ applications with results, the score-vs-callback
pattern tells you whether the gate is calibrated for *you*.

## Design principles (read before editing memory)
1. **Memory is the source of truth.** Resumes are derived. If a resume says X and
   memory says Y, memory wins. Update memory first; resumes regenerate.
2. **Attribution is explicit.** Every metric carries
   `attribution: personal | team-owned | platform-level` and
   `source_confidence: high | medium | low`. The engine uses these to choose
   "led" vs "drove" vs "contributed to" — and to know what it can't claim.
3. **Bullets are pre-composed at multiple altitudes.** You write each achievement
   truthfully once, at 2-3 scopes; the engine picks the right altitude per JD
   instead of rewriting from scratch. Less hallucination surface.
4. **The engine refuses to invent.** When a JD needs evidence memory doesn't have,
   it logs a gap and asks you (via `capture-memory`) rather than fabricating.

## Requirements
- **Claude Code** (recommended) or **Claude.ai Projects**.
- **Python 3.9+** for the optional scripts (`fetch_jd.py` uses stdlib + optional
  `requests`/`lxml`; `ats_score.py` is pure stdlib). Both degrade gracefully.
- **A Chrome MCP** only for Stage-1 bulk discovery. Fetching a single known JD URL
  needs no MCP.

## Privacy note
The `.gitignore` excludes your live memory files (`profile.yaml`, `roles/*.yaml`,
etc.) so a public fork won't leak your data — only the `.example` scaffolds are
tracked. If you keep your own filled repo private, you can remove those ignore
rules to version your real memory.
