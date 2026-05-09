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
| `entities/projectile.py` | Arrow projectile — physics (gravity + wind), platform collision, enemy hit, oriented line draw |

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
| `world/zone.py` | Loads a single zone JSON file; builds platforms, enemies, save points, item drops, NPCs, buildings |

## ui/
| File | Purpose |
|------|---------|
| `ui/hud.py` | HUD overlay — health bar (top-left) and hotbar slots (bottom-center), screen space only |
| `ui/menus.py` | CraftingMenu overlay — recipe list, ingredient counts, cursor nav, feedback flash |
| `ui/dialogue.py` | DialogueBox — word-wrapped NPC dialogue panel above hotbar, advances on E |
| `ui/pause_menu.py` | PauseMenu overlay — controls reference + Resume/Quit; opened by Esc during gameplay |

## data/
| File | Purpose |
|------|---------|
| `data/enemies.json` | Enemy type definitions — health, size, drop tables |
| `data/items.json` | Item type definitions — name, color, stackability, use effects |
| `data/recipes.json` | Crafting recipe definitions — result, count, ingredients |
| `data/npcs.json` | NPC type definitions — name, color, size |
| `data/dialogue.json` | Dialogue scripts keyed by dialogue_id — ordered list of lines per script |
| `data/zones/zone_01.json` | First zone — platforms, enemy spawns, save points, item drops, NPC, building |
| `data/zones/zone_01_interior.json` | Interior zone for the Abandoned Cabin — entered via building door |

## tools/
| File | Purpose |
|------|---------|
| `tools/editor.py` | Standalone content editor (Tkinter) — run `python tools/editor.py`; edits all data JSON files; visual zone canvas |

## assets/
| Folder | Purpose |
|--------|---------|
| `assets/sprites/` | Sprites — drop a PNG and it auto-loads (see naming guide in README) |
| `assets/sounds/` | SFX (.wav/.ogg) and music tracks (.ogg) — auto-loaded by AssetManager |
| `assets/fonts/` | Font files |

## systems/ (additional)
| File | Purpose |
|------|---------|
| `systems/assets.py` | AssetManager singleton — loads sprites + sounds, plays SFX and music, falls back silently |
| `systems/effects.py` | StatusEffect system — poison, burn, stun, freeze, slow; tick_all() applied to entities each frame |
| `systems/active_attacks.py` | Special attack objects — WaveAttack, AreaAttack, AuraAttack; updated and drawn by engine |
| `systems/abilities.py` | AbilitySystem — reads abilities.json, dispatches to correct attack type, handles mana/item costs |
| `systems/shop.py` | ShopSystem — loads shops.json, handles buy/sell transactions against player inventory + gold |

## ui/ (additional)
| File | Purpose |
|------|---------|
| `ui/inventory_screen.py` | 32-slot grid inventory (I key) — keyboard nav, use/drop items, hotbar mirrors first 8 slots |
| `ui/shop_menu.py` | Shop overlay — buy/sell panel opened by pressing E near a shopkeeper NPC |

## data/ (additional)
| File | Purpose |
|------|---------|
| `data/abilities.json` | All ability definitions — type, damage, status_effect, mana_cost, cooldown, color, sound |
| `data/shops.json` | Shop definitions — name, buy_rate, inventory (item_id, price, stock) |
