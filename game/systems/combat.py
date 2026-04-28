"""
systems/combat.py
Attack hitbox — spawned by the player when swinging, lives for ATTACK_DURATION seconds.
Owns: position relative to owner, damage value, hit tracking, expiry timer.
Does NOT own: who to hit (engine handles that), drawing logic (engine draws it for debug).
"""

import pygame
from game.settings import (
    ATTACK_WIDTH, ATTACK_HEIGHT, ATTACK_DAMAGE, ATTACK_DURATION
)


class AttackHitbox:
    def __init__(self, owner):
        """
        owner   — the Player; hitbox is positioned in front of them based on facing.
        facing  — owner.facing at spawn time (1 = right, -1 = left).
        """
        self.owner      = owner
        self.facing     = owner.facing
        self.damage     = ATTACK_DAMAGE
        self.timer      = ATTACK_DURATION
        self.already_hit = set()          # enemies we've already damaged this swing

        # Build rect — offset forward from owner's left/right edge
        x = (owner.rect.right if self.facing == 1 else owner.rect.left - ATTACK_WIDTH)
        self.rect = pygame.Rect(x, owner.rect.y, ATTACK_WIDTH, ATTACK_HEIGHT)

    # ------------------------------------------------------------------
    # Update (called by engine each frame)
    # ------------------------------------------------------------------

    def update(self, dt):
        # Track the owner so the hitbox moves with them mid-swing
        x = (self.owner.rect.right if self.facing == 1
             else self.owner.rect.left - ATTACK_WIDTH)
        self.rect.x = x
        self.rect.y = self.owner.rect.y

        self.timer -= dt

    @property
    def expired(self):
        return self.timer <= 0
