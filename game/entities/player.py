"""
entities/player.py
The player entity — position, movement, and input handling.
Owns: the player rect, speed, input reading, drawing itself via camera.
Does NOT own: physics (M2), combat (M4), inventory (M8).
"""

import pygame
from game.settings import PLAYER_SPEED, PLAYER_WIDTH, PLAYER_HEIGHT, PLAYER_COLOR


class Player:
    def __init__(self, x, y):
        # rect is the player's hitbox and position in world coordinates
        self.rect  = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.speed = PLAYER_SPEED

    def handle_input(self):
        """Read keyboard state and move the rect. WASD or arrow keys."""
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed
        if keys[pygame.K_UP]    or keys[pygame.K_w]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]:
            self.rect.y += self.speed

    def update(self):
        self.handle_input()

    def draw(self, screen, camera):
        """Draw player rect at its screen position (world pos converted by camera)."""
        screen_rect = camera.apply(self.rect)
        pygame.draw.rect(screen, PLAYER_COLOR, screen_rect)
