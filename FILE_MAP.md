# FILE MAP
*One-line purpose per file. Updated at the end of every session. This is the first thing read each session.*

---

## Root
| File | Purpose |
|------|---------|
| `main.py` | Entry point — initializes pygame, creates engine, starts game loop |
| `settings.py` | All constants: screen size, FPS, colors, physics values, tuning numbers |
| `FILE_MAP.md` | This file — map of every file's purpose |
| `requirements.txt` | Python dependencies |
| `save.json` | Auto-generated save file — zone, player position/health/inventory, collected zone drops |

## core/
| File | Purpose |
|------|---------|
| `core/engine.py` | Main game loop, clock, screen surface, top-level update/draw calls |
| `core/camera.py` | Scrolling camera — tracks player, converts world coords to screen coords |

## entities/
| File | Purpose |
|------|---------|
| `entities/player.py` | Player class — movement, physics, facing direction, attack cooldown, inventory, hotbar slot |
| `entities/enemy.py` | Enemy class — health, hit-flash timer, take_damage(), alive flag, loot table |
| `entities/item_drop.py` | World item drop — rect, item_id, quantity, color, alive flag, zone_drop_index |
| `entities/npc.py` | NPC class — rect, name, color, dialogue lines, [E] Talk proximity prompt |

## systems/
| File | Purpose |
|------|---------|
| `systems/combat.py` | AttackHitbox — temporary rect spawned on swing, already_hit set prevents multi-hit, expires after ATTACK_DURATION |
| `systems/inventory.py` | Inventory class — fixed slot list, add/remove/count/serialize, loads item defs from items.json |
| `systems/crafting.py` | CraftingSystem — loads recipes.json, can_craft check, craft (consume ingredients + add result) |
| `systems/saving.py` | save_game / load_game — JSON serialization of zone, player state, collected zone drops |

## world/
| File | Purpose |
|------|---------|
| `world/world.py` | Owns the active zone + all data registries; engine talks here, not to Zone directly |
| `world/zone.py` | Loads a single zone JSON file; builds platforms, enemies, save points, item drops, NPCs |

## ui/
| File | Purpose |
|------|---------|
| `ui/hud.py` | HUD overlay — health bar (top-left) and hotbar slots (bottom-center), screen space only |
| `ui/menus.py` | CraftingMenu overlay — recipe list, ingredient counts, cursor nav, feedback flash |
| `ui/dialogue.py` | DialogueBox — word-wrapped NPC dialogue panel above hotbar, advances on E |

## data/
| File | Purpose |
|------|---------|
| `data/enemies.json` | Enemy type definitions — health, size, drop tables |
| `data/items.json` | Item type definitions — name, color, stackability, use effects |
| `data/recipes.json` | Crafting recipe definitions — result, count, ingredients |
| `data/npcs.json` | NPC type definitions — name, color, size |
| `data/dialogue.json` | Dialogue scripts keyed by dialogue_id — ordered list of lines per script |
| `data/zones/zone_01.json` | First zone — platforms, enemy spawns, save point, item drops, NPC |

## assets/
| Folder | Purpose |
|--------|---------|
| `assets/sprites/` | All sprite sheets and individual sprites |
| `assets/sounds/` | Sound effects and music |
| `assets/fonts/` | Font files |
