"""
systems/inventory.py
Owns the player's item storage — a fixed list of slots, each holding an
InventoryItem (item_id + quantity) or None (empty).
Also loads and owns item definitions from data/items.json.

Does NOT own: item world objects (entities/item_drop.py, M7B), crafting (M7C),
              rendering (ui/hud.py reads inventory but doesn't modify it).
"""

import json
from pathlib import Path

# data/ is three levels up from game/systems/
_DATA_DIR = Path(__file__).parent.parent.parent / "data"


class InventoryItem:
    """One stack in an inventory slot — an item type and a quantity."""
    def __init__(self, item_id, quantity=1):
        self.item_id  = item_id
        self.quantity = quantity


class Inventory:
    def __init__(self, size):
        """
        size — number of slots (equals HOTBAR_SLOTS for now; grows when
               the full inventory screen is added).
        """
        self.slots     = [None] * size
        self.item_defs = self._load_item_defs()

    # ------------------------------------------------------------------
    # Item definitions
    # ------------------------------------------------------------------

    @staticmethod
    def _load_item_defs():
        path = _DATA_DIR / "items.json"
        with open(path) as f:
            return json.load(f)

    def get_def(self, item_id):
        """Return the item definition dict, or {} if unknown."""
        return self.item_defs.get(item_id, {})

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, item_id, quantity=1):
        """
        Add items to the inventory. Returns any leftover quantity that
        didn't fit (0 means everything was added).
        Stackable items fill existing stacks first, then open slots.
        """
        defn      = self.get_def(item_id)
        stackable = defn.get("stackable", False)
        max_stack = defn.get("max_stack", 1) if stackable else 1
        remaining = quantity

        # Pass 1 — top up existing stacks of the same item
        if stackable:
            for slot in self.slots:
                if slot and slot.item_id == item_id and slot.quantity < max_stack:
                    space    = max_stack - slot.quantity
                    take     = min(remaining, space)
                    slot.quantity += take
                    remaining     -= take
                    if remaining == 0:
                        return 0

        # Pass 2 — fill empty slots
        for i, slot in enumerate(self.slots):
            if slot is None and remaining > 0:
                take          = min(remaining, max_stack)
                self.slots[i] = InventoryItem(item_id, take)
                remaining     -= take
                if remaining == 0:
                    return 0

        return remaining   # leftover if inventory was full

    def remove(self, slot_index, quantity=1):
        """
        Remove quantity from the given slot.
        Clears the slot if it reaches 0. Does nothing if slot is empty.
        """
        slot = self.slots[slot_index]
        if not slot:
            return
        slot.quantity -= quantity
        if slot.quantity <= 0:
            self.slots[slot_index] = None

    # ------------------------------------------------------------------
    # Serialization — used by saving.py
    # ------------------------------------------------------------------

    def serialize(self):
        """Return a JSON-serializable list representing the current slots."""
        return [
            {"item_id": s.item_id, "quantity": s.quantity} if s else None
            for s in self.slots
        ]

    def load_slots(self, slots_data):
        """
        Restore slot contents from a list previously produced by serialize().
        Called by engine after loading a save file.
        """
        for i, entry in enumerate(slots_data):
            if i >= len(self.slots):
                break
            self.slots[i] = InventoryItem(entry["item_id"], entry["quantity"]) if entry else None
