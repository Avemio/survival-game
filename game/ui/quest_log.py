"""
ui/quest_log.py
Quest log overlay — press J to open/close.
Shows active quests with progress bars and a completed section.
Pause pattern: world pauses while open.
"""

import pygame
from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CRAFT_PANEL_BG, CRAFT_PANEL_BORDER,
    CRAFT_TITLE_COLOR, CRAFT_FOOTER_COLOR,
    CRAFT_INGREDIENT_OK, CRAFT_INGREDIENT_MISS,
    WHITE,
)

_PANEL_W    = 460
_PANEL_H    = 520
_PAD        = 16
_ROW_H      = 28
_BAR_H      = 6
_DONE_COLOR = (80, 160, 80)
_DIM_COLOR  = (80, 80, 100)


class QuestLog:
    def __init__(self, quest_system):
        self.open          = False
        self._quest_system = quest_system

        self._px = (SCREEN_WIDTH  - _PANEL_W) // 2
        self._py = (SCREEN_HEIGHT - _PANEL_H) // 2

        self._font_title  = pygame.font.SysFont(None, 26)
        self._font_name   = pygame.font.SysFont(None, 20)
        self._font_desc   = pygame.font.SysFont(None, 17)
        self._font_hint   = pygame.font.SysFont(None, 17)

        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 150))

        self._title_surf = self._font_title.render("QUEST LOG", True, CRAFT_TITLE_COLOR)
        self._hint_surf  = self._font_hint.render(
            "J / Esc  Close", True, CRAFT_FOOTER_COLOR)
        self._empty_surf = self._font_desc.render(
            "No active quests. Talk to NPCs to get quests.", True, _DIM_COLOR)

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_j, pygame.K_ESCAPE):
            self.close()

    def draw(self, screen):
        if not self.open:
            return

        screen.blit(self._overlay, (0, 0))

        px, py = self._px, self._py
        panel  = pygame.Rect(px, py, _PANEL_W, _PANEL_H)
        pygame.draw.rect(screen, CRAFT_PANEL_BG,     panel, border_radius=8)
        pygame.draw.rect(screen, CRAFT_PANEL_BORDER,  panel, 2, border_radius=8)

        # Title
        screen.blit(self._title_surf,
                    (px + (_PANEL_W - self._title_surf.get_width()) // 2, py + _PAD))

        div_y = py + _PAD + 28
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PAD, div_y), (px + _PANEL_W - _PAD, div_y))

        y = div_y + 10

        # ---- Active quests ----
        active = self._quest_system.get_active_display()
        if not active:
            screen.blit(self._empty_surf, (px + _PAD, y))
            y += 30
        else:
            for q in active:
                if y + _ROW_H + _BAR_H + 30 > py + _PANEL_H - 60:
                    break

                # Quest name
                ns = self._font_name.render(q["name"], True, WHITE)
                screen.blit(ns, (px + _PAD, y))

                # Progress fraction
                frac_str = f"{q['progress']} / {q['count']}"
                fs = self._font_desc.render(frac_str, True, CRAFT_INGREDIENT_OK)
                screen.blit(fs, (px + _PANEL_W - _PAD - fs.get_width(), y + 2))

                y += ns.get_height() + 2

                # Description
                ds = self._font_desc.render(q["description"], True, _DIM_COLOR)
                screen.blit(ds, (px + _PAD + 8, y))
                y += ds.get_height() + 4

                # Progress bar
                bar_x = px + _PAD
                bar_w = _PANEL_W - _PAD * 2
                pygame.draw.rect(screen, (20, 20, 50), (bar_x, y, bar_w, _BAR_H))
                ratio  = min(1.0, q["progress"] / q["count"]) if q["count"] > 0 else 1.0
                fill_w = int(bar_w * ratio)
                if fill_w > 0:
                    pygame.draw.rect(screen, CRAFT_INGREDIENT_OK, (bar_x, y, fill_w, _BAR_H))
                pygame.draw.rect(screen, CRAFT_PANEL_BORDER, (bar_x, y, bar_w, _BAR_H), 1)
                y += _BAR_H + 12

        # ---- Completed quests ----
        done_names = self._quest_system.get_done_names()
        if done_names:
            pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                             (px + _PAD, y), (px + _PANEL_W - _PAD, y))
            y += 6
            hdr = self._font_desc.render(f"Completed ({len(done_names)})", True, _DONE_COLOR)
            screen.blit(hdr, (px + _PAD, y))
            y += hdr.get_height() + 4
            for name in done_names:
                if y + 20 > py + _PANEL_H - 50:
                    break
                ds = self._font_desc.render(f"✓  {name}", True, _DONE_COLOR)
                screen.blit(ds, (px + _PAD + 8, y))
                y += ds.get_height() + 2

        # Footer
        footer_y = py + _PANEL_H - 36
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PAD, footer_y), (px + _PANEL_W - _PAD, footer_y))
        screen.blit(self._hint_surf,
                    (px + (_PANEL_W - self._hint_surf.get_width()) // 2,
                     footer_y + (36 - self._hint_surf.get_height()) // 2))
