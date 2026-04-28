"""
world/zone.py
A single playable area — loads from a JSON file, builds platforms and enemies.
Owns: platforms list, enemies list, spawn point.
Does NOT own: zone transitions (World handles that), AI, or combat.
"""

import json
import pygame
from pathlib import Path
from game.entities.enemy import Enemy


class Zone:
    def __init__(self, path, enemy_types):
        """
        path        — pathlib.Path (or str) to the zone's JSON file
        enemy_types — dict loaded from data/enemies.json, keyed by type string
                      e.g. {"basic": {"health": 100, "width": 40, "height": 60}}
        """
        self.platforms = []
        self.enemies   = []
        self.spawn     = (200, 580)   # fallback; always overwritten by JSON

        self._load(Path(path), enemy_types)

    # ------------------------------------------------------------------
    # Internal loader
    # ------------------------------------------------------------------

    def _load(self, path, enemy_types):
        with open(path) as f:
            data = json.load(f)

        self.spawn = tuple(data["spawn"])

        for p in data["platforms"]:
            self.platforms.append(
                pygame.Rect(p["x"], p["y"], p["w"], p["h"])
            )

        for e in data["enemies"]:
            # Look up the type's stat block; fall back to {} so Enemy uses
            # its own defaults (from settings.py) for any missing fields.
            stats = enemy_types.get(e["type"], {})
            self.enemies.append(Enemy(e["x"], e["y"], stats))
