---
name: memory-audit
description: Use this skill when the user asks to "audit memory", "find inconsistencies", "check for gaps", "what might be missing", "sanity check the docs", or "what did we miss". Looks specifically for things the update-memory skill and normal session-end updates tend to miss — design drift, contradictions between sources, undocumented decisions, and orphaned references.
version: 1.0.0
---

# Memory Audit

Finds things that fall through the cracks — contradictions, drift, undocumented decisions, and references that no longer match reality. This is the skeptic pass; update-memory handles the sync pass.

## What this looks for (that the sync pass misses)

### 1. Contradictions between memory tiers
- A design decision documented differently in `architecture.md` vs the Second Brain
- A milestone listed as "done" in one place and "queued" in another
- Different descriptions of the same system in `project_milestones.md` vs `game_roadmap.md`
- `CLAUDE.md` describing behavior that no longer matches the code

### 2. Undocumented decisions
- Systems in the code that have no memory entry explaining *why* they work the way they do
- Constants or magic numbers in `settings.py` with no corresponding design decision logged
- JSON fields in data files (enemies.json, quests.json, etc.) that don't appear in any memory doc
- Files in FILE_MAP.md that aren't mentioned in any memory file

### 3. Stale references
- Memory files that name specific functions, file paths, or flags — verify they still exist with Grep/Read
- Architecture rules in CLAUDE.md or memory that reference patterns no longer in the code
- "Next steps" or "queued" items in memory that were actually completed but not marked done

### 4. Story/roadmap drift
- Characters, zones, or quests described in `game_roadmap.md` that contradict what's in `quests.json` or `dialogue.json`
- Milestone numbers in the Second Brain that don't match the `.claude` memory milestone numbering
- Systems listed as "deferred" that have since been partially built

### 5. Gaps in session coverage
- Commits in `git log` that don't correspond to any session log entry in the Second Brain
- Work described in memory that has no git commit (was it actually saved?)
- Features play-tested and confirmed working but not noted as such in memory

## Workflow

1. Read `git log --format="%h %ad %s" --date=short -30`
2. Read `CLAUDE.md`, all `.claude` memory files, and the Second Brain file
3. Spot-check 2–3 key systems: grep for a function/class named in memory, confirm it exists and matches the description
4. Read `game/settings.py` — flag any constants with no memory explanation
5. Scan `data/*.json` field names — flag any undocumented fields
6. Check FILE_MAP.md entries against memory docs

## Output format

Produce a numbered list of findings. For each:

```
[FINDING #N — TYPE]
Where found: <file or source>
Issue: <what's wrong or missing>
Suggested fix: <what should be updated and where>
```

Types: CONTRADICTION, STALE_REFERENCE, UNDOCUMENTED, GAP, DRIFT

End with a short summary: total findings by type, and which ones are highest priority to fix.

Do NOT make any edits — this skill only reports. After reviewing the findings, the user can ask the update-memory skill (or Claude directly) to fix them.
