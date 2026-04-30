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

## Second Brain duties
Bobby's Obsidian vault lives at:
`C:\Users\bobby\OneDrive\Documents\Claude Code\Second Brain\`

**Update these files during/after every session:**
- `Projects/active/Survival Game.md` — update milestone table, session log, resume talking points as work progresses
- `Reviews/YYYY-MM-DD - Survival Game Session.md` — create at end of meaningful sessions (what was built, decisions made, patterns learned)
- `Knowledge/` — if anything technically interesting is researched or solved, save a note there

Don't wait until the end. Update the project file as milestones complete.

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
**Last completed:** M9 — zone transitions + second zone  
**Next:** M10 — Combat complete (enemy AI, enemy damage, player death/respawn, item usage)

Full milestone table in `Survival Game.md` in the second brain.

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
- **WASD / arrows** — move + jump (W = jump)
- **Z** — attack
- **1–8** — hotbar slots
- **C** — crafting menu
- **E** — interact with NPC / advance dialogue
- **Esc** — close menu / quit
