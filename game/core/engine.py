"""
core/engine.py
The main game loop. Owns the screen, clock, and top-level update/draw calls.
Talks to World for all zone content — platforms, enemies, spawn point.
Does NOT own: game logic, combat, zone data.
"""

import sys
import random
import pygame

from game.settings        import (SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
                                   BG_COLOR, PLATFORM_COLOR, ATTACK_COLOR)
from game.core.camera        import Camera
from game.entities.player    import Player
from game.entities.item_drop import ItemDrop
from game.world.world        import World
from game.ui.hud             import HUD
from game.systems.saving     import save_game, load_game


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
        self.item_drops  = self.world.item_drops

        # Indices of zone drops the player has already collected (persists across loads)
        self.collected_zone_drops = set()

        self.player = Player(*self.world.spawn)

        # Apply saved player state if a save exists
        if save_data:
            px = save_data["player"]["x"]
            py = save_data["player"]["y"]
            self.player.rect.topleft = (px, py)
            self.player.pos.x        = px
            self.player.pos.y        = py
            self.player.health       = save_data["player"]["health"]

            inv_data = save_data["player"].get("inventory")
            if inv_data:
                self.player.inventory.load_slots(inv_data)

            collected = save_data.get("collected_zone_drops", [])
            self.collected_zone_drops = set(collected)

        # Remove zone drops the player has already collected
        self.item_drops[:] = [
            d for d in self.item_drops
            if d.zone_drop_index not in self.collected_zone_drops
        ]

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
        self._update_item_drops()
        self._update_save_points(dt)
        self.camera.update(self.player.rect)

    def _update_enemies(self, dt):
        for enemy in self.enemies:
            enemy.update(dt)
        # Spawn drops for enemies that died this frame, then cull them
        for enemy in self.enemies:
            if not enemy.alive:
                self._spawn_drops(enemy)
        self.enemies[:] = [e for e in self.enemies if e.alive]

    def _spawn_drops(self, enemy):
        """Roll loot table and create ItemDrop objects at the enemy's position."""
        item_defs = self.player.inventory.item_defs
        for drop in enemy.loot:
            if random.random() < drop.get("chance", 1.0):
                item_id  = drop["item_id"]
                quantity = drop.get("quantity", 1)
                color    = tuple(item_defs.get(item_id, {}).get("color", [200, 200, 200]))
                # Center the drop on the enemy, sitting at its feet
                x = enemy.rect.centerx - ItemDrop.SIZE // 2
                y = enemy.rect.bottom  - ItemDrop.SIZE
                self.item_drops.append(ItemDrop(x, y, item_id, quantity, color))

    def _update_item_drops(self):
        """Pick up any drops the player is standing on."""
        for drop in self.item_drops:
            if drop.rect.colliderect(self.player.rect):
                leftover = self.player.inventory.add(drop.item_id, drop.quantity)
                if leftover == 0:
                    drop.alive = False
                    # Track zone drops so they don't respawn on next load
                    if drop.zone_drop_index is not None:
                        self.collected_zone_drops.add(drop.zone_drop_index)
                else:
                    drop.quantity = leftover   # partial pickup if inventory was nearly full
        self.item_drops[:] = [d for d in self.item_drops if d.alive]

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
                save_game(self.player, self.world.zone_id, self.collected_zone_drops)
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

        # Draw item drops
        for drop in self.item_drops:
            drop.draw(self.screen, self.camera)

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
