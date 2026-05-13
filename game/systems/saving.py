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
import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)

_CURRENT_VERSION = 1


def _migrate(data: dict) -> dict:
    """
    Upgrade save data from older versions to the current format.
    Add a new elif block here whenever save_version increments.
    """
    v = data.get("save_version", 0)
    # Future: elif v == 1: apply v1→v2 changes; data["save_version"] = 2
    if v < _CURRENT_VERSION:
        _log.info("Migrating save from version %d to %d", v, _CURRENT_VERSION)
        data["save_version"] = _CURRENT_VERSION
    return data


# save.json lives at the project root
# (game/systems/saving.py → game/systems/ → game/ → project root)
_SAVE_PATH = Path(__file__).parent.parent.parent / "save.json"


def save_game(player, zone_id, collected_zone_drops, opened_zone_chests=None,
              quest_state=None, achievement_state=None):
    """
    Write current game state to disk. Health is saved at its current value.
    (At save points the engine heals to max before calling this; zone transitions save current HP.)
    collected_zone_drops — dict mapping zone_id -> set of collected drop indices.
    """
    if opened_zone_chests is None:
        opened_zone_chests = {}
    if quest_state is None:
        quest_state = {}
    if achievement_state is None:
        achievement_state = {}
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
            "skill_points":  player.skill_points,
            "attack_damage": player.attack_damage,
            "speed":         player.speed,
            "mana_regen":    player.mana_regen,
            "inventory":     player.inventory.serialize(),
            "ability_slots": player.ability_slots,
        },
        "collected_zone_drops":  {k: sorted(v) for k, v in collected_zone_drops.items()},
        "opened_zone_chests":    {k: sorted(v) for k, v in opened_zone_chests.items()},
        "quests":                quest_state,
        "achievements":          achievement_state
    }
    # Write to a temp file first, then atomically replace the real save.
    # If the process dies mid-write, the old save stays intact.
    tmp = _SAVE_PATH.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _SAVE_PATH)
    except OSError as exc:
        _log.error("Save failed: %s", exc)
        raise   # re-raise so engine can notify the player


def load_game():
    """
    Returns the save dict if a save file exists, otherwise None.
    Caller is responsible for applying the data to game objects.
    """
    if not _SAVE_PATH.exists():
        return None
    try:
        with open(_SAVE_PATH) as f:
            data = json.load(f)
        return _migrate(data)
    except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
        _log.error("Save file unreadable (%s) — starting fresh", exc)
        return None
