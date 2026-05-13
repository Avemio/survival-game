"""
world/platform_grid.py
Spatial bucket index for O(1) platform lookups.
Replaces full-list scans for both collision resolution and draw culling.

Owns: bucket registration, query_rect (collision), query_screen (draw).
Does NOT own: platform Rect data (those live in zone.platforms).
"""

import pygame
from game.settings import PLATFORM_BUCKET_SIZE


class PlatformGrid:
    """
    Divides the world into vertical columns (buckets) of PLATFORM_BUCKET_SIZE px each.
    Every platform registers in every bucket its X span overlaps.

    query_rect  — returns candidates near an entity rect  (for collision checks)
    query_screen — returns platforms visible in the camera viewport (for drawing)

    Both deduplicate by object id so wide platforms (e.g. a 10 000 px ground slab)
    are never returned more than once per query.
    """

    def __init__(self, platforms: list, bucket_size: int = PLATFORM_BUCKET_SIZE):
        self._bucket_size = bucket_size
        self._buckets: dict = {}
        for p in platforms:
            self._register(p)

    def _register(self, rect: pygame.Rect) -> None:
        b_start = rect.left  // self._bucket_size
        b_end   = rect.right // self._bucket_size
        for b in range(b_start, b_end + 1):
            self._buckets.setdefault(b, []).append(rect)

    def query_rect(self, rect: pygame.Rect) -> list:
        """Return all platforms whose bucket overlaps rect (for collision checks)."""
        b_start = rect.left  // self._bucket_size
        b_end   = rect.right // self._bucket_size
        if b_start == b_end:
            return self._buckets.get(b_start, [])
        seen   = set()
        result = []
        for b in range(b_start, b_end + 1):
            for p in self._buckets.get(b, ()):
                pid = id(p)
                if pid not in seen:
                    seen.add(pid)
                    result.append(p)
        return result

    def query_screen(self, cam_x: int, cam_y: int,
                     screen_w: int, screen_h: int) -> list:
        """Return all platforms visible inside the camera viewport (for drawing)."""
        b_start  = cam_x // self._bucket_size
        b_end    = (cam_x + screen_w) // self._bucket_size
        viewport = pygame.Rect(cam_x, cam_y, screen_w, screen_h)
        seen     = set()
        result   = []
        for b in range(b_start, b_end + 1):
            for p in self._buckets.get(b, ()):
                pid = id(p)
                if pid not in seen and viewport.colliderect(p):
                    seen.add(pid)
                    result.append(p)
        return result
