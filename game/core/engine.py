"""
core/engine.py
The main game loop. Owns the screen, clock, and top-level update/draw calls.
Talks to World for all zone content — platforms, enemies, spawn point.
Does NOT own: game logic, combat, zone data.
"""

import sys
import pygame

from game.settings        import (SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
                                   BG_COLOR, PLATFORM_COLOR, ATTACK_COLOR)
from game.core.camera     import Camera
from game.entities.player import Player
from game.world.world     import World
from game.ui.hud          import HUD


class Engine:
    def __init__(self):
        pygame.init()
        self.screen  = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        # Load the first zone through World
        self.world   = World("zone_01")

        # Direct references to the zone's lists — kept in sync via in-place mutation
        self.platforms = self.world.platforms
        self.enemies   = self.world.enemies

        self.player  = Player(*self.world.spawn)
        self.camera  = Camera()
        self.hud     = HUD(self.player)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self, dt):
        self.player.update(dt, self.platforms)

        # Update enemies
        for enemy in self.enemies:
            enemy.update(dt)

        # Combat resolution — hitbox vs every enemy
        hitbox = self.player.active_hitbox
        if hitbox:
            hitbox.update(dt)
            for enemy in self.enemies:
                if (enemy not in hitbox.already_hit
                        and hitbox.rect.colliderect(enemy.rect)):
                    enemy.take_damage(hitbox.damage)
                    hitbox.already_hit.add(enemy)
            # Clear hitbox once it expires
            if hitbox.expired:
                self.player.active_hitbox = None

        # Remove dead enemies — in-place so self.world.enemies stays in sync
        self.enemies[:] = [e for e in self.enemies if e.alive]

        self.camera.update(self.player.rect)

    def draw(self):
        self.screen.fill(BG_COLOR)

        # Draw platforms
        for p in self.platforms:
            pygame.draw.rect(self.screen, PLATFORM_COLOR, self.camera.apply(p))

        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(self.screen, self.camera)

        # Draw player on top
        self.player.draw(self.screen, self.camera)

        # Draw attack hitbox outline (debug — remove when sprites exist)
        hitbox = self.player.active_hitbox
        if hitbox:
            pygame.draw.rect(self.screen, ATTACK_COLOR,
                             self.camera.apply(hitbox.rect), 2)

        # HUD — drawn last, in screen space (no camera offset)
        self.hud.draw(self.screen)

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # seconds since last frame

            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()
