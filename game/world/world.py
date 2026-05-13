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
        src = f"data/zones/{zone_id}.json"
        for enemy in zone.enemies:
            t = enemy._type_key
            if t and t not in self._enemy_types:
                _log.warning("[%s] Unknown enemy type %r — check data/enemies.json", src, t)
        for npc in zone.npcs:
            if npc.dialogue_lines == [] and not npc.shop_id:
                _log.warning("[%s] NPC %r has no dialogue or shop_id", src, npc.name)
        for drop in zone.item_drops:
            if drop.item_id not in self._item_defs:
                _log.warning("[%s] Unknown item_id %r in item_drops — check data/items.json", src, drop.item_id)
        for chest in zone.chests:
            for c in chest.contents:
                iid = c.get("item_id")
                if iid not in self._item_defs:
                    _log.warning("[%s] Unknown item_id %r in chest contents", src, iid)
        for building in zone.buildings:
            bzone = building.target_zone
            if not (_DATA_DIR / "zones" / f"{bzone}.json").exists():
                _log.warning("[%s] Building target_zone %r not found in data/zones/", src, bzone)
        for exit_ in zone.exits:
            tzone = exit_.target_zone
            if not (_DATA_DIR / "zones" / f"{tzone}.json").exists():
                _log.warning("[%s] Exit target_zone %r not found in data/zones/", src, tzone)

    def transition_to(self, zone_id):
        """Swap out the active zone. Engine calls _setup_zone() after this to re-point references."""
        if self.zone:
            self.zone.on_exit()
        self.zone = self._load_zone(zone_id)
        self.zone.on_enter()

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

    # ------------------------------------------------------------------
    # Registry access — read-only views of loaded data files
    # ------------------------------------------------------------------

    @property
    def enemy_types(self) -> dict:
        return self._enemy_types

    @property
    def item_defs(self) -> dict:
        return self._item_defs

    @property
    def npc_types(self) -> dict:
        return self._npc_types
