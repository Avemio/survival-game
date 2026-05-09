"""
systems/effects.py
Status effect system — poison, burn, stun, freeze, slow.
StatusEffect instances are stored on entities and ticked every frame.
Any attack type can carry a status_def dict to apply an effect on hit.

status_def format (from abilities.json):
  {"type": "poison", "duration": 5.0, "damage_per_second": 12}
  {"type": "stun",   "duration": 1.5}
  {"type": "slow",   "duration": 3.0, "slow_factor": 0.4}
"""


class StatusEffect:
    """A timed effect on an entity — damage over time, movement penalty, or state lock."""

    def __init__(self, effect_def: dict):
        self.type     = effect_def["type"]
        self.duration = float(effect_def["duration"])
        self.timer    = self.duration
        self.dps      = float(effect_def.get("damage_per_second", 0))
        self.slow_factor = float(effect_def.get("slow_factor", 1.0))
        self._dmg_accum  = 0.0   # fractional damage accumulator for DoT

    @property
    def active(self) -> bool:
        return self.timer > 0

    def tick(self, dt: float, target) -> None:
        """Advance timer and apply this frame's effect to target."""
        self.timer -= dt

        if self.type in ("poison", "burn") and self.dps > 0:
            self._dmg_accum += self.dps * dt
            if self._dmg_accum >= 1.0:
                dmg = int(self._dmg_accum)
                target.take_damage(dmg)
                self._dmg_accum -= dmg

        elif self.type in ("stun", "freeze"):
            target.stunned = True   # re-asserted every frame while active


def apply_status(entity, effect_def: dict) -> None:
    """
    Apply or refresh a status effect on an entity.
    Refreshes duration if the same effect type is already active.
    entity must have a `status_effects` list attribute.
    """
    if not hasattr(entity, "status_effects"):
        return
    existing = next((e for e in entity.status_effects if e.type == effect_def["type"]), None)
    if existing:
        existing.timer = max(existing.timer, float(effect_def["duration"]))
    else:
        entity.status_effects.append(StatusEffect(effect_def))


def tick_all(entity, dt: float) -> None:
    """
    Tick all active status effects on an entity and remove expired ones.
    Resets stunned and slow_factor before ticking so effects re-assert each frame.
    Call this at the start of entity.update().
    """
    if not hasattr(entity, "status_effects"):
        return

    entity.stunned     = False
    entity.slow_factor = 1.0

    # Tick first so the last frame of each effect is fully applied
    for effect in entity.status_effects:
        effect.tick(dt, entity)
    # Then remove expired effects in-place (keeps the same list object)
    entity.status_effects[:] = [e for e in entity.status_effects if e.active]

    # Derive slow_factor from still-active effects
    for effect in entity.status_effects:
        if effect.type == "slow":
            entity.slow_factor = min(entity.slow_factor, effect.slow_factor)
        elif effect.type == "freeze":
            entity.slow_factor = 0.0
