"""
systems/inventory.py
Owns the player's item storage — a fixed list of slots, each holding an
InventoryItem (item_id + quantity) or None (empty).

Performance: count() is O(1) via a parallel _totals dict kept in sync with
every mutation (add/remove/consume/load_slots).

Item definitions are a module-level singleton — parsed once, shared across
all Inventory instances (player, chests, shops).
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Module-level singleton — loaded once, shared by every Inventory instance
_ITEM_DEFS: dict = {}


def _ensure_defs() -> dict:
    global _ITEM_DEFS
    if not _ITEM_DEFS:
        with open(_DATA_DIR / "items.json") as f:
            _ITEM_DEFS = json.load(f)
    return _ITEM_DEFS


class InventoryItem:
    """One stack in an inventory slot — an item type and a quantity."""
    __slots__ = ("item_id", "quantity")

    def __init__(self, item_id, quantity=1):
        self.item_id  = item_id
        self.quantity = quantity


class Inventory:
    def __init__(self, size):
        self.slots:     list = [None] * size
        self._totals:   dict = {}          # O(1) count cache — kept in sync
        self.item_defs: dict = _ensure_defs()

    # ------------------------------------------------------------------
    # Item definitions
    # ------------------------------------------------------------------

    def get_def(self, item_id: str) -> dict:
        return self.item_defs.get(item_id, {})

    # ------------------------------------------------------------------
    # O(1) count
    # ------------------------------------------------------------------

    def count(self, item_id: str) -> int:
        """Total quantity of item_id across all slots. O(1)."""
        return self._totals.get(item_id, 0)

    # ------------------------------------------------------------------
    # Mutation — every method keeps _totals in sync
    # ------------------------------------------------------------------

    def add(self, item_id: str, quantity: int = 1) -> int:
        """
        Add items to the inventory. Returns leftover that didn't fit (0 = all added).
        Stackable items fill existing stacks first, then open slots.
        """
        defn      = self.get_def(item_id)
        stackable = defn.get("stackable", False)
        max_stack = defn.get("max_stack", 1) if stackable else 1
        remaining = quantity

        if stackable:
            for slot in self.slots:
                if slot and slot.item_id == item_id and slot.quantity < max_stack:
                    space         = max_stack - slot.quantity
                    take          = min(remaining, space)
                    slot.quantity += take
                    remaining     -= take
                    if remaining == 0:
                        self._totals[item_id] = self._totals.get(item_id, 0) + quantity
                        return 0

        for i, slot in enumerate(self.slots):
            if slot is None and remaining > 0:
                take          = min(remaining, max_stack)
                self.slots[i] = InventoryItem(item_id, take)
                remaining     -= take
                if remaining == 0:
                    break

        added = quantity - remaining
        if added > 0:
            self._totals[item_id] = self._totals.get(item_id, 0) + added
        return remaining

    def remove(self, slot_index: int, quantity: int = 1):
        """Remove quantity from a specific slot. Clears slot if it reaches 0."""
        slot = self.slots[slot_index]
        if not slot:
            return
        actual = min(quantity, slot.quantity)
        slot.quantity -= actual
        if slot.quantity <= 0:
            self.slots[slot_index] = None
        self._totals[slot.item_id] = max(0, self._totals.get(slot.item_id, 0) - actual)

    def consume(self, item_id: str, quantity: int = 1):
        """Remove quantity of item_id, consuming across multiple slots."""
        remaining = quantity
        for i, slot in enumerate(self.slots):
            if slot and slot.item_id == item_id:
                take           = min(remaining, slot.quantity)
                slot.quantity -= take
                remaining     -= take
                if slot.quantity <= 0:
                    self.slots[i] = None
                if remaining == 0:
                    break
        consumed = quantity - remaining
        if consumed > 0:
            self._totals[item_id] = max(0, self._totals.get(item_id, 0) - consumed)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize(self) -> list:
        return [
            {"item_id": s.item_id, "quantity": s.quantity} if s else None
            for s in self.slots
        ]

    def load_slots(self, slots_data: list):
        """Restore from a list produced by serialize(). Rebuilds _totals from scratch."""
        self.slots[:] = [None] * len(self.slots)
        self._totals.clear()
        for i, entry in enumerate(slots_data):
            if i >= len(self.slots):
                break
            if entry and "item_id" in entry and "quantity" in entry:
                iid = entry["item_id"]
                qty = entry["quantity"]
                self.slots[i] = InventoryItem(iid, qty)
                self._totals[iid] = self._totals.get(iid, 0) + qty
