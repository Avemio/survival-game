"""
entities/player.py
The player entity — position, movement, physics, and input handling.
Owns: rect, velocity, gravity, variable jump, collision resolution, drawing.
Does NOT own: combat (M4), inventory (M8), animation (later).

Physics model:
  - Float position (self.pos) drives movement; rect snaps to it each frame.
  - X and Y are resolved separately to prevent diagonal corner-clipping.
  - Variable jump: hold SPACE to extend jump height, release early to jump lower.
"""

import pygame
from game.settings import (
    PLAYER_SPEED, PLAYER_WIDTH, PLAYER_HEIGHT, PLAYER_COLOR,
    GRAVITY, JUMP_FORCE, JUMP_HOLD_FORCE, MAX_JUMP_TIME, MAX_FALL_SPEED,
    ATTACK_COOLDOWN, PLAYER_MAX_HEALTH, HOTBAR_SLOTS
)
from game.systems.combat import AttackHitbox


class Player:
    def __init__(self, x, y):
        self.rect      = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.pos       = pygame.math.Vector2(x, y)   # float position
        self.velocity  = pygame.math.Vector2(0, 0)   # pixels per second

        # Jump state
        self.on_ground  = False
        self.jump_held  = False   # True while space is held after a jump
        self.jump_time  = 0.0     # seconds the jump extension has been active

        # Health
        self.max_health = PLAYER_MAX_HEALTH
        self.health     = PLAYER_MAX_HEALTH

        # Combat state
        self.facing          = 1      # 1 = right, -1 = left
        self.attack_cooldown = 0.0    # counts down to 0; can attack when 0
        self.active_hitbox   = None   # set by attack(); cleared by engine

        # Hotbar — tracks selected slot; items added in M7
        self.hotbar_slot = 0          # index of the currently selected slot (0 to HOTBAR_SLOTS-1)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()

        # Horizontal — set velocity directly so releasing a key stops instantly
        self.velocity.x = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.velocity.x = -PLAYER_SPEED
            self.facing     = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.velocity.x =  PLAYER_SPEED
            self.facing     =  1

        # Attack — Z key, only when cooldown is done and no hitbox already active
        if keys[pygame.K_z] and self.attack_cooldown <= 0 and self.active_hitbox is None:
            self.attack_cooldown = ATTACK_COOLDOWN
            self.active_hitbox   = AttackHitbox(self)

        # Jump
        jump_key = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]

        if jump_key:
            if self.on_ground and not self.jump_held:
                # Initial jump impulse
                self.velocity.y = -JUMP_FORCE
                self.on_ground  = False
                self.jump_held  = True
                self.jump_time  = 0.0
            elif self.jump_held and self.jump_time < MAX_JUMP_TIME and self.velocity.y < 0:
                # Extend jump while: key held, within time limit, still rising
                self.velocity.y -= JUMP_HOLD_FORCE * dt
                self.jump_time  += dt
        else:
            # Key released — stop extending, gravity takes over naturally
            self.jump_held = False

    # ------------------------------------------------------------------
    # Physics
    # ------------------------------------------------------------------

    def apply_gravity(self, dt):
        self.velocity.y += GRAVITY * dt
        # Clamp to terminal velocity so the player doesn't accelerate forever
        if self.velocity.y > MAX_FALL_SPEED:
            self.velocity.y = MAX_FALL_SPEED

    # ------------------------------------------------------------------
    # Collision resolution (called by engine after moving)
    # ------------------------------------------------------------------

    def resolve_x(self, platforms):
        """Push player out of any platform on the X axis."""
        for p in platforms:
            if self.rect.colliderect(p):
                if self.velocity.x > 0:       # moving right — push left
                    self.rect.right = p.left
                elif self.velocity.x < 0:     # moving left — push right
                    self.rect.left  = p.right
                self.velocity.x = 0
                self.pos.x = self.rect.x

    def resolve_y(self, platforms):
        """Push player out of any platform on the Y axis. Sets on_ground."""
        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p):
                if self.velocity.y > 0:       # falling down — land on top
                    self.rect.bottom = p.top
                    self.on_ground   = True
                    self.jump_held   = False  # can't extend a jump after landing
                elif self.velocity.y < 0:     # moving up — hit ceiling
                    self.rect.top = p.bottom
                self.velocity.y = 0
                self.pos.y = self.rect.y

    # ------------------------------------------------------------------
    # Update (called by engine each frame)
    # ------------------------------------------------------------------

    def update(self, dt, platforms):
        # Tick cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        self.handle_input(dt)
        self.apply_gravity(dt)

        # Move X → resolve X collisions
        self.pos.x     += self.velocity.x * dt
        self.rect.x     = int(self.pos.x)
        self.resolve_x(platforms)

        # Move Y → resolve Y collisions
        self.pos.y     += self.velocity.y * dt
        self.rect.y     = int(self.pos.y)
        self.resolve_y(platforms)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, camera):
        pygame.draw.rect(screen, PLAYER_COLOR, camera.apply(self.rect))
