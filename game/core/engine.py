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
from game.core.camera       import Camera
from game.entities.player   import Player
from game.world.world       import World
from game.ui.hud            import HUD
from game.systems.saving    import save_game, load_game


class Engine:
    def __init__(self):
        pygame.init()
        self.screen  = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        # Load save data first so we know which zone to load
        save_data = load_game()
        zone_id   = save_data["zone"] if save_data else "zone_01"

        self.world       = World(zone_id)
        self.platforms   = self.world.platforms
        self.enemies     = self.world.enemies
        self.save_points = self.world.save_points

        self.player = Player(*self.world.spawn)

        # Apply saved player state if a save exists
        if save_data:
            px = save_data["player"]["x"]
            py = save_data["player"]["y"]
            self.player.rect.topleft = (px, py)
            self.player.pos.x        = px
            self.player.pos.y        = py
            self.player.health       = save_data["player"]["health"]

        self.camera = Camera()
        self.hud    = HUD(self.player)

        # Pre-warm save point overlap state — prevents a flash trigger if the
        # player spawns directly on top of a save point (e.g. after loading a save)
        for sp in self.save_points:
            sp.was_overlapping = sp.rect.colliderect(self.player.rect)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self, dt):
        self.player.update(dt, self.platforms)
        self._update_enemies(dt)
        self._update_combat(dt)
        self._update_save_points(dt)
        self.camera.update(self.player.rect)

    def _update_enemies(self, dt):
        for enemy in self.enemies:
            enemy.update(dt)
        self.enemies[:] = [e for e in self.enemies if e.alive]

    def _update_combat(self, dt):
        hitbox = self.player.active_hitbox
        if not hitbox:
            return
        hitbox.update(dt)
        for enemy in self.enemies:
            if (enemy not in hitbox.already_hit
                    and hitbox.rect.colliderect(enemy.rect)):
                enemy.take_damage(hitbox.damage)
                hitbox.already_hit.add(enemy)
        if hitbox.expired:
            self.player.active_hitbox = None

    def _update_save_points(self, dt):
        for sp in self.save_points:
            sp.update(dt)
            overlapping = sp.rect.colliderect(self.player.rect)
            if overlapping and not sp.was_overlapping:
                self.player.health = self.player.max_health
                save_game(self.player, self.world.zone_id)
                sp.flash_timer = sp.FLASH_DURATION
            sp.was_overlapping = overlapping

    def draw(self):
        self.screen.fill(BG_COLOR)

        # Draw platforms
        for p in self.platforms:
            pygame.draw.rect(self.screen, PLATFORM_COLOR, self.camera.apply(p))

        # Draw save points
        for sp in self.save_points:
            sp.draw(self.screen, self.camera)

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
