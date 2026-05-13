"""
systems/achievements.py
Tracks player achievements and fires notifications on unlock.
Subscribes to EventBus using persistent subscriptions so it survives zone transitions.
Does NOT own: UI, save I/O, or player state — reads event data only.

Tracked stats:
  kills          — cumulative enemy kills
  gold_collected — total gold picked up from drops
  max_level      — highest player level ever reached
  zones_visited  — count of unique zone IDs entered
  skills_spent   — total skill points spent
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "achievements.json"


class AchievementSystem:
    def __init__(self, notifications):
        self._notifications = notifications

        with open(_DATA_PATH) as f:
            self._defs: dict = json.load(f)

        self._counters:      dict[str, int | float] = {}
        self._visited_zones: set[str]               = set()
        self._unlocked:      set[str]               = set()

    # ------------------------------------------------------------------
    # EventBus wiring — call once after both bus and self are created
    # ------------------------------------------------------------------

    def subscribe_to(self, event_bus) -> None:
        event_bus.subscribe("entity_killed",   self._on_entity_killed)
        event_bus.subscribe("item_collected",  self._on_item_collected)
        event_bus.subscribe("player_level_up", self._on_player_level_up)
        event_bus.subscribe("zone_entered",    self._on_zone_entered)
        event_bus.subscribe("skill_spent",     self._on_skill_spent)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_entity_killed(self, **_):
        self._increment("kills", 1)

    def _on_item_collected(self, item_id, quantity, **_):
        if item_id == "gold":
            self._increment("gold_collected", quantity)

    def _on_player_level_up(self, level, **_):
        current = self._counters.get("max_level", 0)
        if level > current:
            self._counters["max_level"] = level
            self._check_all()

    def _on_zone_entered(self, zone_id, **_):
        if zone_id not in self._visited_zones:
            self._visited_zones.add(zone_id)
            self._counters["zones_visited"] = len(self._visited_zones)
            self._check_all()

    def _on_skill_spent(self, **_):
        self._increment("skills_spent", 1)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _increment(self, stat: str, amount) -> None:
        self._counters[stat] = self._counters.get(stat, 0) + amount
        self._check_all()

    def _check_all(self) -> None:
        for ach_id, ach in self._defs.items():
            if ach_id in self._unlocked:
                continue
            current = self._counters.get(ach["stat"], 0)
            if current >= ach["goal"]:
                self._unlock(ach_id, ach)

    def _unlock(self, ach_id: str, ach: dict) -> None:
        self._unlocked.add(ach_id)
        self._notifications.push(
            f"★ Achievement: {ach['name']}",
            (255, 215, 0), 6.0, big=True,
        )
        self._notifications.push(ach["desc"], (200, 200, 180), 5.0)

    # ------------------------------------------------------------------
    # Save / load
    # ------------------------------------------------------------------

    def serialize(self) -> dict:
        return {
            "counters":      self._counters,
            "visited_zones": sorted(self._visited_zones),
            "unlocked":      sorted(self._unlocked),
        }

    def load(self, data: dict) -> None:
        self._counters      = dict(data.get("counters", {}))
        self._visited_zones = set(data.get("visited_zones", []))
        self._unlocked      = set(data.get("unlocked", []))
        # Keep zones_visited counter in sync after load
        if self._visited_zones:
            self._counters["zones_visited"] = len(self._visited_zones)
