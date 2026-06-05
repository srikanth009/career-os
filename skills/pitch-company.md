---
name: pitch-company
description: Proactive value-first pitch engine — the inverse of tailor-resume. Given a company name, does dated, cited deep research (last 6 months) across news, earnings, product launches, engineering/product blogs, exec statements, and especially OPEN JOB POSTINGS; synthesizes 2-4 evidence-backed problem hypotheses; scores each against the candidate's memory layer to find where they're genuinely credible; identifies the owning person + reach path; and produces a consultative pitch (research dossier + 1-page memo + slide deck + outreach drafts) positioning the candidate as the PM to solve a specific problem. Also has a DISCOVERY mode (scans memory/target-companies.yaml for pitchable openings) and a PER-ROLE / JD-anchored mode (pipeline stage 5b: builds a pitch to accompany an application to a specific top-tier role, seeded by the fetched JD as a leaked problem statement and the hiring manager from find-hiring-manager). Triggers on "pitch myself to <company>", "deep-research <company> for a proactive pitch", "who should I pitch at <company>", "build a pitch for [role]", "find pitchable companies", or `/pitch-company`.
---

# Skill: pitch-company

## What this does
Turns a company into a grounded, consultative self-pitch. It is the mirror image of
`tailor-resume`: instead of JD → résumé, it runs company → problem → fit → person → pitch.
It reuses the same `memory/` layer (profile, roles, projects, frameworks, stories) as the
"what can I *credibly* solve" engine, and obeys the same non-negotiable rule:

> **Never invent.** No company fact without a dated, cited source. No problem without
> evidence. No person or contact detail that isn't real. Mark confidence everywhere.
> When you don't know, say so.

A pitch built on a misread of the company actively destroys credibility with a senior
leader. The whole skill is engineered against that failure mode.

## Three modes
- **On-demand** (default): user names a company → full deep-dive + pitch.
- **Discovery**: user says "find pitchable companies" → light-touch scan of
  `memory/target-companies.yaml`, ranks which have a live, pitchable opening, user picks
  one to go deep on.
- **Per-role (JD-anchored)**: the pipeline's stage 5b. User has a specific top-tier role (a triage
  GO/BORDERLINE with a tailored resume) and wants a pitch to send *alongside the application* to the
  hiring manager `find-hiring-manager` identified. The fetched JD IS a leaked problem statement —
  so the problem hypothesis starts grounded, not from scratch. See PER-ROLE MODE below.

---

## ON-DEMAND MODE

### Step 0 — Load the candidate
Read `memory/profile.yaml`, `memory/roles/*.yaml`, `memory/projects/*.yaml`,
`memory/frameworks.yaml`, `memory/stories.yaml`. This is the credibility inventory — the
ONLY evidence you may use to claim the candidate can solve something. Note the strongest
real metrics, named frameworks, and domains (with `attribution` + `source_confidence`).

### Step 1 — Deep research (dated + cited, last 6 months)
Use web search + web fetch. Time-box to the **last 6 months**; older material is allowed
ONLY as essential context and must be flagged as such. Pull from, in priority order:

**Tier 1 — primary / high-signal**
- **Open job postings** — the single highest-signal source. What a company is hiring for
  *is its roadmap leaking*. Mine: how many roles in area X, brand-new teams forming, tech
  named in the JDs, seniority of the hires, locations (new site = new bet).
- Earnings calls / shareholder letters / investor decks (public cos).
- Official press releases, product launches, changelogs, official blog posts.
- Verbatim exec statements (interviews, keynotes, LinkedIn posts) — quote + date.

**Tier 2 — reputable journalism**
- Trade and mainstream press covering the company's moves.

**Tier 3 — directional only (label as such)**
- Analyst summaries, third-party blogs, Glassdoor, Reddit, employee chatter.
- NOTE: Gartner/Forrester/McKinsey/BCG decks are almost always paywalled/proprietary —
  do NOT claim to have read one you haven't. Cite only what you actually accessed.

For every signal captured, record: `{ claim, source_url, date, tier, confirmed-fact vs interpretation }`.
Write these to `research.md` as you go. Keep raw quotes for the strongest signals.

### Step 2 — Synthesize problem hypotheses (2-4)
Cluster the signals into 2-4 candidate problem spaces. For EACH:
- **The hypothesis** (one sentence — the problem, stated as a problem, not a solution).
- **Evidence** (the dated, cited signals that support it).
- **Why now** (what in the last 6 months makes this live).
- **Confidence**: HIGH / MEDIUM / LOW.
- **What I'm assuming** (the inference leaps an outsider is making).
- **What would invalidate this** (the fact that, if true, kills the hypothesis).
- **Steelman the insider** ("what they may have already done about this") — if you can't
  argue they probably haven't solved it, the hypothesis is weak.

Reject any hypothesis that is generic ("they need better data"), evidence-free, or that a
competent internal team has obviously already handled. Write to `problems.md`.

### Step 3 — Profile-fit scoring
For each surviving hypothesis, map it to the candidate's memory:
- Which specific projects / metrics / frameworks make them *credible for THIS problem*?
  Cite the memory file + the real outcome.
- Honor `attribution` — "led" vs "contributed to" must match memory.
- Score fit HIGH / MEDIUM / LOW.
- **Drop any problem the candidate can't actually back.** Pitching a problem you can't
  credibly solve is the résumé-fabrication sin in another costume.

Pick the **single strongest** problem (occasionally two) where evidence × fit is highest.
That is the pitch. Write the mapping to `fit.md`.

### Step 4 — Identify the right person + reach path
- **Target the entity that actually owns the problem — not the famous parent.** A problem may
  live in an acquired subsidiary, a JV, a specific new office, or a delivery arm, NOT the
  headline brand. Verify that entity exists *where you think it does* (offices, footprint,
  named team). Pitching "BigCo <City>" when the real operator is "AcquiredCo" makes you look
  like you didn't do the homework. (This session: target was Fractional AI, not "Anthropic Dubai.")
- Identify the **owning function + seniority** for that problem (e.g., "VP Product,
  Quick Commerce" / "Head of Platform Engineering").
- Find a **named individual** via public sources (company leadership page, LinkedIn,
  press quotes, conference speakers). Record name, title, source_url, date, confidence.
  Titles churn — mark confidence and date. **Verify the person's real LinkedIn URL via search
  (ideally from their own posts) — never guess a vanity URL.**
- **Reachability beats seniority. Aim for who will actually READ it, not the most senior name.**
  A flooded exec / big-company MD with a locked-down inbox is a vanity target; their "congrats"
  filter eats inbound. Founders of a young firm, peer-level ICs, or a short-staffed hiring
  manager are far more likely to reply. Rank candidates by *probability of a reply*, not title.
- **Research the recipient's verified background to understand HOW THEY THINK** — prior
  companies, what they built, public essays/podcasts/talks (cited). Use it to frame the problem
  in *their* worldview and to respect their stated philosophy (if they deliberately chose X,
  don't pitch anti-X). **Do NOT quote their profile/interviews back at them — it reads as
  surveillance and kills a cold open.** If someone's only public quotes are paraphrases, don't
  tailor to them (risk of attributing words they didn't say).
- **Contact research / reach path**, best-to-worst:
  1. Warm intro — check for any overlap signal (shared school/employer/community) the
     candidate could leverage.
  2. LinkedIn (direct message / connection note).
  3. Inferred email — only via a **known public company email pattern**
     (e.g. `first.last@company.com` confirmed from a real published address). Label it
     explicitly `UNVERIFIED — pattern-inferred`. **Never present a guessed email as fact;
     never fabricate one.**
- Pull the candidate's own real contact details (LinkedIn, email, phone) from
  `memory/profile.yaml` — don't leave `[LinkedIn]`/`[phone]` placeholders in final drafts.
- If you cannot find a real person, say so and give the title to target. Write `target.md`,
  including a short **recipient dossier** (verified background + worldview cues + sources),
  flagged "to understand them, NOT to quote."

### Step 5 — Produce the artifacts
Create `career-os/pitches/<YYYY-MM-DD>-<company-slug>/` containing:

1. **`research.md`** — the cited dossier (Step 1).
2. **`problems.md`** — problem hypotheses + confidence + fit summary (Steps 2-3).
3. **`target.md`** — person + reach path + confidence (Step 4).
4. **`pitch-memo.md`** — the 1-page proposal. Structure:
   - *What I'm seeing* (2-3 cited signals, dated).
   - *The hypothesis* (the problem, framed as a question: "Am I reading this right?").
   - *How I'd approach it* (an outline, not a finished plan — you're an outsider).
   - *Why me* (2-3 real, attributed proof points from memory).
   - *The ask* — pitch the **problem**, not a job and not even a meeting slot. "Your read on
     this — am I right about the constraint?" The role/seat emerges later; never lead with it.
5. **`outreach.md`** — drafts built as a **SEQUENCE, not one blast** (see the Cold-outreach
   playbook below). Touch 1 = a short story-led LinkedIn note that surfaces the problem and
   asks for nothing (no deck, no meeting, no job). The memo + deck are **touch-3 artifacts**,
   sent only after they engage. Provide a ≤300-char connection-note version (LinkedIn's hard
   limit — count it) plus the longer message version. No flattery, no presumption, no "I can
   fix your company."
6. **`pitch-deck.pptx`** — invoke the **pptx skill** to build a 5-7 slide deck from the
   memo: (1) the pattern I noticed, (2) the problem hypothesis, (3) why now, (4) how I'd
   approach it, (5) why me — proof points, (6) the ask. Keep the deck's claims identical
   to the memo; the memo is canonical (same discipline as tailor-resume's md-is-canonical).
7. **`confidence-ledger.md`** — the honest appendix: every key claim's confidence, the
   assumptions, what would invalidate the thesis, and what you could NOT find. This is the
   credibility backstop — read it before sending anything.

### Step 6 — In-flow memory capture
If research reveals the candidate is missing evidence they likely *have* (e.g. the problem
needs a metric or a domain story they haven't logged), ASK in chat — batched, one message —
via `capture-memory.md`, and write answers back to memory. Don't pitch around a gap you
could close in one question.

### Step 7 — Report
```
Pitch built: career-os/pitches/<dir>/

Company: <name>   ·   Research window: last 6 months   ·   Signals cited: <N>
Problem pitched: <one line>   (evidence: <conf> · profile fit: <conf>)
Other hypotheses considered: <list with why not chosen>

Target: <Name>, <Title>  (confidence: <H/M/L>, source dated <date>)
Reach path: <warm intro / LinkedIn / unverified email>

Artifacts: research.md · problems.md · target.md · pitch-memo.md · outreach.md
           · pitch-deck.pptx · confidence-ledger.md

Honest read: <1-2 lines — is this a strong pitch or a stretch, and why>
Open caveats: <the biggest thing that could be wrong>
```
Always give the honest read — including "this is a stretch, here's why" when it is.

---

## PER-ROLE MODE  (JD-anchored — pipeline stage 5b)

Use when the user has a specific top-tier role (a triage **GO/BORDERLINE** with a tailored resume)
and wants a pitch to accompany the application to a real hiring manager. This mode is **cheaper and
more grounded** than On-Demand because two artifacts already exist: the **fetched JD** (a leaked
problem statement) and, ideally, **`hm-candidates.md`** from `find-hiring-manager` (the person +
reach path, found account-safely). Don't redo work those already did.

### Inputs (must exist — STOP if missing)
- The fetched JD + its triage report (the run dir / tailoring dir). If there's no fetched JD, this
  isn't per-role mode — refuse and point to On-Demand.
- `hm-candidates.md` from `find-hiring-manager` if available. If absent, you MAY run a minimal
  person-identification (On-Demand Step 4 discipline), but prefer to tell the user to run
  `find-hiring-manager` first — keep the who/what responsibilities separate.
- The memory layer (On-Demand Step 0) — the credibility inventory.

### Process (reuses On-Demand steps, JD-seeded)
1. **Step 0** — load the candidate (same as On-Demand). This bounds what you may claim.
2. **Step 1′ — JD-seeded research.** The JD already tells you the problem the team is hiring to
   solve — extract it (the pains, the named tech, the scope, the "why this role exists"). Then do a
   **light** dated/cited pass (last 6 months) to confirm **why now** and that the problem is live —
   NOT a full dossier. Cite what you actually read; flag interpretation vs fact.
3. **Step 2-3 — one problem hypothesis.** Anchor the hypothesis to the JD's core problem (not a
   generic company observation), then run On-Demand Step 3 profile-fit scoring: which real,
   attributed memory evidence makes the candidate credible for *this* problem. **Drop the pitch if
   the candidate can't back it** — same rule as always.
4. **Step 4′ — person.** Consume `hm-candidates.md` (top target + reach path + worldview cues). Do
   NOT redo the search or override find-HM's account-safe sourcing. If it's missing, minimally
   identify the owning person per On-Demand Step 4, but say you're doing find-HM's job inline.
5. **Step 5-6 — artifacts + memory capture**, but write them into the **role's existing dir**
   (next to `tailored-resume.md`), not a fresh `pitches/` dir, so the application package is one
   place. Produce: `pitch-memo.md`, `outreach.md` (the touch-1 LinkedIn lure first; memo/deck are
   touch-3), `confidence-ledger.md`. A deck is optional here — for an application-accompanying pitch
   a tight memo + outreach note usually beats a deck; build the deck only if the user asks.

### The application-pitch nuance
This pitch rides alongside a job application, so the tone shifts slightly from cold On-Demand: the
person already knows there's a role. Still **lead with the problem, not "hire me"** — the resume is
the "hire me"; the pitch is "here's how I'd think about your problem on day one." The cold-outreach
playbook (touch-1 asks for nothing) still applies if the user is reaching the HM *directly* rather
than just submitting through the ATS.

### Report
```
Per-role pitch built: <role dir>/

Role: <Title> @ <Company>   (triage band: <STRONG/FIT-WITH-GAPS/STRETCH>)
Problem pitched: <one line, JD-anchored>   (evidence: <conf> · profile fit: <conf>)
Target HM: <Name/title from hm-candidates.md>   ·   Reach: <warm/LinkedIn/unverified email>
Artifacts: pitch-memo.md · outreach.md · confidence-ledger.md  (in the role dir, next to the resume)
Honest read: <strong pitch or a stretch, and why>
The HUMAN sends it — I never do.
```

---

## DISCOVERY MODE

When the user asks to "find pitchable companies":
1. Read `memory/target-companies.yaml` (+ memory layer from Step 0).
2. For each company, do a **light** version of Step 1 (a few targeted searches, emphasis on
   job postings + recent news) — NOT the full dossier.
3. Score each on: **signal strength** (is something clearly happening?) × **profile fit**
   (does it touch the candidate's real strengths?) × **reachability** (product-led / founder-led
   / findable owner?).
4. Output `career-os/pitches/_scans/<YYYY-MM-DD>/pitchable.md` — a ranked shortlist, one line
   each: company, the live signal, the rough problem angle, fit, and why it's reachable.
5. User picks one → run On-Demand mode on it.

Respect the same safety posture as `discover-jds`: human-paced, stop on detection signals,
don't hammer any one site.

---

## Cold-outreach playbook (lessons banked — read before writing outreach)
The pitch package (memo/deck) is the *substance*, but it is NOT the opener. A founder/exec spends
**≤3 seconds** on a cold message, in a pile of "job please" notes. The first touch's only job is to
earn a reply. Sequence it:

- **Touch 1 — LinkedIn only. A LURE, not a pitch.** Open with an intriguing **story hook** ("I've
  got a story about how I [concrete result]"), drop **one proof number** (e.g. "8 weeks to 4"), then
  **reverse the ask**: be genuinely curious how *they* do it and say you'd "probably learn more than
  you'd share." Ask for *nothing* — no meeting, no deck, no job. A curiosity gap + a flattering
  reverse-ask is what survives the 3-second scan and beats the "job please" pile, because there's
  nothing to decline. End on an **open question**.
- **Touch 2 — only after they reply.** Now deepen the *problem* (in their worldview), offer to share
  how you'd shape it, tease the one-pager/deck. Still no job ask.
- **Touch 3 — send the memo + deck.** Only once they're engaged on the problem.
- **Speak their language, don't quote it.** Frame the problem the way *they* would describe it
  (from the recipient dossier) — but never literally quote their profile/posts back. The former
  signals "this person gets my world"; the latter signals "this person stalked me."
- **Hold back self-interest signals.** Don't mention the new office / your relocation / the role you
  want in the opener — it flips the read from "interesting peer" to "wants something." Let those
  surface only when *they* ask (e.g. "where are you based?").
- **Respect their stated philosophy.** If they deliberately chose bespoke over productized (or any
  strong public stance), frame your idea as *protecting* that choice, not overturning it.
- **Sound human, not AI.** No em-dashes, no arrows (→), no over-polished symmetry. Short sentences,
  contractions, a little informality. Read it aloud — if it sounds like a press release, rewrite it.
- **Mind the channel limits.** LinkedIn connection-request notes are **hard-capped at 300 chars**
  (count them; the platform counts every space). A subject/heading only shows on InMail or an
  existing thread, not on a connection request.

## Tone rules (consultative hypothesis — non-negotiable)
- You are an **outsider with a hypothesis**, not a consultant with a diagnosis. Frame the
  problem as "here's a pattern I noticed — am I reading this right?"
- Lead with **their** situation and evidence; earn the "why me" only after.
- **Value-first**: the ask is the problem/a conversation, never "give me a job" — and the cold
  opener asks for nothing at all (see the Cold-outreach playbook).
- No flattery, no hype, no presumption that they haven't thought of this.
- Short. A busy VP skims. The memo is one page; the message is a few lines.
- **Use the candidate's OWN language and frameworks.** Never import vocabulary, framing, or named
  concepts from another company's corpus / a prior client's confidential material — it's an
  originality and confidentiality risk, and it shows. Borrowed categories (e.g. calling a services
  firm an "SI" when it isn't) also misread the target — get the category right first.

## Anti-patterns — do NOT do these
- Don't state a company fact without a dated, cited source.
- Don't invent a problem, a person, a title, or a contact detail. UNVERIFIED means UNVERIFIED.
- Don't claim to have read paywalled analyst/consultant material you didn't access.
- Don't pitch a problem the candidate can't back with real, attributed evidence from memory.
- Don't inflate the candidate's attribution (no "led" where memory says "contributed to").
- Don't write a confident "I solved your problem" pitch — that's the naive version that backfires.
- Don't let the deck claim anything the memo (and confidence-ledger) doesn't support.
- Don't skip the confidence-ledger. It's the part that keeps the pitch honest.
- **Don't conflate "exists/described" with "operational."** A claim can be MEDIUM-HIGH on one axis
  (an office/team is *described* as X) and LOW-MEDIUM on another (it's *running* today). Split the
  confidence; say "they're standing up X," not "they run X," when the source says "building."
- **Don't trust a single self-marketing source.** If the only evidence is the company's own careers
  page / marketing, flag it and note when primary press *omits or contradicts* it. Seek a second,
  independent source before asserting.
- **Don't quote a person's profile/interviews back to them** in outreach (creepy). Don't lead the
  cold opener with what *you* want (job/relocation/the office).
- **Don't pitch the most senior name by default** — pitch whoever will actually read and reply.
- **Don't borrow another corpus's vocabulary or a wrong category.** Verify the target entity (parent
  vs. subsidiary/JV/office) before building the whole pitch around it.
- **Don't leave placeholder contact details** (`[LinkedIn]`, `[phone]`) or em-dashes/AI-tells in
  final drafts.
