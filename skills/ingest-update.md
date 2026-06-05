---
name: ingest-update
description: Maintenance skill for the career-os memory layer. Triggers when user says they have a new project, new role, new metric, want to fix a contradiction, or wants to resolve an item in open-questions.yaml.
---

# Skill: ingest-update

## When to use this
- User completed a new project at current role → add to `projects/`
- User starts a new role → add to `roles/`, update `profile.yaml.years_of_experience`
- A metric changed (e.g., RFP win rate updated, ARR grew) → update the relevant role + project files
- A contradiction was discovered → resolve in source file + log in `open-questions.yaml.contradictions_resolved`
- An item in `open-questions.yaml` got an answer from the user
- User wants to add an interview story to `stories.yaml`
- User completed an interview and wants to capture a new anticipated objection

## What this skill does NOT do
- Does NOT auto-discover changes by scanning external sources (LinkedIn, other job boards). User must tell it.
- Does NOT modify multiple roles' attributions without explicit user confirmation.
- Does NOT delete from memory. If something is wrong, it gets corrected with a note about the prior value.

## Process

### Adding a new project
1. Ask user for:
   - Project title + slug
   - Role it belongs to (must match an existing `roles/*.yaml`)
   - Period
   - Problem space (3-5 bullets)
   - Actions taken (3-7 bullets)
   - Outcomes with metric values + confidence + attribution
   - Architecture / tech signals
   - Frameworks applied
   - 4-6 tags
   - Pre-composed bullets at relevant altitudes (mid-pm + at least one other)
   - Any open questions

2. Create `projects/<slug>.yaml` following the schema of existing files.

3. Update the parent `roles/<role>.yaml` → `projects:` list to include the new slug.

4. If new tags are introduced, surface them to the user — they may be reusable across other projects.

### Adding a new role
1. Ask user for:
   - Company (canonical name)
   - Title
   - Location
   - Start / end dates
   - Domain + industry tags
   - Scope (3-5 bullets of what they owned)
   - Headline metrics (each with attribution + source_confidence)
   - Tech stack
   - Linked projects (slugs)

2. Create `roles/<slug>.yaml`.

3. Update `profile.yaml.years_of_experience` if needed.

4. Prompt user: "Do any existing narratives in `narratives/*.md` need updating to mention this role?"

### Resolving an open question
1. Read `open-questions.yaml` and present the question to user.
2. Get user's answer.
3. Apply the answer to the relevant source file (role / project / education).
4. Move the question entry from `open-questions.yaml.low_confidence_metrics` to `open-questions.yaml.contradictions_resolved` (or delete if it was purely a missing fact, not a contradiction).
5. If the answer changes any existing bullet, ASK the user before silently re-writing the bullet — they may want to keep old framings for specific JDs.

### Updating a metric
1. Identify all files that reference the metric (search across `roles/`, `projects/`, `stories.yaml`).
2. Update all of them consistently.
3. Log the change in `open-questions.yaml.contradictions_resolved` with the old value + new value + date + reason.

### Adding an anticipated objection
1. Append to `stories.yaml.anticipated_objections`.
2. If the objection has a known good answer, capture it under `suggested_answer`. If not, mark `user_answer_needed: true`.

## Rule: never silently delete

If a field is being changed, write the old value as a comment so the history is recoverable:

```yaml
metric:
  value: "30% YoY"  # was "25% YoY" until 2026-Q2 — updated after a data review
```

## Rule: re-validate narratives after structural changes

After any change to roles/ or projects/, ask: "Do the three narrative files still accurately reflect what's in memory?" If yes, done. If no, update them.

## Rule: dates are ISO

All dates as `YYYY-MM` or `YYYY-MM-DD`. No "Q1 2024" or "early 2024".
