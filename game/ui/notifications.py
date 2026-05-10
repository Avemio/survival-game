"""
ui/notifications.py
Floating notification queue — shows brief messages that fade out on the
right side of the screen (below the wind/gold indicators).
Called from engine with self.notifications.push(text, color, duration).
Does NOT own: game logic. Just renders pre-built text.
"""

import pygame
from game.settings import SCREEN_WIDTH

_X_RIGHT  = SCREEN_WIDTH - 16   # right-aligned
_Y_START  = 80                   # below the wind bar
_LINE_GAP = 5
_MAX      = 6                    # cap simultaneous messages


class NotificationQueue:
    def __init__(self):
        self._items: list[dict] = []
        self._font_big   = pygame.font.SysFont(None, 22)
        self._font_small = pygame.font.SysFont(None, 18)

    def push(self, text: str, color=(255, 240, 80),
             duration: float = 3.0, big: bool = False):
        """Add a notification. Oldest entry is dropped if the queue is full."""
        if len(self._items) >= _MAX:
            self._items.pop(0)
        font = self._font_big if big else self._font_small
        surf = font.render(text, True, color)
        self._items.append({
            "surf":  surf,
            "timer": duration,
            "max":   duration,
        })

    def update(self, dt: float):
        for n in self._items:
            n["timer"] -= dt
        self._items[:] = [n for n in self._items if n["timer"] > 0]

    def draw(self, screen):
        y = _Y_START
        for n in self._items:
            # Fade quickly into view, linger, then fade out in last 0.5 s
            ratio = n["timer"] / max(0.001, n["max"])
            if ratio > 0.85:
                alpha = int(255 * (1.0 - ratio) / 0.15)   # fade in
            elif ratio < 0.2:
                alpha = int(255 * ratio / 0.2)             # fade out
            else:
                alpha = 255
            s = n["surf"]
            s.set_alpha(alpha)
            screen.blit(s, (_X_RIGHT - s.get_width(), y))
            y += s.get_height() + _LINE_GAP
