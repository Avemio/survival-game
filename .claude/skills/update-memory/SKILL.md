---
name: update-memory
description: Use this skill when the user asks to "update memory", "sync memory", "check if memory is current", "make sure everything is up to date", or "update the docs". Audits all memory sources against ground truth (git log, codebase, Second Brain) and rewrites anything out of sync.
version: 1.0.0
---

# Update Memory

Cross-checks all memory tiers against ground truth and updates anything stale.

## Sources of truth (in priority order)
1. `git log --oneline -20` — what was actually committed and when
2. Live codebase files — what systems actually exist right now
3. `.claude` project memory files — quick-access facts
4. Second Brain (`C:\Users\bobby\OneDrive\Documents\Claude Code\Second Brain\Projects\active\Survival Game.md`) — full session log

## Step 1 — Gather ground truth

Run these in parallel:
- `git log --format="%h %ad %s" --date=short -20` — recent commits with dates
- Read `FILE_MAP.md` — actual file structure
- Read `data/` JSON files (enemies.json, items.json, quests.json, etc.) — actual content counts
- Check `assets/sprites/` for what sprites exist

## Step 2 — Read all memory files

Read every file in `.claude/projects/C--Users-bobby-survival-game/memory/`:
- `MEMORY.md` (index)
- `project_milestones.md`
- `architecture.md`
- `game_roadmap.md`
- `user.md`
- `feedback.md`
- Any other `.md` files present

Also read the Second Brain file.

## Step 3 — Identify gaps

Compare memory against ground truth. Flag anything where:
- A milestone is marked queued but the code/commit shows it's done
- A milestone is marked done but no corresponding code exists
- File paths or system names in memory don't match FILE_MAP.md
- Second Brain session log is missing sessions that appear in git log
- Second Brain milestone table is behind the `.claude` memory
- The "Last completed" date in any file doesn't match the latest commit date
- Any system described in memory doesn't match how it actually works in code

## Step 4 — Update

For each gap found:
- Update the relevant `.claude` memory file (use Edit, not full rewrite unless >30% changed)
- Update the Second Brain file if its session log or milestone table is behind
- Update `MEMORY.md` index if any memory file was added or renamed
- Update the `updated:` frontmatter date in the Second Brain file

## Step 5 — Report

Tell the user:
- What was checked
- What was out of date (and what you changed)
- What is confirmed current
- Anything you couldn't verify automatically (e.g., systems that exist in memory but weren't checked because the files are large)
