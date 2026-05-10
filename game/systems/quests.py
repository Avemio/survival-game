"""
systems/quests.py
Quest system — loads quest definitions from data/quests.json and tracks
active/completed quest state for the current session.

Quest types:
  kill       — kill N enemies of a specific type (by enemies.json key)
  kill_any   — kill N enemies of any type
  collect    — have N of a specific item_id picked up total (not in inventory)
  reach_zone — enter a specific zone_id

Engine notifies the quest system on relevant events. The system returns a list
of newly completed quest IDs so the engine can award rewards.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


class QuestSystem:
    def __init__(self):
        path = _DATA_DIR / "quests.json"
        with open(path) as f:
            self._defs: dict = json.load(f)
        self._active: dict = {}   # quest_id -> {progress: int}
        self._done:   set  = set()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def all_defs(self) -> dict:
        return self._defs

    def get_def(self, quest_id: str) -> dict | None:
        return self._defs.get(quest_id)

    def is_active(self, quest_id: str) -> bool:
        return quest_id in self._active

    def is_done(self, quest_id: str) -> bool:
        return quest_id in self._done

    def progress(self, quest_id: str) -> int:
        return self._active.get(quest_id, {}).get("progress", 0)

    def get_active_display(self) -> list[dict]:
        """Return list of dicts for the quest log UI."""
        result = []
        for qid, state in self._active.items():
            q = self._defs.get(qid, {})
            result.append({
                "id":          qid,
                "name":        q.get("name", qid),
                "description": q.get("description", ""),
                "progress":    state["progress"],
                "count":       q.get("count", 1),
            })
        return result

    def get_done_names(self) -> list[str]:
        return [self._defs.get(qid, {}).get("name", qid) for qid in sorted(self._done)]

    # ------------------------------------------------------------------
    # State changes
    # ------------------------------------------------------------------

    def start(self, quest_id: str) -> bool:
        """Begin tracking a quest. Returns False if already active or done."""
        if quest_id not in self._defs or quest_id in self._done or quest_id in self._active:
            return False
        self._active[quest_id] = {"progress": 0}
        return True

    def notify(self, event_type: str, **kwargs) -> list[str]:
        """
        Advance quest progress for matching active quests.
        Returns a list of quest IDs that just completed.

        Supported event_type values and kwargs:
          "kill"      target=enemy_type_key  (e.g. "basic")
          "kill_any"  (no extra kwargs)
          "collect"   target=item_id         (e.g. "herb")
          "reach_zone" target=zone_id
        """
        completed = []
        for quest_id, state in list(self._active.items()):
            q = self._defs[quest_id]
            q_type = q.get("type")

            if q_type == "kill" and event_type == "kill":
                if q.get("target") != kwargs.get("target"):
                    continue
            elif q_type == "kill_any" and event_type in ("kill", "kill_any"):
                pass   # any kill counts
            elif q_type == event_type:
                if "target" in q and q["target"] != kwargs.get("target"):
                    continue
            else:
                continue

            state["progress"] += kwargs.get("amount", 1)
            if state["progress"] >= q.get("count", 1):
                self._active.pop(quest_id)
                self._done.add(quest_id)
                completed.append(quest_id)

        return completed

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def serialize(self) -> dict:
        return {
            "active": {k: dict(v) for k, v in self._active.items()},
            "done":   list(self._done),
        }

    def load(self, data: dict):
        self._active = {k: dict(v) for k, v in data.get("active", {}).items()}
        self._done   = set(data.get("done", []))
