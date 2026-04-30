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
from game.ui.menus           import CraftingMenu
from game.ui.dialogue        import DialogueBox
from game.systems.saving     import save_game, load_game
from game.systems.crafting   import CraftingSystem


class Engine:
    def __init__(self):
        pygame.init()
        self.screen  = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        # Load save data first so we know which zone to load
        save_data = load_game()
        zone_id   = save_data.get("zone", "zone_01") if save_data else "zone_01"

        self.world       = World(zone_id)
        self.platforms   = self.world.platforms
        self.enemies     = self.world.enemies
        self.save_points = self.world.save_points
        self.item_drops  = self.world.item_drops
        self.npcs        = self.world.npcs
        self.exits       = self.world.exits

        # Per-zone drop log: {zone_id: set of int indices already collected}
        self.collected_zone_drops = {}

        self.player = Player(*self.world.spawn)

        # Apply saved player state if a save exists
        if save_data:
            player_data = save_data.get("player", {})
            px = player_data.get("x", self.world.spawn[0])
            py = player_data.get("y", self.world.spawn[1])
            self.player.rect.topleft = (px, py)
            self.player.pos.x        = px
            self.player.pos.y        = py
            self.player.health       = player_data.get("health", self.player.max_health)

            inv_data = player_data.get("inventory")
            if inv_data:
                self.player.inventory.load_slots(inv_data)

            raw = save_data.get("collected_zone_drops", {})
            if isinstance(raw, list):
                # Migrate old flat-list format (assumed to be zone_01 drops)
                self.collected_zone_drops = {zone_id: set(raw)}
            else:
                self.collected_zone_drops = {k: set(v) for k, v in raw.items()}

        # Remove zone drops the player has already collected in this zone
        already = self.collected_zone_drops.get(zone_id, set())
        self.item_drops[:] = [
            d for d in self.item_drops
            if d.zone_drop_index not in already
        ]

        self.camera        = Camera()
        self.hud           = HUD(self.player)
        self.crafting      = CraftingSystem()
        self.crafting_menu = CraftingMenu(self.player, self.crafting)
        self.dialogue_box  = DialogueBox()

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
                    if self.crafting_menu.open:
                        self.crafting_menu.close()
                    else:
                        self.running = False

                elif event.key == pygame.K_c:
                    if not self.dialogue_box.open:
                        self.crafting_menu.toggle()

                elif event.key == pygame.K_e:
                    if self.dialogue_box.open:
                        self.dialogue_box.advance()
                    elif not self.crafting_menu.open:
                        # Start dialogue if the player is within interact range of an NPC
                        for npc in self.npcs:
                            if npc.interact_rect.colliderect(self.player.rect):
                                self.dialogue_box.start(npc.name, npc.dialogue_lines)
                                break

                # Forward navigation keys to the crafting menu while it's open
                if self.crafting_menu.open:
                    self.crafting_menu.handle_event(event)

    def update(self, dt):
        self.crafting_menu.update(dt)

        # Pause all world simulation while any overlay is open
        if self.crafting_menu.open or self.dialogue_box.open:
            return

        self.player.update(dt, self.platforms)
        self._update_enemies(dt)
        self._update_combat(dt)
        self._update_item_drops()
        self._update_save_points(dt)
        self._update_zone_exits()
        self.camera.update(self.player.rect)

    def _update_enemies(self, dt):
        living = []
        for enemy in self.enemies:
            enemy.update(dt)
            if enemy.alive:
                living.append(enemy)
            else:
                self._spawn_drops(enemy)
        self.enemies[:] = living

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
                        self.collected_zone_drops.setdefault(
                            self.world.zone_id, set()
                        ).add(drop.zone_drop_index)
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

    def _update_zone_exits(self):
        for exit_ in self.exits:
            if exit_.rect.colliderect(self.player.rect):
                self._transition_zone(exit_.target_zone)
                return   # stop — lists just changed

    def _transition_zone(self, target_zone_id):
        """Save, swap zones, re-point all engine list references, teleport player."""
        # Auto-save before leaving
        save_game(self.player, self.world.zone_id, self.collected_zone_drops)

        # Load the new zone
        self.world.transition_to(target_zone_id)

        # Re-point all engine references — world's lists are brand new after transition
        self.platforms   = self.world.platforms
        self.enemies     = self.world.enemies
        self.save_points = self.world.save_points
        self.npcs        = self.world.npcs
        self.exits       = self.world.exits
        self.item_drops  = self.world.item_drops

        # Filter out zone drops already collected in the target zone
        already = self.collected_zone_drops.get(target_zone_id, set())
        self.item_drops[:] = [
            d for d in self.item_drops
            if d.zone_drop_index not in already
        ]

        # Teleport player to the new zone's spawn point
        sx, sy = self.world.spawn
        self.player.rect.topleft = (sx, sy)
        self.player.pos.x        = sx
        self.player.pos.y        = sy
        self.player.velocity.x   = 0
        self.player.velocity.y   = 0
        self.player.active_hitbox = None   # cancel any in-flight swing

        # Pre-warm save point overlap so touching the spawn save point doesn't flash
        for sp in self.save_points:
            sp.was_overlapping = sp.rect.colliderect(self.player.rect)

    def draw(self):
        self.screen.fill(BG_COLOR)

        # Draw platforms
        for p in self.platforms:
            pygame.draw.rect(self.screen, PLATFORM_COLOR, self.camera.apply_tuple(p))

        # Draw zone exits
        for exit_ in self.exits:
            exit_.draw(self.screen, self.camera)

        # Draw save points
        for sp in self.save_points:
            sp.draw(self.screen, self.camera)

        # Draw item drops
        for drop in self.item_drops:
            drop.draw(self.screen, self.camera)

        # Draw NPCs
        for npc in self.npcs:
            npc.draw(self.screen, self.camera, self.player.rect)

        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(self.screen, self.camera)

        # Draw player on top
        self.player.draw(self.screen, self.camera)

        # Draw attack hitbox outline (debug — remove when sprites exist)
        hitbox = self.player.active_hitbox
        if hitbox:
            pygame.draw.rect(self.screen, ATTACK_COLOR,
                             self.camera.apply_tuple(hitbox.rect), 2)

        # HUD — drawn last, in screen space (no camera offset)
        self.hud.draw(self.screen)

        # Crafting menu — drawn over HUD when open
        self.crafting_menu.draw(self.screen)

        # Dialogue box — drawn over everything when open
        self.dialogue_box.draw(self.screen)

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # seconds since last frame

            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()
