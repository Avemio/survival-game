"""
core/engine.py
The main game loop. Owns the screen, clock, and top-level update/draw calls.
Talks to World for all zone content — platforms, enemies, spawn point.
Does NOT own: game logic, combat, zone data.
"""

import sys
import math
import random
import pygame

from game.settings        import (SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
                                   BG_COLOR, PLATFORM_COLOR, ATTACK_COLOR, ENEMY_ATTACK_COLOR,
                                   DEATH_OVERLAY_DURATION, DEATH_TEXT_COLOR,
                                   ARROW_SPEED, ARROW_DAMAGE, ARROW_WIDTH, ARROW_HEIGHT,
                                   WIND_MAX, WIND_CHANGE_RATE, WIND_TARGET_MIN, WIND_TARGET_MAX,
                                   AIM_PREVIEW_STEPS, AIM_PREVIEW_STEP_T, AIM_DOT_COLOR,
                                   ARROW_GRAVITY)
from game.core.camera        import Camera
from game.entities.player    import Player
from game.entities.item_drop import ItemDrop
from game.world.world        import World
from game.ui.hud             import HUD
from game.ui.menus           import CraftingMenu
from game.ui.dialogue        import DialogueBox
from game.ui.pause_menu      import PauseMenu
from game.systems.saving     import save_game, load_game
from game.systems.crafting   import CraftingSystem
from game.entities.projectile import Projectile


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
        self.pause_menu    = PauseMenu()

        # Pre-warm save point overlap state — prevents a flash trigger if the
        # player spawns directly on top of a save point (e.g. after loading a save)
        for sp in self.save_points:
            sp.was_overlapping = sp.rect.colliderect(self.player.rect)

        # Death overlay — all surfaces built once at init (never inside draw)
        self.death_timer    = 0.0
        self._death_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._death_overlay.fill((120, 0, 0, 180))
        self._death_font    = pygame.font.SysFont(None, 96)
        self._death_text    = self._death_font.render("YOU DIED", True, DEATH_TEXT_COLOR)

        # Projectiles
        self.projectiles = []

        # Wind — drifts slowly toward a random target strength
        self.wind          = 0.0
        self._wind_target  = 0.0
        self._wind_timer   = random.uniform(WIND_TARGET_MIN, WIND_TARGET_MAX)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_x and self.player.aiming:
                    self._fire_arrow()
                    self.player.aiming    = False
                    self.player.aim_angle = 0.0

            if event.type == pygame.KEYDOWN:
                # Block all key input during the death overlay countdown
                if self.death_timer > 0:
                    continue

                # Pause menu intercepts all keys while open
                if self.pause_menu.open:
                    self.pause_menu.handle_event(event)
                    continue

                if event.key == pygame.K_ESCAPE:
                    if self.crafting_menu.open:
                        self.crafting_menu.close()
                    elif self.dialogue_box.open:
                        pass   # E closes dialogue; Esc intentionally does nothing here
                    else:
                        self.pause_menu.toggle()

                elif event.key == pygame.K_c:
                    if not self.dialogue_box.open:
                        self.crafting_menu.toggle()

                elif event.key == pygame.K_e:
                    if self.dialogue_box.open:
                        self.dialogue_box.advance()
                    elif not self.crafting_menu.open:
                        for npc in self.npcs:
                            if npc.interact_rect.colliderect(self.player.rect):
                                self.dialogue_box.start(npc.name, npc.dialogue_lines)
                                break

                elif event.key == pygame.K_f:
                    if not self.crafting_menu.open and not self.dialogue_box.open:
                        self._use_hotbar_item()

                elif event.key == pygame.K_x:
                    if not self.crafting_menu.open and not self.dialogue_box.open:
                        self._start_aim()

                # Forward navigation keys to the crafting menu while it's open
                if self.crafting_menu.open:
                    self.crafting_menu.handle_event(event)

    def update(self, dt):
        self.crafting_menu.update(dt)

        # Death countdown — world paused; respawn fires when timer expires
        if self.death_timer > 0:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self._respawn()
            return

        # Pause all world simulation while any overlay is open
        if self.pause_menu.open or self.crafting_menu.open or self.dialogue_box.open:
            return

        self._update_wind(dt)
        self.player.update(dt, self.platforms)
        self._update_enemies(dt)
        self._update_combat(dt)
        self._update_enemy_attacks(dt)
        self._update_projectiles(dt)
        self._update_item_drops()
        self._update_save_points(dt)
        self._update_zone_exits()
        self.camera.update(self.player.rect)

        if self.player.health <= 0:
            self.death_timer = DEATH_OVERLAY_DURATION

    def _update_enemies(self, dt):
        living = []
        for enemy in self.enemies:
            enemy.update(dt, self.player, self.platforms)
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

    def _update_enemy_attacks(self, dt):
        for enemy in self.enemies:
            hitbox = enemy.active_hitbox
            if not hitbox:
                continue
            hitbox.update(dt)
            if (self.player not in hitbox.already_hit
                    and hitbox.rect.colliderect(self.player.rect)):
                self.player.take_damage(hitbox.damage)
                hitbox.already_hit.add(self.player)
            if hitbox.expired:
                enemy.active_hitbox = None

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
        self.player.rect.topleft  = (sx, sy)
        self.player.pos.x         = sx
        self.player.pos.y         = sy
        self.player.velocity.x    = 0
        self.player.velocity.y    = 0
        self.player.active_hitbox = None   # cancel any in-flight swing
        self.player.aiming        = False
        self.projectiles.clear()

        # Pre-warm save point overlap so touching the spawn save point doesn't flash
        for sp in self.save_points:
            sp.was_overlapping = sp.rect.colliderect(self.player.rect)

    def _update_wind(self, dt):
        self._wind_timer -= dt
        if self._wind_timer <= 0:
            self._wind_target = random.uniform(-WIND_MAX, WIND_MAX)
            self._wind_timer  = random.uniform(WIND_TARGET_MIN, WIND_TARGET_MAX)
        # Smooth lerp toward the target wind strength
        self.wind += (self._wind_target - self.wind) * WIND_CHANGE_RATE * dt

    def _update_projectiles(self, dt):
        for proj in self.projectiles:
            proj.update(dt, self.platforms, self.wind)
            if not proj.alive:
                continue
            for enemy in self.enemies:
                if enemy not in proj.already_hit and proj.rect.colliderect(enemy.rect):
                    enemy.take_damage(proj.damage)
                    proj.already_hit.add(enemy)
                    proj.alive = False
                    break
        self.projectiles[:] = [p for p in self.projectiles if p.alive]

    def _start_aim(self):
        """Begin aiming if the player has a bow in the selected hotbar slot."""
        slot = self.player.inventory.slots[self.player.hotbar_slot]
        if slot and slot.item_id == "bow":
            self.player.aiming = True

    def _fire_arrow(self):
        """Spawn a projectile if arrows are available; consume one."""
        if self.player.inventory.count("arrow") <= 0:
            return
        self.player.inventory.consume("arrow", 1)

        angle_rad = math.radians(self.player.aim_angle)
        vx = math.cos(angle_rad) * ARROW_SPEED * self.player.facing
        vy = -math.sin(angle_rad) * ARROW_SPEED   # negative: up is -y in pygame

        x = self.player.rect.centerx - ARROW_WIDTH  // 2
        y = self.player.rect.centery - ARROW_HEIGHT // 2
        self.projectiles.append(Projectile(x, y, vx, vy, ARROW_DAMAGE))

    def _use_hotbar_item(self):
        """Consume one of the selected hotbar item and apply its use effect."""
        slot_idx = self.player.hotbar_slot
        slot     = self.player.inventory.slots[slot_idx]
        if not slot:
            return
        item_def = self.player.inventory.item_defs.get(slot.item_id, {})
        use = item_def.get("use")
        if use == "heal":
            if self.player.health >= self.player.max_health:
                return   # already full — don't waste the potion
            heal = item_def.get("heal_amount", 0)
            self.player.health = min(self.player.max_health, self.player.health + heal)
            self.player.inventory.remove(slot_idx, 1)

    def _respawn(self):
        """Reload from save file and restore the world to its saved state."""
        self.death_timer = 0.0

        # Close any open overlays
        self.crafting_menu.close()
        self.dialogue_box.close()
        self.pause_menu.close()

        save_data = load_game()
        zone_id   = save_data.get("zone", "zone_01") if save_data else self.world.zone_id

        # Reload the zone so enemies and drops are fresh
        self.world.transition_to(zone_id)
        self.platforms   = self.world.platforms
        self.enemies     = self.world.enemies
        self.save_points = self.world.save_points
        self.npcs        = self.world.npcs
        self.exits       = self.world.exits
        self.item_drops  = self.world.item_drops

        # Restore player state from save, or reset to spawn if no save exists
        if save_data:
            player_data = save_data.get("player", {})
            px = player_data.get("x", self.world.spawn[0])
            py = player_data.get("y", self.world.spawn[1])
            self.player.health = player_data.get("health", self.player.max_health)
            inv_data = player_data.get("inventory")
            if inv_data:
                self.player.inventory.load_slots(inv_data)
            raw = save_data.get("collected_zone_drops", {})
            if isinstance(raw, list):
                self.collected_zone_drops = {zone_id: set(raw)}
            else:
                self.collected_zone_drops = {k: set(v) for k, v in raw.items()}
        else:
            px, py = self.world.spawn
            self.player.health = self.player.max_health

        self.player.rect.topleft  = (px, py)
        self.player.pos.x         = px
        self.player.pos.y         = py
        self.player.velocity.x    = 0
        self.player.velocity.y    = 0
        self.player.active_hitbox = None
        self.player.aiming        = False
        self.projectiles.clear()

        # Filter already-collected zone drops
        already = self.collected_zone_drops.get(zone_id, set())
        self.item_drops[:] = [
            d for d in self.item_drops if d.zone_drop_index not in already
        ]

        # Pre-warm save point overlap so respawn location doesn't flash
        for sp in self.save_points:
            sp.was_overlapping = sp.rect.colliderect(self.player.rect)

        self.camera.update(self.player.rect)

    def _draw_aim_indicator(self):
        """Draw a dotted trajectory preview arc including gravity and wind."""
        angle_rad = math.radians(self.player.aim_angle)
        vx = math.cos(angle_rad) * ARROW_SPEED * self.player.facing
        vy = -math.sin(angle_rad) * ARROW_SPEED

        px = float(self.player.rect.centerx)
        py = float(self.player.rect.centery)
        cur_vx, cur_vy = vx, vy

        for i in range(AIM_PREVIEW_STEPS):
            cur_vy += ARROW_GRAVITY * AIM_PREVIEW_STEP_T
            cur_vx += self.wind    * AIM_PREVIEW_STEP_T
            px     += cur_vx       * AIM_PREVIEW_STEP_T
            py     += cur_vy       * AIM_PREVIEW_STEP_T

            sx = int(px - self.camera.offset.x)
            sy = int(py - self.camera.offset.y)
            if not (0 <= sx <= SCREEN_WIDTH and 0 <= sy <= SCREEN_HEIGHT):
                break   # dot left the screen — stop drawing

            # Dots shrink and fade as they get further from the player
            radius = max(1, 3 - i // 7)
            alpha  = max(40, 220 - i * 10)
            color  = (AIM_DOT_COLOR[0], AIM_DOT_COLOR[1], AIM_DOT_COLOR[2])
            pygame.draw.circle(self.screen, color, (sx, sy), radius)

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

        # Draw projectiles
        for proj in self.projectiles:
            proj.draw(self.screen, self.camera)

        # Draw aim indicator while player is aiming
        if self.player.aiming:
            self._draw_aim_indicator()

        # Draw attack hitboxes (debug — remove when sprites exist)
        hitbox = self.player.active_hitbox
        if hitbox:
            pygame.draw.rect(self.screen, ATTACK_COLOR,
                             self.camera.apply_tuple(hitbox.rect), 2)
        for enemy in self.enemies:
            if enemy.active_hitbox:
                pygame.draw.rect(self.screen, ENEMY_ATTACK_COLOR,
                                 self.camera.apply_tuple(enemy.active_hitbox.rect), 2)

        # HUD — drawn last, in screen space (no camera offset)
        self.hud.draw(self.screen, self.wind)

        # Crafting menu — drawn over HUD when open
        self.crafting_menu.draw(self.screen)

        # Dialogue box — drawn over everything when open
        self.dialogue_box.draw(self.screen)

        # Pause menu — drawn over dialogue (Esc can't open it while dialogue is active)
        self.pause_menu.draw(self.screen)

        # Death overlay — drawn last so it covers all UI
        if self.death_timer > 0:
            self.screen.blit(self._death_overlay, (0, 0))
            self.screen.blit(self._death_text, (
                SCREEN_WIDTH  // 2 - self._death_text.get_width()  // 2,
                SCREEN_HEIGHT // 2 - self._death_text.get_height() // 2,
            ))

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)  # seconds; capped to prevent physics tunneling on alt-tab

            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()
