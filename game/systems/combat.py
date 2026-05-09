"""
systems/combat.py
Attack hitbox — spawned by the player when swinging, lives for ATTACK_DURATION seconds.
Supports optional knockback and status effect for special melee abilities.
Owns: position relative to owner, damage, hit tracking, expiry timer.
Does NOT own: who to hit (engine handles that), drawing logic (engine draws it for debug).
"""

import pygame
from game.settings import (
    ATTACK_WIDTH, ATTACK_HEIGHT, ATTACK_DAMAGE, ATTACK_DURATION
)


class AttackHitbox:
    def __init__(self, owner, damage=ATTACK_DAMAGE,
                 width=None, height=None,
                 knockback=0, status_def=None,
                 duration=None):
        """
        owner      — the entity swinging; must have .facing and .rect.
        damage     — hp to deal on hit.
        width/height — override default ATTACK_WIDTH/HEIGHT for special abilities.
        knockback  — px/s horizontal impulse applied to hit targets.
        status_def — optional status effect dict applied on hit.
        duration   — override default ATTACK_DURATION.
        """
        self.owner        = owner
        self.facing       = owner.facing
        self.damage       = damage
        self.knockback    = float(knockback)
        self.status_def   = status_def
        self.timer        = float(duration) if duration is not None else ATTACK_DURATION
        self.already_hit  = set()
        self.sound_played = False

        w = int(width)  if width  is not None else ATTACK_WIDTH
        h = int(height) if height is not None else ATTACK_HEIGHT

        x = (owner.rect.centerx if self.facing == 1
             else owner.rect.centerx - w)
        self.rect = pygame.Rect(x, owner.rect.y, w, h)

    def update(self, dt):
        w = self.rect.width
        x = (self.owner.rect.centerx if self.facing == 1
             else self.owner.rect.centerx - w)
        self.rect.x = x
        self.rect.y = self.owner.rect.y
        self.timer -= dt

    @property
    def expired(self):
        return self.timer <= 0
