"""
core/engine.py
The main game loop. Owns the screen, clock, and top-level update/draw calls.
Knows about the current scene's objects (player, camera, platforms) — this will
be handed off to scene_manager.py in a later milestone when scenes exist.
Does NOT own: game logic, combat, world data.
"""

import sys
import pygame

from game.settings        import (SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
                                   BG_COLOR, PLATFORM_COLOR)
from game.core.camera     import Camera
from game.entities.player import Player


# Temporary platforms for M2 testing.
# Replaced by real zone data when world loading is implemented (M5).
# Ground spans the full world width so the player always has somewhere to land.
PLATFORMS = [
    pygame.Rect(0,    660, 10000, 60),   # ground — full world width
    pygame.Rect(300,  540, 200,   20),   # floating platform
    pygame.Rect(600,  460, 180,   20),   # higher platform
    pygame.Rect(900,  380, 160,   20),   # even higher
    pygame.Rect(1200, 460, 200,   20),   # back down
    pygame.Rect(1500, 540, 250,   20),   # near ground again
]


class Engine:
    def __init__(self):
        pygame.init()
        self.screen  = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        # Spawn player above the ground platform
        self.player = Player(x=200, y=580)
        self.camera = Camera()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self, dt):
        self.player.update(dt, PLATFORMS)
        self.camera.update(self.player.rect)

    def draw(self):
        self.screen.fill(BG_COLOR)

        # Draw platforms
        for p in PLATFORMS:
            pygame.draw.rect(self.screen, PLATFORM_COLOR, self.camera.apply(p))

        # Draw player on top
        self.player.draw(self.screen, self.camera)

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # seconds since last frame

            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()
