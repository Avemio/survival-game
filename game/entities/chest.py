"""
entities/chest.py
A lootable chest placed in a zone.
Press E near it to open and transfer contents to the player's inventory.
Owns: rect, contents list, open state, zone persistence index.
Does NOT own: inventory logic (engine handles the transfer), trigger (engine E key).
"""

import pygame
from game.systems.assets import get as _assets

_CLOSED_COLOR  = (140, 100, 40)
_OPEN_COLOR    = (80,  60,  30)
_BORDER_COLOR  = (200, 160, 60)
_OPEN_BORDER   = (100,  80, 40)


class Chest:
    WIDTH  = 48
    HEIGHT = 36

    def __init__(self, x, y, contents: list, zone_chest_index=None):
        """
        contents           — list of {item_id: str, quantity: int}
        zone_chest_index   — int used to persist opened state in save; None = ephemeral
        """
        self.rect             = pygame.Rect(x, y, self.WIDTH, self.HEIGHT)
        self.contents         = list(contents)
        self.open             = False
        self.zone_chest_index = zone_chest_index

        # Interaction trigger (wider than chest for comfortable approach)
        self.interact_rect = self.rect.inflate(60, 0)

        # Prompt surfaces — created once at init
        self._prompt_font   = pygame.font.SysFont(None, 18)
        self._prompt_shadow = self._prompt_font.render("[E] Open", True, (0, 0, 0))
        self._prompt_surf   = self._prompt_font.render("[E] Open", True, (255, 230, 120))

    def draw(self, screen, camera, player_rect):
        r     = camera.apply_tuple(self.rect)
        color = _OPEN_COLOR  if self.open else _CLOSED_COLOR
        bclr  = _OPEN_BORDER if self.open else _BORDER_COLOR

        pygame.draw.rect(screen, color, r, border_radius=3)
        pygame.draw.rect(screen, bclr,  r, 2, border_radius=3)

        if not self.open:
            # Draw a small horizontal line as a "lid seam"
            mid_y = r[1] + r[3] // 2
            pygame.draw.line(screen, bclr, (r[0] + 4, mid_y), (r[0] + r[2] - 4, mid_y), 1)

        # Prompt overhead when player is nearby and chest is still closed
        if not self.open and self.interact_rect.colliderect(player_rect):
            px = r[0] + r[2] // 2 - self._prompt_surf.get_width() // 2
            py = r[1] - self._prompt_surf.get_height() - 4
            screen.blit(self._prompt_shadow, (px + 1, py + 1))
            screen.blit(self._prompt_surf,   (px,     py))
