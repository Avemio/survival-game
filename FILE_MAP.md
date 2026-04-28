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

## core/
| File | Purpose |
|------|---------|
| `core/engine.py` | Main game loop, clock, screen surface, top-level update/draw calls |
| `core/scene_manager.py` | Switches between scenes (menu, world, dungeon, dialogue) — owns scene stack |
| `core/camera.py` | Scrolling camera — tracks player, converts world coords to screen coords |

## entities/
| File | Purpose |
|------|---------|
| `entities/player.py` | Player class — movement, stats, state (health, resources), input handling |
| `entities/enemy.py` | Base enemy class — AI hooks, stats, combat interface |
| `entities/npc.py` | Town NPCs — dialogue triggers, shop interface |

## systems/
| File | Purpose |
|------|---------|
| `systems/combat.py` | Attack resolution, hit detection, damage calculation, knockback |
| `systems/inventory.py` | Item storage, equipping, hotbar logic |
| `systems/crafting.py` | Crafting recipes, resource consumption validation |
| `systems/saving.py` | Save/load game state, heal-to-full at save points |

## world/
| File | Purpose |
|------|---------|
| `world/world.py` | Master world — zone order, loads/unloads zones, tracks player position in world |
| `world/zone.py` | Base zone class — shared logic for all area types (platforms, entities, triggers) |
| `world/zones/zone_01_start.py` | Opening area — tutorial zone, story intro |

## ui/
| File | Purpose |
|------|---------|
| `ui/hud.py` | HUD overlay — health bar, resource meters, hotbar |
| `ui/dialogue.py` | Story text boxes, NPC conversation rendering |
| `ui/menus.py` | Title screen, pause menu, inventory screen |

## data/
| File | Purpose |
|------|---------|
| `data/enemies.json` | Enemy type definitions — stats, behavior flags, drop tables |
| `data/items.json` | All item definitions — properties, crafting recipes |
| `data/world.json` | Zone order, story beat triggers, world metadata |

## assets/
| Folder | Purpose |
|--------|---------|
| `assets/sprites/` | All sprite sheets and individual sprites |
| `assets/sounds/` | Sound effects and music |
| `assets/fonts/` | Font files |
