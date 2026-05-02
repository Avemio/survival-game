"""
entities/projectile.py
A projectile (arrow) in flight — physics, collision, damage.
Owns: position, velocity, gravity, wind response, platform/enemy collision.
Does NOT own: firing logic (engine), wind value (engine passes it in), inventory.
"""

import math
import pygame
from game.settings import ARROW_GRAVITY, ARROW_WIDTH, ARROW_HEIGHT, ARROW_COLOR


class Projectile:
    def __init__(self, x, y, vx, vy, damage):
        self.pos      = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(vx, vy)
        self.rect     = pygame.Rect(x, y, ARROW_WIDTH, ARROW_HEIGHT)
        self.damage   = damage
        self.alive    = True
        self.already_hit = set()

    def update(self, dt, platforms, wind):
        # Wind pushes horizontally; gravity pulls down
        self.velocity.y += ARROW_GRAVITY * dt
        self.velocity.x += wind * dt

        self.pos.x += self.velocity.x * dt
        self.pos.y += self.velocity.y * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        for p in platforms:
            if self.rect.colliderect(p):
                self.alive = False
                return

    def draw(self, screen, camera):
        # Orient the arrow rect along the direction of travel
        angle = math.degrees(math.atan2(-self.velocity.y, self.velocity.x))

        # Build a rotated line from tail to tip using the velocity direction
        length  = ARROW_WIDTH
        rad     = math.radians(angle)
        tip_x   = self.pos.x + math.cos(rad) * length * 0.5
        tip_y   = self.pos.y - math.sin(rad) * length * 0.5
        tail_x  = self.pos.x - math.cos(rad) * length * 0.5
        tail_y  = self.pos.y + math.sin(rad) * length * 0.5

        cx, cy = int(tip_x - camera.offset.x),  int(tip_y - camera.offset.y)
        tx, ty = int(tail_x - camera.offset.x), int(tail_y - camera.offset.y)
        pygame.draw.line(screen, ARROW_COLOR, (tx, ty), (cx, cy), ARROW_HEIGHT)
