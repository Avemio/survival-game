"""
ui/skill_menu.py
Skill point spending overlay — opened with K, pauses the world.
Owns: skill option display, keyboard navigation, stat application.
Does NOT own: player stats (reads/modifies via reference).
"""

import pygame
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT

_PANEL_W = 480
_PANEL_H = 380
_PANEL_X = (SCREEN_WIDTH  - _PANEL_W) // 2
_PANEL_Y = (SCREEN_HEIGHT - _PANEL_H) // 2

_BG     = (18,  18,  28)
_BORDER = (90,  90, 120)
_TITLE  = (220, 200,  80)
_HI_BG  = (45,  45,  65)
_NAME   = (210, 210, 220)
_DESC   = (140, 160, 180)
_VAL    = (120, 200, 140)
_FOOTER = (120, 120, 140)
_GOLD   = (255, 210,  30)
_DIM    = (100, 100, 120)

_ROW_H     = 52
_ROW_PAD   = 14
_ROW_START = 72

_SKILLS = [
    {"name": "Vitality",  "desc": "+25 Max HP",       "stat": "max_health",    "amount": 25,  "heal":    True},
    {"name": "Endurance", "desc": "+20 Max Mana",      "stat": "max_mana",      "amount": 20,  "restore": True},
    {"name": "Strength",  "desc": "+5 Attack Damage",  "stat": "attack_damage", "amount": 5},
    {"name": "Agility",   "desc": "+15 Move Speed",    "stat": "speed",         "amount": 15},
    {"name": "Focus",     "desc": "+2 Mana Regen/s",   "stat": "mana_regen",    "amount": 2.0},
]


def _stat_label(player, skill: dict) -> str:
    v = getattr(player, skill["stat"], 0)
    if skill["stat"] == "mana_regen":
        return f"Now: {v:.1f}/s"
    return f"Now: {int(v)}"


class SkillMenu:
    def __init__(self, player):
        self.player  = player
        self.open    = False
        self._cursor = 0

        self._title_font  = pygame.font.SysFont(None, 26)
        self._pts_font    = pygame.font.SysFont(None, 22)
        self._name_font   = pygame.font.SysFont(None, 22)
        self._desc_font   = pygame.font.SysFont(None, 18)
        self._val_font    = pygame.font.SysFont(None, 18)
        self._footer_font = pygame.font.SysFont(None, 16)

        self._title_surf  = self._title_font.render("SKILL POINTS", True, _TITLE)
        self._footer_surf = self._footer_font.render(
            "↑↓ Navigate    Enter: Spend    K/Esc: Close", True, _FOOTER)
        self._arrow_surf  = self._name_font.render(">", True, _GOLD)

        # Static skill name + desc surfaces (never change)
        self._skill_surfs = [
            (
                self._name_font.render(s["name"], True, _NAME),
                self._desc_font.render(s["desc"],  True, _DESC),
            )
            for s in _SKILLS
        ]

        # Dynamic caches
        self._pts_cache  = (-1, None)                   # (pts, Surface)
        self._val_caches = [None] * len(_SKILLS)        # each: (label_str, Surface)

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_k, pygame.K_ESCAPE):
            self.close()
        elif event.key == pygame.K_UP:
            self._cursor = (self._cursor - 1) % len(_SKILLS)
        elif event.key == pygame.K_DOWN:
            self._cursor = (self._cursor + 1) % len(_SKILLS)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return self._spend()
        return None

    def _spend(self):
        """Apply the selected upgrade. Returns a (name, desc) tuple if successful, else None."""
        if self.player.skill_points <= 0:
            return None
        skill = _SKILLS[self._cursor]
        amt   = skill["amount"]
        setattr(self.player, skill["stat"], getattr(self.player, skill["stat"]) + amt)
        if skill.get("heal"):
            self.player.health = min(self.player.health + amt, self.player.max_health)
        if skill.get("restore"):
            self.player.mana = min(self.player.mana + amt, self.player.max_mana)
        self.player.skill_points -= 1
        self._val_caches[self._cursor] = None   # invalidate stat display
        return (skill["name"], skill["desc"])

    def draw(self, screen):
        if not self.open:
            return

        panel = pygame.Rect(_PANEL_X, _PANEL_Y, _PANEL_W, _PANEL_H)
        pygame.draw.rect(screen, _BG, panel)
        pygame.draw.rect(screen, _BORDER, panel, 2)

        # Title
        screen.blit(self._title_surf,
                    (_PANEL_X + (_PANEL_W - self._title_surf.get_width()) // 2,
                     _PANEL_Y + 14))

        # Points available
        pts = self.player.skill_points
        if self._pts_cache[0] != pts:
            color = _GOLD if pts > 0 else _DIM
            surf  = self._pts_font.render(f"Available: {pts}", True, color)
            self._pts_cache = (pts, surf)
        screen.blit(self._pts_cache[1],
                    (_PANEL_X + (_PANEL_W - self._pts_cache[1].get_width()) // 2,
                     _PANEL_Y + 42))

        # Skill rows
        for i, (name_surf, desc_surf) in enumerate(self._skill_surfs):
            row_y    = _PANEL_Y + _ROW_START + i * _ROW_H
            row_rect = pygame.Rect(_PANEL_X + _ROW_PAD, row_y,
                                   _PANEL_W - _ROW_PAD * 2, _ROW_H - 4)
            if i == self._cursor:
                pygame.draw.rect(screen, _HI_BG, row_rect)
            pygame.draw.rect(screen, _BORDER, row_rect, 1)

            if i == self._cursor:
                screen.blit(self._arrow_surf, (
                    _PANEL_X + _ROW_PAD + 4,
                    row_y + (row_rect.height - self._arrow_surf.get_height()) // 2,
                ))

            tx = _PANEL_X + _ROW_PAD + 24
            screen.blit(name_surf, (tx, row_y + 8))
            screen.blit(desc_surf, (tx, row_y + 8 + name_surf.get_height() + 2))

            # Current stat value (right-aligned) — cached per row
            label = _stat_label(self.player, _SKILLS[i])
            cache = self._val_caches[i]
            if cache is None or cache[0] != label:
                surf = self._val_font.render(label, True, _VAL)
                self._val_caches[i] = (label, surf)
            val_surf = self._val_caches[i][1]
            screen.blit(val_surf, (
                _PANEL_X + _PANEL_W - _ROW_PAD - val_surf.get_width() - 10,
                row_y + (row_rect.height - val_surf.get_height()) // 2,
            ))

        # Footer
        screen.blit(self._footer_surf,
                    (_PANEL_X + (_PANEL_W - self._footer_surf.get_width()) // 2,
                     _PANEL_Y + _PANEL_H - self._footer_surf.get_height() - 10))
