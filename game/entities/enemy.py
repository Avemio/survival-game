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
    GRAVITY, MAX_FALL_SPEED, JUMP_FORCE,
)
from game.entities.entity     import Entity
from game.systems.combat      import AttackHitbox
from game.entities.projectile import Projectile
from game.systems.assets      import get as _assets
from game.systems.effects     import tick_all


class EnemyState(Enum):
    PATROL = auto()
    CHASE  = auto()
    ATTACK = auto()


_WINDUP_DURATION = 0.4   # seconds of orange wind-up before hitbox spawns
_EDGE_PROBE_W    = 4     # width of the ground-ahead sensor rect
_EDGE_PROBE_H    = 8     # height — tall enough to catch slightly uneven platforms


class Enemy(Entity):
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
        self.alive      = True
        self.hit_flash  = 0.0   # countdown; >0 = flashing white
        self.loot       = stats.get("drops", [])
        self.xp_reward  = stats.get("xp_reward", 0)
        self._type_key  = stats.get("_type_key", "")
        self.facing     = 1     # 1 = right, -1 = left
        self.on_ground  = False

        # AI stats — read from data, fall back to settings defaults
        self.patrol_speed    = stats.get("speed",           ENEMY_SPEED)
        self.chase_speed     = stats.get("chase_speed",     ENEMY_CHASE_SPEED)
        self.aggro_range     = stats.get("aggro_range",     ENEMY_AGGRO_RANGE)
        self.deaggro_range   = stats.get("deaggro_range",   ENEMY_DEAGGRO_RANGE)
        self.attack_range    = stats.get("attack_range",    ENEMY_ATTACK_RANGE)
        self.attack_damage   = stats.get("attack_damage",   ENEMY_ATTACK_DAMAGE)
        self.attack_hitbox_w = stats.get("attack_hitbox_w", None)  # None = use ATTACK_WIDTH default
        self.attack_hitbox_h = stats.get("attack_hitbox_h", None)  # None = use ATTACK_HEIGHT default
        self.attack_cooldown = stats.get("attack_cooldown", ENEMY_ATTACK_COOLDOWN)
        self.patrol_radius   = stats.get("patrol_radius",   ENEMY_PATROL_RADIUS)
        self._spawn_x        = float(x)   # leash anchor — enemy won't patrol past ± patrol_radius

        self.state         = EnemyState.PATROL
        self._attack_timer = 0.0
        self._windup_timer = 0.0
        self.active_hitbox = None

        # Ranged AI: projectiles are appended to this list by _do_attack_tick
        # Engine must pass it in via update(); empty list = melee enemy
        self._ai_type        = stats.get("ai_type", "melee")  # "melee" or "ranged"
        self._proj_speed     = float(stats.get("proj_speed",    400))
        self._proj_damage    = int(stats.get("proj_damage",     15))
        self._proj_color     = tuple(stats.get("proj_color",    [255, 160, 40]))
        self._proj_gravity   = float(stats.get("proj_gravity",  0))   # 0 = flat shot
        self.pending_projectiles: list = []   # engine reads these each frame

        # Cached probe rect for edge detection (avoids per-frame allocation)
        self._probe = pygame.Rect(0, 0, _EDGE_PROBE_W, _EDGE_PROBE_H)

        # Status effects
        self.status_effects: list = []
        self.stunned:   bool  = False
        self.slow_factor: float = 1.0

        # Sprites — base (facing right) + flipped (facing left)
        sprite_name      = stats.get("sprite", "enemy_basic")
        _base            = _assets().get_sprite_scaled(sprite_name, w, h)
        self._sprite      = _base
        self._sprite_flip = pygame.transform.flip(_base, True, False) if _base else None

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

    def update(self, dt, player, platform_grid):
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
            self._move(dt, platform_grid)
            return

        # Horizontal distance to player (signed: positive = player is to the right)
        dx   = player.rect.centerx - self.rect.centerx
        dist = abs(dx)

        # State machine
        if self.state == EnemyState.PATROL:
            self._do_patrol(platform_grid)
            if dist < self.aggro_range:
                self.state = EnemyState.CHASE

        elif self.state == EnemyState.CHASE:
            if dist > self.deaggro_range:
                self.state = EnemyState.PATROL
            elif dist <= self.attack_range:
                self.facing     = 1 if dx > 0 else -1
                self.velocity.x = 0
                if self._attack_timer <= 0:
                    self._begin_attack(dx)
            else:
                if self._ai_type == "ranged":
                    # Ranged enemies stop at a comfortable shooting distance
                    preferred = self.attack_range * 0.6
                    if dist > preferred:
                        self._do_chase(dx)
                    else:
                        self.facing     = 1 if dx > 0 else -1
                        self.velocity.x = 0
                        if self._attack_timer <= 0:
                            self._begin_attack(dx)
                else:
                    self._do_chase(dx)
                    # Melee enemies jump toward elevated player
                    if self.on_ground and player.rect.centery < self.rect.centery - 40:
                        self.velocity.y = -JUMP_FORCE * 0.85

        elif self.state == EnemyState.ATTACK:
            self._do_attack_tick(dt)

        # Move and resolve collisions
        self._move(dt, platform_grid)

    # ------------------------------------------------------------------
    # State behaviours
    # ------------------------------------------------------------------

    def _do_patrol(self, platform_grid):
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
            candidates = platform_grid.query_rect(self._probe)
            if not any(self._probe.colliderect(p) for p in candidates):
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
        if self._windup_timer <= 0 and self.active_hitbox is None:
            if self._ai_type == "ranged":
                # Fire a projectile toward the player (facing is already set)
                vx = self._proj_speed * self.facing
                proj = Projectile(
                    self.rect.centerx - 7, self.rect.centery - 2,
                    vx, 0,
                    damage        = self._proj_damage,
                    gravity_factor= self._proj_gravity / 550.0 if self._proj_gravity else 0.0,
                    wind_affected = False,
                    width         = 14,
                    height        = 4,
                    pierce        = False,
                    color         = self._proj_color,
                    owner         = "enemy",
                )
                self.pending_projectiles.append(proj)
            else:
                self.active_hitbox = AttackHitbox(
                    self, self.attack_damage,
                    width=self.attack_hitbox_w,
                    height=self.attack_hitbox_h,
                )
            self._attack_timer = self.attack_cooldown
            self.state         = EnemyState.CHASE

    # ------------------------------------------------------------------
    # Physics + collision resolution
    # ------------------------------------------------------------------

    def _move(self, dt, platform_grid):
        # X axis — move then resolve
        self.pos.x  += self.velocity.x * dt
        self.rect.x  = int(self.pos.x)
        self._resolve_x(platform_grid)

        # Y axis — move then resolve
        self.pos.y  += self.velocity.y * dt
        self.rect.y  = int(self.pos.y)
        self._resolve_y(platform_grid)

    def _resolve_x(self, platform_grid):
        for p in platform_grid.query_rect(self.rect):
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

    def _resolve_y(self, platform_grid):
        self.on_ground = False
        for p in platform_grid.query_rect(self.rect):
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
            spr = self._sprite_flip if self.facing == -1 else self._sprite
            screen.blit(spr, (r[0], r[1]))
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
