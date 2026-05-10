"""
ui/hud.py
Heads-up display — drawn in screen space every frame on top of the world.
Owns: health bar, mana bar, hotbar slots, ability slots (Q/R), wind indicator.
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
    MANA_BAR_H, MANA_BAR_BG, MANA_BAR_FG, MANA_BAR_BORDER,
    ABILITY_SLOT_SIZE,
    WIND_MAX, WHITE,
    STATUS_COLORS,
    XP_BAR_H, XP_BAR_BG, XP_BAR_FG, XP_BAR_BORDER,
)

_ITEM_MARGIN = 6
_WIND_BAR_W  = 100
_WIND_BAR_H  = 8
_WIND_HUD_X  = SCREEN_WIDTH - 130
_WIND_HUD_Y  = 20

_MANA_BAR_X = HUD_HEALTH_X
_MANA_BAR_Y = HUD_HEALTH_Y + HUD_HEALTH_H + 5
_XP_BAR_Y   = _MANA_BAR_Y + MANA_BAR_H + 4


class HUD:
    def __init__(self, player, ability_system=None):
        self.player = player
        self._ability_system = ability_system

        # Fonts — created once here, never in draw()
        self._font      = pygame.font.SysFont(None, 18)
        self._wind_font = pygame.font.SysFont(None, 16)
        self._num_font  = pygame.font.SysFont(None, 14)
        self._ab_font   = pygame.font.SysFont(None, 16)
        self._hp_font   = pygame.font.SysFont(None, 16)

        # Pre-compute hotbar geometry
        total_w = HOTBAR_SLOTS * HOTBAR_SLOT_SIZE + (HOTBAR_SLOTS - 1) * HOTBAR_SLOT_GAP
        self._hotbar_x = (SCREEN_WIDTH - total_w) // 2
        self._hotbar_y = SCREEN_HEIGHT - HOTBAR_SLOT_SIZE - HOTBAR_Y_OFFSET

        # Pre-rendered static surfaces
        self._wind_label = self._wind_font.render("WIND", True, (160, 160, 180))

        # Hotbar slot number labels (1–8) — static
        self._slot_nums = [
            self._num_font.render(str(i + 1), True, (140, 140, 160))
            for i in range(HOTBAR_SLOTS)
        ]

        # Ability slot key labels — static
        self._q_label = self._ab_font.render("Q", True, (200, 200, 220))
        self._r_label = self._ab_font.render("R", True, (200, 200, 220))

        # Pre-allocate cooldown overlay surface (full size; blit a subsurface slice in draw)
        self._cd_overlay = pygame.Surface((ABILITY_SLOT_SIZE, ABILITY_SLOT_SIZE))
        self._cd_overlay.set_alpha(140)
        self._cd_overlay.fill((0, 0, 0))

        # Ability name surface cache per slot: (ability_id, Surface) or None
        self._ab_name_cache = [None, None]

        # Per-slot quantity surface cache: (quantity, Surface) or None
        self._qty_cache   = [None] * HOTBAR_SLOTS

        # Arrow count cache: (count, Surface)
        self._arrow_cache = (-1, None)

        # Gold display cache: (count, Surface)
        self._gold_cache = (-1, None)

        # Health number cache: (hp_text, Surface)
        self._hp_cache = ("", None)

        # XP / level cache
        self._xp_cache    = (-1, -1, None)   # (xp, xp_to_next, Surface)
        self._level_cache = (-1, None)        # (level, Surface)
        self._levelup_font = pygame.font.SysFont(None, 36)
        self._levelup_surf = self._levelup_font.render("LEVEL UP!", True, (255, 240, 80))

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, wind=0.0):
        self._draw_health_bar(screen)
        self._draw_mana_bar(screen)
        self._draw_xp_bar(screen)
        self._draw_hotbar(screen)
        self._draw_ability_slots(screen)
        self._draw_wind(screen, wind)
        self._draw_arrow_count(screen)
        self._draw_gold(screen)
        self._draw_status_effects(screen)
        self._draw_levelup_flash(screen)

    # ------------------------------------------------------------------
    # Health bar
    # ------------------------------------------------------------------

    def _draw_health_bar(self, screen):
        x, y, w, h = HUD_HEALTH_X, HUD_HEALTH_Y, HUD_HEALTH_W, HUD_HEALTH_H
        pygame.draw.rect(screen, HUD_HEALTH_BG, (x, y, w, h))
        ratio = max(0, self.player.health / self.player.max_health)
        fill_w = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, HUD_HEALTH_FG, (x, y, fill_w, h))
        pygame.draw.rect(screen, HUD_HEALTH_BORDER, (x, y, w, h), 2)

        # Numeric HP display — cached; updates only when value changes
        hp_text = f"{int(self.player.health)} / {self.player.max_health}"
        if self._hp_cache[0] != hp_text:
            surf = self._hp_font.render(hp_text, True, WHITE)
            self._hp_cache = (hp_text, surf)
        screen.blit(self._hp_cache[1], (x + w + 6, y + 1))

    # ------------------------------------------------------------------
    # Mana bar
    # ------------------------------------------------------------------

    def _draw_mana_bar(self, screen):
        x, y, w, h = _MANA_BAR_X, _MANA_BAR_Y, HUD_HEALTH_W, MANA_BAR_H
        pygame.draw.rect(screen, MANA_BAR_BG, (x, y, w, h))
        ratio = max(0, self.player.mana / self.player.max_mana)
        fill_w = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, MANA_BAR_FG, (x, y, fill_w, h))
        pygame.draw.rect(screen, MANA_BAR_BORDER, (x, y, w, h), 1)

    # ------------------------------------------------------------------
    # Hotbar
    # ------------------------------------------------------------------

    def _draw_hotbar(self, screen):
        inv = self.player.inventory

        for i in range(HOTBAR_SLOTS):
            slot_x = self._hotbar_x + i * (HOTBAR_SLOT_SIZE + HOTBAR_SLOT_GAP)
            slot_y = self._hotbar_y
            rect   = (slot_x, slot_y, HOTBAR_SLOT_SIZE, HOTBAR_SLOT_SIZE)

            pygame.draw.rect(screen, HOTBAR_BG, rect)

            # Slot number (top-left)
            screen.blit(self._slot_nums[i], (slot_x + 3, slot_y + 2))

            item = inv.slots[i]
            if item:
                item_def = inv.get_def(item.item_id)
                color    = tuple(item_def.get("color", [200, 200, 200]))
                pygame.draw.rect(screen, color, (
                    slot_x + _ITEM_MARGIN,
                    slot_y + _ITEM_MARGIN,
                    HOTBAR_SLOT_SIZE - _ITEM_MARGIN * 2,
                    HOTBAR_SLOT_SIZE - _ITEM_MARGIN * 2,
                ))
                if item.quantity > 1:
                    cache = self._qty_cache[i]
                    if cache is None or cache[0] != item.quantity:
                        surf = self._font.render(str(item.quantity), True, WHITE)
                        self._qty_cache[i] = (item.quantity, surf)
                    qty_surf = self._qty_cache[i][1]
                    screen.blit(qty_surf, (
                        slot_x + HOTBAR_SLOT_SIZE - qty_surf.get_width()  - 3,
                        slot_y + HOTBAR_SLOT_SIZE - qty_surf.get_height() - 2,
                    ))

            border_color = HOTBAR_SELECTED if i == self.player.hotbar_slot else HOTBAR_BORDER
            pygame.draw.rect(screen, border_color, rect, 2)

    # ------------------------------------------------------------------
    # Ability slots (Q / R) — shown to the left of hotbar
    # ------------------------------------------------------------------

    def _draw_ability_slots(self, screen):
        ab_y   = self._hotbar_y + (HOTBAR_SLOT_SIZE - ABILITY_SLOT_SIZE) // 2
        gap    = 6
        ab_x_r = self._hotbar_x - ABILITY_SLOT_SIZE - gap          # R slot
        ab_x_q = ab_x_r       - ABILITY_SLOT_SIZE - gap // 2       # Q slot

        for slot_idx, ab_x, label_surf in [
            (0, ab_x_q, self._q_label),
            (1, ab_x_r, self._r_label),
        ]:
            rect   = (ab_x, ab_y, ABILITY_SLOT_SIZE, ABILITY_SLOT_SIZE)
            pygame.draw.rect(screen, (30, 30, 45), rect)

            ability_id = self.player.ability_slots[slot_idx]
            if ability_id:
                # Cached ability name surface — only re-renders when slot changes
                cache = self._ab_name_cache[slot_idx]
                if cache is None or cache[0] != ability_id:
                    name = ability_id.replace("_", " ")[:8]
                    surf = self._ab_font.render(name, True, (180, 200, 255))
                    self._ab_name_cache[slot_idx] = (ability_id, surf)
                ns = self._ab_name_cache[slot_idx][1]
                screen.blit(ns, (
                    ab_x + (ABILITY_SLOT_SIZE - ns.get_width())  // 2,
                    ab_y + (ABILITY_SLOT_SIZE - ns.get_height()) // 2,
                ))
                # Cooldown overlay using pre-allocated surface
                cd = self.player.ability_cooldowns[slot_idx]
                if cd > 0:
                    max_cd = 1.0
                    if self._ability_system:
                        ab_def = self._ability_system.get(ability_id)
                        if ab_def:
                            max_cd = max(ab_def.get("cooldown", 1.0), 0.001)
                    overlay_h = int(ABILITY_SLOT_SIZE * min(1.0, cd / max_cd))
                    if overlay_h > 0:
                        src = pygame.Rect(0, ABILITY_SLOT_SIZE - overlay_h,
                                          ABILITY_SLOT_SIZE, overlay_h)
                        screen.blit(self._cd_overlay,
                                    (ab_x, ab_y + ABILITY_SLOT_SIZE - overlay_h), src)

            # Key label at top-left, border
            screen.blit(label_surf, (ab_x + 3, ab_y + 2))
            pygame.draw.rect(screen, (80, 80, 120), rect, 1)

    # ------------------------------------------------------------------
    # Wind indicator
    # ------------------------------------------------------------------

    def _draw_wind(self, screen, wind):
        x, y = _WIND_HUD_X, _WIND_HUD_Y
        screen.blit(self._wind_label, (x, y))
        y += self._wind_label.get_height() + 3

        pygame.draw.rect(screen, (50, 50, 60), (x, y, _WIND_BAR_W, _WIND_BAR_H))

        ratio    = max(-1.0, min(1.0, wind / WIND_MAX))
        center_x = x + _WIND_BAR_W // 2
        fill_w   = int(abs(ratio) * (_WIND_BAR_W // 2))

        if ratio > 0:
            bar_x, color = center_x, (220, 180, 80)
        elif ratio < 0:
            bar_x, color = center_x - fill_w, (100, 180, 220)
        else:
            bar_x, fill_w, color = center_x, 0, (160, 160, 180)

        if fill_w > 0:
            pygame.draw.rect(screen, color, (bar_x, y, fill_w, _WIND_BAR_H))

        pygame.draw.rect(screen, (100, 100, 120), (x, y, _WIND_BAR_W, _WIND_BAR_H), 1)
        pygame.draw.line(screen, (100, 100, 120), (center_x, y), (center_x, y + _WIND_BAR_H))

    # ------------------------------------------------------------------
    # Arrow count — always shown if player has bow + arrows
    # ------------------------------------------------------------------

    def _draw_arrow_count(self, screen):
        inv = self.player.inventory
        has_bow = inv.count("bow") > 0
        if not has_bow:
            return
        count = inv.count("arrow")
        if count != self._arrow_cache[0]:
            surf = self._wind_font.render(f"Arrows: {count}", True, (220, 200, 120))
            self._arrow_cache = (count, surf)
        screen.blit(self._arrow_cache[1], (_WIND_HUD_X, _WIND_HUD_Y + 28))

    # ------------------------------------------------------------------
    # XP bar + level
    # ------------------------------------------------------------------

    def _draw_xp_bar(self, screen):
        p = self.player
        x, y, w, h = HUD_HEALTH_X, _XP_BAR_Y, HUD_HEALTH_W, XP_BAR_H
        pygame.draw.rect(screen, XP_BAR_BG, (x, y, w, h))
        ratio  = p.xp / p.xp_to_next if p.xp_to_next > 0 else 1.0
        fill_w = int(w * max(0.0, min(1.0, ratio)))
        if fill_w > 0:
            pygame.draw.rect(screen, XP_BAR_FG, (x, y, fill_w, h))
        pygame.draw.rect(screen, XP_BAR_BORDER, (x, y, w, h), 1)

        # Level badge (left of bar)
        if self._level_cache[0] != p.level:
            surf = self._hp_font.render(f"Lv{p.level}", True, (180, 200, 255))
            self._level_cache = (p.level, surf)
        screen.blit(self._level_cache[1], (x + w + 6, y - 2))

        # XP numbers (small, right of level badge)
        xp_key = (p.xp, p.xp_to_next)
        if self._xp_cache[:2] != xp_key:
            surf = self._num_font.render(f"{p.xp}/{p.xp_to_next}", True, (120, 140, 220))
            self._xp_cache = (p.xp, p.xp_to_next, surf)
        screen.blit(self._xp_cache[2], (x + w + 46, y))

    def _draw_levelup_flash(self, screen):
        if self.player._leveled_up_timer <= 0:
            return
        ratio = min(1.0, self.player._leveled_up_timer / 2.5)
        self._levelup_surf.set_alpha(int(ratio * 255))
        sx = SCREEN_WIDTH  // 2 - self._levelup_surf.get_width()  // 2
        sy = SCREEN_HEIGHT // 2 - 80
        screen.blit(self._levelup_surf, (sx, sy))

    # ------------------------------------------------------------------
    # Gold counter (below wind indicator)
    # ------------------------------------------------------------------

    def _draw_gold(self, screen):
        gold = self.player.inventory.count("gold")
        if self._gold_cache[0] != gold:
            surf = self._wind_font.render(f"⬡ {gold}g", True, (255, 210, 30))
            self._gold_cache = (gold, surf)
        screen.blit(self._gold_cache[1], (_WIND_HUD_X, _WIND_HUD_Y + 46))

    # ------------------------------------------------------------------
    # Status effect icons (top of health bar)
    # ------------------------------------------------------------------

    def _draw_status_effects(self, screen):
        effects = self.player.status_effects
        if not effects:
            return
        # Start to the right of the HP number text area
        px = HUD_HEALTH_X + HUD_HEALTH_W + 80
        icon_w, icon_h = 14, HUD_HEALTH_H + 4
        for effect in effects:
            color = STATUS_COLORS.get(effect.type, (200, 200, 200))
            icon_r = (px, HUD_HEALTH_Y - 2, icon_w, icon_h)
            pygame.draw.rect(screen, color, icon_r)
            pygame.draw.rect(screen, (200, 200, 200), icon_r, 1)
            # Duration fill bar (shrinks from right as timer counts down)
            ratio = max(0.0, effect.timer / effect.duration)
            bar_w = int(icon_w * ratio)
            if bar_w > 0:
                pygame.draw.rect(screen, (255, 255, 255),
                                 (px, HUD_HEALTH_Y + icon_h - 4, bar_w, 2))
            px += icon_w + 3
