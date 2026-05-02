"""
ui/hud.py
Heads-up display — drawn in screen space every frame on top of the world.
Owns: health bar, hotbar slots (reads inventory from player).
Does NOT own: player state (reads it), camera (screen space only).

All surfaces and fonts are created once at init — never inside draw().
"""

import pygame
from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    HUD_HEALTH_X, HUD_HEALTH_Y, HUD_HEALTH_W, HUD_HEALTH_H,
    HUD_HEALTH_BG, HUD_HEALTH_FG, HUD_HEALTH_BORDER,
    HOTBAR_SLOTS, HOTBAR_SLOT_SIZE, HOTBAR_SLOT_GAP, HOTBAR_Y_OFFSET,
    HOTBAR_BG, HOTBAR_BORDER, HOTBAR_SELECTED,
    WIND_MAX, WHITE
)

_ITEM_MARGIN = 6   # pixels between slot edge and item icon


_WIND_BAR_W    = 100   # total width of the wind gauge track
_WIND_BAR_H    = 8     # height of the gauge bar
_WIND_HUD_X    = SCREEN_WIDTH - 130   # top-right area
_WIND_HUD_Y    = 20


class HUD:
    def __init__(self, player):
        self.player = player

        # Fonts — created once here, never in draw()
        self._font      = pygame.font.SysFont(None, 18)
        self._wind_font = pygame.font.SysFont(None, 16)

        # Pre-compute hotbar geometry — doesn't change frame to frame
        total_w = HOTBAR_SLOTS * HOTBAR_SLOT_SIZE + (HOTBAR_SLOTS - 1) * HOTBAR_SLOT_GAP
        self._hotbar_x = (SCREEN_WIDTH - total_w) // 2
        self._hotbar_y = SCREEN_HEIGHT - HOTBAR_SLOT_SIZE - HOTBAR_Y_OFFSET

    # ------------------------------------------------------------------
    # Draw (called by engine each frame, after all world drawing)
    # ------------------------------------------------------------------

    def draw(self, screen, wind=0.0):
        self._draw_health_bar(screen)
        self._draw_hotbar(screen)
        self._draw_wind(screen, wind)
        if self.player.aiming:
            self._draw_arrow_count(screen)

    # ------------------------------------------------------------------
    # Health bar
    # ------------------------------------------------------------------

    def _draw_health_bar(self, screen):
        x, y, w, h = HUD_HEALTH_X, HUD_HEALTH_Y, HUD_HEALTH_W, HUD_HEALTH_H

        pygame.draw.rect(screen, HUD_HEALTH_BG, (x, y, w, h))

        ratio  = max(0, self.player.health / self.player.max_health)
        fill_w = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, HUD_HEALTH_FG, (x, y, fill_w, h))

        pygame.draw.rect(screen, HUD_HEALTH_BORDER, (x, y, w, h), 2)

    # ------------------------------------------------------------------
    # Hotbar
    # ------------------------------------------------------------------

    def _draw_hotbar(self, screen):
        inv = self.player.inventory

        for i in range(HOTBAR_SLOTS):
            slot_x = self._hotbar_x + i * (HOTBAR_SLOT_SIZE + HOTBAR_SLOT_GAP)
            slot_y = self._hotbar_y
            rect   = (slot_x, slot_y, HOTBAR_SLOT_SIZE, HOTBAR_SLOT_SIZE)

            # Slot background
            pygame.draw.rect(screen, HOTBAR_BG, rect)

            # Item icon + quantity
            item = inv.slots[i]
            if item:
                item_def = inv.get_def(item.item_id)
                color    = tuple(item_def.get("color", [200, 200, 200]))

                # Colored square with margin inside the slot
                pygame.draw.rect(screen, color, (
                    slot_x + _ITEM_MARGIN,
                    slot_y + _ITEM_MARGIN,
                    HOTBAR_SLOT_SIZE - _ITEM_MARGIN * 2,
                    HOTBAR_SLOT_SIZE - _ITEM_MARGIN * 2
                ))

                # Quantity in bottom-right — only show if > 1
                if item.quantity > 1:
                    qty_surf = self._font.render(str(item.quantity), True, WHITE)
                    screen.blit(qty_surf, (
                        slot_x + HOTBAR_SLOT_SIZE - qty_surf.get_width()  - 3,
                        slot_y + HOTBAR_SLOT_SIZE - qty_surf.get_height() - 2
                    ))

            # Border — yellow for selected, grey otherwise
            border_color = HOTBAR_SELECTED if i == self.player.hotbar_slot else HOTBAR_BORDER
            pygame.draw.rect(screen, border_color, rect, 2)

    # ------------------------------------------------------------------
    # Wind indicator
    # ------------------------------------------------------------------

    def _draw_wind(self, screen, wind):
        x, y = _WIND_HUD_X, _WIND_HUD_Y

        # Label
        label = self._wind_font.render("WIND", True, (160, 160, 180))
        screen.blit(label, (x, y))
        y += label.get_height() + 3

        # Track background
        pygame.draw.rect(screen, (50, 50, 60), (x, y, _WIND_BAR_W, _WIND_BAR_H))

        # Filled portion — center-out in wind direction
        ratio    = max(-1.0, min(1.0, wind / WIND_MAX))
        center_x = x + _WIND_BAR_W // 2
        fill_w   = int(abs(ratio) * (_WIND_BAR_W // 2))

        if ratio > 0:   # wind blows right
            bar_x = center_x
            color = (220, 180, 80)
        elif ratio < 0: # wind blows left
            bar_x = center_x - fill_w
            color = (100, 180, 220)
        else:
            bar_x, fill_w, color = center_x, 0, (160, 160, 180)

        if fill_w > 0:
            pygame.draw.rect(screen, color, (bar_x, y, fill_w, _WIND_BAR_H))

        # Center divider + outline
        pygame.draw.rect(screen, (100, 100, 120), (x, y, _WIND_BAR_W, _WIND_BAR_H), 1)
        pygame.draw.line(screen, (100, 100, 120), (center_x, y), (center_x, y + _WIND_BAR_H))

    # ------------------------------------------------------------------
    # Arrow count (shown while aiming)
    # ------------------------------------------------------------------

    def _draw_arrow_count(self, screen):
        count = self.player.inventory.count("arrow")
        surf  = self._wind_font.render(f"Arrows: {count}", True, (220, 200, 120))
        screen.blit(surf, (_WIND_HUD_X, _WIND_HUD_Y + 28))
