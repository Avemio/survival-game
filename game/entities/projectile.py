"""
entities/projectile.py
A projectile in flight — physics, collision, damage, optional status effect.
Supports arrows (gravity + wind) and magic projectiles (custom gravity/wind settings).
Owns: position, velocity, gravity, collision, pierce flag.
Does NOT own: firing logic (engine/abilities), wind value (engine passes it in).
"""

import math
import pygame
from game.settings import ARROW_GRAVITY, ARROW_COLOR
from game.systems.effects import apply_status


class Projectile:
    def __init__(self, x, y, vx, vy, damage,
                 gravity_factor=1.0,
                 wind_affected=True,
                 width=14,
                 height=4,
                 pierce=False,
                 color=None,
                 status_def=None):
        self.pos      = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(vx, vy)
        self.rect     = pygame.Rect(x, y, width, height)
        self.damage   = damage
        self.alive    = True
        self.already_hit  = set()

        self._gravity      = ARROW_GRAVITY * gravity_factor
        self._wind_affected = wind_affected
        self._pierce        = pierce
        self._color         = tuple(color) if color else ARROW_COLOR
        self._status_def    = status_def
        self._w             = width
        self._h             = height

    def update(self, dt, platforms, wind):
        self.velocity.y += self._gravity * dt
        if self._wind_affected:
            self.velocity.x += wind * dt

        self.pos.x += self.velocity.x * dt
        self.pos.y += self.velocity.y * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        for p in platforms:
            if self.rect.colliderect(p):
                self.alive = False
                return

    def hit(self, target) -> bool:
        """Apply damage and optional status to target. Returns True if this was a new hit."""
        if target in self.already_hit:
            return False
        self.already_hit.add(target)
        target.take_damage(self.damage)
        if self._status_def:
            apply_status(target, self._status_def)
        if not self._pierce:
            self.alive = False
        return True

    def draw(self, screen, camera):
        # Use atan2 result directly as radians — no pointless degrees round-trip
        rad   = math.atan2(-self.velocity.y, self.velocity.x)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        half  = self._w * 0.5

        tip_x  = self.pos.x + cos_r * half
        tip_y  = self.pos.y - sin_r * half
        tail_x = self.pos.x - cos_r * half
        tail_y = self.pos.y + sin_r * half

        cx, cy = camera.world_to_screen(tip_x,  tip_y)
        tx, ty = camera.world_to_screen(tail_x, tail_y)
        pygame.draw.line(screen, self._color, (tx, ty), (cx, cy), max(1, self._h))
