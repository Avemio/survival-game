"""
ui/shop_menu.py
Shop overlay — opened when the player presses E near a shopkeeper NPC.
Pause pattern: world update halts while open (same as CraftingMenu).

Controls:
  ↑ / ↓      Navigate items
  Tab         Toggle Buy ↔ Sell mode
  Enter       Buy or sell one item
  Esc         Close
"""

import pygame
from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CRAFT_PANEL_BG, CRAFT_PANEL_BORDER,
    CRAFT_TITLE_COLOR, CRAFT_FOOTER_COLOR,
    CRAFT_SELECTED_BG, CRAFT_INGREDIENT_OK, CRAFT_INGREDIENT_MISS,
    WHITE,
)
from game.systems.assets import get as _assets

_PANEL_W = 520
_PANEL_H = 500
_PAD     = 18
_ROW_H   = 30
_GOLD_COLOR  = (255, 215, 50)
_DIM_COLOR   = (90, 90, 100)
_TAB_ON_BG   = (50, 50, 70)
_TAB_OFF_BG  = (30, 30, 42)


class ShopMenu:
    def __init__(self, player, shop_system):
        self.player        = player
        self._shop         = shop_system
        self.open          = False
        self._shop_id      = None
        self._shop_name    = ""
        self._mode         = "buy"   # "buy" or "sell"
        self._cursor       = 0
        self._feedback     = ""
        self._fb_timer     = 0.0
        self._fb_ok        = True    # True=green, False=red

        self._px = (SCREEN_WIDTH  - _PANEL_W) // 2
        self._py = (SCREEN_HEIGHT - _PANEL_H) // 2

        # Fonts — created once, never in draw()
        self._font_title = pygame.font.SysFont(None, 26)
        self._font_tab   = pygame.font.SysFont(None, 21)
        self._font_item  = pygame.font.SysFont(None, 20)
        self._font_hint  = pygame.font.SysFont(None, 17)
        self._font_gold  = pygame.font.SysFont(None, 22)
        self._font_fb    = pygame.font.SysFont(None, 20)

        # Pre-rendered static surfaces
        self._hint_buy  = self._font_hint.render(
            "↑↓ Navigate     Enter  Buy     Tab  Switch to Sell     Esc  Close",
            True, CRAFT_FOOTER_COLOR)
        self._hint_sell = self._font_hint.render(
            "↑↓ Navigate     Enter  Sell 1  Tab  Switch to Buy      Esc  Close",
            True, CRAFT_FOOTER_COLOR)

        # Dim overlay
        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 150))

        # Pre-rendered static tab and cursor surfaces
        self._tab_buy_on  = self._font_tab.render("BUY",  True, CRAFT_TITLE_COLOR)
        self._tab_buy_off = self._font_tab.render("BUY",  True, _DIM_COLOR)
        self._tab_sell_on = self._font_tab.render("SELL", True, CRAFT_TITLE_COLOR)
        self._tab_sell_off= self._font_tab.render("SELL", True, _DIM_COLOR)
        self._cursor_surf = self._font_item.render("▶", True, CRAFT_TITLE_COLOR)

        # Dynamic state rebuilt on open/mode-switch/transaction
        self._rows: list[dict]         = []   # row data dicts
        self._name_surfs: list         = []   # pre-rendered item name surfaces
        self._detail_surfs: list       = []   # pre-rendered price/stock/sv/qty surfs
        self._gold_cache: tuple        = (-1, None)
        self._title_surf               = None
        self._fb_surf                  = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, shop_id: str, shop_name: str):
        self.open       = True
        self._shop_id   = shop_id
        self._shop_name = shop_name
        self._mode      = "buy"
        self._cursor    = 0
        self._feedback  = ""
        self._fb_timer  = 0.0
        self._title_surf = self._font_title.render(
            shop_name, True, CRAFT_TITLE_COLOR)
        self._rebuild()

    def close(self):
        self.open = False

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.close()

        elif event.key == pygame.K_TAB:
            self._mode   = "sell" if self._mode == "buy" else "buy"
            self._cursor = 0
            self._rebuild()

        elif event.key in (pygame.K_UP, pygame.K_w):
            if self._rows:
                self._cursor = (self._cursor - 1) % len(self._rows)
            _assets().play("ui_select")

        elif event.key in (pygame.K_DOWN, pygame.K_s):
            if self._rows:
                self._cursor = (self._cursor + 1) % len(self._rows)
            _assets().play("ui_select")

        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self._mode == "buy":
                self._do_buy()
            else:
                self._do_sell()

    def update(self, dt):
        if self._fb_timer > 0:
            self._fb_timer -= dt

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def _do_buy(self):
        if not self._rows:
            return
        row    = self._rows[self._cursor]
        result = self._shop.buy(self._shop_id, row["item_id"], self.player.inventory)
        if result == "ok":
            _assets().play("item_pickup")
            self._set_feedback(f"Bought {row['name']}  (−{row['price']}g)", ok=True)
            self._rebuild()
        elif result == "cant_afford":
            _assets().play("craft_fail")
            self._set_feedback(f"Not enough gold  (need {row['price']}g)", ok=False)
        elif result == "no_space":
            _assets().play("craft_fail")
            self._set_feedback("Inventory full!", ok=False)
        elif result == "out_of_stock":
            _assets().play("craft_fail")
            self._set_feedback("Out of stock.", ok=False)

    def _do_sell(self):
        if not self._rows:
            return
        row    = self._rows[self._cursor]
        result = self._shop.sell(self._shop_id, row["item_id"], self.player.inventory)
        if result == "ok":
            _assets().play("item_pickup")
            self._set_feedback(f"Sold {row['name']}  (+{row['sell_value']}g)", ok=True)
            self._rebuild()
            self._cursor = min(self._cursor, max(0, len(self._rows) - 1))
        elif result == "no_items":
            self._set_feedback("No more to sell.", ok=False)
        elif result == "not_sellable":
            self._set_feedback("Can't sell that.", ok=False)

    def _set_feedback(self, text: str, ok: bool):
        self._feedback = text
        self._fb_timer = 2.0
        self._fb_ok    = ok
        color = CRAFT_INGREDIENT_OK if ok else CRAFT_INGREDIENT_MISS
        self._fb_surf  = self._font_fb.render(text, True, color)

    # ------------------------------------------------------------------
    # Rebuild pre-rendered row data
    # ------------------------------------------------------------------

    def _rebuild(self):
        self._rows.clear()
        self._name_surfs.clear()
        self._detail_surfs.clear()
        inv      = self.player.inventory
        item_defs= inv.item_defs
        gold     = inv.count("gold")

        if self._mode == "buy":
            shop = self._shop.get(self._shop_id)
            if not shop:
                return
            for entry in shop["inventory"]:
                item_id = entry["item_id"]
                price   = entry["price"]
                stock   = entry.get("stock", -1)
                name    = item_defs.get(item_id, {}).get("name", item_id)
                can     = gold >= price and stock != 0
                self._rows.append({
                    "item_id": item_id, "name": name,
                    "price": price, "can": can, "stock": stock,
                })
                color = CRAFT_INGREDIENT_OK if can else _DIM_COLOR
                self._name_surfs.append(self._font_item.render(name, True, color))
                # Pre-render price and stock detail surfs
                pc = CRAFT_INGREDIENT_OK if can else CRAFT_INGREDIENT_MISS
                ps = self._font_item.render(f"{price}g", True, pc)
                ss = self._font_item.render(f"x{stock}", True, _DIM_COLOR) if stock >= 0 else None
                oos = self._font_hint.render("Out of stock", True, CRAFT_INGREDIENT_MISS) if stock == 0 else None
                self._detail_surfs.append({"price": ps, "stock": ss, "oos": oos})

        else:  # sell mode — show player items that have sell_value
            seen_ids = set()
            for slot in inv.slots:
                if not slot or slot.item_id == "gold":
                    continue
                if slot.item_id in seen_ids:
                    continue
                sv = item_defs.get(slot.item_id, {}).get("sell_value", 0)
                if sv <= 0:
                    continue
                seen_ids.add(slot.item_id)
                name = item_defs.get(slot.item_id, {}).get("name", slot.item_id)
                qty  = inv.count(slot.item_id)
                self._rows.append({
                    "item_id": slot.item_id, "name": name,
                    "sell_value": sv, "qty": qty,
                })
                self._name_surfs.append(self._font_item.render(name, True, WHITE))
                sv_s  = self._font_item.render(f"+{sv}g", True, _GOLD_COLOR)
                qty_s = self._font_item.render(f"x{qty}", True, _DIM_COLOR)
                self._detail_surfs.append({"sv": sv_s, "qty": qty_s})

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen):
        if not self.open:
            return

        screen.blit(self._overlay, (0, 0))

        px, py = self._px, self._py

        # Panel
        panel = pygame.Rect(px, py, _PANEL_W, _PANEL_H)
        pygame.draw.rect(screen, CRAFT_PANEL_BG,    panel, border_radius=8)
        pygame.draw.rect(screen, CRAFT_PANEL_BORDER, panel, 2, border_radius=8)

        # ---- Title + gold ----
        title_y = py + _PAD
        if self._title_surf:
            screen.blit(self._title_surf, (px + _PAD, title_y))

        gold = self.player.inventory.count("gold")
        if self._gold_cache[0] != gold:
            g_surf = self._font_gold.render(f"⬡ {gold} gold", True, _GOLD_COLOR)
            self._gold_cache = (gold, g_surf)
        g_surf = self._gold_cache[1]
        screen.blit(g_surf, (px + _PANEL_W - g_surf.get_width() - _PAD, title_y))

        # Divider
        div1_y = py + _PAD + 28
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PAD, div1_y), (px + _PANEL_W - _PAD, div1_y))

        # ---- Mode tabs (pre-rendered surfs) ----
        tab_y = div1_y + 6
        tab_h = 26
        tab_w = 80
        for i, (on_s, off_s, mode) in enumerate([
            (self._tab_buy_on,  self._tab_buy_off,  "buy"),
            (self._tab_sell_on, self._tab_sell_off, "sell"),
        ]):
            tx  = px + _PAD + i * (tab_w + 8)
            active = self._mode == mode
            bg  = _TAB_ON_BG if active else _TAB_OFF_BG
            pygame.draw.rect(screen, bg, (tx, tab_y, tab_w, tab_h), border_radius=4)
            bclr = CRAFT_TITLE_COLOR if active else CRAFT_PANEL_BORDER
            pygame.draw.rect(screen, bclr, (tx, tab_y, tab_w, tab_h), 1, border_radius=4)
            ts = on_s if active else off_s
            screen.blit(ts, (tx + (tab_w - ts.get_width()) // 2,
                             tab_y + (tab_h - ts.get_height()) // 2))

        # Divider under tabs
        div2_y = tab_y + tab_h + 6
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PAD, div2_y), (px + _PANEL_W - _PAD, div2_y))

        # ---- Item rows ----
        items_top = div2_y + 6
        max_rows  = min(len(self._rows), (_PANEL_H - 120) // _ROW_H)

        if not self._rows:
            no_items = self._font_item.render(
                "Nothing to sell." if self._mode == "sell" else "Shop is empty.",
                True, _DIM_COLOR)
            screen.blit(no_items, (px + _PAD, items_top + 10))

        for i in range(max_rows):
            ry   = items_top + i * _ROW_H
            mid_y = ry + (_ROW_H - self._name_surfs[i].get_height()) // 2

            if i == self._cursor:
                pygame.draw.rect(screen, CRAFT_SELECTED_BG,
                                 (px + 4, ry - 2, _PANEL_W - 8, _ROW_H - 2),
                                 border_radius=3)
                screen.blit(self._cursor_surf,
                            (px + 6, ry + (_ROW_H - self._cursor_surf.get_height()) // 2))

            screen.blit(self._name_surfs[i], (px + _PAD + 14, mid_y))

            det = self._detail_surfs[i]
            if self._mode == "buy":
                ps = det["price"]
                screen.blit(ps, (px + _PANEL_W - _PAD - ps.get_width() - 90, mid_y))
                if det["stock"] is not None:
                    ss = det["stock"]
                    screen.blit(ss, (px + _PANEL_W - _PAD - ss.get_width(), mid_y))
                if det["oos"] is not None:
                    oos = det["oos"]
                    screen.blit(oos, (px + _PANEL_W - _PAD - oos.get_width() - 80, mid_y))
            else:
                sv_s = det["sv"]; qty_s = det["qty"]
                screen.blit(sv_s,  (px + _PANEL_W - _PAD - sv_s.get_width()  - 60, mid_y))
                screen.blit(qty_s, (px + _PANEL_W - _PAD - qty_s.get_width(),       mid_y))

        # ---- Feedback ----
        fb_y = py + _PANEL_H - 62
        if self._fb_timer > 0 and self._fb_surf:
            alpha = min(255, int(self._fb_timer * 300))
            self._fb_surf.set_alpha(alpha)
            screen.blit(self._fb_surf,
                        (px + (_PANEL_W - self._fb_surf.get_width()) // 2, fb_y))

        # ---- Footer ----
        footer_y = py + _PANEL_H - 40
        pygame.draw.line(screen, CRAFT_PANEL_BORDER,
                         (px + _PAD, footer_y), (px + _PANEL_W - _PAD, footer_y))
        hint = self._hint_buy if self._mode == "buy" else self._hint_sell
        screen.blit(hint, (px + (_PANEL_W - hint.get_width()) // 2,
                            footer_y + (40 - hint.get_height()) // 2))
