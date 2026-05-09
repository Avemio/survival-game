# Survival Game

A 2D side-scrolling survival RPG built with Python and Pygame. Explore handcrafted zones, fight enemies, talk to NPCs, craft items, and survive.

---

## Requirements

- Python 3.10+
- pygame-ce 2.5.0+

## Setup

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

Run from the `survival-game/` directory.

---

## Controls

| Action | Key |
|--------|-----|
| Move | WASD or Arrow Keys |
| Jump | W / Space / Up Arrow |
| Attack | Z |
| Draw Bow | Hold X — release to fire |
| Aim Bow | Up / Down while drawing |
| Use Item | F |
| Hotbar Slot | 1 – 8 |
| Talk / Advance | E |
| Crafting Menu | C |
| Pause / Controls | Esc |

---

## Gameplay

- **Save points** (teal markers) heal you to full and save your progress when touched.
- **Crafting** — open the menu with C, navigate with Up/Down, craft with Enter.
- **Bow** — pick up the bow and arrows in zone 1. Hold X to aim, Up/Down to adjust angle, release X to fire. Watch the wind indicator in the top-right.
- **Zone exits** (green portals) take you to the next area.
- **Item drops** are left by defeated enemies and found throughout each zone.

## Zones

| Zone | Description |
|------|-------------|
| Zone 1 | The Forest Edge — introductory platforming, learn the controls, find the bow |
| Zone 2 | The Ruined Highlands — harder enemies, a dramatic tower climb, rare loot rewards |

---

## Crafting Recipes

| Result | Ingredients |
|--------|-------------|
| Plank ×2 | Wood ×3 |
| Health Potion | Herb ×2 + Stone ×1 |

---

## Adding Sprites

Drop a PNG into `assets/sprites/` with the correct name and it loads automatically — no code changes needed.

| Filename | What it replaces |
|----------|-----------------|
| `player.png` | Player character (32×64 px) |
| `enemy_basic.png` | Basic enemy (40×60 px) |
| `npc_villager.png` | Villager NPC (28×52 px) |
| `npc_guard.png` | Guard NPC (28×52 px) |
| `item_wood.png` | Wood drop (20×20 px) |
| `item_stone.png` | Stone drop (20×20 px) |
| `item_herb.png` | Herb drop (20×20 px) |
| `item_bow.png` | Bow drop (20×20 px) |
| `item_arrow.png` | Arrow drop (20×20 px) |
| `item_health_potion.png` | Health potion drop (20×20 px) |

Sprites are scaled to fit the entity's rect automatically. Any size PNG works.

## Adding Sounds

Drop a `.wav` or `.ogg` into `assets/sounds/` — plays automatically at the right moment.

| Filename | When it plays |
|----------|--------------|
| `attack_swing.wav` | Player sword swing |
| `arrow_fire.wav` | Bow fires |
| `enemy_hit.wav` | Enemy takes damage |
| `enemy_death.wav` | Enemy dies |
| `player_hit.wav` | Player takes damage |
| `item_pickup.wav` | Item collected |
| `save_point.wav` | Save point activated |
| `craft_success.wav` | Item crafted |
| `craft_fail.wav` | Not enough materials |
| `zone_transition.wav` | Entering new zone |
| `ui_select.wav` | Menu cursor moves |

## Adding Background Music

Add a `music` field to a zone's JSON and drop the matching `.ogg` in `assets/sounds/`:

```json
{
  "id": "zone_01",
  "music": "zone_01_theme",
  ...
}
```

Then place `assets/sounds/zone_01_theme.ogg` — it loops automatically.

## Customising Settings

Edit `config.json` at the project root:

```json
{
  "resolution": [1280, 720],
  "fps": 60,
  "volume": 0.8,
  "music_volume": 0.5
}
```

## Adding a New Zone

Create `data/zones/zone_XX.json`. Available fields:

```json
{
  "id": "zone_XX",
  "spawn": [x, y],
  "bg_color": [r, g, b],
  "music": "track_name",
  "platforms": [...],
  "enemies": [{"type": "basic", "x": 500, "y": 600}],
  "save_points": [...],
  "item_drops": [{"item_id": "wood", "quantity": 2, "x": 300, "y": 640}],
  "npcs": [{"type": "villager", "dialogue_id": "villager_01", "x": 200, "y": 608}],
  "exits": [{"x": 4950, "y": 0, "w": 50, "h": 720, "target_zone": "zone_YY"}]
}
```

## Adding a New Enemy Type

Add an entry to `data/enemies.json`:

```json
"my_enemy": {
  "sprite":          "enemy_my_enemy",
  "health":          150,
  "width":           50,
  "height":          70,
  "speed":           60,
  "chase_speed":     200,
  "aggro_range":     350,
  "deaggro_range":   600,
  "attack_range":    70,
  "attack_damage":   20,
  "attack_cooldown": 2.0,
  "patrol_radius":   250,
  "drops": [
    {"item_id": "stone", "quantity": 3, "chance": 1.0}
  ]
}
```

Then place enemies in zone JSON with `"type": "my_enemy"`. Drop `assets/sprites/enemy_my_enemy.png` to give it a sprite.
