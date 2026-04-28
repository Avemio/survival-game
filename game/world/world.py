"""
world/world.py
Owns the active zone and the enemy type registry.
Engine talks to World only — it doesn't need to know Zone exists.
Zone transitions will live here in M9.
"""

import json
from pathlib import Path
from game.world.zone import Zone


# data/ lives at the project root, two levels up from this file
# (game/world/world.py → game/world/ → game/ → project root)
_DATA_DIR = Path(__file__).parent.parent.parent / "data"


class World:
    def __init__(self, zone_id):
        # Load enemy type definitions once — reused every time a zone is loaded
        with open(_DATA_DIR / "enemies.json") as f:
            self._enemy_types = json.load(f)

        self.zone = self._load_zone(zone_id)

    # ------------------------------------------------------------------
    # Zone management
    # ------------------------------------------------------------------

    def _load_zone(self, zone_id):
        path = _DATA_DIR / "zones" / f"{zone_id}.json"
        return Zone(path, self._enemy_types)

    # Zone transitions go here in M9:
    # def transition_to(self, zone_id):
    #     self.zone = self._load_zone(zone_id)

    # ------------------------------------------------------------------
    # Convenience properties — engine uses these, not zone internals
    # ------------------------------------------------------------------

    @property
    def platforms(self):
        return self.zone.platforms

    @property
    def enemies(self):
        return self.zone.enemies

    @property
    def spawn(self):
        return self.zone.spawn
