"""
ui/hud.py
Heads-up display — drawn in screen space every frame on top of the world.
Owns: health bar, hotbar slots.
Does NOT own: player state (reads it), inventory items (M7), camera (screen space only).

All surfaces and fonts are created once at init — never inside draw().
"""

import pygame
from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    HUD_HEALTH_X, HUD_HEALTH_Y, HUD_HEALTH_W, HUD_HEALTH_H,
    HUD_HEALTH_BG, HUD_HEALTH_FG, HUD_HEALTH_BORDER,
    HOTBAR_SLOTS, HOTBAR_SLOT_SIZE, HOTBAR_SLOT_GAP, HOTBAR_Y_OFFSET,
    HOTBAR_BG, HOTBAR_BORDER, HOTBAR_SELECTED
)


class HUD:
    def __init__(self, player):
        self.player = player

        # Pre-compute hotbar geometry — doesn't change frame to frame
        total_w = HOTBAR_SLOTS * HOTBAR_SLOT_SIZE + (HOTBAR_SLOTS - 1) * HOTBAR_SLOT_GAP
        self._hotbar_x = (SCREEN_WIDTH - total_w) // 2   # centered horizontally
        self._hotbar_y = SCREEN_HEIGHT - HOTBAR_SLOT_SIZE - HOTBAR_Y_OFFSET

    # ------------------------------------------------------------------
    # Draw (called by engine each frame, after all world drawing)
    # ------------------------------------------------------------------

    def draw(self, screen):
        self._draw_health_bar(screen)
        self._draw_hotbar(screen)

    # ------------------------------------------------------------------
    # Health bar
    # ------------------------------------------------------------------

    def _draw_health_bar(self, screen):
        x, y, w, h = HUD_HEALTH_X, HUD_HEALTH_Y, HUD_HEALTH_W, HUD_HEALTH_H

        # Background (empty bar)
        pygame.draw.rect(screen, HUD_HEALTH_BG, (x, y, w, h))

        # Filled portion — scaled by current health ratio
        ratio    = max(0, self.player.health / self.player.max_health)
        fill_w   = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, HUD_HEALTH_FG, (x, y, fill_w, h))

        # Border drawn last so it sits on top of the fill
        pygame.draw.rect(screen, HUD_HEALTH_BORDER, (x, y, w, h), 2)

    # ------------------------------------------------------------------
    # Hotbar
    # ------------------------------------------------------------------

    def _draw_hotbar(self, screen):
        for i in range(HOTBAR_SLOTS):
            slot_x = self._hotbar_x + i * (HOTBAR_SLOT_SIZE + HOTBAR_SLOT_GAP)
            slot_y = self._hotbar_y
            rect   = (slot_x, slot_y, HOTBAR_SLOT_SIZE, HOTBAR_SLOT_SIZE)

            # Slot background
            pygame.draw.rect(screen, HOTBAR_BG, rect)

            # Border — yellow for selected slot, grey for the rest
            border_color = HOTBAR_SELECTED if i == self.player.hotbar_slot else HOTBAR_BORDER
            pygame.draw.rect(screen, border_color, rect, 2)
