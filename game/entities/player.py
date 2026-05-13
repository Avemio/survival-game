"""
entities/player.py
The player entity — position, movement, physics, mana, status effects, ability slots.
Owns: rect, velocity, gravity, variable jump, collision resolution, drawing.
Does NOT own: combat (systems/combat.py), crafting, animation (later).

Physics model:
  - Float position (self.pos) drives movement; rect snaps to it each frame.
  - X and Y are resolved separately to prevent diagonal corner-clipping.
  - Variable jump: hold SPACE to extend jump height, release early to jump lower.
"""

import pygame
from game.settings import (
    PLAYER_SPEED, PLAYER_WIDTH, PLAYER_HEIGHT, PLAYER_COLOR,
    GRAVITY, JUMP_FORCE, JUMP_HOLD_FORCE, MAX_JUMP_TIME, MAX_FALL_SPEED,
    ATTACK_COOLDOWN, ATTACK_DAMAGE, PLAYER_MAX_HEALTH, PLAYER_MAX_MANA, MANA_REGEN_RATE,
    HOTBAR_SLOTS, INVENTORY_SLOTS,
    ARROW_ANGLE_MAX, ARROW_ANGLE_SPEED,
    STATUS_COLORS,
    XP_BASE, XP_SCALE, MAX_LEVEL,
)

_COYOTE_TIME      = 0.10   # seconds of coyote grace after walking off a ledge
_JUMP_BUFFER_TIME = 0.10   # seconds a jump input is buffered before landing
from game.entities.entity   import Entity
from game.systems.combat    import AttackHitbox
from game.systems.inventory import Inventory
from game.systems.assets    import get as _assets
from game.systems.effects   import tick_all

# Module-level constant — avoids recreating this list every handle_input() call
_HOTBAR_KEYS = [
    pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
    pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8,
]


class Player(Entity):
    def __init__(self, x, y):
        self.rect      = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.pos       = pygame.math.Vector2(x, y)
        self.velocity  = pygame.math.Vector2(0, 0)

        # Jump state
        self.on_ground  = False
        self.jump_held  = False
        self.jump_time  = 0.0
        self._coyote_timer     = 0.0   # grace window after leaving a ledge
        self._jump_buffer      = 0.0   # pending jump input waiting for ground
        self._landing_velocity = 0.0   # fall speed at moment of landing (for shake)

        # Health
        self.max_health = PLAYER_MAX_HEALTH
        self.health     = PLAYER_MAX_HEALTH

        # Mana
        self.max_mana = PLAYER_MAX_MANA
        self.mana     = float(PLAYER_MAX_MANA)

        # Skill-upgradeable stats — base values; increased via skill points
        self.attack_damage = float(ATTACK_DAMAGE)
        self.speed         = float(PLAYER_SPEED)
        self.mana_regen    = MANA_REGEN_RATE
        self.skill_points  = 0

        # XP / Level
        self.level          = 1
        self.xp             = 0
        self.xp_to_next     = XP_BASE
        self._leveled_up_timer = 0.0   # > 0 = show "LEVEL UP!" flash

        # Combat state
        self.facing          = 1
        self.attack_cooldown = 0.0
        self.active_hitbox   = None
        self.hit_flash       = 0.0   # countdown; >0 = flash white

        # Status effects
        self.status_effects: list = []
        self.stunned:   bool  = False
        self.slow_factor: float = 1.0

        # Ability slots — Q and R keys; store ability_id strings or None
        self.ability_slots: list[str | None] = [None, None]
        self.ability_cooldowns: list[float]  = [0.0, 0.0]

        # Inventory (full 32-slot; hotbar shows first HOTBAR_SLOTS)
        self.inventory    = Inventory(size=INVENTORY_SLOTS)
        self._hotbar_slot = 0

        # Bow aiming
        self.aiming    = False
        self.aim_angle = 0.0

        # Sprites — base (facing right) and flipped (facing left), scaled once at init
        _base = _assets().get_sprite_scaled("player", PLAYER_WIDTH, PLAYER_HEIGHT)
        self._sprite       = _base
        self._sprite_flip  = pygame.transform.flip(_base, True, False) if _base else None

    @property
    def hotbar_slot(self):
        return self._hotbar_slot

    @hotbar_slot.setter
    def hotbar_slot(self, value):
        self._hotbar_slot = max(0, min(HOTBAR_SLOTS - 1, value))

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_input(self, dt):
        if self.stunned:
            self.velocity.x = 0
            return   # stun blocks all input

        keys = pygame.key.get_pressed()

        # Horizontal movement (respect slow_factor)
        self.velocity.x = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.velocity.x = -self.speed * self.slow_factor
            self.facing     = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.velocity.x =  self.speed * self.slow_factor
            self.facing     =  1

        # Hotbar slot selection
        for i, key in enumerate(_HOTBAR_KEYS):
            if keys[key]:
                self.hotbar_slot = i
                break

        # Basic attack — Z
        if (keys[pygame.K_z]
                and self.attack_cooldown <= 0
                and self.active_hitbox is None
                and not self.aiming):
            self.attack_cooldown = ATTACK_COOLDOWN
            self.active_hitbox   = AttackHitbox(self, damage=self.attack_damage)

        # Bow aim
        if self.aiming:
            if keys[pygame.K_UP]:
                self.aim_angle = min(ARROW_ANGLE_MAX,  self.aim_angle + ARROW_ANGLE_SPEED * dt)
            if keys[pygame.K_DOWN]:
                self.aim_angle = max(-ARROW_ANGLE_MAX, self.aim_angle - ARROW_ANGLE_SPEED * dt)

        # Jump (coyote time: also allow jump within grace window after leaving a ledge)
        jump_key = keys[pygame.K_SPACE] or keys[pygame.K_w] or (
            keys[pygame.K_UP] and not self.aiming
        )
        can_jump = (self.on_ground or self._coyote_timer > 0) and not self.jump_held
        if jump_key:
            if can_jump:
                self.velocity.y    = -JUMP_FORCE
                self.on_ground     = False
                self.jump_held     = True
                self.jump_time     = 0.0
                self._coyote_timer = 0.0   # consume coyote window
            elif self.jump_held and self.jump_time < MAX_JUMP_TIME and self.velocity.y < 0:
                self.velocity.y -= JUMP_HOLD_FORCE * dt
                self.jump_time  += dt
            elif not self.on_ground and not self.jump_held:
                self._jump_buffer = _JUMP_BUFFER_TIME   # buffer for the next landing
        else:
            self.jump_held = False

    # ------------------------------------------------------------------
    # Physics
    # ------------------------------------------------------------------

    def apply_gravity(self, dt):
        self.velocity.y += GRAVITY * dt
        if self.velocity.y > MAX_FALL_SPEED:
            self.velocity.y = MAX_FALL_SPEED

    def resolve_x(self, platforms):
        for p in platforms:
            if self.rect.colliderect(p):
                if self.velocity.x > 0:
                    self.rect.right = p.left
                elif self.velocity.x < 0:
                    self.rect.left  = p.right
                self.velocity.x = 0
                self.pos.x = self.rect.x

    def resolve_y(self, platforms):
        self.on_ground         = False
        self._landing_velocity = 0.0
        for p in platforms:
            if self.rect.colliderect(p):
                if self.velocity.y > 0:
                    self._landing_velocity = self.velocity.y  # capture before zeroing
                    self.rect.bottom = p.top
                    self.on_ground   = True
                    self.jump_held   = False
                    # Jump buffer: trigger jump immediately on landing if input was queued.
                    # Break out of the platform loop so a low ceiling can't cancel it.
                    if self._jump_buffer > 0:
                        self._jump_buffer = 0.0
                        self.velocity.y   = -JUMP_FORCE
                        self.on_ground    = False
                        self.jump_held    = True
                        self.jump_time    = 0.0
                        self.pos.y        = self.rect.y
                        break
                    else:
                        self.velocity.y = 0
                elif self.velocity.y < 0:
                    self.rect.top   = p.bottom
                    self.velocity.y = 0
                self.pos.y = self.rect.y

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt, platforms):
        # Tick status effects first (sets stunned / slow_factor)
        tick_all(self, dt)

        # Tick cooldowns
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        for i, cd in enumerate(self.ability_cooldowns):
            if cd > 0:
                self.ability_cooldowns[i] -= dt

        # Mana regen
        if self.mana < self.max_mana:
            self.mana = min(self.max_mana, self.mana + self.mana_regen * dt)

        # Tick flash / input timers
        if self.hit_flash          > 0: self.hit_flash          -= dt
        if self._coyote_timer      > 0: self._coyote_timer      -= dt
        if self._jump_buffer       > 0: self._jump_buffer       -= dt
        if self._leveled_up_timer  > 0: self._leveled_up_timer  -= dt

        was_on_ground = self.on_ground

        self.handle_input(dt)
        self.apply_gravity(dt)

        self.pos.x  += self.velocity.x * dt
        self.rect.x  = int(self.pos.x)
        self.resolve_x(platforms)

        self.pos.y  += self.velocity.y * dt
        self.rect.y  = int(self.pos.y)
        self.resolve_y(platforms)

        # Start coyote timer when walking off a ledge (not from a jump)
        if was_on_ground and not self.on_ground and self.velocity.y > 0:
            self._coyote_timer = _COYOTE_TIME

    # ------------------------------------------------------------------
    # Combat helpers
    # ------------------------------------------------------------------

    def take_damage(self, amount):
        self.health    = max(0, self.health - amount)
        self.hit_flash = 0.12   # flash white on taking any damage

    def award_xp(self, amount: int):
        """Add XP and trigger level-up(s) if threshold crossed."""
        if self.level >= MAX_LEVEL:
            return
        self.xp += amount
        while self.xp >= self.xp_to_next and self.level < MAX_LEVEL:
            self.xp           -= self.xp_to_next
            self.level        += 1
            self.skill_points += 1
            self.xp_to_next    = int(XP_BASE * (XP_SCALE ** (self.level - 1)))
            self._leveled_up_timer = 2.5

    def reset_to(self, x, y):
        """Teleport player to (x, y) and zero out all motion state."""
        self.rect.topleft      = (int(x), int(y))
        self.pos.x             = float(x)
        self.pos.y             = float(y)
        self.velocity.x        = 0.0
        self.velocity.y        = 0.0
        self.active_hitbox     = None
        self.aiming            = False
        self._coyote_timer     = 0.0
        self._jump_buffer      = 0.0
        self._landing_velocity = 0.0

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, camera):
        r = camera.apply_tuple(self.rect)
        if self._sprite and self.hit_flash <= 0:
            spr = self._sprite_flip if self.facing == -1 else self._sprite
            screen.blit(spr, (r[0], r[1]))
        else:
            if self.hit_flash > 0:
                color = (255, 255, 255)   # white flash on damage
            elif self.status_effects:
                color = STATUS_COLORS.get(self.status_effects[0].type, PLAYER_COLOR)
            else:
                color = PLAYER_COLOR
            pygame.draw.rect(screen, color, r)
