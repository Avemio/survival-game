"""
core/camera.py
Scrolling camera that tracks a target rect.
Owns one job: convert world coordinates to screen coordinates.
Nothing in here knows about players, enemies, or game logic.
"""

import pygame
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT


class Camera:
    def __init__(self):
        # offset is how far the camera has moved from the world origin
        # to draw something at screen position: screen_pos = world_pos - offset
        self.offset = pygame.math.Vector2(0, 0)

    def update(self, target):
        """
        Center the camera on the target rect each frame.
        target: any pygame.Rect (usually the player)
        """
        self.offset.x = target.centerx - SCREEN_WIDTH  // 2
        self.offset.y = target.centery - SCREEN_HEIGHT // 2

    def apply(self, rect):
        """
        Takes a rect in world coordinates.
        Returns a new pygame.Rect in screen coordinates.
        Use when you need Rect attributes (centerx, top, etc.) after the call.
        """
        return pygame.Rect(
            rect.x      - self.offset.x,
            rect.y      - self.offset.y,
            rect.width,
            rect.height
        )

    def apply_tuple(self, rect):
        """
        Like apply(), but returns a plain 4-tuple instead of a Rect.
        Use this for all direct pygame.draw calls — avoids a Rect allocation per frame.
        """
        return (
            rect.x      - self.offset.x,
            rect.y      - self.offset.y,
            rect.width,
            rect.height
        )
