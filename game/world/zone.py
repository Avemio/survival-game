"""
world/zone.py
A single playable area — loads from a JSON file, builds platforms, enemies, and save points.
Owns: platforms list, enemies list, save_points list, spawn point, zone id.
Does NOT own: zone transitions (World handles that), AI, or combat.
"""

import json
import pygame
from pathlib import Path
from game.entities.enemy import Enemy
from game.settings import SAVE_POINT_COLOR, SAVE_POINT_ACTIVE_COLOR


class SavePoint:
    FLASH_DURATION = 1.0   # seconds the bright color shows after saving

    def __init__(self, x, y, w, h):
        self.rect            = pygame.Rect(x, y, w, h)
        self.was_overlapping = False   # edge detection — trigger only on entry
        self.flash_timer     = 0.0

    def update(self, dt):
        if self.flash_timer > 0:
            self.flash_timer -= dt

    def draw(self, screen, camera):
        color = SAVE_POINT_ACTIVE_COLOR if self.flash_timer > 0 else SAVE_POINT_COLOR
        pygame.draw.rect(screen, color, camera.apply(self.rect))


class Zone:
    def __init__(self, path, enemy_types):
        """
        path        — pathlib.Path (or str) to the zone's JSON file
        enemy_types — dict loaded from data/enemies.json, keyed by type string
        """
        self.id          = "unknown"
        self.platforms   = []
        self.enemies     = []
        self.save_points = []
        self.spawn       = (200, 580)   # fallback; always overwritten by JSON

        self._load(Path(path), enemy_types)

    # ------------------------------------------------------------------
    # Internal loader
    # ------------------------------------------------------------------

    def _load(self, path, enemy_types):
        with open(path) as f:
            data = json.load(f)

        self.id    = data.get("id", path.stem)
        self.spawn = tuple(data["spawn"])

        for p in data["platforms"]:
            self.platforms.append(
                pygame.Rect(p["x"], p["y"], p["w"], p["h"])
            )

        for e in data["enemies"]:
            stats = enemy_types.get(e["type"], {})
            self.enemies.append(Enemy(e["x"], e["y"], stats))

        for sp in data.get("save_points", []):
            self.save_points.append(
                SavePoint(sp["x"], sp["y"], sp["w"], sp["h"])
            )
