"""
core/engine.py
The main game loop. Owns the screen, clock, and top-level update/draw calls.
Talks to World for all zone content — platforms, enemies, spawn point.
Does NOT own: game logic, combat, zone data.
"""

import sys
import math
import random
from enum import Enum, auto
import pygame


class GameState(Enum):
    TITLE   = auto()
    PLAYING = auto()

from game.settings        import (SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
                                   BG_COLOR, PLATFORM_COLOR, ATTACK_COLOR, ENEMY_ATTACK_COLOR,
                                   DEATH_OVERLAY_DURATION, DEATH_TEXT_COLOR,
                                   PLAYER_COLOR, ENEMY_COLOR, ENEMY_HIT_COLOR,
                                   ARROW_SPEED, ARROW_DAMAGE, ARROW_WIDTH, ARROW_HEIGHT,
                                   WIND_MAX, WIND_CHANGE_RATE, WIND_TARGET_MIN, WIND_TARGET_MAX,
                                   AIM_PREVIEW_STEPS, AIM_PREVIEW_STEP_T, AIM_DOT_COLOR,
                                   ARROW_GRAVITY, HITSTOP_DURATION)
from game.core.camera        import Camera
from game.entities.player    import Player
from game.entities.item_drop import ItemDrop
from game.world.world        import World
from game.ui.hud              import HUD
from game.ui.menus            import CraftingMenu
from game.ui.dialogue         import DialogueBox
from game.ui.pause_menu       import PauseMenu
from game.ui.inventory_screen import InventoryScreen
from game.ui.title_screen     import TitleScreen
from game.systems.assets      import get as _assets
from game.systems.saving      import save_game, load_game
from game.systems.crafting    import CraftingSystem
from game.systems.abilities   import AbilitySystem
from game.systems.effects     import apply_status
from game.systems.shop        import ShopSystem
from game.systems.quests      import QuestSystem
from game.ui.shop_menu        import ShopMenu
from game.ui.quest_log        import QuestLog
from game.ui.notifications    import NotificationQueue
from game.entities.projectile import Projectile


class _Particle:
    """Lightweight visual particle — world-space position, fades and shrinks over its lifetime."""
    __slots__ = ('pos', 'vel', 'color', 'life', 'max_life', 'radius', 'gravity')

    def __init__(self, x, y, vx, vy, color, life, radius, gravity=400.0):
        self.pos      = pygame.math.Vector2(x, y)
        self.vel      = pygame.math.Vector2(vx, vy)
        self.color    = color
        self.life     = life
        self.max_life = life
        self.radius   = radius
        self.gravity  = gravity


class _DamageNumber:
    """Floating damage number — drifts upward for 0.75 s then expires."""
    __slots__ = ('x', 'y', 'surf', 'life', 'max_life')

    def __init__(self, x, y, surf):
        self.x        = float(x)
        self.y        = float(y)
        self.surf     = surf
        self.life     = 0.75
        self.max_life = 0.75


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

        # Per-zone drop log: {zone_id: set of int indices already collected}
        self.collected_zone_drops = {}
        # Per-zone chest log: {zone_id: set of int indices already opened}
        self.opened_zone_chests   = {}

        self.player       = Player(*self.world.spawn)
        self.quest_system = QuestSystem()   # created early so save loading can call .load()

        # Apply saved player state if a save exists
        if save_data:
            player_data = save_data.get("player", {})
            px = player_data.get("x", self.world.spawn[0])
            py = player_data.get("y", self.world.spawn[1])
            self.player.max_health = player_data.get("max_health", self.player.max_health)
            self.player.max_mana   = player_data.get("max_mana",   self.player.max_mana)
            self.player.health     = player_data.get("health", self.player.max_health)
            self.player.mana       = float(player_data.get("mana", self.player.max_mana))
            self.player.level      = player_data.get("level", 1)
            self.player.xp         = player_data.get("xp", 0)
            self.player.xp_to_next = player_data.get("xp_to_next", 100)

            inv_data = player_data.get("inventory")
            if inv_data:
                self.player.inventory.load_slots(inv_data)

            ab_slots = player_data.get("ability_slots")
            if ab_slots and len(ab_slots) >= 2:
                self.player.ability_slots = list(ab_slots[:2])

            raw = save_data.get("collected_zone_drops", {})
            if isinstance(raw, list):
                # Migrate old flat-list format (assumed to be zone_01 drops)
                self.collected_zone_drops = {zone_id: set(raw)}
            else:
                self.collected_zone_drops = {k: set(v) for k, v in raw.items()}
            raw_chests = save_data.get("opened_zone_chests", {})
            self.opened_zone_chests = {k: set(v) for k, v in raw_chests.items()}
            quest_data = save_data.get("quests", {})
            if quest_data:
                self.quest_system.load(quest_data)
        else:
            px, py = self.world.spawn

        self.camera           = Camera()
        self.ability_system   = AbilitySystem()
        self.hud              = HUD(self.player, self.ability_system)
        self.crafting         = CraftingSystem()
        self.crafting_menu    = CraftingMenu(self.player, self.crafting)
        self.dialogue_box     = DialogueBox()
        self.pause_menu       = PauseMenu()
        self.inventory_screen = InventoryScreen(self.player)
        self.shop_system      = ShopSystem()
        self.shop_menu        = ShopMenu(self.player, self.shop_system)
        self.quest_log        = QuestLog(self.quest_system)
        self.notifications    = NotificationQueue()

        # Item use dispatch — add new use types here or via register_item_use()
        self._item_use_handlers = {
            "heal":          self._use_heal,
            "equip_ability": self._use_equip_ability,
        }

        # Title screen — always shown first on startup
        self._state       = GameState.TITLE
        self._title_screen = TitleScreen(has_save=save_data is not None)

        # Auto-start any quests flagged auto_start: true in quests.json
        self.quest_system.auto_start_all()

        # Death overlay — all surfaces built once at init (never inside draw)
        self.death_timer    = 0.0
        self._death_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._death_overlay.fill((120, 0, 0, 180))
        self._death_font    = pygame.font.SysFont(None, 96)
        self._death_text    = self._death_font.render("YOU DIED", True, DEATH_TEXT_COLOR)
        self._dmg_font      = pygame.font.SysFont(None, 20)

        # Projectiles, particles, damage numbers, special attacks
        self.projectiles    = []
        self.particles      = []
        self.damage_numbers = []
        self.active_attacks = []

        # Hitstop — brief physics pause when landing a hit
        self._hitstop_timer = 0.0

        # Zone list references and setup
        self._setup_zone()
        self.player.reset_to(px, py)
        self._warm_save_points()

        # Wind — drifts slowly toward a random target strength
        self.wind          = 0.0
        self._wind_target  = 0.0
        self._wind_timer   = random.uniform(WIND_TARGET_MIN, WIND_TARGET_MAX)

        # Atmospheric wind streaks (screen-space, purely visual)
        self._wind_streaks = [
            {
                'x':      random.uniform(0, SCREEN_WIDTH),
                'y':      random.uniform(50, SCREEN_HEIGHT - 80),
                'length': random.randint(20, 55),
            }
            for _ in range(10)
        ]

        # Loot pity: guarantee a rare drop every _PITY_THRESHOLD kills without one
        self._pity_count     = 0
        self._PITY_THRESHOLD = 8

    def _new_game(self):
        """Reset to a fresh game ignoring any existing save."""
        from pathlib import Path
        save_path = Path(__file__).parent.parent.parent / "save.json"
        if save_path.exists():
            save_path.unlink()
        # Reload zone_01 fresh
        self.collected_zone_drops = {}
        self.opened_zone_chests   = {}
        self.world.transition_to("zone_01")
        self._setup_zone()
        # Reset player to default state
        from game.settings import PLAYER_MAX_HEALTH, PLAYER_MAX_MANA
        self.player.max_health     = PLAYER_MAX_HEALTH
        self.player.max_mana       = PLAYER_MAX_MANA
        self.player.health         = PLAYER_MAX_HEALTH
        self.player.mana           = float(PLAYER_MAX_MANA)
        self.player.level          = 1
        self.player.xp             = 0
        self.player.xp_to_next     = 100
        self.player.inventory      = __import__('game.systems.inventory', fromlist=['Inventory']).Inventory(
            size=__import__('game.settings', fromlist=['INVENTORY_SLOTS']).INVENTORY_SLOTS)
        self.player.ability_slots  = [None, None]
        self.player.ability_cooldowns = [0.0, 0.0]
        self.player.reset_to(*self.world.spawn)
        self._warm_save_points()
        self.camera.update(self.player.rect, 0.0)
        # Re-start any auto_start quests after a fresh game (quests.json drives this)
        self.quest_system.auto_start_all()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Title screen intercepts all input while active
            if self._state == GameState.TITLE:
                if event.type == pygame.KEYDOWN:
                    result = self._title_screen.handle_event(event)
                    if result == "new_game":
                        self._new_game()
                        self._state = GameState.PLAYING
                    elif result == "continue":
                        self._state = GameState.PLAYING
                    elif result == "quit":
                        self.running = False
                continue

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_x and self.player.aiming:
                    # Only fire if no menu/overlay is open and the world is running
                    if not (self.pause_menu.open or self.crafting_menu.open
                            or self.dialogue_box.open or self.inventory_screen.open
                            or self.death_timer > 0):
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

                # Shop menu intercepts all keys while open
                if self.shop_menu.open:
                    self.shop_menu.handle_event(event)
                    continue

                # Quest log intercepts all keys while open
                if self.quest_log.open:
                    self.quest_log.handle_event(event)
                    continue

                # Inventory screen intercepts while open
                if self.inventory_screen.open:
                    action = self.inventory_screen.handle_event(event)
                    if action == "use":
                        self._use_inventory_slot(self.inventory_screen.cursor_slot)
                    elif action == "drop":
                        self._drop_inventory_slot(self.inventory_screen.cursor_slot)
                    continue

                if event.key == pygame.K_ESCAPE:
                    if self.shop_menu.open:
                        self.shop_menu.close()
                    elif self.crafting_menu.open:
                        self.crafting_menu.close()
                    elif self.dialogue_box.open:
                        pass
                    else:
                        self.pause_menu.toggle()

                elif event.key == pygame.K_i:
                    if not self.crafting_menu.open and not self.dialogue_box.open:
                        self.inventory_screen.toggle()

                elif event.key == pygame.K_j:
                    if not self.crafting_menu.open and not self.dialogue_box.open:
                        self.quest_log.toggle()

                elif event.key == pygame.K_c:
                    if not self.dialogue_box.open:
                        self.crafting_menu.toggle()

                elif event.key == pygame.K_e:
                    if self.dialogue_box.open:
                        self.dialogue_box.advance()
                    elif self.shop_menu.open:
                        self.shop_menu.handle_event(event)
                    elif not self.crafting_menu.open:
                        # Check NPCs — shopkeepers open shop, others open dialogue
                        for npc in self.npcs:
                            if npc.interact_rect.colliderect(self.player.rect):
                                if npc.shop_id:
                                    shop = self.shop_system.get(npc.shop_id)
                                    name = shop.get("name", npc.name) if shop else npc.name
                                    self.shop_menu.start(npc.shop_id, name)
                                elif npc.dialogue_lines:
                                    lines = list(npc.dialogue_lines)
                                    self.dialogue_box.start(npc.name, lines)
                                # Give quest — inject description into dialogue and notify
                                qid = getattr(npc, 'gives_quest', None)
                                if qid:
                                    started = self.quest_system.start(qid)
                                    if started:
                                        q = self.quest_system.get_def(qid)
                                        if q:
                                            self.notifications.push(
                                                f"New Quest: {q['name']}",
                                                (255, 220, 60), 4.0, big=True)
                                            self.notifications.push(
                                                q.get('description', ''),
                                                (200, 200, 220), 4.0)
                                break
                        else:
                            for chest in self.chests:
                                if not chest.open and chest.interact_rect.colliderect(self.player.rect):
                                    self._open_chest(chest)
                                    break
                            else:
                                for building in self.buildings:
                                    if building.interact_rect.colliderect(self.player.rect):
                                        self._enter_building(building)
                                        break

                elif event.key == pygame.K_f:
                    if not self.crafting_menu.open and not self.dialogue_box.open:
                        self._use_hotbar_item()

                elif event.key == pygame.K_x:
                    if not self.crafting_menu.open and not self.dialogue_box.open:
                        self._start_aim()

                elif event.key == pygame.K_q:
                    if not self.crafting_menu.open and not self.dialogue_box.open:
                        self._fire_ability(0)

                elif event.key == pygame.K_r:
                    if not self.crafting_menu.open and not self.dialogue_box.open:
                        self._fire_ability(1)

                # Forward navigation keys to the crafting menu while it's open
                if self.crafting_menu.open:
                    self.crafting_menu.handle_event(event)

    def update(self, dt):
        if self._state == GameState.TITLE:
            return

        self.crafting_menu.update(dt)
        self.shop_menu.update(dt)
        self.notifications.update(dt)

        # Death countdown — world paused; respawn fires when timer expires
        if self.death_timer > 0:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self._respawn()
            return

        # Pause all world simulation while any overlay is open
        if (self.pause_menu.open or self.crafting_menu.open
                or self.dialogue_box.open or self.inventory_screen.open
                or self.shop_menu.open or self.quest_log.open):
            return

        self._update_wind(dt)
        self.player.update(dt, self.platforms)

        # Check death BEFORE zone exits (prevents player entering new zone at 0 HP)
        if self.player.health <= 0:
            self.death_timer = DEATH_OVERLAY_DURATION
            return

        # Landing shake: player just hit the ground at high speed
        if self.player.on_ground and self.player._landing_velocity > 500:
            intensity = min(4, int(self.player._landing_velocity / 350))
            self.camera.shake(intensity=intensity, duration=0.08)

        # Hitstop: brief physics freeze after landing a hit — camera still updates
        if self._hitstop_timer > 0:
            self._hitstop_timer -= dt
            self.camera.update(self.player.rect, dt)
            return

        self._update_enemies(dt)
        self._update_combat(dt)
        self._update_enemy_attacks(dt)
        self._update_projectiles(dt)
        self._update_item_drops()
        self._update_save_points(dt)
        self._update_zone_exits()
        self._update_particles(dt)
        self._update_damage_numbers(dt)
        self._update_active_attacks(dt)
        self._update_wind_streaks(dt)
        self.camera.update(self.player.rect, dt)

    def _update_enemies(self, dt):
        living = []
        for enemy in self.enemies:
            enemy.update(dt, self.player, self.platforms)
            if enemy.alive:
                living.append(enemy)
            else:
                self._spawn_drops(enemy)
                xp = getattr(enemy, 'xp_reward', 0)
                if xp > 0:
                    self.player.award_xp(xp)
                    self._spawn_xp_number(enemy.rect.centerx, enemy.rect.top - 4, xp)
                # Quest notifications for kills
                enemy_type = getattr(enemy, '_type_key', None)
                completed = self.quest_system.notify("kill", target=enemy_type or "")
                completed += self.quest_system.notify("kill_any")
                self._award_quest_rewards(completed)
                self._spawn_death_particles(enemy.rect.center, ENEMY_COLOR, 10)
                _assets().play("enemy_death")
        self.enemies[:] = living

    def _spawn_drops(self, enemy):
        """Roll loot table and create ItemDrop objects at the enemy's position."""
        item_defs = self.player.inventory.item_defs
        got_rare  = False
        for drop in enemy.loot:
            chance  = drop.get("chance", 1.0)
            is_rare = chance < 1.0
            # Pity system: guarantee rare drops after _PITY_THRESHOLD kills without one
            forced = is_rare and self._pity_count >= self._PITY_THRESHOLD
            if forced or random.random() < chance:
                if is_rare:
                    got_rare = True
                item_id  = drop["item_id"]
                quantity = drop.get("quantity", 1)
                color    = tuple(item_defs.get(item_id, {}).get("color", [200, 200, 200]))
                x = enemy.rect.centerx - ItemDrop.SIZE // 2
                y = enemy.rect.bottom  - ItemDrop.SIZE
                self.item_drops.append(ItemDrop(x, y, item_id, quantity, color))
        self._pity_count = 0 if got_rare else self._pity_count + 1

    def _update_item_drops(self):
        """Pick up any drops the player is standing on."""
        for drop in self.item_drops:
            if drop.rect.colliderect(self.player.rect):
                leftover = self.player.inventory.add(drop.item_id, drop.quantity)
                if leftover == 0:
                    drop.alive = False
                    _assets().play("item_pickup")
                    if drop.zone_drop_index is not None:
                        self.collected_zone_drops.setdefault(
                            self.world.zone_id, set()
                        ).add(drop.zone_drop_index)
                    # Quest notify for collect
                    completed = self.quest_system.notify("collect", target=drop.item_id,
                                                         amount=drop.quantity)
                    self._award_quest_rewards(completed)
                    # Ability scroll hint
                    item_def = self.player.inventory.item_defs.get(drop.item_id, {})
                    if item_def.get("use") == "equip_ability":
                        ability_id = item_def.get("ability_id", "")
                        self.notifications.push(
                            f"Ability scroll: {item_def.get('name', ability_id)}",
                            (160, 200, 255), 4.0, big=True)
                        self.notifications.push(
                            "Open inventory (I) or hotbar → select scroll → press F to equip",
                            (180, 180, 220), 4.0)
                else:
                    drop.quantity = leftover
        self.item_drops[:] = [d for d in self.item_drops if d.alive]

    def _award_quest_rewards(self, completed: list[str]):
        """Award XP + gold for each completed quest, notify the player."""
        for quest_id in completed:
            q = self.quest_system.get_def(quest_id)
            if not q:
                continue
            xp   = q.get("reward_xp",   0)
            gold = q.get("reward_gold",  0)
            if xp   > 0: self.player.award_xp(xp)
            if gold > 0: self.player.inventory.add("gold", gold)
            _assets().play("save_point")
            self.notifications.push(
                f"Quest Complete: {q['name']}!",
                (80, 255, 120), 4.0, big=True)
            parts = []
            if xp   > 0: parts.append(f"+{xp} XP")
            if gold > 0: parts.append(f"+{gold} gold")
            if parts:
                self.notifications.push("  ".join(parts), (200, 230, 200), 3.5)

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
                _assets().play("player_hit")
                self.camera.shake(intensity=3, duration=0.12)
                self._spawn_hit_particles(self.player.rect.center, PLAYER_COLOR, 5)
                self._spawn_damage_number(
                    self.player.rect.centerx, self.player.rect.top - 4,
                    hitbox.damage, color=(255, 80, 80)
                )
            if hitbox.expired:
                enemy.active_hitbox = None

    def _update_combat(self, dt):
        hitbox = self.player.active_hitbox
        if not hitbox:
            return
        if not hitbox.sound_played:
            _assets().play("attack_swing")
            hitbox.sound_played = True
        hitbox.update(dt)
        for enemy in self.enemies:
            if (enemy not in hitbox.already_hit
                    and hitbox.rect.colliderect(enemy.rect)):
                enemy.take_damage(hitbox.damage)
                hitbox.already_hit.add(enemy)
                if hitbox.knockback > 0:
                    sign = 1 if enemy.rect.centerx >= self.player.rect.centerx else -1
                    enemy.velocity.x = hitbox.knockback * sign
                if hitbox.status_def:
                    apply_status(enemy, hitbox.status_def)
                _assets().play("enemy_hit")
                self._spawn_hit_particles(enemy.rect.center, ENEMY_HIT_COLOR, 6)
                self._spawn_damage_number(enemy.rect.centerx, enemy.rect.top - 4, hitbox.damage)
                self._hitstop_timer = HITSTOP_DURATION
        if hitbox.expired:
            self.player.active_hitbox = None

    def _update_save_points(self, dt):
        for sp in self.save_points:
            sp.update(dt)
            overlapping = sp.rect.colliderect(self.player.rect)
            if overlapping and not sp.was_overlapping:
                self.player.health = self.player.max_health
                save_game(self.player, self.world.zone_id, self.collected_zone_drops, self.opened_zone_chests, self.quest_system.serialize())
                sp.flash_timer = sp.FLASH_DURATION
                _assets().play("save_point")
            sp.was_overlapping = overlapping

    def _update_zone_exits(self):
        for exit_ in self.exits:
            overlapping = exit_.rect.colliderect(self.player.rect)
            if overlapping and not exit_.was_overlapping:
                self._transition_zone(exit_.target_zone, exit_.spawn_override)
                return   # stop — lists just changed
            exit_.was_overlapping = overlapping

    def _setup_zone(self):
        """Re-point all engine list references after a zone load. Call after world.transition_to()."""
        zone_id          = self.world.zone_id
        self.platforms   = self.world.platforms
        self.enemies     = self.world.enemies
        self.save_points = self.world.save_points
        self.npcs        = self.world.npcs
        self.exits       = self.world.exits
        self.item_drops  = self.world.item_drops
        self.buildings   = self.world.buildings
        self.chests      = self.world.chests

        # Filter already-collected drops for this zone
        already_drops = self.collected_zone_drops.get(zone_id, set())
        self.item_drops[:] = [d for d in self.item_drops if d.zone_drop_index not in already_drops]

        # Mark already-opened chests
        already_chests = self.opened_zone_chests.get(zone_id, set())
        for chest in self.chests:
            if chest.zone_chest_index in already_chests:
                chest.open = True

        # Reset zone exit overlap state (rising-edge guard)
        for exit_ in self.exits:
            exit_.was_overlapping = False

        # Clear all in-flight objects
        self.projectiles.clear()
        self.active_attacks.clear()
        self.particles.clear()
        self.damage_numbers.clear()

        self._on_zone_loaded()

    def _warm_save_points(self):
        """Pre-warm save point overlap flags after player is positioned."""
        for sp in self.save_points:
            sp.was_overlapping = sp.rect.colliderect(self.player.rect)

    def _transition_zone(self, target_zone_id, spawn_override=None):
        """Save, swap zones, re-point engine references, teleport player to spawn."""
        save_game(self.player, self.world.zone_id, self.collected_zone_drops, self.opened_zone_chests, self.quest_system.serialize())
        self.world.transition_to(target_zone_id)
        self._setup_zone()
        sx, sy = spawn_override if spawn_override else self.world.spawn
        self.player.reset_to(sx, sy)
        self._warm_save_points()
        _assets().play("zone_transition")

    def _open_chest(self, chest):
        """Open a chest and transfer contents to player inventory."""
        chest.open = True
        _assets().play("item_pickup")
        if chest.zone_chest_index is not None:
            self.opened_zone_chests.setdefault(self.world.zone_id, set()).add(
                chest.zone_chest_index)
        for item in chest.contents:
            leftover = self.player.inventory.add(item["item_id"], item["quantity"])
            if leftover > 0:
                # Drop what didn't fit at the player's feet
                from game.entities.item_drop import ItemDrop
                color = tuple(self.player.inventory.item_defs.get(
                    item["item_id"], {}).get("color", [200, 200, 200]))
                x = self.player.rect.centerx - ItemDrop.SIZE // 2
                y = self.player.rect.bottom  - ItemDrop.SIZE
                self.item_drops.append(ItemDrop(x, y, item["item_id"], leftover, color))

    def _enter_building(self, building):
        """Transition into a building's interior zone (triggered by E key at door)."""
        save_game(self.player, self.world.zone_id, self.collected_zone_drops, self.opened_zone_chests, self.quest_system.serialize())
        self.world.transition_to(building.target_zone)
        self._setup_zone()
        sx, sy = self.world.spawn
        self.player.reset_to(sx, sy)
        self._warm_save_points()
        _assets().play("zone_transition")

    def _fire_ability(self, slot_idx: int):
        """Fire the ability assigned to slot 0 (Q) or 1 (R)."""
        ability_id = self.player.ability_slots[slot_idx]
        if not ability_id:
            return
        if self.player.ability_cooldowns[slot_idx] > 0:
            return
        if self.ability_system.execute(ability_id, self.player, self):
            ab = self.ability_system.get(ability_id)
            if ab:
                self.player.ability_cooldowns[slot_idx] = ab.get("cooldown", 0.0)
                sound = ab.get("sound")
                if sound:
                    _assets().play(sound)

    def _update_active_attacks(self, dt):
        for attack in self.active_attacks:
            attack.update(dt, self.platforms, self.enemies, self.player)
        self.active_attacks[:] = [a for a in self.active_attacks if a.alive]

    def _on_zone_loaded(self):
        """Called whenever the active zone changes — starts zone music if defined."""
        if self.world.music:
            _assets().play_music(self.world.music)

    def _update_wind(self, dt):
        self._wind_timer -= dt
        if self._wind_timer <= 0:
            self._wind_target = random.uniform(-WIND_MAX, WIND_MAX)
            self._wind_timer  = random.uniform(WIND_TARGET_MIN, WIND_TARGET_MAX)
        self.wind += (self._wind_target - self.wind) * WIND_CHANGE_RATE * dt

    def _update_wind_streaks(self, dt):
        """Scroll atmospheric streak positions with the wind; wrap at screen edges."""
        for s in self._wind_streaks:
            s['x'] += self.wind * dt * 0.8
            if s['x'] > SCREEN_WIDTH + 60:
                s['x'] = -60.0
            elif s['x'] < -60:
                s['x'] = SCREEN_WIDTH + 60.0

    # ------------------------------------------------------------------
    # Particle helpers
    # ------------------------------------------------------------------

    def _update_particles(self, dt):
        for p in self.particles:
            p.vel.y += p.gravity * dt
            p.pos   += p.vel * dt
            p.life  -= dt
        self.particles[:] = [p for p in self.particles if p.life > 0]

    def _spawn_hit_particles(self, pos, color, count=6):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 190)
            self.particles.append(_Particle(
                pos[0], pos[1],
                math.cos(angle) * speed,
                math.sin(angle) * speed - 50,
                color,
                random.uniform(0.14, 0.26),
                random.randint(2, 3),
                gravity=420.0,
            ))

    def _spawn_damage_number(self, x, y, value, color=(255, 240, 80)):
        surf = self._dmg_font.render(str(int(value)), True, color)
        self.damage_numbers.append(_DamageNumber(x - surf.get_width() // 2, y, surf))

    def _spawn_xp_number(self, x, y, amount: int):
        surf = self._dmg_font.render(f"+{amount} XP", True, (100, 140, 255))
        self.damage_numbers.append(_DamageNumber(x - surf.get_width() // 2, y - 18, surf))

    def _update_damage_numbers(self, dt):
        for dn in self.damage_numbers:
            dn.y  -= 45.0 * dt   # float upward
            dn.life -= dt
        self.damage_numbers[:] = [d for d in self.damage_numbers if d.life > 0]

    def _spawn_death_particles(self, pos, color, count=10):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 240)
            self.particles.append(_Particle(
                pos[0], pos[1],
                math.cos(angle) * speed,
                math.sin(angle) * speed - 70,
                color,
                random.uniform(0.28, 0.55),
                random.randint(2, 5),
                gravity=480.0,
            ))

    def _update_projectiles(self, dt):
        for proj in self.projectiles:
            proj.update(dt, self.platforms, self.wind)
            if not proj.alive:
                continue
            for enemy in self.enemies:
                if proj.rect.colliderect(enemy.rect):
                    if proj.hit(enemy):
                        self._spawn_hit_particles(enemy.rect.center, ENEMY_HIT_COLOR, 4)
                    if not proj.alive:
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
        _assets().play("arrow_fire")

        angle_rad = math.radians(self.player.aim_angle)
        vx = math.cos(angle_rad) * ARROW_SPEED * self.player.facing
        vy = -math.sin(angle_rad) * ARROW_SPEED   # negative: up is -y in pygame

        x = self.player.rect.centerx - ARROW_WIDTH  // 2
        y = self.player.rect.centery - ARROW_HEIGHT // 2
        self.projectiles.append(Projectile(x, y, vx, vy, ARROW_DAMAGE))

    def _use_hotbar_item(self):
        """Use the selected hotbar item."""
        self._use_inventory_slot(self.player.hotbar_slot)

    def _use_inventory_slot(self, slot_idx: int):
        """Consume one of the item in slot_idx and apply its use effect via registry."""
        slot = self.player.inventory.slots[slot_idx]
        if not slot:
            return
        item_def = self.player.inventory.item_defs.get(slot.item_id, {})
        use      = item_def.get("use")
        handler  = self._item_use_handlers.get(use)
        if handler:
            handler(slot_idx, slot, item_def)

    # Handlers registered by use-type string — add new item use types here,
    # not inside _use_inventory_slot.
    def _use_heal(self, slot_idx, slot, item_def):
        if self.player.health >= self.player.max_health:
            return
        heal = item_def.get("heal_amount", 0)
        self.player.health = min(self.player.max_health, self.player.health + heal)
        self.player.inventory.remove(slot_idx, 1)

    def _use_equip_ability(self, slot_idx, slot, item_def):
        ability_id = item_def.get("ability_id")
        if ability_id:
            idx = next(
                (i for i, s in enumerate(self.player.ability_slots) if s is None), 0
            )
            self.player.ability_slots[idx] = ability_id
            self.player.inventory.remove(slot_idx, 1)
            _assets().play("ui_confirm")

    def _drop_inventory_slot(self, slot_idx: int):
        """Drop the item in slot_idx at the player's feet."""
        slot = self.player.inventory.slots[slot_idx]
        if not slot:
            return
        item_defs = self.player.inventory.item_defs
        color = tuple(item_defs.get(slot.item_id, {}).get("color", [200, 200, 200]))
        x = self.player.rect.centerx - ItemDrop.SIZE // 2
        y = self.player.rect.bottom  - ItemDrop.SIZE
        self.item_drops.append(ItemDrop(x, y, slot.item_id, slot.quantity, color))
        self.player.inventory.slots[slot_idx] = None

    def _respawn(self):
        """Reload from save file and restore the world to its saved state."""
        self.death_timer = 0.0
        self.crafting_menu.close()
        self.dialogue_box.close()
        self.pause_menu.close()
        self.inventory_screen.close()

        save_data = load_game()
        zone_id   = save_data.get("zone", "zone_01") if save_data else self.world.zone_id

        self.world.transition_to(zone_id)
        self._setup_zone()

        if save_data:
            player_data = save_data.get("player", {})
            px = player_data.get("x", self.world.spawn[0])
            py = player_data.get("y", self.world.spawn[1])
            self.player.max_health = player_data.get("max_health", self.player.max_health)
            self.player.max_mana   = player_data.get("max_mana",   self.player.max_mana)
            self.player.health     = player_data.get("health", self.player.max_health)
            self.player.mana       = float(player_data.get("mana", self.player.max_mana))
            self.player.level      = player_data.get("level", 1)
            self.player.xp         = player_data.get("xp", 0)
            self.player.xp_to_next = player_data.get("xp_to_next", 100)
            inv_data = player_data.get("inventory")
            if inv_data:
                self.player.inventory.load_slots(inv_data)
            ab_slots = player_data.get("ability_slots")
            if ab_slots and len(ab_slots) >= 2:
                self.player.ability_slots = list(ab_slots[:2])
            raw = save_data.get("collected_zone_drops", {})
            if isinstance(raw, list):
                self.collected_zone_drops = {zone_id: set(raw)}
            else:
                self.collected_zone_drops = {k: set(v) for k, v in raw.items()}
            raw_chests = save_data.get("opened_zone_chests", {})
            self.opened_zone_chests = {k: set(v) for k, v in raw_chests.items()}
            quest_data = save_data.get("quests", {})
            if quest_data:
                self.quest_system.load(quest_data)
            already = self.collected_zone_drops.get(zone_id, set())
            self.item_drops[:] = [d for d in self.item_drops if d.zone_drop_index not in already]
        else:
            px, py = self.world.spawn
            self.player.health = self.player.max_health

        self.player.reset_to(px, py)
        self._warm_save_points()
        self.camera.update(self.player.rect, 0.0)

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

            # Dots shrink as they get further from the player
            radius = max(1, 3 - i // 7)
            pygame.draw.circle(self.screen, AIM_DOT_COLOR, (sx, sy), radius)

    def draw(self):
        if self._state == GameState.TITLE:
            self._title_screen.draw(self.screen)
            pygame.display.flip()
            return

        self.screen.fill(self.world.bg_color)

        # Atmospheric wind streaks — drawn first, behind everything
        if abs(self.wind) > 8:
            streak_color = (52, 52, 62)
            for s in self._wind_streaks:
                length = int(s['length'] * abs(self.wind) / WIND_MAX)
                if length > 3:
                    x1 = int(s['x'])
                    x2 = x1 + (length if self.wind > 0 else -length)
                    pygame.draw.line(self.screen, streak_color,
                                     (x1, int(s['y'])), (x2, int(s['y'])), 1)

        # Draw platforms
        for p in self.platforms:
            pygame.draw.rect(self.screen, PLATFORM_COLOR, self.camera.apply_tuple(p))

        # Draw buildings (behind NPCs/enemies)
        for building in self.buildings:
            building.draw(self.screen, self.camera, self.player.rect)

        # Draw chests
        for chest in self.chests:
            chest.draw(self.screen, self.camera, self.player.rect)

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

        # Draw special attacks (wave, area, aura)
        for attack in self.active_attacks:
            attack.draw(self.screen, self.camera)

        # Draw damage numbers (world-space, float upward)
        for dn in self.damage_numbers:
            sx, sy = self.camera.world_to_screen(dn.x, dn.y)
            if 0 <= sx <= SCREEN_WIDTH and 0 <= sy <= SCREEN_HEIGHT:
                alpha = int(255 * dn.life / dn.max_life)
                dn.surf.set_alpha(alpha)
                self.screen.blit(dn.surf, (sx, int(sy)))

        # Draw particles (world-space, fading color + shrinking radius)
        for p in self.particles:
            sx, sy = self.camera.world_to_screen(p.pos.x, p.pos.y)
            if 0 <= sx <= SCREEN_WIDTH and 0 <= sy <= SCREEN_HEIGHT:
                ratio = p.life / p.max_life
                r     = max(1, int(p.radius * ratio))
                color = (
                    int(p.color[0] * ratio),
                    int(p.color[1] * ratio),
                    int(p.color[2] * ratio),
                )
                pygame.draw.circle(self.screen, color, (sx, sy), r)

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

        # Inventory screen — drawn over HUD
        self.inventory_screen.draw(self.screen)

        # Shop menu — drawn over HUD/inventory
        self.shop_menu.draw(self.screen)

        # Quest log
        self.quest_log.draw(self.screen)

        # Floating notifications (right side, above pause menu)
        self.notifications.draw(self.screen)

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
