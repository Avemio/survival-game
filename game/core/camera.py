"""
core/camera.py
Scrolling camera that tracks a target rect.
Owns one job: convert world coordinates to screen coordinates.
Nothing in here knows about players, enemies, or game logic.
"""

import random
import pygame
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT


class Camera:
    def __init__(self):
        # offset is how far the camera has moved from the world origin
        # to draw something at screen position: screen_pos = world_pos - offset
        self.offset = pygame.math.Vector2(0, 0)

        # Screen-shake state — computed once per frame, used by all draw helpers
        self._shake_timer     = 0.0
        self._shake_duration  = 0.1
        self._shake_intensity = 0
        self._shake_x         = 0
        self._shake_y         = 0

    def shake(self, intensity=4, duration=0.12):
        """Trigger a screen shake. A stronger shake overrides a weaker one."""
        if intensity > self._shake_intensity or self._shake_timer <= 0:
            self._shake_intensity = intensity
            self._shake_duration  = max(duration, 0.001)
            self._shake_timer     = duration

    def update(self, target, dt=0.0):
        """
        Center the camera on the target rect each frame.
        target: any pygame.Rect (usually the player)
        dt:     seconds since last frame — used to tick the shake timer.

        X snaps immediately (horizontal movement is fast and direct).
        Y lerps smoothly so the camera eases down on falls rather than snapping.
        """
        target_x = float(target.centerx - SCREEN_WIDTH  // 2)
        target_y = float(target.centery - SCREEN_HEIGHT // 2)
        self.offset.x = target_x
        if dt > 0:
            self.offset.y += (target_y - self.offset.y) * min(1.0, 8.0 * dt)
        else:
            self.offset.y = target_y

        if self._shake_timer > 0:
            self._shake_timer -= dt
            ratio = max(0.0, self._shake_timer / self._shake_duration)
            mag   = int(self._shake_intensity * ratio)
            self._shake_x = random.randint(-mag, mag) if mag else 0
            self._shake_y = random.randint(-mag, mag) if mag else 0
        else:
            self._shake_x = 0
            self._shake_y = 0

    def world_to_screen(self, x, y):
        """Convert a world-space point to screen-space (int tuple), including shake."""
        return (
            int(x - self.offset.x + self._shake_x),
            int(y - self.offset.y + self._shake_y),
        )

    def apply(self, rect):
        """
        Takes a rect in world coordinates.
        Returns a new pygame.Rect in screen coordinates (with shake).
        Use when you need Rect attributes (centerx, top, etc.) after the call.
        """
        return pygame.Rect(
            rect.x - self.offset.x + self._shake_x,
            rect.y - self.offset.y + self._shake_y,
            rect.width,
            rect.height,
        )

    def apply_tuple(self, rect):
        """
        Like apply(), but returns a plain 4-tuple of ints instead of a Rect (with shake).
        Use this for all direct pygame.draw calls — avoids a Rect allocation per frame.
        """
        return (
            int(rect.x - self.offset.x + self._shake_x),
            int(rect.y - self.offset.y + self._shake_y),
            rect.width,
            rect.height,
        )
