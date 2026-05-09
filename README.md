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
