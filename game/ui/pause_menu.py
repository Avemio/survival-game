"""
ui/pause_menu.py
Pause overlay — shown when Esc is pressed during normal gameplay.
Displays all controls and offers Resume / Quit options.
Does NOT own: game state or input routing (engine handles those).
"""

import sys
import pygame
from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CRAFT_PANEL_BG, CRAFT_PANEL_BORDER,
    CRAFT_TITLE_COLOR, CRAFT_FOOTER_COLOR,
    DIALOGUE_TEXT_COLOR, DIALOGUE_HINT_COLOR,
)

_PANEL_W  = 500
_PANEL_H  = 496   # 15 rows × 26px + title + footer
_PADDING  = 24
_TITLE_H  = 52   # y-offset from panel top to the divider under "PAUSED"
_ROW_H    = 26   # height per control row
_COL_KEY  = 200  # x-offset from panel left (after padding) to key column

_CONTROLS = [
    ("Move",              "WASD  /  Arrow Keys"),
    ("Jump",              "W  /  Space  /  Up"),
    ("Attack",            "Z"),
    ("Ability Q / R",     "Q  /  R"),
    ("Draw Bow",          "Hold X  →  release to fire"),
    ("Aim Bow",           "Up / Down  while drawing"),
    ("Use / Equip Item",  "F"),
    ("Hotbar Slot",       "1 – 8"),
    ("Inventory",         "I"),
    ("Quest Log",         "J"),
    ("Skill Points",      "K"),
    ("Talk / Shop / Open","E"),
    ("Crafting Menu",     "C"),
    ("Shop: Switch Mode", "Tab  (while shop is open)"),
    ("Pause / Close",     "Esc"),
]


class PauseMenu:
    def __init__(self):
        self.open = False

        self._px = (SCREEN_WIDTH  - _PANEL_W) // 2
        self._py = (SCREEN_HEIGHT - _PANEL_H) // 2

        # Fonts — created once at init
        self._font_title  = pygame.font.SysFont(None, 38)
        self._font_action = pygame.font.SysFont(None, 21)
        self._font_key    = pygame.font.SysFont(None, 21)
        self._font_foot   = pygame.font.SysFont(None, 19)

        # Full-screen dim layer
        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 160))

        # Pre-render everything that never changes
        self._title_surf = self._font_title.render("PAUSED", True, CRAFT_TITLE_COLOR)
        self._footer_surf = self._font_foot.render(
            "Esc / Enter  —  Resume               Q  —  Quit",
            True, CRAFT_FOOTER_COLOR,
        )
        self._rows = [
            (
                self._font_action.render(action, True, DIALOGUE_HINT_COLOR),
                self._font_key.render(key,    True, DIALOGUE_TEXT_COLOR),
            )
            for action, key in _CONTROLS
        ]

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    # ------------------------------------------------------------------
    # Input — engine calls this for every KEYDOWN while the menu is open
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.close()
        elif event.key == pygame.K_q:
            pygame.quit()
            sys.exit()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen):
        if not self.open:
            return

        screen.blit(self._overlay, (0, 0))

        px, py = self._px, self._py
        panel_rect = pygame.Rect(px, py, _PANEL_W, _PANEL_H)
        pygame.draw.rect(screen, CRAFT_PANEL_BG,     panel_rect, border_radius=8)
        pygame.draw.rect(screen, CRAFT_PANEL_BORDER,  panel_rect, 2, border_radius=8)

        # Title
        screen.blit(self._title_surf, (
            px + (_PANEL_W - self._title_surf.get_width()) // 2,
            py + _PADDING,
        ))

        # Divider under title
        div_y = py + _TITLE_H
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PADDING, div_y),
                         (px + _PANEL_W - _PADDING, div_y))

        # Control rows — two columns: action (dim) | key binding (bright)
        row_y = div_y + 12
        for a_surf, k_surf in self._rows:
            screen.blit(a_surf, (px + _PADDING, row_y))
            screen.blit(k_surf, (px + _PADDING + _COL_KEY, row_y))
            row_y += _ROW_H

        # Divider above footer
        footer_div_y = py + _PANEL_H - 44
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PADDING, footer_div_y),
                         (px + _PANEL_W - _PADDING, footer_div_y))

        # Footer hint
        screen.blit(self._footer_surf, (
            px + (_PANEL_W - self._footer_surf.get_width()) // 2,
            footer_div_y + (44 - self._footer_surf.get_height()) // 2,
        ))
