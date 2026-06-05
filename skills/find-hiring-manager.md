---
name: find-hiring-manager
description: Stage 5a of the pipeline — for a specific top-tier role (a triage GO/BORDERLINE the user chose to pursue), identify the most likely HIRING MANAGER / owning person and a realistic, account-safe reach path. Account-SAFE by design — uses only public web search + X-ray (never logged-in LinkedIn people-search, which flags accounts) and is SUGGESTION-ONLY (never connects, messages, or sends anything; the human does all outreach). Also consumes scout-jds' hiring-leads.jsonl (linkedin-posts-xray hits where someone is openly hiring). Produces a ranked candidate list with verified sources, confidence, and a reach path — NOT a contact dump. Triggers on "find the hiring manager for [role]", "who do I reach at [company] for [role]", "work the hiring leads", or `/find-hiring-manager`.
---

# Skill: find-hiring-manager

## What this does
Given a specific role the user has decided to pursue (a triage **GO/BORDERLINE**, top-tier only —
this is effort-intensive, don't run it on the whole funnel), it finds **who likely owns the hire**
and **how the user could realistically reach them** — without touching anything that risks the
user's LinkedIn account and without sending a single message. It is the bridge between a tailored
resume and the `pitch-company` outreach engine: find-HM answers "*who*", pitch-company answers
"*what to say*".

It obeys the same non-negotiable rule as the rest of career-os:

> **Never invent a person, a title, or a contact detail.** No name without a real, dated, cited
> public source. No email unless it's a known published pattern, and then it's labeled
> `UNVERIFIED — pattern-inferred`. When you can't find a real person, say so and give the title to target.

## Account safety — read first (this is why the skill exists)
- **NEVER drive logged-in LinkedIn people-search / "see who works here" / Sales Navigator.** That
  behavior is exactly what flags accounts. This skill uses only: public web search, public X-ray
  (`site:linkedin.com/in`, `site:linkedin.com/posts`), company leadership/about pages, press, and
  conference/speaker listings. All unauthenticated.
- **SUGGESTION-ONLY.** This skill NEVER sends a connection request, message, InMail, or email, and
  never opens an "apply"/"connect"/"send" control. It outputs *who and how*; the human does the rest.
- Human-in-the-loop on every step — the user reviews and eliminates bad candidates before any outreach.

## What this does NOT do
- Does NOT scrape logged-in LinkedIn or any authenticated surface.
- Does NOT message, connect, or send anything (that's the human, later).
- Does NOT do the company problem/solution research or write the pitch — that's `pitch-company`.
- Does NOT fabricate a person, title, email, or LinkedIn URL. UNVERIFIED stays UNVERIFIED.
- Does NOT compile broad personal data — only the work-relevant, public facts needed to reach ONE
  owning person for THIS role.

## Pre-flight
- The target role must be a **fetched, triaged JD** (a GO/BORDERLINE in a run dir), OR a hiring lead
  from `scout-jds`' `hiring-leads.jsonl`. If neither exists, STOP — find-HM needs a real anchor, not
  a company name alone (that's `pitch-company` Discovery mode's job).
- Read `memory/profile.yaml` for the user's own real contact details + any overlap signals
  (shared school/employer/community) usable for a warm intro.
- The **WebSearch** tool must be available. If not, STOP and say so — do not guess people.

---

## INPUT MODES
- **Mode A — JD-anchored** (default): user names a role/company from a triage run. Use the JD's
  team/scope/seniority signals to infer the owning function.
- **Mode B — hiring-lead** (`work the hiring leads`): read `hiring-leads.jsonl` from the latest
  scout run. Each lead is already a person openly posting about hiring — the HM identification is
  half-done; verify and enrich.

## Step 1 — Read the role's owning signals
From the fetched JD (or the lead's post), pull what tells you who owns it: the **team/org named**,
the **reporting line if stated** ("reports to the Director of Platform"), the **scope/seniority**,
and the **location/site**. The owning manager is usually 1-2 levels above the role's seniority,
inside the named function — not the CEO, not HR. Write the inferred **owning function + seniority**
(e.g. "Head of Platform PM, India" / "Director, AI Products").

## Step 2 — Find named candidates (public sources only)
Search for real people who plausibly hold that owning function. Account-safe shapes:
- `site:linkedin.com/in "<company>" ("Head of Product" OR "Director of Product" OR "VP Product") (platform OR AI) <city>`
- Company leadership / "our team" / "about" page (often names directors+).
- Press quotes, podcast/conference speaker bios, the company blog's author bylines.
- For Mode B: the lead's own post + profile is the primary candidate — verify their role.
For each candidate capture `{ name, title, source_url, date, confidence }`. Titles churn — date and
confidence-flag everything. **Verify the real LinkedIn URL from a public source (ideally their own
posts) — never guess a vanity URL.** If you can only find a paraphrase of someone's words, don't
attribute quotes to them.

## Step 3 — Rank by REACHABILITY, not seniority
The goal is a reply, not the most impressive name. Rank candidates by probability of actually
reading and responding:
- **Higher**: the role's direct hiring manager, a short-staffed team lead, someone who *personally
  posted* the role (Mode B leads are gold), a founder/eng-leader at a smaller company, a peer-level
  IC who could refer.
- **Lower**: a flooded big-company exec / MD with a locked-down inbox, anyone 3+ levels above the role.
Note any **warm-intro path** (shared school/employer/community from `profile.yaml`) — a warm path
beats any cold target and jumps to the top.

## Step 4 — Reach path (best-to-worst, suggestion-only)
For the top 1-2 candidates, lay out the reach options the *human* could use:
1. **Warm intro** — name the overlap and who could introduce, if any.
2. **LinkedIn** — connection note / message (the human sends it; provide the verified profile URL).
3. **Inferred email** — ONLY via a known published company pattern (e.g. `first.last@company.com`
   confirmed from a real public address). Label `UNVERIFIED — pattern-inferred`. Never present a
   guessed email as fact; never fabricate one.
Pull the user's own real LinkedIn/email/phone from `profile.yaml` so the handoff to pitch-company
has no placeholders.

## Step 5 — Write the output
Write to the role's run dir (or the JD's tailoring dir): `hm-candidates.md`:
```markdown
# Hiring-manager candidates — <Title> @ <Company>
**Role source**: <jd url / hiring-lead url>   ·   **Found**: <YYYY-MM-DD>   ·   **Account-safe**: yes (public sources only)

## Owning function (inferred)
<title + seniority>, <team>, <location> — basis: <JD signal cited>

## Candidates (ranked by reachability)
### [1] <Name> — <Title>  ·  reachability: <HIGH/MED/LOW>  ·  confidence: <H/M/L>
- Why them: <one line — why they likely own this hire>
- Source: <url> (<date>)
- Verified LinkedIn: <url, from public source> | not found
- Reach path: <warm intro via X | LinkedIn message | UNVERIFIED email pattern>
- Worldview cues (to understand them, NOT to quote): <prior cos / public stance, cited> | none found

### [2] ...

## If no real person found
Target this title: <function + seniority>. Reach path: <company careers / team page / referral>.

## Handoff
Top target: <Name or title>. Next: `pitch myself to <Company>` (pitch-company) to build the
problem/solution + outreach sequence for this person. The HUMAN sends everything.
```

## Step 6 — Report
```
Hiring-manager candidates for <Title> @ <Company> — see <dir>/hm-candidates.md

Top target: <Name>, <Title>  (reachability <H/M/L>, confidence <H/M/L>, source dated <date>)
Reach path: <warm intro / LinkedIn / unverified email>
Other candidates: <N>   ·   Sources: public web only (account-safe)

Honest read: <can we actually reach a real owner, or is this only a title to aim at?>
Next: run pitch-company for the problem/solution + outreach. You send it — I never do.
```

## Anti-patterns — do NOT do these
- Don't drive logged-in LinkedIn people-search or any authenticated lookup. Public sources only.
- Don't send, connect, or message anything. Suggestion-only — the human does outreach.
- Don't invent a name, title, LinkedIn URL, or email. Guessed contact detail = fabrication.
- Don't default to the most senior name; rank by who will actually reply.
- Don't quote a person's profile/posts back at them (that's pitch-company's rule too — it's creepy).
- Don't run this on every triaged role — it's for top-tier GO/BORDERLINE roles the user is pursuing.
- Don't do the company problem research here — hand that to pitch-company.
