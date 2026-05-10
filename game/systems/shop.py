"""
systems/shop.py
Shop system — loads shop definitions from data/shops.json and handles
buy/sell transactions against the player's inventory + gold balance.
Owns: shop catalog, transaction logic, runtime stock tracking.
Does NOT own: UI (ui/shop_menu.py), triggering (engine/NPC interaction).

Shop JSON format:
  {
    "general_store": {
      "name":      "General Store",
      "buy_rate":  0.5,           -- fraction of buy price paid when player sells
      "inventory": [
        {"item_id": "health_potion", "price": 20, "stock": -1}  -- -1 = unlimited
      ]
    }
  }
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


class ShopSystem:
    def __init__(self):
        path = _DATA_DIR / "shops.json"
        with open(path) as f:
            self._defs: dict = json.load(f)

    def get(self, shop_id: str) -> dict | None:
        return self._defs.get(shop_id)

    def all_ids(self) -> list[str]:
        return list(self._defs.keys())

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def buy(self, shop_id: str, item_id: str, inventory) -> str:
        """
        Player buys one of item_id from the shop.
        Returns: "ok" | "cant_afford" | "no_space" | "out_of_stock" | "not_found"
        """
        shop  = self._defs.get(shop_id)
        if not shop:
            return "not_found"
        entry = next((e for e in shop["inventory"] if e["item_id"] == item_id), None)
        if not entry:
            return "not_found"

        stock = entry.get("stock", -1)
        if stock == 0:
            return "out_of_stock"

        price = entry["price"]
        if inventory.count("gold") < price:
            return "cant_afford"

        leftover = inventory.add(item_id, 1)
        if leftover > 0:
            return "no_space"

        inventory.consume("gold", price)
        if stock > 0:
            entry["stock"] -= 1

        return "ok"

    def sell(self, shop_id: str, item_id: str, inventory) -> str:
        """
        Player sells one of item_id to the shop.
        Returns: "ok" | "no_items" | "not_sellable"
        """
        shop = self._defs.get(shop_id)
        if not shop:
            return "not_found"
        if inventory.count(item_id) < 1:
            return "no_items"

        gold_earned = self.sell_price(shop_id, item_id, inventory.item_defs)
        if gold_earned <= 0:
            return "not_sellable"

        inventory.consume(item_id, 1)
        inventory.add("gold", gold_earned)
        return "ok"

    def sell_price(self, shop_id: str, item_id: str, item_defs: dict) -> int:
        """
        Gold earned when the player sells one of item_id.
        Uses the shop's buy_rate against the item's sell_value in items.json.
        Returns 0 if the item has no sell_value (not sellable).
        """
        shop = self._defs.get(shop_id)
        buy_rate = shop.get("buy_rate", 0.5) if shop else 0.5
        item_def = item_defs.get(item_id, {})
        base = item_def.get("sell_value", 0)
        return max(0, int(base * buy_rate))

    def buy_price(self, shop_id: str, item_id: str) -> int | None:
        """Return the buy price for item_id in this shop, or None if not sold."""
        shop = self._defs.get(shop_id)
        if not shop:
            return None
        entry = next((e for e in shop["inventory"] if e["item_id"] == item_id), None)
        return entry["price"] if entry else None
