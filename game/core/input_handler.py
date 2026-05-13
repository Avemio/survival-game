"""
core/input_handler.py
All keyboard input routing extracted from Engine.handle_events().
Owns: KEYDOWN dispatch, item use registry, ability/arrow firing, item drop.
Does NOT own: game state (held by Engine), rendering, world transitions.
"""

import math

import pygame

from game.settings    import ARROW_SPEED, ARROW_DAMAGE, ARROW_WIDTH, ARROW_HEIGHT
from game.systems.assets import get as _assets
from game.entities.item_drop import ItemDrop
from game.entities.projectile import Projectile


class InputHandler:
    def __init__(self, engine):
        self._e = engine
        self._item_use_handlers = {
            "heal":          self._use_heal,
            "equip_ability": self._use_equip_ability,
        }

    def register_item_use(self, use_type: str, handler) -> None:
        """Register a new item use handler at runtime."""
        self._item_use_handlers[use_type] = handler

    # ------------------------------------------------------------------
    # Main KEYDOWN dispatch — called by Engine.handle_events()
    # ------------------------------------------------------------------

    def handle_keydown(self, event) -> None:
        """Route a KEYDOWN event. Return immediately when an overlay intercepts."""
        e = self._e

        if e.death_timer > 0:
            return

        if e.pause_menu.open:
            e.pause_menu.handle_event(event)
            return

        if e.shop_menu.open:
            e.shop_menu.handle_event(event)
            return

        if e.quest_log.open:
            e.quest_log.handle_event(event)
            return

        if e.skill_menu.open:
            result = e.skill_menu.handle_event(event)
            if result:
                name, desc = result
                e.notifications.push(f"{name}: {desc}", (120, 200, 140), 3.0)
                e.events.post("skill_spent", stat=name)
            return

        if e.inventory_screen.open:
            action = e.inventory_screen.handle_event(event)
            if action == "use":
                self.use_inventory_slot(e.inventory_screen.cursor_slot)
            elif action == "drop":
                self.drop_inventory_slot(e.inventory_screen.cursor_slot)
            return

        # --- No exclusive overlay open ---

        if event.key == pygame.K_ESCAPE:
            if e.crafting_menu.open:
                e.crafting_menu.close()
            elif e.dialogue_box.open:
                pass
            else:
                e.pause_menu.toggle()

        elif event.key == pygame.K_i:
            if not e.crafting_menu.open and not e.dialogue_box.open:
                e.inventory_screen.toggle()

        elif event.key == pygame.K_j:
            if not e.crafting_menu.open and not e.dialogue_box.open:
                e.quest_log.toggle()

        elif event.key == pygame.K_k:
            if not e.crafting_menu.open and not e.dialogue_box.open:
                e.skill_menu.toggle()

        elif event.key == pygame.K_c:
            if not e.dialogue_box.open and not e.shop_menu.open:
                e.crafting_menu.toggle()

        elif event.key == pygame.K_e:
            self._handle_interact()

        elif event.key == pygame.K_f:
            if not e.crafting_menu.open and not e.dialogue_box.open:
                self.use_hotbar_item()

        elif event.key == pygame.K_x:
            if not e.crafting_menu.open and not e.dialogue_box.open:
                self.start_aim()

        elif event.key == pygame.K_q:
            if not e.crafting_menu.open and not e.dialogue_box.open:
                self.fire_ability(0)

        elif event.key == pygame.K_r:
            if not e.crafting_menu.open and not e.dialogue_box.open:
                self.fire_ability(1)

        # Crafting menu also listens for nav keys while open
        if e.crafting_menu.open:
            e.crafting_menu.handle_event(event)

    # ------------------------------------------------------------------
    # KEYUP dispatch — arrow release fires the shot
    # ------------------------------------------------------------------

    def handle_keyup(self, event) -> None:
        e = self._e
        if event.key == pygame.K_x and e.player.aiming:
            if not (e.pause_menu.open or e.crafting_menu.open
                    or e.dialogue_box.open or e.inventory_screen.open
                    or e.death_timer > 0):
                self.fire_arrow()
            e.player.aiming    = False
            e.player.aim_angle = 0.0

    # ------------------------------------------------------------------
    # Interaction (E key)
    # ------------------------------------------------------------------

    def _handle_interact(self) -> None:
        e = self._e
        if e.dialogue_box.open:
            e.dialogue_box.advance()
            return
        if e.shop_menu.open:
            e.shop_menu.confirm()
            return
        if e.crafting_menu.open:
            return

        # NPCs
        for npc in e.npcs:
            if npc.interact_rect.colliderect(e.player.rect):
                did_act = False
                if npc.shop_id:
                    shop = e.shop_system.get(npc.shop_id)
                    name = shop.get("name", npc.name) if shop else npc.name
                    e.shop_menu.start(npc.shop_id, name)
                    if npc.dialogue_lines:
                        e.notifications.push(
                            f"{npc.name}: {npc.dialogue_lines[0]}",
                            (255, 230, 150), 4.0)
                    did_act = True
                elif npc.dialogue_lines:
                    e.dialogue_box.start(npc.name, list(npc.dialogue_lines))
                    did_act = True
                qid = getattr(npc, 'gives_quest', None)
                if qid:
                    started = e.quest_system.start(qid)
                    if started:
                        q = e.quest_system.get_def(qid)
                        if q:
                            e.notifications.push(
                                f"New Quest: {q['name']}", (255, 220, 60), 4.0, big=True)
                            e.notifications.push(
                                q.get('description', ''), (200, 200, 220), 4.0)
                        did_act = True
                if did_act:
                    return

        # Chests
        for chest in e.chests:
            if not chest.open and chest.interact_rect.colliderect(e.player.rect):
                e._open_chest(chest)
                return

        # Buildings
        for building in e.buildings:
            if building.interact_rect.colliderect(e.player.rect):
                e._enter_building(building)
                return

    # ------------------------------------------------------------------
    # Ability / arrow / aim
    # ------------------------------------------------------------------

    def fire_ability(self, slot_idx: int) -> None:
        e          = self._e
        ability_id = e.player.ability_slots[slot_idx]
        if not ability_id:
            return
        if e.player.ability_cooldowns[slot_idx] > 0:
            return
        if e.ability_system.execute(ability_id, e.player, e):
            ab = e.ability_system.get(ability_id)
            if ab:
                e.player.ability_cooldowns[slot_idx] = ab.get("cooldown", 0.0)
                sound = ab.get("sound")
                if sound:
                    _assets().play(sound)

    def start_aim(self) -> None:
        e    = self._e
        slot = e.player.inventory.slots[e.player.hotbar_slot]
        if slot and slot.item_id == "bow":
            e.player.aiming = True

    def fire_arrow(self) -> None:
        e = self._e
        if e.player.inventory.count("arrow") <= 0:
            return
        e.player.inventory.consume("arrow", 1)
        _assets().play("arrow_fire")
        angle_rad = math.radians(e.player.aim_angle)
        vx = math.cos(angle_rad) * ARROW_SPEED * e.player.facing
        vy = -math.sin(angle_rad) * ARROW_SPEED
        x  = e.player.rect.centerx - ARROW_WIDTH  // 2
        y  = e.player.rect.centery - ARROW_HEIGHT // 2
        e.projectiles.append(Projectile(x, y, vx, vy, ARROW_DAMAGE))

    # ------------------------------------------------------------------
    # Item use
    # ------------------------------------------------------------------

    def use_hotbar_item(self) -> None:
        self.use_inventory_slot(self._e.player.hotbar_slot)

    def use_inventory_slot(self, slot_idx: int) -> None:
        e       = self._e
        slot    = e.player.inventory.slots[slot_idx]
        if not slot:
            return
        item_def = e.player.inventory.item_defs.get(slot.item_id, {})
        handler  = self._item_use_handlers.get(item_def.get("use"))
        if handler:
            handler(slot_idx, slot, item_def)

    def _use_heal(self, slot_idx, slot, item_def) -> None:
        e = self._e
        if e.player.health >= e.player.max_health:
            return
        heal = item_def.get("heal_amount", 0)
        e.player.health = min(e.player.max_health, e.player.health + heal)
        e.player.inventory.remove(slot_idx, 1)

    def _use_equip_ability(self, slot_idx, slot, item_def) -> None:
        e          = self._e
        ability_id = item_def.get("ability_id")
        if ability_id:
            free = next((i for i, s in enumerate(e.player.ability_slots)
                         if s is None), None)
            if free is None:
                e.notifications.push(
                    "Ability slots full! Q or R slot must be empty.",
                    (255, 150, 50), 3.0)
                return
            e.player.ability_slots[free] = ability_id
            e.player.inventory.remove(slot_idx, 1)
            _assets().play("ui_confirm")

    def drop_inventory_slot(self, slot_idx: int) -> None:
        e    = self._e
        slot = e.player.inventory.slots[slot_idx]
        if not slot:
            return
        color = tuple(e.player.inventory.item_defs.get(
            slot.item_id, {}).get("color", [200, 200, 200]))
        x = e.player.rect.centerx - ItemDrop.SIZE // 2
        y = e.player.rect.bottom  - ItemDrop.SIZE
        e.item_drops.append(ItemDrop(x, y, slot.item_id, slot.quantity, color))
        e.player.inventory.remove(slot_idx, slot.quantity)
