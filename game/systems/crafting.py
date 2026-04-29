"""
systems/crafting.py
Owns recipe definitions and the logic for checking / performing a craft.
Does NOT own: inventory storage (Inventory owns that), UI (ui/menus.py).

Recipe format (data/recipes.json):
  {
    "plank": {
      "name":        "Plank",
      "result":      "plank",
      "count":       2,
      "ingredients": { "wood": 3 }
    },
    ...
  }
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


class CraftingSystem:
    def __init__(self):
        self._recipes = self._load_recipes()

    @staticmethod
    def _load_recipes():
        path = _DATA_DIR / "recipes.json"
        with open(path) as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def recipes(self):
        """Return the full recipe dict — ordered as in recipes.json."""
        return self._recipes

    def can_craft(self, recipe_id, inventory):
        """True if inventory contains all required ingredients."""
        recipe = self._recipes.get(recipe_id)
        if not recipe:
            return False
        for item_id, qty_needed in recipe["ingredients"].items():
            if inventory.count(item_id) < qty_needed:
                return False
        return True

    def craft(self, recipe_id, inventory):
        """
        Consume ingredients and add the result to inventory.
        Returns True on success, False if ingredients are missing or
        the result item can't be added (full inventory).
        """
        if not self.can_craft(recipe_id, inventory):
            return False

        recipe = self._recipes[recipe_id]

        # Consume all ingredients before adding the result so a recipe
        # that both needs and produces the same item works correctly.
        for item_id, qty_needed in recipe["ingredients"].items():
            self._consume(inventory, item_id, qty_needed)

        leftover = inventory.add(recipe["result"], recipe.get("count", 1))

        # If the result didn't fit, refund ingredients (inventory was full)
        if leftover > 0:
            for item_id, qty_needed in recipe["ingredients"].items():
                inventory.add(item_id, qty_needed)
            return False

        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _consume(inventory, item_id, quantity):
        """Remove `quantity` of item_id, spanning multiple slots if needed."""
        remaining = quantity
        for i, slot in enumerate(inventory.slots):
            if slot and slot.item_id == item_id:
                take = min(remaining, slot.quantity)
                slot.quantity -= take
                if slot.quantity == 0:
                    inventory.slots[i] = None
                remaining -= take
                if remaining == 0:
                    return
