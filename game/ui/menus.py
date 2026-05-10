"""
ui/menus.py
In-game overlay menus — currently just the crafting screen.
Owns: layout geometry, font objects, draw logic, cursor state.
Does NOT own: recipe data (CraftingSystem), inventory (Player).

Controls (when open):
  UP / DOWN  — move cursor
  ENTER      — craft selected recipe
  C / ESC    — close
"""

import pygame
from game.systems.assets import get as _assets
from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CRAFT_PANEL_W, CRAFT_PANEL_H,
    CRAFT_PANEL_BG, CRAFT_PANEL_BORDER,
    CRAFT_TITLE_COLOR,
    CRAFT_RECIPE_COLOR, CRAFT_RECIPE_DIM,
    CRAFT_SELECTED_BG,
    CRAFT_INGREDIENT_OK, CRAFT_INGREDIENT_MISS,
    CRAFT_FOOTER_COLOR,
    WHITE,
)

# Layout constants — tweak without touching draw logic
_PADDING        = 20    # inner horizontal/vertical margin
_TITLE_H        = 44    # height of title row (includes bottom gap)
_DIVIDER_H      = 1     # separator line thickness
_RECIPE_NAME_H  = 28    # height of each recipe name row
_INGREDIENT_H   = 22    # height of each ingredient row
_RECIPE_GAP     = 14    # vertical space between recipes
_FOOTER_H       = 36    # height of footer hint bar


class CraftingMenu:
    def __init__(self, player, crafting_system):
        self.player  = player
        self.crafter = crafting_system
        self.open    = False

        # Ordered list of (recipe_id, recipe_def) — stable across frames
        self._recipe_list = list(crafting_system.recipes.items())
        self._cursor      = 0

        # Brief "Crafted!" feedback
        self._feedback_timer = 0.0
        self._feedback_text  = ""

        # Fonts — created once here, never inside draw()
        self._font_title = pygame.font.SysFont(None, 28)
        self._font_name  = pygame.font.SysFont(None, 22)
        self._font_ing   = pygame.font.SysFont(None, 18)
        self._font_foot  = pygame.font.SysFont(None, 17)

        # Panel position — centered on screen
        self._px = (SCREEN_WIDTH  - CRAFT_PANEL_W) // 2
        self._py = (SCREEN_HEIGHT - CRAFT_PANEL_H) // 2

        # Semi-transparent dim overlay — built once
        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 140))

        # Pre-rendered static text — these never change
        self._title_surf  = self._font_title.render("CRAFTING", True, CRAFT_TITLE_COLOR)
        hint_text         = "↑↓  Navigate      Enter  Craft      C / Esc  Close"
        self._footer_surf = self._font_foot.render(hint_text, True, CRAFT_FOOTER_COLOR)
        self._cursor_surf = self._font_name.render("▶", True, CRAFT_TITLE_COLOR)

        # Per-row pre-rendered surfaces — rebuilt when menu opens or after a craft
        self._row_surfs: list = []  # list of (name_surf, [(ing_surf, ok)], craftable)
        self._feedback_surf = None  # pre-rendered feedback surface

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def toggle(self):
        self.open = not self.open
        if self.open:
            self._cursor = 0
            self._feedback_timer = 0.0
            self._rebuild_surfs()

    def close(self):
        self.open = False

    # ------------------------------------------------------------------
    # Input — engine calls this for each KEYDOWN event while menu is open
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        n = len(self._recipe_list)
        if n == 0:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self._cursor = (self._cursor - 1) % n
            self._feedback_timer = 0.0
            _assets().play("ui_select")

        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._cursor = (self._cursor + 1) % n
            self._feedback_timer = 0.0
            _assets().play("ui_select")

        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._try_craft()

    def update(self, dt):
        if self._feedback_timer > 0:
            self._feedback_timer -= dt

    # ------------------------------------------------------------------
    # Crafting
    # ------------------------------------------------------------------

    def _rebuild_surfs(self):
        """Pre-render all recipe/ingredient surfaces (called on open and after craft)."""
        inv = self.player.inventory
        self._row_surfs = []
        for recipe_id, recipe_def in self._recipe_list:
            craftable  = self.crafter.can_craft(recipe_id, inv)
            name_color = CRAFT_RECIPE_COLOR if craftable else CRAFT_RECIPE_DIM
            count      = recipe_def.get("count", 1)
            name_surf  = self._font_name.render(
                f"{recipe_def['name']}  ×{count}", True, name_color)
            ing_surfs  = []
            for item_id, qty_needed in recipe_def["ingredients"].items():
                have      = inv.count(item_id)
                ok        = have >= qty_needed
                ing_color = CRAFT_INGREDIENT_OK if ok else CRAFT_INGREDIENT_MISS
                item_name = inv.get_def(item_id).get("name", item_id)
                ing_surf  = self._font_ing.render(
                    f"{item_name}:  {have} / {qty_needed}", True, ing_color)
                ing_surfs.append(ing_surf)
            self._row_surfs.append((name_surf, ing_surfs, craftable))

    def _try_craft(self):
        if not self._recipe_list:
            return
        recipe_id, recipe_def = self._recipe_list[self._cursor]
        success = self.crafter.craft(recipe_id, self.player.inventory)
        if success:
            count = recipe_def.get("count", 1)
            name  = recipe_def.get("name", recipe_id)
            self._feedback_text  = f"Crafted {name}  ×{count}!"
            self._feedback_timer = 1.8
            self._feedback_surf  = self._font_name.render(self._feedback_text, True, WHITE)
            _assets().play("craft_success")
        else:
            self._feedback_text  = "Not enough materials."
            self._feedback_timer = 1.2
            self._feedback_surf  = self._font_name.render(self._feedback_text, True, WHITE)
            _assets().play("craft_fail")
        self._rebuild_surfs()   # inventory changed; re-render craftable states

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen):
        if not self.open:
            return

        screen.blit(self._overlay, (0, 0))

        # Panel background + border
        panel_rect = pygame.Rect(self._px, self._py, CRAFT_PANEL_W, CRAFT_PANEL_H)
        pygame.draw.rect(screen, CRAFT_PANEL_BG,    panel_rect, border_radius=6)
        pygame.draw.rect(screen, CRAFT_PANEL_BORDER, panel_rect, 2, border_radius=6)

        # Title — pre-rendered at init
        screen.blit(self._title_surf, (
            self._px + (CRAFT_PANEL_W - self._title_surf.get_width()) // 2,
            self._py + _PADDING
        ))

        # Divider under title
        div_y = self._py + _TITLE_H
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (self._px + _PADDING, div_y),
                         (self._px + CRAFT_PANEL_W - _PADDING, div_y))

        # Recipe list
        self._draw_recipes(screen, div_y + 10)

        # Footer
        self._draw_footer(screen)

    def _draw_recipes(self, screen, start_y):
        y     = start_y
        x     = self._px + _PADDING
        max_y = self._py + CRAFT_PANEL_H - _FOOTER_H - 8

        for idx, ((recipe_id, recipe_def), (name_surf, ing_surfs, craftable)) in enumerate(
                zip(self._recipe_list, self._row_surfs)):
            selected = (idx == self._cursor)
            n_ings   = len(recipe_def["ingredients"])
            row_h    = _RECIPE_NAME_H + n_ings * _INGREDIENT_H

            if y + row_h > max_y:
                break

            if selected:
                pygame.draw.rect(screen, CRAFT_SELECTED_BG,
                                 (self._px + 4, y - 3, CRAFT_PANEL_W - 8, row_h + 6),
                                 border_radius=4)

            # Blit pre-rendered surfaces — no render calls here
            screen.blit(name_surf, (x + 8, y + 4))
            if selected:
                screen.blit(self._cursor_surf, (x - 4, y + 4))

            y += _RECIPE_NAME_H
            for ing_surf in ing_surfs:
                screen.blit(ing_surf, (x + 20, y + 2))
                y += _INGREDIENT_H
            y += _RECIPE_GAP

        # Feedback — pre-rendered surface, only set_alpha changes per frame
        if self._feedback_timer > 0 and self._feedback_surf:
            alpha = min(255, int(self._feedback_timer * 300))
            self._feedback_surf.set_alpha(alpha)
            screen.blit(self._feedback_surf, (
                self._px + (CRAFT_PANEL_W - self._feedback_surf.get_width()) // 2,
                self._py + CRAFT_PANEL_H - _FOOTER_H - 32
            ))

    def _draw_footer(self, screen):
        footer_y = self._py + CRAFT_PANEL_H - _FOOTER_H

        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (self._px + _PADDING, footer_y),
                         (self._px + CRAFT_PANEL_W - _PADDING, footer_y))

        screen.blit(self._footer_surf, (
            self._px + (CRAFT_PANEL_W - self._footer_surf.get_width()) // 2,
            footer_y + (_FOOTER_H - self._footer_surf.get_height()) // 2
        ))
