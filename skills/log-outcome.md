---
name: log-outcome
description: Record what happened to a tailored application in memory/outcomes.yaml — applied or not, callback, interview, offer, rejection. Triggers when the user reports a result ("got a callback from <company>", "<company> rejected me", "applied to <company> today", "log outcome for ..."). Closes the loop on the apply-gate so the RECOMMEND-AGAINST threshold can later be tuned from real data.
---

# Skill: log-outcome

## What this does
Updates one entry in `memory/outcomes.yaml` with a real-world result. That file pairs the ATS score + apply verdict (frozen at tailor time) with the actual funnel outcome, so over time you can see whether the score predicts callbacks and re-calibrate the gate.

## Process
1. Identify the application. Match the user's wording (company / role / date) to a `jd:` slug in `outcomes.yaml`. If no entry exists yet (e.g., a JD tailored before this file existed, or applied without tailoring), create one — copy the schema from an existing entry and fill what's known.
2. Update only the fields the user reported. Funnel: `applied → callback → interview → offer`, each `true`/`false`. Set `rejected: true` (with the stage in `notes`) if rejected. Set `applied_date` when they say they applied.
3. If the user is also backfilling the `apply_verdict` (what the gate said), record it — that's the column the calibration analysis needs.
4. Append anything useful to `notes` (recruiter feedback, why rejected, comp). Recruiter feedback is gold — if it contradicts a resume claim or reveals a new objection, ALSO route it: a new objection → `stories.yaml.anticipated_objections` (via capture-memory), a contradiction → fix the source file + log in `open-questions.yaml`.
5. Confirm in one line what was updated.

## Calibration check (only once there's data)
When `outcomes.yaml` has ~10+ entries WITH results, you may surface a quick read on request:
- Callback rate by `ats_band` (STRONG / SOLID / BORDERLINE / WEAK).
- Did any RECOMMEND-AGAINST application get a callback? (If several did, the gate is too strict.)
- Did APPLY-verdict applications convert? (If not, the gate is too loose or the resumes are off.)
This is descriptive only — do NOT auto-change the gate thresholds in `tailor-resume.md`; report the pattern and let the user decide.

## Rules
- Never fabricate an outcome. `null` means unknown — leave it.
- Don't delete entries. A rejection is data, not something to clean up.
- Dates ISO (`YYYY-MM-DD`).
