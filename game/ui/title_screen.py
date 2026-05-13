"""
ui/title_screen.py
Title screen — shown on startup before the world loads.
Handles New Game / Continue / Quit selection.
All surfaces created at __init__; draw() only blits.
"""

import pygame
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TITLE

_BG_COLOR    = (12, 12, 20)
_TITLE_COLOR = (220, 200, 80)
_ON_COLOR    = (240, 240, 255)
_OFF_COLOR   = (80,  80,  100)
_SEL_COLOR   = (255, 220, 60)


_VERSION = "v0.1"


class TitleScreen:
    _OPTIONS = ["New Game", "Continue", "Quit"]

    def __init__(self, has_save: bool, save_info: dict | None = None):
        self._has_save  = has_save
        self._save_info = save_info   # {"level": int, "zone": str} or None
        self._cursor    = 0 if not has_save else 1

        # Fonts — created once
        self._font_title  = pygame.font.SysFont(None, 96)
        self._font_sub    = pygame.font.SysFont(None, 24)
        self._font_option = pygame.font.SysFont(None, 38)
        self._font_hint   = pygame.font.SysFont(None, 18)

        # Pre-render static surfaces
        self._title_surf = self._font_title.render(TITLE, True, _TITLE_COLOR)
        self._sub_surf   = self._font_sub.render(
            "A survival RPG engine  —  build any game on top", True, (120, 120, 140))
        self._hint_surf  = self._font_hint.render(
            "↑ ↓  Navigate      Enter  Select", True, (70, 70, 90))

        # Option surfaces (both enabled / dimmed variants)
        self._opt_on  = [self._font_option.render(o, True, _ON_COLOR)  for o in self._OPTIONS]
        self._opt_off = [self._font_option.render(o, True, _OFF_COLOR) for o in self._OPTIONS]
        self._cur_arr = self._font_option.render("▶", True, _SEL_COLOR)

        # Save info line shown under Continue (e.g. "Level 5  •  Zone 01")
        self._save_info_surf = None
        if has_save and save_info:
            zone_label = save_info.get("zone", "").replace("_", " ").title()
            info_text  = f"Level {save_info.get('level', 1)}   ·   {zone_label}"
            self._save_info_surf = self._font_sub.render(info_text, True, (100, 160, 120))

        # Version label (bottom-right corner)
        self._version_surf = self._font_hint.render(_VERSION, True, (50, 50, 70))

        # Dim overlay for subtle gradient effect
        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 30, 60))

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event) -> str | None:
        """Returns 'new_game', 'continue', 'quit', or None."""
        if event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_UP, pygame.K_w):
            self._cursor = (self._cursor - 1) % len(self._OPTIONS)

        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._cursor = (self._cursor + 1) % len(self._OPTIONS)

        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            opt = self._OPTIONS[self._cursor]
            if opt == "Continue" and not self._has_save:
                return None   # greyed out — ignore
            return opt.lower().replace(" ", "_")

        elif event.key == pygame.K_ESCAPE:
            return "quit"

        return None

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen):
        screen.fill(_BG_COLOR)
        screen.blit(self._overlay, (0, 0))

        cx = SCREEN_WIDTH // 2

        # Title
        ty = SCREEN_HEIGHT // 4
        screen.blit(self._title_surf,
                    (cx - self._title_surf.get_width() // 2, ty))
        screen.blit(self._sub_surf,
                    (cx - self._sub_surf.get_width() // 2,
                     ty + self._title_surf.get_height() + 8))

        # Divider
        div_y = ty + self._title_surf.get_height() + 50
        pygame.draw.line(screen, (40, 40, 60),
                         (cx - 160, div_y), (cx + 160, div_y))

        # Options
        opt_start_y = div_y + 28
        opt_gap     = 52
        for i, label in enumerate(self._OPTIONS):
            disabled = (label == "Continue" and not self._has_save)
            surf = self._opt_off[i] if disabled else self._opt_on[i]

            oy = opt_start_y + i * opt_gap
            ox = cx - surf.get_width() // 2

            # Show save metadata under the Continue option
            if label == "Continue" and self._save_info_surf and not disabled:
                si = self._save_info_surf
                screen.blit(si, (cx - si.get_width() // 2, oy - si.get_height() - 2))

            # Selection highlight background
            if i == self._cursor and not disabled:
                hw = surf.get_width() + 60
                hh = surf.get_height() + 8
                hx = cx - hw // 2
                hy = oy - 4
                pygame.draw.rect(screen, (25, 25, 45), (hx, hy, hw, hh), border_radius=6)
                pygame.draw.rect(screen, (60, 60, 100), (hx, hy, hw, hh), 1, border_radius=6)

                # Cursor arrow
                screen.blit(self._cur_arr,
                            (ox - self._cur_arr.get_width() - 10,
                             oy + (surf.get_height() - self._cur_arr.get_height()) // 2))

            screen.blit(surf, (ox, oy))

        # Hint
        screen.blit(self._hint_surf,
                    (cx - self._hint_surf.get_width() // 2,
                     SCREEN_HEIGHT - 40))

        # Version label (bottom-right)
        screen.blit(self._version_surf,
                    (SCREEN_WIDTH - self._version_surf.get_width() - 12,
                     SCREEN_HEIGHT - self._version_surf.get_height() - 10))
