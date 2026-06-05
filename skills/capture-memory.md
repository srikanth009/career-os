---
name: capture-memory
description: In-flow memory capture for career-os. Whenever any skill (tailor-resume, triage-jds) hits a fact it does not know — a missing metric, an unverified attribution, a JD requirement with no evidence — it asks the user in chat right then and writes the answer back into the correct memory file. This is the fast, synchronous complement to open-questions.yaml (the async backlog). Prefer asking in chat over logging-and-waiting whenever the unknown blocks the current task.
---

# Skill: capture-memory

## Why this exists
`open-questions.yaml` is an **async backlog** — useful, but it makes the user go find a file and write YAML. The user has asked for the opposite default: **when you need something, ask in chat; they answer fast; you persist it.** This skill is that loop. It is invoked *inline* by other skills, not usually on its own.

## The two channels (decide which, every time)
- **Chat (sync, default when the unknown blocks the current task).** A JD must-have with no evidence, a metric the resume needs but whose attribution is unconfirmed, an archetype tie — ask the user now.
- **open-questions.yaml (async, for unknowns that do NOT block the current task).** Things worth knowing eventually but not needed to finish what you're doing. Log them; don't interrupt for them.

Rule of thumb: *if not knowing it would change the artifact you're about to produce, ask in chat.* Otherwise, log it.

## The capture loop

### 1. Detect + classify
Note the unknown and decide: blocking-now (→ chat) or nice-to-have-later (→ open-questions.yaml).

### 2. Ask — batched, specific, one-line-answerable
- **Batch every blocking unknown for this task into ONE message.** Do not interrogate one question at a time — the user explicitly wants to answer fast in a single pass.
- Make each question answerable in one line. State *why* you're asking and what the answer unblocks (mirror the `user_unblock` style in open-questions.yaml).
- Offer a default / "skip" for each, so the user can dismiss a question they can't answer.

Example batch:
```
Three things would sharpen this resume — quick answers and I'll save them:
1. RFP win-rate "5%→15%" — measured where (dashboard / CRM / estimate)? [unblocks: defensibility for analytical-PM roles]
2. The "+8% retrieval accuracy" — vs what baseline + metric (NDCG@k / MRR / internal eval)? [unblocks: AI/ML PM credibility]
3. JD wants "people management" — have you managed anyone (incl. interns/contractors)? If no, I'll mark it a confirmed gap and stop asking. [unblocks: this JD's must-have]
```

### 3. Persist — write the answer to the RIGHT file
Routing table:

| Answer is about… | Write to | Also set |
|---|---|---|
| A metric's value / provenance / attribution | `projects/<slug>.yaml` or `roles/<role>.yaml` (the field) | `source_confidence`, `attribution` |
| A whole new project | `projects/<slug>.yaml` (use `ingest-update` schema) | link slug into `roles/<role>.yaml` |
| A new / clarified interview story | `stories.yaml` | — |
| An objection + how to answer it | `stories.yaml.anticipated_objections` | `risk_level`, `suggested_answer` |
| Identity / contact / recognition | `profile.yaml` | `source_confidence` |
| Credential / degree clarification | `education.yaml` | display-label rules |
| A confirmed *absence* ("I haven't done X") | `open-questions.yaml` as resolved-gap | so it is never re-asked |
| Still uncertain after asking | `open-questions.yaml` (async) | — |

When persisting:
- Add a dated provenance comment, e.g. `# confirmed via chat 2026-05-31`.
- **Never silently overwrite** an existing value — comment the old one: `value: "30% YoY"  # was "25% YoY" until 2026-05-31, confirmed via chat`.
- If the answer resolves an `open-questions.yaml` entry, move it to `contradictions_resolved` (or delete if it was a pure missing-fact), so the backlog shrinks.

### 4. Record confirmed gaps too
If the user says "no / I don't have that / skip": that is itself information. Write it to `open-questions.yaml` as a **resolved gap** (`resolution: "confirmed absent via chat <date>"`). This stops the system from re-asking the same dead end on the next JD, and tells the tailoring engine to route it to interview-prep instead of the resume.

### 5. Re-validate dependents (only if structural)
If the answer added/changed a project or role, ask once: "Do the narrative files still reflect memory?" Update only if needed. Skip this for simple metric-provenance answers.

### 6. Confirm back in one line
Tell the user what was saved and where, e.g.:
`Saved: metric provenance → roles/<current-role>.yaml (source_confidence: high); resolved 1 open-question.`

## Anti-patterns
- Don't dump a blocking unknown into `open-questions.yaml` and proceed as if answered. If it blocks, ask.
- Don't ask one question per message. Batch.
- Don't invent a value to avoid asking. The whole system exists to refuse invention.
- Don't overwrite history. Comment the prior value.
- Don't re-ask something the user already declined — that's what the resolved-gap record is for.
