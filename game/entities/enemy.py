"""
entities/enemy.py
A basic static enemy — no AI yet, just takes damage and flashes on hit.
Owns: rect, health, hit-flash timer, alive flag, drawing.
Does NOT own: AI/movement (later milestone), combat resolution (engine/systems).
"""

import pygame
from game.settings import (
    ENEMY_WIDTH, ENEMY_HEIGHT, ENEMY_HEALTH,
    ENEMY_COLOR, ENEMY_HIT_COLOR, HIT_FLASH_DURATION
)


class Enemy:
    def __init__(self, x, y):
        self.rect        = pygame.Rect(x, y, ENEMY_WIDTH, ENEMY_HEIGHT)
        self.health      = ENEMY_HEALTH
        self.alive       = True
        self.hit_flash   = 0.0     # countdown in seconds; >0 means flashing white

    # ------------------------------------------------------------------
    # Damage
    # ------------------------------------------------------------------

    def take_damage(self, amount):
        self.health    -= amount
        self.hit_flash  = HIT_FLASH_DURATION
        if self.health <= 0:
            self.alive = False

    # ------------------------------------------------------------------
    # Update (called by engine each frame)
    # ------------------------------------------------------------------

    def update(self, dt):
        if self.hit_flash > 0:
            self.hit_flash -= dt

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, camera):
        color = ENEMY_HIT_COLOR if self.hit_flash > 0 else ENEMY_COLOR
        pygame.draw.rect(screen, color, camera.apply(self.rect))
