"""
systems/saving.py
Save and load game state to/from save.json at the project root.
Owns: serialization format, file I/O.
Does NOT own: when to save (engine decides), healing logic (engine does that before calling save).

Save format:
  {
    "zone":   "zone_01",
    "player": {
      "x": 200, "y": 580, "health": 100,
      "inventory": [{"item_id": "wood", "quantity": 5}, null, ...]
    },
    "collected_zone_drops": {
      "zone_01": [0, 1],
      "zone_02": []
    }
  }
"""

import json
import os
from pathlib import Path


# save.json lives at the project root
# (game/systems/saving.py → game/systems/ → game/ → project root)
_SAVE_PATH = Path(__file__).parent.parent.parent / "save.json"


def save_game(player, zone_id, collected_zone_drops, opened_zone_chests=None, quest_state=None):
    """
    Write current game state to disk. Health is saved at its current value.
    (At save points the engine heals to max before calling this; zone transitions save current HP.)
    collected_zone_drops — dict mapping zone_id -> set of collected drop indices.
    """
    if opened_zone_chests is None:
        opened_zone_chests = {}
    if quest_state is None:
        quest_state = {}
    data = {
        "save_version": 1,
        "zone": zone_id,
        "player": {
            "x":             player.rect.x,
            "y":             player.rect.y,
            "health":        player.health,
            "mana":          player.mana,
            "level":         player.level,
            "xp":            player.xp,
            "xp_to_next":    player.xp_to_next,
            "max_health":    player.max_health,
            "max_mana":      player.max_mana,
            "inventory":     player.inventory.serialize(),
            "ability_slots": player.ability_slots,
        },
        "collected_zone_drops":  {k: sorted(v) for k, v in collected_zone_drops.items()},
        "opened_zone_chests":    {k: sorted(v) for k, v in opened_zone_chests.items()},
        "quests":                quest_state
    }
    # Write to a temp file first, then atomically replace the real save.
    # If the process dies mid-write, the old save stays intact.
    tmp = _SAVE_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _SAVE_PATH)


def load_game():
    """
    Returns the save dict if a save file exists, otherwise None.
    Caller is responsible for applying the data to game objects.
    """
    if not _SAVE_PATH.exists():
        return None
    try:
        with open(_SAVE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        # Corrupted save — treat as a fresh start rather than crashing
        return None
