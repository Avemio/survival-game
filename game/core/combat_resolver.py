"""
core/combat_resolver.py
All combat, damage, particle, and drop logic extracted from Engine.
Owns: hit resolution, enemy death, projectile collision, particle spawning,
      XP/quest reward routing, pity-drop system.
Does NOT own: game state (held by Engine), world transitions, input.
"""

import math
import random

import pygame

from game.settings import (
    PLAYER_COLOR, ENEMY_COLOR, ENEMY_HIT_COLOR,
    HITSTOP_DURATION, ENEMY_ACTIVE_RADIUS,
)
from game.systems.effects  import apply_status
from game.systems.assets   import get as _assets
from game.entities.item_drop import ItemDrop
from game.core.particles   import Particle, DamageNumber


class CombatResolver:
    def __init__(self, engine):
        self._e = engine

    # ------------------------------------------------------------------
    # Enemy update + kill detection
    # ------------------------------------------------------------------

    def update_enemies(self, dt: float) -> None:
        e       = self._e
        living  = []
        for enemy in e.enemies:
            # Skip AI + physics for enemies beyond the active radius — they'll
            # activate naturally once the player approaches.
            if abs(enemy.rect.centerx - e.player.rect.centerx) > ENEMY_ACTIVE_RADIUS:
                if enemy.alive:
                    living.append(enemy)
                continue
            enemy.update(dt, e.player, e.platform_grid)
            if enemy.pending_projectiles:
                e.projectiles.extend(enemy.pending_projectiles)
                enemy.pending_projectiles.clear()
            if enemy.alive:
                living.append(enemy)
            else:
                self.spawn_drops(enemy)
                xp = getattr(enemy, 'xp_reward', 0)
                if xp > 0:
                    self.award_xp(xp)
                    self.spawn_xp_number(enemy.rect.centerx, enemy.rect.top - 4, xp)
                enemy_type = getattr(enemy, '_type_key', None)
                completed = e.quest_system.notify("kill", target=enemy_type or "")
                self.award_quest_rewards(completed)
                self.spawn_death_particles(enemy.rect.center, ENEMY_COLOR, 10)
                _assets().play("enemy_death")
                e.events.post("entity_killed", entity=enemy, xp=xp)
        e.enemies[:] = living

    # ------------------------------------------------------------------
    # Player attack vs enemies
    # ------------------------------------------------------------------

    def update_combat(self, dt: float) -> None:
        e      = self._e
        hitbox = e.player.active_hitbox
        if not hitbox:
            return
        if not hitbox.sound_played:
            _assets().play("attack_swing")
            hitbox.sound_played = True
        hitbox.update(dt)
        for enemy in e.enemies:
            if (enemy not in hitbox.already_hit
                    and hitbox.rect.colliderect(enemy.rect)):
                enemy.take_damage(hitbox.damage)
                hitbox.already_hit.add(enemy)
                if hitbox.knockback > 0:
                    sign = 1 if enemy.rect.centerx >= e.player.rect.centerx else -1
                    enemy.velocity.x = hitbox.knockback * sign
                if hitbox.status_def:
                    apply_status(enemy, hitbox.status_def)
                _assets().play("enemy_hit")
                self.spawn_hit_particles(enemy.rect.center, ENEMY_HIT_COLOR, 6)
                self.spawn_damage_number(enemy.rect.centerx, enemy.rect.top - 4, hitbox.damage)
                e._hitstop_timer = HITSTOP_DURATION
        if hitbox.expired:
            e.player.active_hitbox = None

    # ------------------------------------------------------------------
    # Enemy attacks vs player
    # ------------------------------------------------------------------

    def update_enemy_attacks(self, dt: float) -> None:
        e = self._e
        for enemy in e.enemies:
            hitbox = enemy.active_hitbox
            if not hitbox:
                continue
            hitbox.update(dt)
            if (e.player not in hitbox.already_hit
                    and hitbox.rect.colliderect(e.player.rect)):
                e.player.take_damage(hitbox.damage)
                hitbox.already_hit.add(e.player)
                e.events.post("player_damaged", amount=hitbox.damage, source=enemy)
                _assets().play("player_hit")
                e.camera.shake(intensity=3, duration=0.12)
                self.spawn_hit_particles(e.player.rect.center, PLAYER_COLOR, 5)
                self.spawn_damage_number(
                    e.player.rect.centerx, e.player.rect.top - 4,
                    hitbox.damage, color=(255, 80, 80))
            if hitbox.expired:
                enemy.active_hitbox = None

    # ------------------------------------------------------------------
    # Projectiles
    # ------------------------------------------------------------------

    def update_projectiles(self, dt: float) -> None:
        e = self._e
        for proj in e.projectiles:
            proj.update(dt, e.platform_grid, e.wind)
            if not proj.alive:
                continue
            if proj.owner == "enemy":
                if proj.rect.colliderect(e.player.rect):
                    if proj.hit(e.player):
                        _assets().play("player_hit")
                        e.camera.shake(intensity=3, duration=0.12)
                        self.spawn_hit_particles(e.player.rect.center, PLAYER_COLOR, 5)
                        self.spawn_damage_number(
                            e.player.rect.centerx, e.player.rect.top - 4,
                            proj.damage, color=(255, 80, 80))
            else:
                for enemy in e.enemies:
                    if proj.rect.colliderect(enemy.rect):
                        if proj.hit(enemy):
                            self.spawn_hit_particles(enemy.rect.center, ENEMY_HIT_COLOR, 4)
                        if not proj.alive:
                            break
        e.projectiles[:] = [p for p in e.projectiles if p.alive]

    # ------------------------------------------------------------------
    # Special attacks (wave / area / aura)
    # ------------------------------------------------------------------

    def update_active_attacks(self, dt: float) -> None:
        e = self._e
        for attack in e.active_attacks:
            attack.update(dt, e.platform_grid, e.enemies, e.player)
        e.active_attacks[:] = [a for a in e.active_attacks if a.alive]

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------

    def update_particles(self, dt: float) -> None:
        e = self._e
        for p in e.particles:
            p.vel.y += p.gravity * dt
            p.pos   += p.vel * dt
            p.life  -= dt
        e.particles[:] = [p for p in e.particles if p.life > 0]

    def update_damage_numbers(self, dt: float) -> None:
        e = self._e
        for dn in e.damage_numbers:
            dn.y    -= 45.0 * dt
            dn.life -= dt
        e.damage_numbers[:] = [d for d in e.damage_numbers if d.life > 0]

    def spawn_hit_particles(self, pos, color, count: int = 6) -> None:
        e = self._e
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 190)
            e.particles.append(Particle(
                pos[0], pos[1],
                math.cos(angle) * speed,
                math.sin(angle) * speed - 50,
                color,
                random.uniform(0.14, 0.26),
                random.randint(2, 3),
                gravity=420.0,
            ))

    def spawn_death_particles(self, pos, color, count: int = 10) -> None:
        e = self._e
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 240)
            e.particles.append(Particle(
                pos[0], pos[1],
                math.cos(angle) * speed,
                math.sin(angle) * speed - 70,
                color,
                random.uniform(0.28, 0.55),
                random.randint(2, 5),
                gravity=480.0,
            ))

    def spawn_damage_number(self, x, y, value, color=(255, 240, 80)) -> None:
        e    = self._e
        surf = e._dmg_font.render(str(int(value)), True, color)
        e.damage_numbers.append(DamageNumber(x - surf.get_width() // 2, y, surf))

    def spawn_xp_number(self, x, y, amount: int) -> None:
        e    = self._e
        surf = e._dmg_font.render(f"+{amount} XP", True, (100, 140, 255))
        e.damage_numbers.append(DamageNumber(x - surf.get_width() // 2, y - 18, surf))

    # ------------------------------------------------------------------
    # Drops (with pity system)
    # ------------------------------------------------------------------

    def spawn_drops(self, enemy) -> None:
        e         = self._e
        item_defs = e.player.inventory.item_defs
        got_rare  = False
        for drop in enemy.loot:
            chance  = drop.get("chance", 1.0)
            is_rare = chance < 1.0
            forced  = is_rare and e._pity_count >= e._PITY_THRESHOLD
            if forced or random.random() < chance:
                if is_rare:
                    got_rare = True
                item_id  = drop["item_id"]
                quantity = drop.get("quantity", 1)
                color    = tuple(item_defs.get(item_id, {}).get("color", [200, 200, 200]))
                x = enemy.rect.centerx - ItemDrop.SIZE // 2
                y = enemy.rect.bottom  - ItemDrop.SIZE
                e.item_drops.append(ItemDrop(x, y, item_id, quantity, color))
        e._pity_count = 0 if got_rare else e._pity_count + 1

    # ------------------------------------------------------------------
    # XP and quest rewards
    # ------------------------------------------------------------------

    def award_xp(self, amount: int) -> None:
        e       = self._e
        old_pts = e.player.skill_points
        e.player.award_xp(amount)
        if e.player.skill_points > old_pts:
            n = e.player.skill_points
            s = "point" if n == 1 else "points"
            e.notifications.push(
                f"Level {e.player.level}! {n} skill {s} — press K",
                (220, 200, 80), 5.0, big=True)
            e.events.post("player_level_up",
                          level=e.player.level,
                          skill_points=e.player.skill_points)

    def award_quest_rewards(self, completed: list[str]) -> None:
        e = self._e
        for quest_id in completed:
            q = e.quest_system.get_def(quest_id)
            if not q:
                continue
            xp   = q.get("reward_xp",  0)
            gold = q.get("reward_gold", 0)
            if xp   > 0: self.award_xp(xp)
            if gold > 0: e.player.inventory.add("gold", gold)
            _assets().play("save_point")
            e.notifications.push(f"Quest Complete: {q['name']}!", (80, 255, 120), 4.0, big=True)
            parts = []
            if xp   > 0: parts.append(f"+{xp} XP")
            if gold > 0: parts.append(f"+{gold} gold")
            if parts:
                e.notifications.push("  ".join(parts), (200, 230, 200), 3.5)
