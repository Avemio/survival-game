"""
systems/events.py
Lightweight publish-subscribe event bus with two subscription tiers.

  subscribe()      — persistent: survives zone transitions (use for achievements, stats, etc.)
  subscribe_zone() — zone-scoped: cleared on every zone transition (use for zone-local logic)

Engine posts events; any system can subscribe without importing the engine.
Does NOT own: game state. Just routes events to registered callbacks.

Usage:
    bus.subscribe("entity_killed", my_callback)          # persistent
    bus.subscribe_zone("zone_fx", my_zone_callback)      # cleared on next zone load
    bus.post("entity_killed", entity=enemy, xp=30)
    bus.unsubscribe("entity_killed", my_callback)
    bus.clear_zone_listeners()                           # call on zone transitions
"""

from collections import defaultdict
from itertools   import chain as _chain


class EventBus:
    def __init__(self):
        self._persistent:  dict[str, list] = defaultdict(list)
        self._zone_local:  dict[str, list] = defaultdict(list)

    def subscribe(self, event_type: str, callback) -> None:
        """Persistent subscription — survives zone transitions."""
        self._persistent[event_type].append(callback)

    def subscribe_zone(self, event_type: str, callback) -> None:
        """Zone-scoped subscription — cleared when transitioning zones."""
        self._zone_local[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback) -> None:
        for bucket in (self._persistent, self._zone_local):
            listeners = bucket.get(event_type, [])
            try:
                listeners.remove(callback)
                return
            except ValueError:
                pass

    def post(self, event_type: str, **data) -> None:
        for cb in _chain(self._persistent.get(event_type, ()),
                         self._zone_local.get(event_type, ())):
            cb(**data)

    def clear_zone_listeners(self) -> None:
        """Clear zone-scoped subscriptions — call at the start of every zone transition."""
        self._zone_local.clear()
