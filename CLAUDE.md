# Survival Game — Claude Instructions

## What this project is
2D side-scrolling survival RPG in Python + Pygame. Handcrafted zones, action combat, NPC dialogue, crafting, save/load. Building milestone by milestone toward a playable game.

**Repo:** https://github.com/Avemio/survival-game  
**Run:** `python main.py` from project root

---

## Session start checklist
1. Read `FILE_MAP.md` — one-line purpose per file, canonical source of truth for structure
2. Read `C:\Users\bobby\OneDrive\Documents\Claude Code\Second Brain\Projects\active\Survival Game.md` — milestone status, design decisions, session log
3. Check `git log --oneline -10` to see what was last committed

---

## Skills

Project-specific skills live in `.claude/skills/`. Invoke them with `/skill-name`.

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `end-session` | `/end-session` | Full close-of-session checklist — commit, FILE_MAP, memory sync, Second Brain update, session review |
| `update-memory` | `/update-memory` | Syncs all memory tiers against git log + codebase; rewrites anything stale |
| `memory-audit` | `/memory-audit` | Skeptic pass — finds contradictions, stale references, undocumented decisions, and gaps the sync pass misses. Reports only, no edits |

Run `/end-session` at the end of every session.
Run `/memory-audit` when something feels off or memory hasn't been audited in a while.

---

## Memory systems

**Two tiers — both matter:**

### `.claude` project memory (auto-loaded, fast)
Lives at `.claude/projects/.../memory/`. Loaded automatically at session start.
Use for: quick-access facts, user preferences, confirmed patterns, concise milestone backlog.
**Update this whenever something important is learned mid-session.**

### Second Brain (manual read, full detail)
Bobby's Obsidian vault: `C:\Users\bobby\OneDrive\Documents\Claude Code\Second Brain\`
Use for: full session logs, detailed milestone specs, design decisions, resume talking points.

**Update these files during/after every session:**
- `Projects/active/Survival Game.md` — milestone table, full session log, pending work detail
- `Reviews/YYYY-MM-DD - Survival Game Session.md` — create at end of meaningful sessions
- `Knowledge/` — technically interesting solutions worth saving

The `.claude` memory holds the *quick facts*. The Second Brain holds the *full story*.

---

## Codebase structure
See `FILE_MAP.md` for full detail. Short version:

```
game/
  core/       engine.py (main loop), camera.py
  entities/   player, enemy, npc, item_drop
  systems/    combat, inventory, crafting, saving
  world/      world.py (zone registry), zone.py (loads JSON)
  ui/         hud, menus (crafting), dialogue
data/
  zones/      zone_01.json, zone_02.json
  enemies.json, items.json, recipes.json, npcs.json, dialogue.json
```

---

## Current status
**Last completed:** 2026-05-17 — Story redesign (Steve/Caldrath/The Sow), Pixellab sprite pipeline, enemy animation system, 22-review bug sweep
**Next:** Generate fast + archer enemy sprites (`python tools/generate_sprites.py`), then settings menu (M15)

**What's built:** trading (gold/shop/shopkeeper), XP/leveling, chests, title screen, quest system
(4 quests, NPC givers, J key log), archer enemy type (ai_type="ranged"), content editor
(tools/editor.py, 8 tabs), packaging (package.py → dist/), zone_02, world-bounds camera clamping,
cross-reference validation, O(1) inventory count, pre-rendered UI surfaces,
Animator system (play_once + foot_y pinning), data-driven SpriteLoader (data/sprites/{name}.json),
player assassin sprites (idle/run/jump/attack), enemy animation system (foot-pin rendering),
Sergeant at Arms + City Watchman animated, Pixellab API generator (tools/generate_sprites.py),
can_jump enemy flag, 22 bugs fixed (EventBus, arrow tunneling, zone transition cleanup, JSON safety)

**Queued:** fast + archer enemy sprites, settings menu, sound effects, day/night cycle, zone redesign for Steve story

Full detail in `.claude` project memory — read architecture.md and project_milestones.md.

---

## Architecture rules
These are established patterns — don't break them:

- **Engine owns everything, nothing owns engine.** Systems (combat, inventory, crafting) don't import each other.
- **Data-driven.** Enemies, items, zones, NPCs, dialogue, recipes are all JSON. Adding content = editing data, not code.
- **Delta-time physics everywhere.** All movement, timers, and cooldowns use `dt` (seconds). Never frame-based numbers.
- **Fonts created at `__init__`, never inside `draw()`.** Creating fonts every frame is a known pygame pitfall.
- **In-place list mutation** (`self.enemies[:] = [...]`) keeps references valid across the codebase.
- **Rising-edge detection** for one-shot triggers (save points, zone exits): `was_overlapping` flag.
- **`camera.apply_tuple(rect)`** for all `pygame.draw` calls. `camera.apply(rect)` (returns Rect) only when you need `.centerx`, `.top`, etc.

---

## Key design decisions
| Decision | Choice |
|----------|--------|
| Healing | Full heal at save points + craftable potions |
| Enemy drops | Don't persist (enemies respawn each load) |
| Zone drops | Persist per-zone via index in save file |
| Save writes | Atomic: write `.tmp` → `os.replace` |
| Zone transitions | Auto-save on exit, per-zone drop dict |
| World pause | Crafting menu and dialogue both pause update() |

---

## Coding conventions
- All new files get a module docstring: what it owns, what it does NOT own
- Settings constants go in `game/settings.py` — nothing hardcoded elsewhere
- New entity types go in `entities/`, new data in `data/`, new UI in `ui/`
- Update `FILE_MAP.md` whenever a file is added or its purpose changes
- Commit after each milestone with a descriptive message

---

## Controls (for testing)
- **WASD / arrows** — move + jump (W/Space/Up = jump)
- **Z** — attack
- **Q / R** — ability slots (equip scrolls first with F)
- **Hold X** — draw bow (Up/Down to aim, release to fire)
- **F** — use/equip selected item
- **1–8** — hotbar slots
- **I** — inventory screen (32 slots)
- **J** — quest log
- **C** — crafting menu
- **E** — interact with NPC / advance dialogue / open shop / open chest
- **Tab** — switch Buy/Sell in shop
- **Esc** — close menu / pause
