"""
systems/active_attacks.py
Special attack objects — spawned by the AbilitySystem, updated and drawn by the engine.
Each class represents one attack TYPE; parameters come from abilities.json at spawn time.

Types:
  WaveAttack  — shockwave that travels horizontally along the ground (earthquake, sonic boom)
  AreaAttack  — instant burst at a point, expands-then-fades visual (lightning, explosion)
  AuraAttack  — lingering cloud centered on owner (poison cloud, fire ring)

Melee abilities reuse AttackHitbox (combat.py) with extended params.
Projectile abilities reuse Projectile (projectile.py) with extended params.
"""

import math
import pygame
from game.systems.effects import apply_status


class _AttackBase:
    """Shared interface for all special attack objects."""

    def __init__(self, owner, ab: dict):
        self.owner       = owner
        self.ab          = ab
        self.alive       = True
        self.already_hit: set = set()
        self.status_def  = ab.get("status_effect")  # None or {type, duration, ...}
        self.damage      = int(ab.get("damage", 0))
        self.color       = tuple(ab.get("color", [255, 220, 50]))

    def _hit(self, target) -> None:
        """Apply damage and optional status to target, mark as hit."""
        if target in self.already_hit:
            return
        self.already_hit.add(target)
        if self.damage > 0:
            target.take_damage(self.damage)
        if self.status_def:
            apply_status(target, self.status_def)

    def update(self, dt, platforms, enemies, player):
        raise NotImplementedError

    def draw(self, screen, camera):
        raise NotImplementedError


# ------------------------------------------------------------------
# Wave — travels horizontally along the ground
# ------------------------------------------------------------------

class WaveAttack(_AttackBase):
    """
    A shockwave that expands outward from the owner's feet.
    Damages every enemy it passes through; can stun, slow, etc.
    """

    def __init__(self, owner, ab: dict):
        super().__init__(owner, ab)
        self.speed        = float(ab.get("speed", 300)) * owner.facing
        self.max_distance = float(ab.get("max_distance", 500))
        self.height       = int(ab.get("height", 28))
        self.traveled     = 0.0

        base_x = owner.rect.right if owner.facing == 1 else owner.rect.left
        self.rect = pygame.Rect(base_x, owner.rect.bottom - self.height, 1, self.height)

    def update(self, dt, platforms, enemies, player):
        dist = abs(self.speed) * dt
        self.traveled += dist
        if self.traveled >= self.max_distance:
            self.alive = False
            return

        # Grow the wave rect from the owner outward
        if self.speed > 0:
            self.rect.x     = self.owner.rect.right
            self.rect.width = int(self.traveled)
        else:
            self.rect.width = int(self.traveled)
            self.rect.x     = self.owner.rect.left - self.rect.width

        self.rect.y = self.owner.rect.bottom - self.height

        for enemy in enemies:
            if self.rect.colliderect(enemy.rect):
                self._hit(enemy)

        # Enemy-owned waves can also hit the player
        if self.owner is not player and self.rect.colliderect(player.rect):
            self._hit(player)

    def draw(self, screen, camera):
        if self.rect.width < 2:
            return
        ratio  = max(0.0, 1.0 - self.traveled / self.max_distance)
        color  = tuple(int(c * (0.4 + 0.6 * ratio)) for c in self.color)
        pygame.draw.rect(screen, color, camera.apply_tuple(self.rect))
        # Bright leading edge
        edge_w = 4
        if self.speed > 0:
            ex = self.rect.right - edge_w
        else:
            ex = self.rect.left
        edge_r = pygame.Rect(ex, self.rect.y, edge_w, self.rect.height)
        pygame.draw.rect(screen, self.color, camera.apply_tuple(edge_r))


# ------------------------------------------------------------------
# Area — instant burst expanding circle
# ------------------------------------------------------------------

class AreaAttack(_AttackBase):
    """
    An expanding ring burst at a world position.
    Damage is applied immediately on creation; visual persists for duration.
    """

    def __init__(self, owner, ab: dict, cx: float, cy: float, enemies, player):
        super().__init__(owner, ab)
        self.cx       = cx
        self.cy       = cy
        self.radius   = float(ab.get("radius", 80))
        self.duration = float(ab.get("visual_duration", ab.get("duration", 0.4)))
        self.timer    = self.duration

        # Hit everything in radius immediately
        hit_rect = pygame.Rect(cx - self.radius, cy - self.radius,
                               self.radius * 2, self.radius * 2)
        for enemy in enemies:
            if hit_rect.colliderect(enemy.rect) and self._in_radius(enemy.rect.center):
                self._hit(enemy)
        if owner is not player and hit_rect.colliderect(player.rect):
            if self._in_radius(player.rect.center):
                self._hit(player)

    def _in_radius(self, center) -> bool:
        dx = center[0] - self.cx
        dy = center[1] - self.cy
        return dx * dx + dy * dy <= self.radius * self.radius

    def update(self, dt, platforms, enemies, player):
        self.timer -= dt
        if self.timer <= 0:
            self.alive = False

    def draw(self, screen, camera):
        sx, sy = camera.world_to_screen(self.cx, self.cy)
        ratio  = self.timer / self.duration
        r      = int(self.radius * (2.0 - ratio))   # ring expands outward
        alpha  = max(0, int(ratio * 220))
        color  = tuple(min(255, int(c * ratio)) for c in self.color)
        if r > 0:
            pygame.draw.circle(screen, color, (sx, sy), r, max(1, int(3 * ratio)))


# ------------------------------------------------------------------
# Aura — lingering cloud centered on owner
# ------------------------------------------------------------------

class AuraAttack(_AttackBase):
    """
    A cloud that stays centered on the owner and ticks damage/status onto
    enemies inside it at a regular interval.
    """

    def __init__(self, owner, ab: dict):
        super().__init__(owner, ab)
        self.radius    = float(ab.get("radius", 100))
        self.timer     = float(ab.get("duration", 5.0))
        self.max_timer = self.timer
        self.dps       = float(ab.get("damage_per_second", 0))
        self._tick     = 0.0
        self._tick_rate = 0.5   # apply damage every 0.5 s

    def _in_radius(self, center) -> bool:
        cx = self.owner.rect.centerx
        cy = self.owner.rect.centery
        dx = center[0] - cx
        dy = center[1] - cy
        return dx * dx + dy * dy <= self.radius * self.radius

    def update(self, dt, platforms, enemies, player):
        self.timer -= dt
        if self.timer <= 0:
            self.alive = False
            return

        self._tick -= dt
        if self._tick <= 0:
            self._tick = self._tick_rate
            for enemy in enemies:
                if self._in_radius(enemy.rect.center):
                    if self.dps > 0:
                        enemy.take_damage(self.dps * self._tick_rate)
                    if self.status_def:
                        apply_status(enemy, self.status_def)

    def draw(self, screen, camera):
        cx = self.owner.rect.centerx
        cy = self.owner.rect.centery
        sx, sy = camera.world_to_screen(cx, cy)
        ratio  = self.timer / self.max_timer
        r      = int(self.radius)
        # Pulsing fill
        pulse  = 0.3 + 0.2 * abs(math.sin(self.timer * 3))
        color  = tuple(int(c * pulse) for c in self.color)
        pygame.draw.circle(screen, color, (sx, sy), r)
        # Bright ring
        edge_color = tuple(min(255, int(c * 0.8)) for c in self.color)
        pygame.draw.circle(screen, edge_color, (sx, sy), r, 2)
