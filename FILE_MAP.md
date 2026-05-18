# FILE MAP
*One-line purpose per file. Updated at the end of every session. This is the first thing read each session.*

---

## Root
| File | Purpose |
|------|---------|
| `main.py` | Entry point — initializes pygame, creates engine, starts game loop |
| `FILE_MAP.md` | This file — map of every file's purpose |
| `requirements.txt` | Python dependencies |
| `package.py` | Build script — `python package.py all` → dist/survival-game/ and dist/survival-game-editor/ |
| `GAME_GUIDE.md` | Player-facing controls and feature reference |
| `EDITOR_GUIDE.md` | Content editor usage guide |
| `README.md` | Project overview |
| `config.json` | Runtime config — volume, resolution (written by settings menu) |
| `save.json` | Auto-generated save file — not committed (in .gitignore) |

## core/
| File | Purpose |
|------|---------|
| `core/engine.py` | Main game loop, clock, screen surface, top-level update/draw calls, GameState enum |
| `core/camera.py` | Scrolling camera — tracks player, world-bounds clamping, shake, Y-lerp |
| `core/combat_resolver.py` | All hit resolution, enemy kill, projectile collision, particle spawning, XP/drop/quest routing |
| `core/input_handler.py` | All KEYDOWN dispatch, item use registry, ability/arrow firing, interact handling |
| `core/particles.py` | Particle + DamageNumber data classes — shared by engine and combat_resolver |

## entities/
| File | Purpose |
|------|---------|
| `entities/entity.py` | Base class for all game entities — alive flag, draw() stub; all entities inherit this |
| `entities/player.py` | Player class — movement, physics, facing direction, attack cooldown, inventory, hotbar slot |
| `entities/enemy.py` | Enemy class — health, hit-flash timer, take_damage(), alive flag, loot table |
| `entities/item_drop.py` | World item drop — rect, item_id, quantity, color, alive flag, zone_drop_index |
| `entities/chest.py` | Lootable chest — E key to open, transfers contents to inventory, persists open state |
| `entities/npc.py` | NPC class — rect, name, color, dialogue lines, [E] Talk proximity prompt |
| `entities/projectile.py` | Arrow projectile — physics (gravity), platform collision, enemy hit, oriented line draw |

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
| `world/scene.py` | Base class for game scenes/zones — on_enter/on_exit lifecycle hooks; Zone inherits this |
| `world/world.py` | Owns the active zone + all data registries; engine talks here, not to Zone directly |
| `world/zone.py` | Loads a single zone JSON file; builds platforms, enemies, save points, item drops, NPCs, buildings |
| `world/platform_grid.py` | Spatial bucket index — O(1) platform lookups for collision (query_rect) and draw culling (query_screen) |

## ui/
| File | Purpose |
|------|---------|
| `ui/hud.py` | HUD overlay — health bar (top-left) and hotbar slots (bottom-center), screen space only |
| `ui/menus.py` | CraftingMenu overlay — recipe list, ingredient counts, cursor nav, feedback flash |
| `ui/dialogue.py` | DialogueBox — word-wrapped NPC dialogue panel above hotbar, advances on E |
| `ui/pause_menu.py` | PauseMenu overlay — controls reference + Resume/Quit; opened by Esc during gameplay |
| `ui/notifications.py` | Right-side fading notification queue — push(text, color, duration, big) |

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
| `data/zones/zone_02.json` | Second zone — varied enemies (basic/heavy/fast/archer), 2 save points, chest with ability scroll |

## tools/
| File | Purpose |
|------|---------|
| `tools/editor.py` | Standalone content editor (Tkinter) — run `python tools/editor.py`; edits all data JSON files; visual zone canvas |
| `tools/generate_sprites.py` | Pixellab API sprite generator — generates idle/run/attack/jump frames, saves to assets/sprites/, writes data/sprites/ JSON config |

## assets/
| Folder | Purpose |
|--------|---------|
| `assets/sprites/player/` | Player assassin sprites — idle, run, jump, attack (4 frames each, API-generated) |
| `assets/sprites/enemy_basic/` | City Watchman sprites — idle, run, attack (4 frames each, API-generated) |
| `assets/sprites/enemy_heavy/` | Sergeant at Arms sprites — idle, walk (6 frames), attack (4 frames) |
| `assets/sounds/` | SFX (.wav/.ogg) and music tracks (.ogg) — auto-loaded by AssetManager |
| `assets/fonts/` | Font files |

## data/sprites/
| File | Purpose |
|------|---------|
| `data/sprites/player.json` | Player sprite config — base_path, fps, idle filenames, animation prefixes + frame counts |
| `data/sprites/enemy_basic.json` | City Watchman sprite config |
| `data/sprites/enemy_heavy.json` | Sergeant at Arms sprite config (uses walk_ prefix for run states) |
| `data/sprites/kael.json` | Legacy config (superseded by player.json) |

## systems/ (additional)
| File | Purpose |
|------|---------|
| `systems/events.py` | EventBus — two-tier pub/sub (persistent + zone-scoped); engine posts events, systems subscribe |
| `systems/achievements.py` | AchievementSystem — tracks kills/gold/level/zones/skills via EventBus; unlocks + notifies |
| `systems/assets.py` | AssetManager singleton — loads sprites + sounds, plays SFX and music, falls back silently |
| `systems/animator.py` | Animator class — frame sequencing, state switching, per-state FPS, per-frame foot_y alignment |
| `systems/sprite_loader.py` | Data-driven sprite loader — reads data/sprites/{name}.json, returns Animator + idle surfaces |
| `systems/effects.py` | StatusEffect system — poison, burn, stun, freeze, slow; tick_all() applied to entities each frame |
| `systems/active_attacks.py` | Special attack objects — WaveAttack, AreaAttack, AuraAttack; updated and drawn by engine |
| `systems/abilities.py` | AbilitySystem — reads abilities.json, dispatches to correct attack type, handles mana/item costs |
| `systems/shop.py` | ShopSystem — loads shops.json, handles buy/sell transactions against player inventory + gold |
| `systems/quests.py` | QuestSystem — loads quests.json, tracks kill/collect/zone progress, serializes for save |

## ui/ (additional)
| File | Purpose |
|------|---------|
| `ui/inventory_screen.py` | 32-slot grid inventory (I key) — keyboard nav, use/drop items, hotbar mirrors first 8 slots |
| `ui/shop_menu.py` | Shop overlay — buy/sell panel opened by pressing E near a shopkeeper NPC |
| `ui/title_screen.py` | Title screen — New Game / Continue / Quit; shown on every startup |
| `ui/quest_log.py` | Quest log overlay (J key) — active quest progress bars + completed list |
| `ui/skill_menu.py` | Skill point spending overlay (K key) — 5 stat upgrades, pauses the world |

## .claude/skills/
| File | Purpose |
|------|---------|
| `.claude/skills/end-session/SKILL.md` | Full session-close checklist — commit, FILE_MAP, memory sync, Second Brain, session review |
| `.claude/skills/update-memory/SKILL.md` | Syncs all memory tiers against git log + codebase; rewrites anything stale |
| `.claude/skills/memory-audit/SKILL.md` | Skeptic pass — finds contradictions, stale refs, undocumented decisions; reports only |
| `data/achievements.json` | Achievement definitions — id, name, desc, stat to track, goal threshold |
| `data/abilities.json` | All ability definitions — type, damage, status_effect, mana_cost, cooldown |
| `data/shops.json` | Shop definitions — name, buy_rate, inventory (item_id, price, stock) |
