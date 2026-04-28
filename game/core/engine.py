"""
core/engine.py
The main game loop. Owns the screen, clock, and top-level update/draw calls.
Knows about the current scene's objects (player, camera) — this will be
handed off to scene_manager.py in a later milestone when scenes exist.
Does NOT own: game logic, combat, world data.
"""

import sys
import pygame

from game.settings      import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, BG_COLOR, MARKER_COLOR
from game.core.camera   import Camera
from game.entities.player import Player


# Temporary world markers so we can see the camera actually scrolling.
# These are plain rects placed at fixed world positions.
# They will be replaced by real zone content in the world milestone.
MARKERS = [
    pygame.Rect(300,  300, 60, 60),
    pygame.Rect(700,  250, 40, 80),
    pygame.Rect(1200, 310, 80, 40),
    pygame.Rect(1800, 280, 50, 50),
    pygame.Rect(2500, 290, 70, 70),
    pygame.Rect(3200, 270, 60, 90),
]


class Engine:
    def __init__(self):
        pygame.init()
        self.screen  = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        # Spawn player near the left side, vertically centered
        self.player = Player(x=200, y=SCREEN_HEIGHT // 2 - 32)
        self.camera = Camera()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self):
        self.player.update()
        self.camera.update(self.player.rect)

    def draw(self):
        self.screen.fill(BG_COLOR)

        # Draw world markers so the scrolling is visible
        for marker in MARKERS:
            pygame.draw.rect(self.screen, MARKER_COLOR, self.camera.apply(marker))

        # Draw player on top
        self.player.draw(self.screen, self.camera)

        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()
