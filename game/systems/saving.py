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
    }
  }
"""

import json
from pathlib import Path


# save.json lives at the project root
# (game/systems/saving.py → game/systems/ → game/ → project root)
_SAVE_PATH = Path(__file__).parent.parent.parent / "save.json"


def save_game(player, zone_id, collected_zone_drops):
    """Write current game state to disk. Health is saved as max (full heal on save)."""
    data = {
        "zone": zone_id,
        "player": {
            "x":         player.rect.x,
            "y":         player.rect.y,
            "health":    player.max_health,
            "inventory": player.inventory.serialize()
        },
        "collected_zone_drops": sorted(collected_zone_drops)
    }
    with open(_SAVE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_game():
    """
    Returns the save dict if a save file exists, otherwise None.
    Caller is responsible for applying the data to game objects.
    """
    if not _SAVE_PATH.exists():
        return None
    with open(_SAVE_PATH) as f:
        return json.load(f)
