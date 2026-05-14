---
name: end-session
description: Use this skill when the user says "end session", "wrap up", "we're done", "save everything", "end the session", or "commit and close". Runs the full session-close checklist — commits, memory sync, Second Brain update, and session review.
version: 1.0.0
---

# End Session

Runs the full close-of-session checklist in order. Do not skip steps even if nothing seems to have changed — verify each one.

---

## Step 1 — Commit any uncommitted work

```bash
git status
git diff --stat
```

If there are uncommitted changes:
- Stage relevant files (never `git add -A` blindly — check for .env, save.json, screenshots, large binaries)
- Write a descriptive commit message summarizing what was built this session
- Commit

If nothing to commit, note that and move on.

---

## Step 2 — Check FILE_MAP.md

Read `FILE_MAP.md`. If any files were added, removed, or meaningfully changed this session that aren't reflected there, update it.

---

## Step 3 — Sync `.claude` project memory

Read all files in `.claude/projects/C--Users-bobby-survival-game/memory/`. For each one, check whether this session's work makes any entry stale:

- `project_milestones.md` — mark newly completed milestones done, update "Last completed" date, move anything started to in-progress, add new queued items
- `architecture.md` — update file structure or design decisions if anything changed
- `game_roadmap.md` — update only if story/character/zone design changed
- `user.md` / `feedback.md` — add anything learned about Bobby's preferences or corrections this session

Update whatever is stale. If nothing changed, note that.

---

## Step 4 — Update the Second Brain

File: `C:\Users\bobby\OneDrive\Documents\Claude Code\Second Brain\Projects\active\Survival Game.md`

Update:
- `updated:` frontmatter date → today
- **Current Status** section — last completed, branch state, what's next
- **Milestone table** — mark done milestones ✅ with date, update queued/next
- **Session Log** — append one entry for today's session in this format:
  ```
  - **YYYY-MM-DD** — [What was built, bullet style, specific and detailed]
  ```

---

## Step 5 — Write a session review

Only if meaningful work was done (more than minor config changes). Skip for short/exploratory sessions.

Create: `C:\Users\bobby\OneDrive\Documents\Claude Code\Second Brain\Reviews\YYYY-MM-DD - Survival Game Session.md`

Use this format:
```markdown
---
tags: [review, session, survival-game]
updated: YYYY-MM-DD
---

# Session Review — YYYY-MM-DD

## What got built
[Per-milestone or per-feature breakdown. Be specific — file names, system names, key decisions made.]

## Lessons / patterns worth remembering
[Non-obvious things that came up — architecture insights, bugs caught, design decisions and why.]

## Next
[Exactly what the next session should start with.]
```

---

## Step 6 — Save to Knowledge/ (optional)

If this session produced a technically interesting solution worth saving as a standalone reference (a novel pattern, a non-obvious fix, a useful algorithm), create a file in:
`C:\Users\bobby\OneDrive\Documents\Claude Code\Second Brain\Knowledge\`

Only do this if something genuinely novel came up. Don't create a knowledge file for routine work.

---

## Step 7 — Update CLAUDE.md

Read the **Current status** section of `CLAUDE.md`. If it's stale (wrong "Last completed" date, wrong "Next" milestone, missing systems in "What's built"), update it.

---

## Final report

Tell Bobby:
- What was committed (or that nothing needed committing)
- Which memory files were updated and what changed
- Whether a session review was written and where
- Whether CLAUDE.md was updated
- What the next session should start with
