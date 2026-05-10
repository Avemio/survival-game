"""
ui/inventory_screen.py
Full 32-slot inventory screen — opened with the I key.
Shows all inventory slots in a grid; first 8 mirror the hotbar.

Controls while open:
  Arrow keys  — move cursor
  Enter / F   — use selected item
  D           — drop item at player's world position
  I / Esc     — close
"""

import pygame
from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    HOTBAR_SLOTS, INVENTORY_SLOTS,
    CRAFT_PANEL_BG, CRAFT_PANEL_BORDER,
    CRAFT_TITLE_COLOR, CRAFT_FOOTER_COLOR,
    DIALOGUE_TEXT_COLOR, DIALOGUE_HINT_COLOR,
    WHITE,
)

_COLS       = 8
_ROWS       = INVENTORY_SLOTS // _COLS     # 4
_CELL       = 52    # cell size (px)
_GAP        = 4     # gap between cells
_PADDING    = 20
_TITLE_H    = 46

_PANEL_W = _COLS * (_CELL + _GAP) - _GAP + _PADDING * 2
_PANEL_H = _TITLE_H + _ROWS * (_CELL + _GAP) - _GAP + _PADDING + 46  # +footer

_ITEM_MARGIN = 6


class InventoryScreen:
    def __init__(self, player):
        self.player = player
        self.open   = False
        self._cursor = 0   # flat slot index 0–31

        self._px = (SCREEN_WIDTH  - _PANEL_W) // 2
        self._py = (SCREEN_HEIGHT - _PANEL_H) // 2

        self._font_title = pygame.font.SysFont(None, 28)
        self._font_qty   = pygame.font.SysFont(None, 18)
        self._font_name  = pygame.font.SysFont(None, 19)
        self._font_foot  = pygame.font.SysFont(None, 17)

        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 150))

        self._title_surf = self._font_title.render("INVENTORY", True, CRAFT_TITLE_COLOR)
        self._foot_surf  = self._font_foot.render(
            "↑↓←→  Move      F / Enter  Use      D  Drop      I / Esc  Close",
            True, CRAFT_FOOTER_COLOR,
        )

        self._qty_cache:  list  = [None] * INVENTORY_SLOTS
        # (item_id, Surface) — invalidates when item_id changes or slot is cleared
        self._name_cache: list  = [None] * INVENTORY_SLOTS
        # (cursor_slot, item_id, tip_string, Surface)
        self._tip_cache:  tuple = (-1, "", "", None)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    def invalidate_cache(self, slot_idx: int):
        """Call when an item is removed from a slot to clear its name cache."""
        if 0 <= slot_idx < len(self._name_cache):
            self._name_cache[slot_idx] = None
        self._tip_cache = (-1, "", "", None)

    # ------------------------------------------------------------------
    # Input — engine forwards KEYDOWN events here while open
    # ------------------------------------------------------------------

    def handle_event(self, event) -> str | None:
        """
        Handle a key event.  Returns an action string so the engine can act:
          "use"   — use the item in the cursor slot
          "drop"  — drop the item at the player's world position
          None    — no action needed
        """
        if event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_ESCAPE, pygame.K_i):
            self.close()
            return None

        if event.key == pygame.K_RIGHT:
            self._cursor = (self._cursor + 1) % INVENTORY_SLOTS
        elif event.key == pygame.K_LEFT:
            self._cursor = (self._cursor - 1) % INVENTORY_SLOTS
        elif event.key == pygame.K_DOWN:
            self._cursor = (self._cursor + _COLS) % INVENTORY_SLOTS
        elif event.key == pygame.K_UP:
            self._cursor = (self._cursor - _COLS) % INVENTORY_SLOTS
        elif event.key in (pygame.K_RETURN, pygame.K_f):
            return "use"
        elif event.key == pygame.K_d:
            return "drop"

        return None

    @property
    def cursor_slot(self) -> int:
        return self._cursor

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen):
        if not self.open:
            return

        screen.blit(self._overlay, (0, 0))

        px, py = self._px, self._py
        panel  = pygame.Rect(px, py, _PANEL_W, _PANEL_H)
        pygame.draw.rect(screen, CRAFT_PANEL_BG,     panel, border_radius=8)
        pygame.draw.rect(screen, CRAFT_PANEL_BORDER,  panel, 2, border_radius=8)

        # Title
        screen.blit(self._title_surf, (
            px + (_PANEL_W - self._title_surf.get_width()) // 2,
            py + _PADDING,
        ))

        # Divider
        div_y = py + _TITLE_H
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PADDING, div_y),
                         (px + _PANEL_W - _PADDING, div_y))

        # Grid
        inv = self.player.inventory
        start_y = div_y + _GAP

        for idx in range(INVENTORY_SLOTS):
            col = idx % _COLS
            row = idx // _COLS
            cx  = px + _PADDING + col * (_CELL + _GAP)
            cy  = start_y + row * (_CELL + _GAP)
            cell_r = (cx, cy, _CELL, _CELL)

            # Background — dim for hotbar slots, normal for backpack
            is_hotbar = idx < HOTBAR_SLOTS
            bg = (50, 50, 65) if is_hotbar else CRAFT_PANEL_BG
            pygame.draw.rect(screen, bg, cell_r)

            item = inv.slots[idx]
            if item:
                item_def = inv.get_def(item.item_id)
                color    = tuple(item_def.get("color", [200, 200, 200]))
                pygame.draw.rect(screen, color, (
                    cx + _ITEM_MARGIN, cy + _ITEM_MARGIN,
                    _CELL - _ITEM_MARGIN * 2, _CELL - _ITEM_MARGIN * 2,
                ))
                # Quantity
                if item.quantity > 1:
                    cache = self._qty_cache[idx]
                    if cache is None or cache[0] != item.item_id or cache[1] != item.quantity:
                        surf = self._font_qty.render(str(item.quantity), True, WHITE)
                        self._qty_cache[idx] = (item.item_id, item.quantity, surf)
                    qty_s = self._qty_cache[idx][2]
                    screen.blit(qty_s, (
                        cx + _CELL - qty_s.get_width()  - 3,
                        cy + _CELL - qty_s.get_height() - 2,
                    ))
                # Item name below — cached per slot by item_id
                nc = self._name_cache[idx]
                if nc is None or nc[0] != item.item_id:
                    raw = item_def.get("name", item.item_id)[:8]
                    nc  = (item.item_id, self._font_name.render(raw, True, DIALOGUE_HINT_COLOR))
                    self._name_cache[idx] = nc
                screen.blit(nc[1], (cx + 2, cy + _CELL - nc[1].get_height() - 2))

            # Border — gold for selected, grey otherwise
            border = CRAFT_TITLE_COLOR if idx == self._cursor else CRAFT_PANEL_BORDER
            pygame.draw.rect(screen, border, cell_r, 2)

        # Tooltip for hovered item — cached; re-renders only when cursor or item changes
        hovered = inv.slots[self._cursor]
        tip_y   = start_y + _ROWS * (_CELL + _GAP) + 4
        if hovered:
            item_def  = inv.get_def(hovered.item_id)
            tip_parts = [item_def.get("name", hovered.item_id)]
            if item_def.get("use") == "heal":
                tip_parts.append(f"+{item_def.get('heal_amount', 0)} HP")
            elif item_def.get("use") == "equip_ability":
                tip_parts.append(f"Ability: {item_def.get('ability_id', '')}")
            tip_str = "  |  ".join(tip_parts)
            tc = self._tip_cache
            if tc[0] != self._cursor or tc[1] != hovered.item_id or tc[2] != tip_str:
                tip_s = self._font_name.render(tip_str, True, DIALOGUE_TEXT_COLOR)
                self._tip_cache = (self._cursor, hovered.item_id, tip_str, tip_s)
            screen.blit(self._tip_cache[3], (px + _PADDING, tip_y))

        # Footer divider + hint
        footer_y = py + _PANEL_H - 40
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PADDING, footer_y),
                         (px + _PANEL_W - _PADDING, footer_y))
        screen.blit(self._foot_surf, (
            px + (_PANEL_W - self._foot_surf.get_width()) // 2,
            footer_y + (40 - self._foot_surf.get_height()) // 2,
        ))
