"""
ui/quest_log.py
Quest log overlay — press J to open/close.
Shows active quests with progress bars and a completed section.
Pause pattern: world pauses while open.

Performance: all text surfaces are pre-rendered on open / on state change.
draw() only blits pre-built surfaces.
"""

import pygame
from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CRAFT_PANEL_BG, CRAFT_PANEL_BORDER,
    CRAFT_TITLE_COLOR, CRAFT_FOOTER_COLOR,
    CRAFT_INGREDIENT_OK,
    WHITE,
)

_PANEL_W    = 460
_PANEL_H    = 520
_PAD        = 16
_ROW_H      = 28
_BAR_H      = 6
_DONE_COLOR = (80, 160, 80)
_DIM_COLOR  = (80,  80, 100)


class QuestLog:
    def __init__(self, quest_system):
        self.open          = False
        self._quest_system = quest_system
        self._scroll       = 0   # active-quest scroll offset (index)
        self._scroll_ind_cache: tuple = (-1, -1, None)  # (scroll, total, Surface)

        self._px = (SCREEN_WIDTH  - _PANEL_W) // 2
        self._py = (SCREEN_HEIGHT - _PANEL_H) // 2

        self._font_title  = pygame.font.SysFont(None, 26)
        self._font_name   = pygame.font.SysFont(None, 20)
        self._font_desc   = pygame.font.SysFont(None, 17)
        self._font_hint   = pygame.font.SysFont(None, 17)

        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 150))

        # Static surfaces — built once
        self._title_surf = self._font_title.render("QUEST LOG", True, CRAFT_TITLE_COLOR)
        self._hint_surf  = self._font_hint.render(
            "↑↓ Scroll   J / Esc  Close", True, CRAFT_FOOTER_COLOR)
        self._empty_surf = self._font_desc.render(
            "No active quests. Talk to NPCs to receive quests.", True, _DIM_COLOR)

        # Pre-rendered quest rows — rebuilt on open and on state change
        self._active_rows: list[dict]  = []   # {name_s, frac_s, desc_s, progress, count}
        self._done_surfs:  list        = []   # pre-rendered name surfs for completed quests
        self._done_hdr:    object      = None

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def toggle(self):
        self.open = not self.open
        if self.open:
            self._scroll = 0
            self._rebuild()

    def close(self):
        self.open = False

    def notify_changed(self):
        """Call when quest state changes while log is open (quest complete, etc.)."""
        if self.open:
            self._rebuild()

    def _rebuild(self):
        """Pre-render all display surfaces from current quest state."""
        self._active_rows.clear()
        for q in self._quest_system.get_active_display():
            ns  = self._font_name.render(q["name"], True, WHITE)
            fs  = self._font_desc.render(
                f"{q['progress']} / {q['count']}", True, CRAFT_INGREDIENT_OK)
            ds  = self._font_desc.render(q["description"], True, _DIM_COLOR)
            self._active_rows.append({
                "name_s": ns, "frac_s": fs, "desc_s": ds,
                "progress": q["progress"], "count": q["count"],
            })

        done_names = self._quest_system.get_done_names()
        self._done_surfs = [
            self._font_desc.render(f"  {name}", True, _DONE_COLOR)
            for name in done_names
        ]
        if done_names:
            self._done_hdr = self._font_desc.render(
                f"Completed ({len(done_names)})", True, _DONE_COLOR)
        else:
            self._done_hdr = None

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_j, pygame.K_ESCAPE):
            self.close()
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._scroll = max(0, self._scroll - 1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            max_scroll = max(0, len(self._active_rows) - self._visible_rows())
            self._scroll = min(max_scroll, self._scroll + 1)

    def _visible_rows(self) -> int:
        body_h = _PANEL_H - 120   # room for title, footer, done section
        return max(1, body_h // (_ROW_H + _BAR_H + 18))

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen):
        if not self.open:
            return

        px, py = self._px, self._py
        panel  = pygame.Rect(px, py, _PANEL_W, _PANEL_H)
        screen.blit(self._overlay, (0, 0))
        pygame.draw.rect(screen, CRAFT_PANEL_BG,     panel, border_radius=8)
        pygame.draw.rect(screen, CRAFT_PANEL_BORDER,  panel, 2, border_radius=8)

        # Title
        screen.blit(self._title_surf,
                    (px + (_PANEL_W - self._title_surf.get_width()) // 2, py + _PAD))
        div_y = py + _PAD + 28
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PAD, div_y), (px + _PANEL_W - _PAD, div_y))

        y = div_y + 8
        visible = self._visible_rows()

        # ---- Active quests ----
        active_slice = self._active_rows[self._scroll: self._scroll + visible]
        if not self._active_rows:
            screen.blit(self._empty_surf, (px + _PAD, y))
            y += 30
        else:
            # Scroll indicator
            total = len(self._active_rows)
            if total > visible:
                hi = min(self._scroll + visible, total)
                sc = self._scroll_ind_cache
                if sc[0] != self._scroll or sc[1] != total:
                    ind = self._font_desc.render(
                        f"({self._scroll + 1}–{hi}/{total})", True, _DIM_COLOR)
                    self._scroll_ind_cache = (self._scroll, total, ind)
                screen.blit(self._scroll_ind_cache[2],
                            (px + _PANEL_W - _PAD - self._scroll_ind_cache[2].get_width(),
                             py + _PAD + 2))

            for row in active_slice:
                if y + _ROW_H + _BAR_H + 22 > py + _PANEL_H - 60:
                    break
                screen.blit(row["name_s"], (px + _PAD, y))
                screen.blit(row["frac_s"],
                            (px + _PANEL_W - _PAD - row["frac_s"].get_width(), y + 2))
                y += row["name_s"].get_height() + 2
                screen.blit(row["desc_s"], (px + _PAD + 8, y))
                y += row["desc_s"].get_height() + 4

                # Progress bar
                bx  = px + _PAD
                bw  = _PANEL_W - _PAD * 2
                ratio = min(1.0, row["progress"] / row["count"]) if row["count"] > 0 else 1.0
                pygame.draw.rect(screen, (20, 20, 50), (bx, y, bw, _BAR_H))
                fw = int(bw * ratio)
                if fw > 0:
                    pygame.draw.rect(screen, CRAFT_INGREDIENT_OK, (bx, y, fw, _BAR_H))
                pygame.draw.rect(screen, CRAFT_PANEL_BORDER, (bx, y, bw, _BAR_H), 1)
                y += _BAR_H + 12

        # ---- Completed ----
        if self._done_hdr:
            pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                             (px + _PAD, y), (px + _PANEL_W - _PAD, y))
            y += 6
            screen.blit(self._done_hdr, (px + _PAD, y))
            y += self._done_hdr.get_height() + 4
            for ds in self._done_surfs:
                if y + 20 > py + _PANEL_H - 50:
                    break
                screen.blit(ds, (px + _PAD, y))
                y += ds.get_height() + 2

        # Footer
        footer_y = py + _PANEL_H - 36
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PAD, footer_y), (px + _PANEL_W - _PAD, footer_y))
        screen.blit(self._hint_surf,
                    (px + (_PANEL_W - self._hint_surf.get_width()) // 2,
                     footer_y + (36 - self._hint_surf.get_height()) // 2))
