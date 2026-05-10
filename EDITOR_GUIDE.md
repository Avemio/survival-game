# Content Editor Guide

## Running the Editor
```
python tools/editor.py
```
From the `survival-game/` directory. Pure Python + Tkinter — no pygame needed.

The editor reads and writes all `data/` JSON files directly. All saves are atomic (writes to `.tmp` then renames) so a crash mid-save never corrupts your data.

---

## Tabs Overview

| Tab | File | What You Edit |
|-----|------|---------------|
| Enemies | `data/enemies.json` | Stats, AI ranges, drops, XP reward |
| Items | `data/items.json` | Name, color, stack rules, sell value, use effect |
| Recipes | `data/recipes.json` | Crafting: ingredients → result |
| NPCs | `data/npcs.json` + `data/dialogue.json` | NPC types + dialogue scripts |
| Abilities | `data/abilities.json` | All ability types and parameters |
| Shops | `data/shops.json` | Shop inventories and pricing |
| Quests | `data/quests.json` | Quest objectives and rewards |
| Zone Editor | `data/zones/*.json` | Full visual level editor |

Every tab follows the same pattern: **list on the left**, **form on the right**, **Save button** at the bottom of the form.

---

## Enemies Tab

### Fields
| Field | Description |
|-------|-------------|
| ID (key) | Internal identifier used in `enemies` arrays in zone JSON |
| Health | Max HP |
| XP reward | XP awarded to the player on kill |
| Width / Height | Hitbox size in pixels |
| Patrol speed | Movement speed while wandering (px/s) |
| Chase speed | Movement speed when chasing the player (px/s) |
| Aggro range | Distance (px) at which enemy starts chasing |
| De-aggro range | Distance (px) at which enemy gives up and returns |
| Attack range | Horizontal distance (px) at which enemy swings |
| Attack damage | HP per hit |
| Attack cooldown | Seconds between swings |
| Patrol radius | Max px the enemy wanders from its spawn X |
| Sprite name | Filename stem in `assets/sprites/` (no extension) |

### Drop Table
Add drops with the **+** button. Each row: `item_id`, `quantity`, `chance` (0.0–1.0; 1.0 = always drops).

### Workflow
1. Pick an existing type from the list, or click **New** and enter an ID.
2. Fill the form. Click **Save Enemy**.
3. The enemy is now available as a `"type"` in any zone JSON.

---

## Items Tab

### Fields
| Field | Description |
|-------|-------------|
| ID (key) | Used everywhere items are referenced |
| Display name | Shown in inventory and HUD |
| Color | Click the color swatch to pick with the color dialog |
| Stackable | Whether multiple can stack in one slot |
| Max stack | Maximum per stack (99 for most resources, 1 for equipment) |
| Sell value | Gold earned when selling one to a shop (0 = not sellable) |
| Use effect | `heal` — restores HP on F press; `equip_ability` — fills Q/R slot |
| Heal amount | HP restored (only for `use: heal`) |
| Ability ID | Which ability this scroll equips (only for `use: equip_ability`) |

---

## Recipes Tab

### Fields
| Field | Description |
|-------|-------------|
| Recipe ID | Internal key |
| Display name | Shown in crafting menu |
| Result item | Item ID produced |
| Result count | How many are produced |
| Ingredients | Table of `item_id` + `quantity` rows |

Use the **+** / **−** buttons to add/remove ingredient rows.

---

## NPCs Tab

This tab has two independent sections:

### NPC Types (left panel)
Defines the visual appearance of NPC classes. Fields: ID, name, sprite, color, width, height.

Once saved, the type can be placed in any zone via the Zone Editor.

### Dialogue Scripts (right panel)
Each script is a list of lines shown in order when the player presses E.

- **New** — create a script with a new ID.
- **Add line / Edit / ↑ ↓ / Remove** — manage the line list.
- **Save Script** — writes both files (npcs.json and dialogue.json) atomically.

**Tip:** To assign a script to an NPC, use the `dialogue_id` field when placing the NPC in the Zone Editor.

---

## Abilities Tab

### Type determines which fields matter

| Type | Key Extra Fields |
|------|-----------------|
| `melee` | Width, Height, Knockback |
| `projectile` | Speed, Gravity (relative to arrow gravity), Pierce, Wind affected |
| `wave` | Speed, Max distance, Height |
| `area` | Radius, Duration |
| `aura` | Radius, Duration, DPS |

### Status Effect
Optional. All ability types can apply one. Fields: type (poison/burn/stun/freeze/slow), duration, DPS (for DoT types), slow factor (for slow).

### Cooldown and Mana Cost
Always set these for player-usable abilities, or the ability can be used every frame.

---

## Shops Tab

### Fields
| Field | Description |
|-------|-------------|
| Shop ID | Used by NPC `shop_id` field in zone JSON |
| Display name | Shown as the shop title in the menu |
| Buy rate | Fraction of `sell_value` paid to player when they sell (0.5 = 50%) |
| Inventory | Table of items for sale |

### Inventory Table
Each row: `item_id`, `price` (gold), `stock` (-1 = unlimited; positive = limited copies).

---

## Quests Tab

### Fields
| Field | Description |
|-------|-------------|
| Quest ID | Referenced by NPCs in zone JSON (`gives_quest` field) |
| Display name | Shown in quest log |
| Description | Full text shown to player on quest accept |
| Quest type | How progress is tracked |
| Target | Entity being tracked (enemy type key, item ID, or zone ID) |
| Count | How many needed to complete |
| Reward XP | XP on completion |
| Reward Gold | Gold on completion |

### Quest Types
| Type | Target | Counts on |
|------|--------|-----------|
| `kill` | Enemy type key (e.g. `basic`) | Killing that specific enemy type |
| `kill_any` | *(no target)* | Killing any enemy |
| `collect` | Item ID (e.g. `herb`) | Picking up that item |
| `reach_zone` | Zone ID | Entering that zone |

---

## Zone Editor

The most powerful part of the editor. Provides a visual, scrollable canvas for building levels.

### Opening / Creating Zones
- **New Zone** — blank slate.
- **Open Zone** — load any `.json` from `data/zones/`.
- **Save Zone** — writes the current zone back to disk (or prompts for a filename if it's new).

### Zone Metadata (top bar)
| Field | Description |
|-------|-------------|
| ID | The zone's internal ID (also the save filename stem) |
| Spawn X / Y | Where the player appears when entering this zone |
| BG color | Background fill color (click swatch to pick) |
| Music | Track name stem in `assets/sounds/` (optional) |

---

### Tools

Select a tool from the toolbar. Each places a different element type.

| Tool | How to Place | What It Creates |
|------|-------------|-----------------|
| **↖ Select** | Click element | Selects for editing / moving |
| **▭ Platform** | Click and drag | Solid collision rect |
| **☠ Enemy** | Click | Enemy spawn point |
| **☺ NPC** | Click | NPC placement |
| **✦ Save Pt** | Click | 60×64 save point |
| **◆ Item Drop** | Click | World item drop |
| **→ Exit** | Click and drag | Zone transition portal |
| **⌂ Building** | Click | Building with door |
| **◻ Chest** | Click | Lootable chest |

---

### Grid Snapping
Toggle **Grid snap (G)** in the toolbar (default ON, 20px grid). Faint grid lines appear on the canvas. All placements snap to the nearest grid cell.

Hold no modifier for 1px nudge, hold **Shift** for 10px nudge on arrow keys.

---

### Select Mode
Click any element to select it (highlighted yellow). While selected:
- **Properties panel** (below canvas) shows all editable fields.
- Edit fields and click **Apply** to update.
- **Arrow keys** — nudge 1px (Shift = 10px).
- **Delete / Backspace** — remove the element.
- **Escape** — deselect.

---

### Undo / Redo
- **Ctrl+Z** — undo (20 levels deep).
- **Ctrl+Y** — redo.

Every placement, deletion, property change, and move is undoable.

---

### Properties Panel Fields by Element Type

**Platform**
`x, y, w, h` — position and size.

**Enemy**
`x, y` — spawn position. `type` — dropdown of enemy types from enemies.json.

**NPC**
`x, y` — position. `type` — NPC type. `dialogue_id` — which dialogue script to use. `shop_id` — which shop to open (optional). `gives_quest` — which quest to hand out on first interaction (optional).

**Save Point**
`x, y, w, h` — position and size (default 60×64).

**Item Drop**
`x, y` — position. `item_id` — dropdown of items. `quantity` — how many.

**Exit (Zone Portal)**
`x, y, w, h` — portal rect. `target_zone` — zone ID to travel to. `spawn_override x / y` — exact player position in the target zone (leave blank to use the zone's default spawn point).

**Building**
`x, y, w, h` — building body. `door_x, door_y, door_w, door_h` — door rect. `target_zone` — interior zone. `label` — optional display name.

**Chest**
`x, y, w, h` — chest rect (auto 48×36). `contents` table — items inside; use **+** / **−** to add/remove.

---

### Status Bar
The bottom-left shows element counts for the current zone. The bottom-right shows the cursor's world coordinates (x, y) as you move the mouse.

---

### Zone Validation
Click **Validate** to run a checklist:
- At least one zone exit.
- At least one save point.
- Enemy/NPC types exist in their respective JSON files.
- Shop IDs and quest IDs referenced by NPCs actually exist.

Fix any warnings before saving for production.

---

## Workflow: Adding a New Enemy to a Zone

1. **Enemies tab** → New → set ID (e.g. `archer`) → fill stats → Save Enemy.
2. **Zone Editor** → Open your zone → select **☠ Enemy** tool → click the canvas → choose type `archer` → Place.
3. **Save Zone**.
4. Run the game: `python main.py` — the enemy appears.

## Workflow: Adding a New Quest

1. **Quests tab** → New → fill quest ID, name, description, type/target/count, rewards → Save Quest.
2. **Zone Editor** → select an NPC → in properties panel, set `gives_quest` to the new quest ID → Apply.
3. **Save Zone**.
4. In-game: talk to that NPC → notification appears → quest appears in quest log (J).

## Workflow: Adding a New Shop Item

1. Make sure the item exists in **Items tab** (create it if not).
2. **Shops tab** → pick the shop → click **+** in the inventory table → enter item ID, price, stock → **Save Shop**.
3. In-game: the item appears in the shopkeeper's buy list immediately.

---

## File Reference

```
data/
  enemies.json      — enemy type definitions
  items.json        — all item definitions (includes sell_value)
  recipes.json      — crafting recipes
  npcs.json         — NPC type definitions
  dialogue.json     — NPC dialogue scripts
  abilities.json    — all ability definitions
  shops.json        — shop catalogs
  quests.json       — quest definitions
  zones/
    zone_01.json    — first outdoor zone
    zone_01_interior.json  — Abandoned Cabin interior
    zone_02.json    — second zone
```

Adding a new zone = create a new JSON file in `data/zones/`. Name it `zone_XX.json`. Reference it from another zone's `exits` array or a building's `target_zone`.
