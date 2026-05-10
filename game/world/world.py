"""
world/world.py
Owns the active zone and all data registries (enemies, items, NPCs, dialogue).
Engine talks to World only — it doesn't need to know Zone exists.
Zone transitions (transition_to) are also handled here.
"""

import json
import logging
from pathlib import Path
from game.world.zone import Zone

_log = logging.getLogger(__name__)


# data/ lives at the project root, two levels up from this file
# (game/world/world.py → game/world/ → game/ → project root)
_DATA_DIR = Path(__file__).parent.parent.parent / "data"


class World:
    def __init__(self, zone_id):
        with open(_DATA_DIR / "enemies.json") as f:
            self._enemy_types = json.load(f)
        with open(_DATA_DIR / "items.json") as f:
            self._item_defs = json.load(f)
        with open(_DATA_DIR / "npcs.json") as f:
            self._npc_types = json.load(f)
        with open(_DATA_DIR / "dialogue.json") as f:
            self._dialogue_data = json.load(f)

        self.zone = self._load_zone(zone_id)

    # ------------------------------------------------------------------
    # Zone management
    # ------------------------------------------------------------------

    def _load_zone(self, zone_id):
        path = _DATA_DIR / "zones" / f"{zone_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Zone '{zone_id}' not found: {path}")
        zone = Zone(path, self._enemy_types, self._item_defs,
                    self._npc_types, self._dialogue_data)
        self._validate_zone(zone, zone_id)
        return zone

    def _validate_zone(self, zone, zone_id: str) -> None:
        """Log warnings for any broken cross-references in a loaded zone."""
        for enemy in zone.enemies:
            t = enemy._type_key
            if t and t not in self._enemy_types:
                _log.warning("Zone '%s': unknown enemy type '%s'", zone_id, t)
        for npc in zone.npcs:
            # NPC type validation — name is stored, type_key not directly available;
            # check via sprite name prefix or just validate dialogue_id
            if npc.dialogue_lines == [] and not npc.shop_id:
                _log.warning("Zone '%s': NPC '%s' has no dialogue or shop", zone_id, npc.name)
        for drop in zone.item_drops:
            if drop.item_id not in self._item_defs:
                _log.warning("Zone '%s': unknown item_id '%s' in item_drops", zone_id, drop.item_id)
        for chest in zone.chests:
            for c in chest.contents:
                if c.get("item_id") not in self._item_defs:
                    _log.warning("Zone '%s': unknown item_id '%s' in chest contents", zone_id, c.get("item_id"))
        for building in zone.buildings:
            bzone = building.target_zone
            bpath = _DATA_DIR / "zones" / f"{bzone}.json"
            if not bpath.exists():
                _log.warning("Zone '%s': building target_zone '%s' does not exist", zone_id, bzone)
        for exit_ in zone.exits:
            epath = _DATA_DIR / "zones" / f"{exit_.target_zone}.json"
            if not epath.exists():
                _log.warning("Zone '%s': exit target_zone '%s' does not exist", zone_id, exit_.target_zone)

    def transition_to(self, zone_id):
        """Swap out the active zone. Engine calls _setup_zone() after this to re-point references."""
        self.zone = self._load_zone(zone_id)

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

    @property
    def zone_id(self):
        return self.zone.id

    @property
    def save_points(self):
        return self.zone.save_points

    @property
    def item_drops(self):
        return self.zone.item_drops

    @property
    def npcs(self):
        return self.zone.npcs

    @property
    def exits(self):
        return self.zone.exits

    @property
    def buildings(self):
        return self.zone.buildings

    @property
    def chests(self):
        return self.zone.chests

    @property
    def bg_color(self):
        return self.zone.bg_color

    @property
    def music(self):
        return self.zone.music

    @property
    def world_w(self):
        return self.zone.world_w

    @property
    def world_h(self):
        return self.zone.world_h
