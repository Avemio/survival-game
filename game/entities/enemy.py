"""
entities/enemy.py
Enemy entity with a three-state AI: PATROL → CHASE → ATTACK.
Owns: rect, float position, velocity, physics, state machine, hit-flash, alive flag, drawing.
Does NOT own: combat resolution (engine._update_enemy_attacks), drops (engine._spawn_drops).

State transitions:
  PATROL  — walks back and forth; edge probe prevents falling off platforms;
             wall hits flip direction. Transitions to CHASE when player enters aggro_range.
  CHASE   — moves toward the player at chase_speed with full gravity/physics.
             Returns to PATROL when player leaves deaggro_range.
             Transitions to ATTACK when player enters attack_range and cooldown is ready.
  ATTACK  — stops, winds up for _WINDUP_DURATION seconds (turns orange), then spawns
             an AttackHitbox. Returns to CHASE immediately after the hitbox is live.
             Engine resolves the hitbox against the player.
"""

import pygame
from enum import Enum, auto
from game.settings import (
    ENEMY_WIDTH, ENEMY_HEIGHT, ENEMY_HEALTH,
    ENEMY_COLOR, ENEMY_HIT_COLOR, ENEMY_WINDUP_COLOR,
    HIT_FLASH_DURATION,
    ENEMY_SPEED, ENEMY_CHASE_SPEED,
    ENEMY_AGGRO_RANGE, ENEMY_DEAGGRO_RANGE,
    ENEMY_ATTACK_RANGE, ENEMY_ATTACK_DAMAGE, ENEMY_ATTACK_COOLDOWN,
    ENEMY_PATROL_RADIUS,
    GRAVITY, MAX_FALL_SPEED,
)
from game.systems.combat  import AttackHitbox
from game.systems.assets  import get as _assets
from game.systems.effects import tick_all


class EnemyState(Enum):
    PATROL = auto()
    CHASE  = auto()
    ATTACK = auto()


_WINDUP_DURATION = 0.4   # seconds of orange wind-up before hitbox spawns
_EDGE_PROBE_W    = 4     # width of the ground-ahead sensor rect
_EDGE_PROBE_H    = 8     # height — tall enough to catch slightly uneven platforms


class Enemy:
    def __init__(self, x, y, stats=None):
        """
        stats — optional dict from enemies.json.  Any missing key falls back to
                the settings.py constant, so Enemy(x, y) still works for quick tests.
        """
        stats = stats or {}
        w = stats.get("width",  ENEMY_WIDTH)
        h = stats.get("height", ENEMY_HEIGHT)

        self.rect     = pygame.Rect(x, y, w, h)
        self.pos      = pygame.math.Vector2(x, y)   # float position drives rect
        self.velocity = pygame.math.Vector2(0, 0)

        self.health     = stats.get("health", ENEMY_HEALTH)
        self.max_health = self.health   # for health bar display
        self.alive     = True
        self.hit_flash = 0.0   # countdown; >0 = flashing white
        self.loot      = stats.get("drops", [])
        self.facing    = 1     # 1 = right, -1 = left
        self.on_ground = False

        # AI stats — read from data, fall back to settings defaults
        self.patrol_speed    = stats.get("speed",           ENEMY_SPEED)
        self.chase_speed     = stats.get("chase_speed",     ENEMY_CHASE_SPEED)
        self.aggro_range     = stats.get("aggro_range",     ENEMY_AGGRO_RANGE)
        self.deaggro_range   = stats.get("deaggro_range",   ENEMY_DEAGGRO_RANGE)
        self.attack_range    = stats.get("attack_range",    ENEMY_ATTACK_RANGE)
        self.attack_damage   = stats.get("attack_damage",   ENEMY_ATTACK_DAMAGE)
        self.attack_cooldown = stats.get("attack_cooldown", ENEMY_ATTACK_COOLDOWN)
        self.patrol_radius   = stats.get("patrol_radius",   ENEMY_PATROL_RADIUS)
        self._spawn_x        = float(x)   # leash anchor — enemy won't patrol past ± patrol_radius

        self.state         = EnemyState.PATROL
        self._attack_timer = 0.0
        self._windup_timer = 0.0
        self.active_hitbox = None

        # Cached probe rect for edge detection (avoids per-frame allocation)
        self._probe = pygame.Rect(0, 0, _EDGE_PROBE_W, _EDGE_PROBE_H)

        # Status effects
        self.status_effects: list = []
        self.stunned:   bool  = False
        self.slow_factor: float = 1.0

        # Sprite — scaled once at init; None = fall back to colored rect
        sprite_name  = stats.get("sprite", "enemy_basic")
        self._sprite = _assets().get_sprite_scaled(sprite_name, w, h)

    # ------------------------------------------------------------------
    # Damage
    # ------------------------------------------------------------------

    def take_damage(self, amount):
        self.health    -= amount
        self.hit_flash  = HIT_FLASH_DURATION
        if self.health <= 0:
            self.alive = False

    # ------------------------------------------------------------------
    # Update — called by engine each frame with player and platforms
    # ------------------------------------------------------------------

    def update(self, dt, player, platforms):
        if not self.alive:
            return

        # Status effects — sets stunned / slow_factor
        tick_all(self, dt)

        # Tick timers
        if self.hit_flash     > 0: self.hit_flash     -= dt
        if self._attack_timer > 0: self._attack_timer -= dt

        # Gravity always applies — stunned enemies fall too (no floating mid-air)
        self.velocity.y += GRAVITY * dt
        if self.velocity.y > MAX_FALL_SPEED:
            self.velocity.y = MAX_FALL_SPEED

        if self.stunned:
            self.velocity.x = 0
            self._move(dt, platforms)
            return

        # Horizontal distance to player (signed: positive = player is to the right)
        dx   = player.rect.centerx - self.rect.centerx
        dist = abs(dx)

        # State machine
        if self.state == EnemyState.PATROL:
            self._do_patrol(platforms)
            if dist < self.aggro_range:
                self.state = EnemyState.CHASE

        elif self.state == EnemyState.CHASE:
            if dist > self.deaggro_range:
                self.state = EnemyState.PATROL
            elif dist <= self.attack_range:
                # Close enough — stop and face the player; swing when cooldown allows
                self.facing     = 1 if dx > 0 else -1
                self.velocity.x = 0
                if self._attack_timer <= 0:
                    self._begin_attack(dx)
            else:
                self._do_chase(dx)
                # Jump toward player if they're significantly above and we're grounded
                if self.on_ground and player.rect.centery < self.rect.centery - 40:
                    self.velocity.y = -JUMP_FORCE * 0.85

        elif self.state == EnemyState.ATTACK:
            self._do_attack_tick(dt)

        # Move and resolve collisions
        self._move(dt, platforms)

    # ------------------------------------------------------------------
    # State behaviours
    # ------------------------------------------------------------------

    def _do_patrol(self, platforms):
        # Leash: don't wander beyond patrol_radius from spawn X — keeps enemies
        # near their placed position on long or continuous ground.
        if self.rect.centerx > self._spawn_x + self.patrol_radius:
            self.facing = -1
        elif self.rect.centerx < self._spawn_x - self.patrol_radius:
            self.facing = 1
        else:
            # Edge probe: reuse cached rect to avoid per-frame allocation.
            probe_x = (self.rect.right if self.facing == 1
                       else self.rect.left - _EDGE_PROBE_W)
            self._probe.x = probe_x
            self._probe.y = self.rect.bottom
            if not any(self._probe.colliderect(p) for p in platforms):
                self.facing *= -1

        self.velocity.x = self.patrol_speed * self.facing * self.slow_factor

    def _do_chase(self, dx):
        self.facing     = 1 if dx > 0 else -1
        self.velocity.x = self.chase_speed * self.facing * self.slow_factor

    def _begin_attack(self, dx):
        self.facing        = 1 if dx > 0 else -1
        self.velocity.x    = 0
        self._windup_timer = _WINDUP_DURATION
        self.state         = EnemyState.ATTACK

    def _do_attack_tick(self, dt):
        self.velocity.x    = 0
        self._windup_timer -= dt
        # Spawn hitbox once wind-up finishes (and no hitbox already active)
        if self._windup_timer <= 0 and self.active_hitbox is None:
            self.active_hitbox = AttackHitbox(self, self.attack_damage)
            self._attack_timer = self.attack_cooldown
            self.state         = EnemyState.CHASE   # hitbox lives on; engine clears it

    # ------------------------------------------------------------------
    # Physics + collision resolution
    # ------------------------------------------------------------------

    def _move(self, dt, platforms):
        # X axis — move then resolve
        self.pos.x  += self.velocity.x * dt
        self.rect.x  = int(self.pos.x)
        self._resolve_x(platforms)

        # Y axis — move then resolve
        self.pos.y  += self.velocity.y * dt
        self.rect.y  = int(self.pos.y)
        self._resolve_y(platforms)

    def _resolve_x(self, platforms):
        for p in platforms:
            if self.rect.colliderect(p):
                if self.velocity.x > 0:
                    self.rect.right = p.left
                elif self.velocity.x < 0:
                    self.rect.left  = p.right
                self.velocity.x = 0
                self.pos.x      = self.rect.x
                # Wall hit during patrol — turn around (same as an edge)
                if self.state == EnemyState.PATROL:
                    self.facing *= -1

    def _resolve_y(self, platforms):
        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p):
                if self.velocity.y > 0:    # landing
                    self.rect.bottom = p.top
                    self.on_ground   = True
                elif self.velocity.y < 0:  # hitting ceiling
                    self.rect.top    = p.bottom
                self.velocity.y = 0
                self.pos.y      = self.rect.y

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, camera):
        r = camera.apply_tuple(self.rect)
        # Sprite used only in the normal state; colored rect handles hit-flash and windup
        if self._sprite and self.hit_flash <= 0 and self.state != EnemyState.ATTACK:
            screen.blit(self._sprite, (r[0], r[1]))
        else:
            if self.hit_flash > 0:
                color = ENEMY_HIT_COLOR
            elif self.state == EnemyState.ATTACK:
                color = ENEMY_WINDUP_COLOR
            else:
                color = ENEMY_COLOR
            pygame.draw.rect(screen, color, r)

        # Health bar — shown above enemy whenever health < max
        if self.health < self.max_health:
            bar_w = r[2]
            bar_h = 4
            bar_x = r[0]
            bar_y = r[1] - 8
            pygame.draw.rect(screen, (80, 20, 20), (bar_x, bar_y, bar_w, bar_h))
            fill_w = max(0, int(bar_w * self.health / self.max_health))
            if fill_w > 0:
                pygame.draw.rect(screen, (220, 50, 50), (bar_x, bar_y, fill_w, bar_h))
