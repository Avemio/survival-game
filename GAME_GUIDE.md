# Survival Game — Player Guide

## Running the Game
```
python main.py
```
From the `survival-game/` directory. Python 3.11+ and pygame-ce required (`pip install -r requirements.txt`).

---

## Controls

| Action | Key |
|--------|-----|
| Move | WASD or Arrow Keys |
| Jump | W / Space / Up |
| Variable jump (hold) | Hold W / Space longer = higher jump |
| Attack (melee) | Z |
| Ability Q | Q |
| Ability R | R |
| Draw bow | Hold X |
| Aim bow | Up / Down while holding X |
| Fire bow | Release X |
| Use hotbar item | F |
| Hotbar slot | 1 – 8 |
| Inventory | I |
| Quest log | J |
| Crafting menu | C |
| Talk / Shop / Open chest | E (when near an NPC or chest) |
| Pause | Esc |

---

## Movement Feel
- **Coyote time** — you can jump for ~0.1 s after walking off a ledge; you don't have to be pixel-perfect at the edge.
- **Jump buffer** — pressing jump just before you land still works; the input is queued.
- **Variable jump** — tap W/Space for a short hop; hold it for maximum height.

---

## Combat

### Melee Attack (Z)
Swing your weapon. A yellow hitbox appears in front of you for 0.18 s. 0.45 s cooldown between swings.

### Abilities (Q / R)
Ability slots are shown to the left of the hotbar. To fill them:
1. Find or buy an **ability scroll** (glowing colored items in the world or from the shopkeeper).
2. Pick it up — it goes into your inventory.
3. Open inventory (**I**) or select it in the hotbar (**1–8**).
4. Press **F** to equip it. It fills the first empty Q or R slot.
5. Press **Q** or **R** in combat to use it.

Abilities cost mana (the blue bar under your health). Mana regenerates at 5/sec.

### Bow (X)
1. Make sure you have a **bow** in your selected hotbar slot.
2. Hold **X** to draw. Use **Up/Down** to aim the trajectory arc.
3. Release **X** to fire. Each shot consumes one arrow.

Wind (shown top-right) affects arrow trajectory — aim slightly into the wind.

### Enemy Types
| Type | HP | Threat |
|------|----|--------|
| Basic | 100 | Slow patrol, telegraphed attacks |
| Fast | 60 | Large aggro range, quick |
| Heavy | 220 | High damage, knocks back |

**Windup telegraph** — enemies flash orange before swinging. That's your dodge window.

Enemies will **jump** toward you if you stand on a platform above them.

---

## Health, Mana, and Leveling

### Health Bar (top-left, red)
Your HP. Die → you respawn at the last save point you touched.

### Mana Bar (blue, below health)
Spent by abilities. Regenerates automatically.

### XP Bar (purple, below mana)
Kill enemies to earn XP. Level up to gain:
- +15 max HP
- +10 max mana

A "LEVEL UP!" flash appears when it happens.

---

## Gold and Trading

**Enemies drop gold** when killed (basic: 6g, fast: 4g, heavy: 20g). Gold is shown top-right.

**Shopkeeper** (gold NPC near zone start) — press **E** to open the shop.
- **BUY tab** — purchase items and ability scrolls.
- **SELL tab** — sell crafting materials and equipment for 50% of their value.
- **Tab** switches between Buy and Sell. **↑↓** to navigate. **Enter** to transact. **Esc** to close.

---

## Quests (J to open Quest Log)

Quests give XP and gold on completion. Press **J** anytime to check progress.

### Getting Quests
| NPC | Quest | Objective |
|-----|-------|-----------|
| Villager (zone start) | First Blood | Kill 3 basic enemies |
| Shopkeeper | Herb Gatherer | Collect 5 herbs |
| Wanderer (mid-zone platform) | Stone Collector | Collect 8 stone |
| Auto (always active) | Monster Slayer | Kill 5 enemies of any type |

Talk to an NPC with **E**. A golden notification appears top-right when a quest starts.

### Quest Completion
Quests auto-complete when you meet the objective. A green "Quest Complete!" notification appears. Rewards (XP + gold) are applied immediately.

---

## Loot and Items

### Picking Up Items
Walk over any item on the ground to pick it up automatically. Full inventory = item stays on the ground.

### Inventory (I key)
32-slot grid. First 8 slots are your **hotbar** (shown at the bottom). Use **↑↓←→** to navigate, **F** or **Enter** to use an item, **D** to drop it.

### Item Types
| Item | Use |
|------|-----|
| Wood, Stone, Herb, Plank | Crafting ingredients |
| Gold | Currency for trading |
| Health Potion | Press F to restore 30 HP |
| Bow | Equip in hotbar for ranged combat |
| Arrow | Consumed by bow shots |
| Ability Scroll | Press F to equip to Q or R slot |

### Chests
Brown boxes with a seam. Press **E** when nearby to open. Contents transfer directly to your inventory.

---

## Crafting (C key)

Open the crafting menu with **C**. Navigate with **↑↓**, press **Enter** to craft.

| Recipe | Ingredients | Result |
|--------|-------------|--------|
| Plank | 3 Wood | 2 Planks |
| Health Potion | 2 Herbs | 1 Potion |
| Arrow | 2 Wood + 1 Stone | 5 Arrows |
| Bow | 3 Planks + 1 Herb | 1 Bow |
| Stone Sword | 5 Stone + 2 Planks | 1 Stone Sword |
| Fireball Scroll | 3 Herbs + 2 Stone | 1 Fireball Scroll |
| Earthquake Scroll | 5 Stone + 2 Herbs | 1 Earthquake Scroll |

---

## Saving

The game **auto-saves** whenever you:
- Touch a **save point** (teal glowing pillar) — also fully heals you.
- Leave a zone through an exit portal.

If you die, you respawn at the last save point with the inventory/level/quests you had when you saved.

---

## Zone Navigation

**Exits** are green glowing portals. Walk into one to travel to the next zone.

**Buildings** (brown structures with a door) — press **E** at the door to enter the interior. Walk left into the exit inside to return to the outdoor zone, appearing at the building's door.

---

## Status Effects

Some enemy abilities and your own can apply:

| Effect | Icon Color | What It Does |
|--------|-----------|--------------|
| Poison | Green | Damage over time |
| Burn | Orange | Damage over time (faster) |
| Stun | Yellow | Can't move or attack |
| Freeze | Cyan | Can't move (stun variant) |
| Slow | Purple | Reduced movement speed |

Status effect icons appear as small colored bars next to your health bar.

---

## Wind

The wind indicator (top-right) shows current wind strength and direction. Wind affects:
- Arrow trajectory (aim into the wind)
- Atmospheric streak visuals

---

## Tips

- Enemies respawn when you change zones or die. Gold and resources respawn with them.
- Ground item drops (not from enemies) are **permanent** — once picked up they don't come back.
- The pity system guarantees a rare drop every 8 kills if you haven't had one.
- Hitstop (brief freeze on hit) means if the world pauses for a frame when you swing — that's normal.
- You can stand on ledges to kite enemies, but they will jump up to reach you.
- The bow shows a trajectory arc accounting for gravity and wind — use it to aim precisely.
