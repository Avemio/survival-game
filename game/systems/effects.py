"""
systems/effects.py
Status effect system — poison, burn, stun, freeze, slow.
StatusEffect instances are stored on entities and ticked every frame.

status_def format (from abilities.json):
  {"type": "poison", "duration": 5.0, "damage_per_second": 12}
  {"type": "stun",   "duration": 1.5}
  {"type": "slow",   "duration": 3.0, "slow_factor": 0.4}

Performance notes:
- tick_all() avoids hasattr checks (caller guarantees the entity has status_effects)
- List rebuild is gated behind a dirty check (no allocation when nothing expired)
- Tick-dispatch is table-driven; new status types are added to _TICKERS, not to tick()
"""


# ---------------------------------------------------------------------------
# Tick dispatch table — add new effect types here, no edits to tick() needed
# ---------------------------------------------------------------------------

def _tick_dot(effect, dt: float, target) -> None:
    effect._dmg_accum += effect.dps * dt
    if effect._dmg_accum >= 1.0:
        dmg = int(effect._dmg_accum)
        target.take_damage(dmg)
        effect._dmg_accum -= dmg

def _tick_stun(effect, dt: float, target) -> None:
    target.stunned = True   # re-asserted every frame while active

_TICKERS: dict = {
    "poison": _tick_dot,
    "burn":   _tick_dot,
    "stun":   _tick_stun,
    "freeze": _tick_stun,
    # "slow" has no per-frame action beyond slow_factor derivation (done in tick_all)
}


# ---------------------------------------------------------------------------
# StatusEffect
# ---------------------------------------------------------------------------

class StatusEffect:
    """A timed effect on an entity — damage over time, movement penalty, or state lock."""

    def __init__(self, effect_def: dict):
        self.type        = effect_def["type"]
        self.duration    = float(effect_def["duration"])
        self.timer       = self.duration
        self.dps         = float(effect_def.get("damage_per_second", 0))
        self.slow_factor = float(effect_def.get("slow_factor", 1.0))
        self._dmg_accum  = 0.0

    @property
    def active(self) -> bool:
        return self.timer > 0

    def tick(self, dt: float, target) -> None:
        self.timer -= dt
        ticker = _TICKERS.get(self.type)
        if ticker:
            ticker(self, dt, target)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_status(entity, effect_def: dict) -> None:
    """
    Apply or refresh a status effect on an entity.
    Refreshes duration if the same type is already active.
    entity must have a `status_effects: list` attribute.
    """
    existing = next((e for e in entity.status_effects if e.type == effect_def["type"]), None)
    if existing:
        existing.timer = max(existing.timer, float(effect_def["duration"]))
    else:
        entity.status_effects.append(StatusEffect(effect_def))


def tick_all(entity, dt: float) -> None:
    """
    Tick all active status effects on an entity and remove expired ones.
    Resets stunned and slow_factor before ticking so effects re-assert each frame.
    Caller guarantees entity has status_effects, stunned, and slow_factor attributes.
    """
    if not entity.status_effects:
        return

    entity.stunned     = False
    entity.slow_factor = 1.0

    # Tick first so the last frame of each effect is fully applied
    for effect in entity.status_effects:
        effect.tick(dt, entity)

    # Gate the rebuild: only allocate if something actually expired
    if any(not e.active for e in entity.status_effects):
        entity.status_effects[:] = [e for e in entity.status_effects if e.active]

    # Derive slow_factor from still-active effects
    for effect in entity.status_effects:
        if effect.type == "slow":
            entity.slow_factor = min(entity.slow_factor, effect.slow_factor)
        elif effect.type == "freeze":
            entity.slow_factor = 0.0
