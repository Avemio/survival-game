"""
systems/abilities.py
Ability execution system — reads ability definitions from data/abilities.json
and dispatches to the correct attack type when an ability fires.

Ability types handled here:
  melee      — extended AttackHitbox with knockback and status
  projectile — extended Projectile with status, pierce, color
  wave       — WaveAttack (traveling shockwave)
  area       — AreaAttack (instant burst)
  aura       — AuraAttack (lingering cloud)

Engine calls ability_system.execute(ability_id, owner, engine) at the point
of input. The engine owns the active_attacks and projectiles lists.
"""

import json
import math
import pygame
from pathlib import Path

from game.systems.combat        import AttackHitbox
from game.entities.projectile   import Projectile
from game.systems.active_attacks import WaveAttack, AreaAttack, AuraAttack

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


class AbilitySystem:
    def __init__(self):
        with open(_DATA_DIR / "abilities.json") as f:
            self.defs: dict = json.load(f)
        self._spawners: dict = self._build_spawner_registry()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, ability_id: str) -> dict | None:
        return self.defs.get(ability_id)

    def can_use(self, ability_id: str, owner) -> bool:
        ab = self.defs.get(ability_id)
        if not ab:
            return False
        if hasattr(owner, "mana") and ab.get("mana_cost", 0) > owner.mana:
            return False
        req = ab.get("requires_item")
        if req and hasattr(owner, "inventory") and owner.inventory.count(req) == 0:
            return False
        return True

    # ------------------------------------------------------------------
    # Execution — called by engine
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Ability type dispatch — add new types here without touching execute()
    # ------------------------------------------------------------------

    def _build_spawner_registry(self) -> dict:
        return {
            "melee":      self._spawn_melee,
            "projectile": self._spawn_projectile,
            "wave":       self._spawn_wave,
            "area":       self._spawn_area,
            "aura":       self._spawn_aura,
        }

    def register_type(self, type_name: str, spawner) -> None:
        """Register a new ability type at runtime (e.g. from a mod or expansion)."""
        self._spawners[type_name] = spawner

    def execute(self, ability_id: str, owner, engine) -> bool:
        """
        Fire ability_id from owner.  Returns True if it fired.
        engine must expose:
          engine.active_attacks (list)
          engine.projectiles    (list)
          engine.enemies        (list)
          engine.player         (Player)
          engine.wind           (float)
        """
        ab = self.defs.get(ability_id)
        if not ab or not self.can_use(ability_id, owner):
            return False

        mana_cost = ab.get("mana_cost", 0)
        if mana_cost > 0 and hasattr(owner, "mana"):
            owner.mana = max(0, owner.mana - mana_cost)

        consume = ab.get("consumes_item")
        if consume and hasattr(owner, "inventory"):
            owner.inventory.consume(consume, 1)

        ab_type = ab.get("type", "melee")
        spawner = self._spawners.get(ab_type)
        if spawner:
            spawner(owner, ab, engine)
        else:
            import logging
            logging.warning("AbilitySystem: unknown ability type %r for %r", ab_type, ability_id)

        return True

    # ------------------------------------------------------------------
    # Spawners
    # ------------------------------------------------------------------

    def _spawn_melee(self, owner, ab: dict, engine) -> None:
        width    = int(ab.get("width",  55))
        height   = int(ab.get("height", 64))
        damage   = int(ab.get("damage", 25))
        knockback = float(ab.get("knockback", 0))
        status   = ab.get("status_effect")
        hitbox   = AttackHitbox(owner, damage=damage, width=width, height=height,
                                knockback=knockback, status_def=status)
        owner.active_hitbox = hitbox

    def _spawn_projectile(self, owner, ab: dict, engine) -> None:
        angle_rad = math.radians(getattr(owner, "aim_angle", 0))
        speed     = float(ab.get("speed", 500))
        vx = math.cos(angle_rad) * speed * owner.facing
        vy = -math.sin(angle_rad) * speed

        w = int(ab.get("width",  14))
        h = int(ab.get("height",  4))
        x = owner.rect.centerx - w // 2
        y = owner.rect.centery - h // 2

        proj = Projectile(
            x, y, vx, vy,
            damage       = int(ab.get("damage", 20)),
            gravity_factor = float(ab.get("gravity", 550)) / 550.0,
            wind_affected  = bool(ab.get("wind_affected", False)),
            width          = w,
            height         = h,
            pierce         = bool(ab.get("pierce", False)),
            color          = tuple(ab.get("color", [220, 200, 120])),
            status_def     = ab.get("status_effect"),
        )
        engine.projectiles.append(proj)

    def _spawn_wave(self, owner, ab: dict, engine) -> None:
        wave = WaveAttack(owner, ab)
        engine.active_attacks.append(wave)

    def _spawn_area(self, owner, ab: dict, engine) -> None:
        cx = float(owner.rect.centerx)
        cy = float(owner.rect.centery)
        area = AreaAttack(owner, ab, cx, cy, engine.enemies, engine.player)
        engine.active_attacks.append(area)

    def _spawn_aura(self, owner, ab: dict, engine) -> None:
        aura = AuraAttack(owner, ab)
        engine.active_attacks.append(aura)
