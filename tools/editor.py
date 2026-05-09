#!/usr/bin/env python3
"""
tools/editor.py
Survival Game — Content Editor

Run from the project root:
    python tools/editor.py

Creates and edits all JSON data files in data/.
Does NOT depend on game/ or pygame — pure Tkinter + stdlib.

Tabs:
  Enemies   — enemies.json         (stats, drops)
  Items     — items.json           (name, color, use effects)
  Recipes   — recipes.json         (ingredients, result)
  NPCs      — npcs.json + dialogue.json
  Abilities — abilities.json       (type, damage, status)
  Zones     — data/zones/*.json    (visual canvas editor)
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, simpledialog
from pathlib import Path
from copy import deepcopy

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT     = Path(__file__).parent.parent
DATA_DIR  = _ROOT / "data"
ZONES_DIR = DATA_DIR / "zones"


# ---------------------------------------------------------------------------
# JSON I/O helpers
# ---------------------------------------------------------------------------

def _load(path: Path):
    with open(path) as f:
        return json.load(f)

def _save(path: Path, data) -> None:
    """Atomic write: .tmp → real file."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)

def _hex(rgb) -> str:
    r, g, b = (max(0, min(255, int(c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"

def _rgb(h: str) -> list:
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


# ---------------------------------------------------------------------------
# Shared widgets
# ---------------------------------------------------------------------------

class ColorButton(tk.Button):
    """Button that shows and edits an [r, g, b] color."""

    def __init__(self, parent, initial=(200, 200, 200), **kwargs):
        self._color = list(initial)
        super().__init__(parent, command=self._pick, width=5, **kwargs)
        self._refresh()

    def _pick(self):
        result = colorchooser.askcolor(color=_hex(self._color), title="Pick color")
        if result[1]:
            self._color = _rgb(result[1])
            self._refresh()

    def _refresh(self):
        self.config(bg=_hex(self._color), activebackground=_hex(self._color), text="  ")

    def get(self) -> list:
        return list(self._color)

    def set(self, rgb):
        self._color = list(rgb)
        self._refresh()


def _field(parent, row, label, default="", width=24):
    """Label + Entry in a grid parent. Returns StringVar."""
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
    v = tk.StringVar(value=str(default) if default is not None else "")
    ttk.Entry(parent, textvariable=v, width=width).grid(
        row=row, column=1, sticky="ew", padx=(6, 0), pady=2)
    return v


def _spin(parent, row, label, from_=0, to=9999, default=0, step=1.0):
    """Label + Spinbox. Returns DoubleVar."""
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
    v = tk.DoubleVar(value=float(default))
    tk.Spinbox(parent, textvariable=v, from_=from_, to=to,
               increment=step, width=10).grid(
        row=row, column=1, sticky="w", padx=(6, 0), pady=2)
    return v


def _check(parent, row, label, default=False):
    """Label + Checkbutton. Returns BooleanVar."""
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
    v = tk.BooleanVar(value=bool(default))
    ttk.Checkbutton(parent, variable=v).grid(
        row=row, column=1, sticky="w", padx=(6, 0))
    return v


def _combo(parent, row, label, values=(), default=""):
    """Label + Combobox (readonly). Returns StringVar."""
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
    v = tk.StringVar(value=str(default) if default is not None else "")
    ttk.Combobox(parent, textvariable=v, values=list(values),
                 state="readonly", width=22).grid(
        row=row, column=1, sticky="w", padx=(6, 0), pady=2)
    return v


# ---------------------------------------------------------------------------
# Enemy tab
# ---------------------------------------------------------------------------

class EnemyTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._path = DATA_DIR / "enemies.json"
        self._data = _load(self._path) if self._path.exists() else {}
        self._selected = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        # Left: list
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)
        ttk.Label(left, text="Enemy Types", font=("", 10, "bold")).pack()
        self._listbox = tk.Listbox(left, width=18, exportselection=False)
        self._listbox.pack(fill="y", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="New",    command=self._new).pack(side="left")
        ttk.Button(btn_row, text="Delete", command=self._delete).pack(side="left", padx=4)

        # Right: form
        right = ttk.LabelFrame(self, text="Properties")
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)
        right.columnconfigure(1, weight=1)

        f = right
        row = 0
        self._v_id     = _field(f, row, "ID (key)");         row += 1
        self._v_health = _spin(f,  row, "Health", 1, 9999, 100); row += 1
        self._v_w      = _spin(f,  row, "Width",  1, 200,  40);  row += 1
        self._v_h      = _spin(f,  row, "Height", 1, 400,  60);  row += 1
        self._v_speed  = _spin(f,  row, "Patrol speed",  0, 1000, 80);  row += 1
        self._v_cspeed = _spin(f,  row, "Chase speed",   0, 1000, 180); row += 1
        self._v_aggro  = _spin(f,  row, "Aggro range",   0, 2000, 300); row += 1
        self._v_deaggro= _spin(f,  row, "De-aggro range",0, 3000, 500); row += 1
        self._v_atk_r  = _spin(f,  row, "Attack range",  0, 500,  65);  row += 1
        self._v_atk_d  = _spin(f,  row, "Attack damage", 0, 999,  15);  row += 1
        self._v_atk_cd = _spin(f,  row, "Attack cooldown", 0.1, 10, 1.5, 0.1); row += 1
        self._v_patrol = _spin(f,  row, "Patrol radius", 0, 5000, 200); row += 1
        self._v_sprite = _field(f, row, "Sprite name",  "enemy_basic");  row += 1

        # Drop table
        ttk.Label(f, text="Drops:", font=("", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=(8, 2)); row += 1

        drop_frame = ttk.Frame(f)
        drop_frame.grid(row=row, column=0, columnspan=2, sticky="ew"); row += 1

        self._drop_tree = ttk.Treeview(
            drop_frame, columns=("item", "qty", "chance"), show="headings", height=4)
        self._drop_tree.heading("item",   text="Item ID")
        self._drop_tree.heading("qty",    text="Qty")
        self._drop_tree.heading("chance", text="Chance")
        self._drop_tree.column("item",   width=120)
        self._drop_tree.column("qty",    width=50)
        self._drop_tree.column("chance", width=60)
        self._drop_tree.pack(side="left", fill="x", expand=True)

        drop_btns = ttk.Frame(drop_frame)
        drop_btns.pack(side="left", padx=(4, 0))
        ttk.Button(drop_btns, text="+", width=3,
                   command=self._add_drop).pack(pady=2)
        ttk.Button(drop_btns, text="−", width=3,
                   command=self._del_drop).pack()

        # Save
        ttk.Button(f, text="Save Enemy", command=self._save_entry).grid(
            row=row, column=0, columnspan=2, pady=10)

    def _refresh_list(self):
        self._listbox.delete(0, "end")
        for k in self._data:
            self._listbox.insert("end", k)

    def _on_select(self, _=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        key = self._listbox.get(sel[0])
        self._selected = key
        d = self._data[key]
        self._v_id.set(key)
        self._v_health.set(float(d.get("health", 100)))
        self._v_w.set(float(d.get("width", 40)))
        self._v_h.set(float(d.get("height", 60)))
        self._v_speed.set(float(d.get("speed", 80)))
        self._v_cspeed.set(float(d.get("chase_speed", 180)))
        self._v_aggro.set(float(d.get("aggro_range", 300)))
        self._v_deaggro.set(float(d.get("deaggro_range", 500)))
        self._v_atk_r.set(float(d.get("attack_range", 65)))
        self._v_atk_d.set(float(d.get("attack_damage", 15)))
        self._v_atk_cd.set(float(d.get("attack_cooldown", 1.5)))
        self._v_patrol.set(float(d.get("patrol_radius", 200)))
        self._v_sprite.set(d.get("sprite", "enemy_basic"))
        # Drops
        self._drop_tree.delete(*self._drop_tree.get_children())
        for drop in d.get("drops", []):
            self._drop_tree.insert("", "end", values=(
                drop.get("item_id", ""),
                drop.get("quantity", 1),
                drop.get("chance", 1.0),
            ))

    def _new(self):
        key = simpledialog.askstring("New Enemy", "Enter enemy type ID (e.g. 'archer'):")
        if not key:
            return
        key = key.strip().lower().replace(" ", "_")
        if key in self._data:
            messagebox.showerror("Error", f"'{key}' already exists.")
            return
        self._data[key] = {
            "sprite": f"enemy_{key}", "health": 100, "width": 40, "height": 60,
            "speed": 80, "chase_speed": 180, "aggro_range": 300, "deaggro_range": 500,
            "attack_range": 65, "attack_damage": 15, "attack_cooldown": 1.5,
            "patrol_radius": 200, "drops": [],
        }
        self._refresh_list()
        # Select the new entry
        keys = list(self._data.keys())
        idx = keys.index(key)
        self._listbox.selection_set(idx)
        self._on_select()

    def _delete(self):
        if not self._selected:
            return
        if not messagebox.askyesno("Delete", f"Delete '{self._selected}'?"):
            return
        del self._data[self._selected]
        self._selected = None
        self._refresh_list()
        _save(self._path, self._data)

    def _add_drop(self):
        win = tk.Toplevel(self)
        win.title("Add Drop")
        win.grab_set()
        f = ttk.Frame(win, padding=12)
        f.pack()
        item_v  = _field(f, 0, "Item ID",  "wood",   20)
        qty_v   = _spin(f,  1, "Quantity", 1, 99, 1)
        chance_v= _spin(f,  2, "Chance",   0.0, 1.0, 1.0, 0.05)

        def ok():
            self._drop_tree.insert("", "end", values=(
                item_v.get(), int(qty_v.get()), round(float(chance_v.get()), 2)))
            win.destroy()

        ttk.Button(f, text="Add", command=ok).grid(row=3, column=0, columnspan=2, pady=8)

    def _del_drop(self):
        sel = self._drop_tree.selection()
        if sel:
            self._drop_tree.delete(sel[0])

    def _save_entry(self):
        key = self._v_id.get().strip().lower().replace(" ", "_")
        if not key:
            messagebox.showerror("Error", "ID cannot be empty.")
            return
        drops = []
        for row_id in self._drop_tree.get_children():
            vals = self._drop_tree.item(row_id, "values")
            drops.append({"item_id": vals[0], "quantity": int(vals[1]),
                          "chance": float(vals[2])})
        entry = {
            "sprite":          self._v_sprite.get() or f"enemy_{key}",
            "health":          int(self._v_health.get()),
            "width":           int(self._v_w.get()),
            "height":          int(self._v_h.get()),
            "speed":           int(self._v_speed.get()),
            "chase_speed":     int(self._v_cspeed.get()),
            "aggro_range":     int(self._v_aggro.get()),
            "deaggro_range":   int(self._v_deaggro.get()),
            "attack_range":    int(self._v_atk_r.get()),
            "attack_damage":   int(self._v_atk_d.get()),
            "attack_cooldown": round(self._v_atk_cd.get(), 2),
            "patrol_radius":   int(self._v_patrol.get()),
            "drops":           drops,
        }
        # Rename key if ID changed
        if self._selected and self._selected != key:
            del self._data[self._selected]
        self._data[key] = entry
        self._selected = key
        _save(self._path, self._data)
        self._refresh_list()
        keys = list(self._data.keys())
        self._listbox.selection_set(keys.index(key))
        messagebox.showinfo("Saved", f"Enemy '{key}' saved.")


# ---------------------------------------------------------------------------
# Item tab
# ---------------------------------------------------------------------------

class ItemTab(ttk.Frame):
    _USE_TYPES = ("", "heal", "equip_ability")

    def __init__(self, parent):
        super().__init__(parent)
        self._path = DATA_DIR / "items.json"
        self._data = _load(self._path) if self._path.exists() else {}
        self._selected = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)
        ttk.Label(left, text="Items", font=("", 10, "bold")).pack()
        self._listbox = tk.Listbox(left, width=22, exportselection=False)
        self._listbox.pack(fill="y", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="New",    command=self._new).pack(side="left")
        ttk.Button(btn_row, text="Delete", command=self._delete).pack(side="left", padx=4)

        right = ttk.LabelFrame(self, text="Properties")
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)
        right.columnconfigure(1, weight=1)

        f = right
        row = 0
        self._v_id   = _field(f, row, "ID (key)");  row += 1
        self._v_name = _field(f, row, "Display name"); row += 1

        # Color picker
        ttk.Label(f, text="Color").grid(row=row, column=0, sticky="w", pady=2)
        self._color_btn = ColorButton(f, initial=(200, 200, 200))
        self._color_btn.grid(row=row, column=1, sticky="w", padx=(6, 0), pady=2)
        row += 1

        self._v_stack = _check(f, row, "Stackable",   True); row += 1
        self._v_maxst = _spin(f,  row, "Max stack",   1, 999, 99); row += 1
        self._v_use   = _combo(f, row, "Use effect",  self._USE_TYPES, ""); row += 1
        self._v_heal  = _spin(f,  row, "Heal amount", 0, 999, 0); row += 1
        self._v_abid  = _field(f, row, "Ability ID"); row += 1

        ttk.Button(f, text="Save Item", command=self._save_entry).grid(
            row=row, column=0, columnspan=2, pady=10)

    def _refresh_list(self):
        self._listbox.delete(0, "end")
        for k in self._data:
            self._listbox.insert("end", k)

    def _on_select(self, _=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        key = self._listbox.get(sel[0])
        self._selected = key
        d = self._data[key]
        self._v_id.set(key)
        self._v_name.set(d.get("name", key))
        self._color_btn.set(d.get("color", [200, 200, 200]))
        self._v_stack.set(d.get("stackable", False))
        self._v_maxst.set(float(d.get("max_stack", 1)))
        self._v_use.set(d.get("use", ""))
        self._v_heal.set(float(d.get("heal_amount", 0)))
        self._v_abid.set(d.get("ability_id", ""))

    def _new(self):
        key = simpledialog.askstring("New Item", "Enter item ID (e.g. 'iron_ore'):")
        if not key:
            return
        key = key.strip().lower().replace(" ", "_")
        if key in self._data:
            messagebox.showerror("Error", f"'{key}' already exists.")
            return
        self._data[key] = {"name": key.replace("_", " ").title(),
                           "color": [200, 200, 200], "stackable": True, "max_stack": 99}
        self._refresh_list()
        keys = list(self._data.keys())
        self._listbox.selection_set(keys.index(key))
        self._on_select()

    def _delete(self):
        if not self._selected:
            return
        if not messagebox.askyesno("Delete", f"Delete '{self._selected}'?"):
            return
        del self._data[self._selected]
        self._selected = None
        self._refresh_list()
        _save(self._path, self._data)

    def _save_entry(self):
        key = self._v_id.get().strip().lower().replace(" ", "_")
        if not key:
            messagebox.showerror("Error", "ID cannot be empty.")
            return
        entry = {
            "name":      self._v_name.get() or key,
            "color":     self._color_btn.get(),
            "stackable": self._v_stack.get(),
            "max_stack": int(self._v_maxst.get()),
        }
        use = self._v_use.get()
        if use:
            entry["use"] = use
        if use == "heal":
            entry["heal_amount"] = int(self._v_heal.get())
        if use == "equip_ability" and self._v_abid.get():
            entry["ability_id"] = self._v_abid.get().strip()

        if self._selected and self._selected != key:
            del self._data[self._selected]
        self._data[key] = entry
        self._selected = key
        _save(self._path, self._data)
        self._refresh_list()
        keys = list(self._data.keys())
        self._listbox.selection_set(keys.index(key))
        messagebox.showinfo("Saved", f"Item '{key}' saved.")


# ---------------------------------------------------------------------------
# Recipe tab
# ---------------------------------------------------------------------------

class RecipeTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._path = DATA_DIR / "recipes.json"
        self._data = _load(self._path) if self._path.exists() else {}
        self._selected = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)
        ttk.Label(left, text="Recipes", font=("", 10, "bold")).pack()
        self._listbox = tk.Listbox(left, width=22, exportselection=False)
        self._listbox.pack(fill="y", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="New",    command=self._new).pack(side="left")
        ttk.Button(btn_row, text="Delete", command=self._delete).pack(side="left", padx=4)

        right = ttk.LabelFrame(self, text="Properties")
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)
        right.columnconfigure(1, weight=1)

        f = right
        row = 0
        self._v_id     = _field(f, row, "Recipe ID (key)"); row += 1
        self._v_name   = _field(f, row, "Display name");    row += 1
        self._v_result = _field(f, row, "Result item ID");   row += 1
        self._v_count  = _spin(f,  row, "Result count", 1, 999, 1); row += 1

        ttk.Label(f, text="Ingredients:", font=("", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=(8, 2)); row += 1

        ing_frame = ttk.Frame(f)
        ing_frame.grid(row=row, column=0, columnspan=2, sticky="ew"); row += 1

        self._ing_tree = ttk.Treeview(
            ing_frame, columns=("item", "qty"), show="headings", height=5)
        self._ing_tree.heading("item", text="Item ID")
        self._ing_tree.heading("qty",  text="Quantity")
        self._ing_tree.column("item", width=160)
        self._ing_tree.column("qty",  width=70)
        self._ing_tree.pack(side="left", fill="x", expand=True)

        btns = ttk.Frame(ing_frame)
        btns.pack(side="left", padx=(4, 0))
        ttk.Button(btns, text="+", width=3, command=self._add_ing).pack(pady=2)
        ttk.Button(btns, text="−", width=3, command=self._del_ing).pack()

        ttk.Button(f, text="Save Recipe", command=self._save_entry).grid(
            row=row, column=0, columnspan=2, pady=10)

    def _refresh_list(self):
        self._listbox.delete(0, "end")
        for k in self._data:
            self._listbox.insert("end", k)

    def _on_select(self, _=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        key = self._listbox.get(sel[0])
        self._selected = key
        d = self._data[key]
        self._v_id.set(key)
        self._v_name.set(d.get("name", key))
        self._v_result.set(d.get("result", ""))
        self._v_count.set(float(d.get("count", 1)))
        self._ing_tree.delete(*self._ing_tree.get_children())
        for item_id, qty in d.get("ingredients", {}).items():
            self._ing_tree.insert("", "end", values=(item_id, qty))

    def _new(self):
        key = simpledialog.askstring("New Recipe", "Enter recipe ID (e.g. 'iron_sword'):")
        if not key:
            return
        key = key.strip().lower().replace(" ", "_")
        if key in self._data:
            messagebox.showerror("Error", f"'{key}' already exists.")
            return
        self._data[key] = {"name": key.replace("_", " ").title(),
                           "result": key, "count": 1, "ingredients": {}}
        self._refresh_list()
        keys = list(self._data.keys())
        self._listbox.selection_set(keys.index(key))
        self._on_select()

    def _delete(self):
        if not self._selected:
            return
        if not messagebox.askyesno("Delete", f"Delete '{self._selected}'?"):
            return
        del self._data[self._selected]
        self._selected = None
        self._refresh_list()
        _save(self._path, self._data)

    def _add_ing(self):
        win = tk.Toplevel(self)
        win.title("Add Ingredient")
        win.grab_set()
        f = ttk.Frame(win, padding=12)
        f.pack()
        item_v = _field(f, 0, "Item ID",  "wood", 20)
        qty_v  = _spin(f,  1, "Quantity", 1, 999, 1)

        def ok():
            self._ing_tree.insert("", "end", values=(item_v.get(), int(qty_v.get())))
            win.destroy()

        ttk.Button(f, text="Add", command=ok).grid(row=2, column=0, columnspan=2, pady=8)

    def _del_ing(self):
        sel = self._ing_tree.selection()
        if sel:
            self._ing_tree.delete(sel[0])

    def _save_entry(self):
        key = self._v_id.get().strip().lower().replace(" ", "_")
        if not key:
            messagebox.showerror("Error", "ID cannot be empty.")
            return
        ingredients = {}
        for row_id in self._ing_tree.get_children():
            vals = self._ing_tree.item(row_id, "values")
            ingredients[vals[0]] = int(vals[1])
        entry = {
            "name":        self._v_name.get() or key,
            "result":      self._v_result.get().strip(),
            "count":       int(self._v_count.get()),
            "ingredients": ingredients,
        }
        if self._selected and self._selected != key:
            del self._data[self._selected]
        self._data[key] = entry
        self._selected = key
        _save(self._path, self._data)
        self._refresh_list()
        keys = list(self._data.keys())
        self._listbox.selection_set(keys.index(key))
        messagebox.showinfo("Saved", f"Recipe '{key}' saved.")


# ---------------------------------------------------------------------------
# NPC tab
# ---------------------------------------------------------------------------

class NPCTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._npc_path = DATA_DIR / "npcs.json"
        self._dlg_path = DATA_DIR / "dialogue.json"
        self._npcs = _load(self._npc_path) if self._npc_path.exists() else {}
        self._dlgs = _load(self._dlg_path) if self._dlg_path.exists() else {}
        self._selected_npc = None
        self._selected_dlg = None
        self._build_ui()
        self._refresh_npc_list()
        self._refresh_dlg_list()

    def _build_ui(self):
        # ---- NPC types (left panel) ----
        left = ttk.LabelFrame(self, text="NPC Types  (npcs.json)")
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)

        self._npc_lb = tk.Listbox(left, width=18, exportselection=False)
        self._npc_lb.pack(fill="y", expand=True)
        self._npc_lb.bind("<<ListboxSelect>>", self._on_npc_select)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="New",    command=self._new_npc).pack(side="left")
        ttk.Button(btn_row, text="Delete", command=self._del_npc).pack(side="left", padx=2)

        # NPC form
        nf = ttk.LabelFrame(left, text="NPC Properties")
        nf.pack(fill="x", padx=4, pady=(8, 4))
        nf.columnconfigure(1, weight=1)
        self._nv_id     = _field(nf, 0, "ID (key)")
        self._nv_name   = _field(nf, 1, "Name")
        self._nv_sprite = _field(nf, 2, "Sprite")
        ttk.Label(nf, text="Color").grid(row=3, column=0, sticky="w", pady=2)
        self._nv_color  = ColorButton(nf, initial=(220, 190, 130))
        self._nv_color.grid(row=3, column=1, sticky="w", padx=(6, 0), pady=2)
        self._nv_w      = _spin(nf, 4, "Width",  1, 200, 28)
        self._nv_h      = _spin(nf, 5, "Height", 1, 400, 52)
        ttk.Button(nf, text="Save NPC", command=self._save_npc).grid(
            row=6, column=0, columnspan=2, pady=6)

        # ---- Dialogue scripts (right panel) ----
        right = ttk.LabelFrame(self, text="Dialogue Scripts  (dialogue.json)")
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)

        self._dlg_lb = tk.Listbox(right, width=22, exportselection=False)
        self._dlg_lb.pack(side="left", fill="y")
        self._dlg_lb.bind("<<ListboxSelect>>", self._on_dlg_select)

        dlg_btn = ttk.Frame(right)
        dlg_btn.pack(side="left", fill="y", padx=(4, 0))
        ttk.Button(dlg_btn, text="New",    command=self._new_dlg).pack(pady=2)
        ttk.Button(dlg_btn, text="Delete", command=self._del_dlg).pack(pady=2)

        line_panel = ttk.LabelFrame(right, text="Lines (one per entry)")
        line_panel.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=4)

        self._dlg_id_var = tk.StringVar()
        ttk.Label(line_panel, text="Script ID:").pack(anchor="w")
        ttk.Entry(line_panel, textvariable=self._dlg_id_var, width=26).pack(
            fill="x", pady=(0, 6))

        self._line_lb = tk.Listbox(line_panel, height=8, exportselection=False)
        self._line_lb.pack(fill="both", expand=True)

        line_btns = ttk.Frame(line_panel)
        line_btns.pack(fill="x", pady=4)
        ttk.Button(line_btns, text="Add line",  command=self._add_line).pack(side="left")
        ttk.Button(line_btns, text="Edit",      command=self._edit_line).pack(side="left", padx=4)
        ttk.Button(line_btns, text="↑",         command=self._move_up).pack(side="left")
        ttk.Button(line_btns, text="↓",         command=self._move_dn).pack(side="left", padx=2)
        ttk.Button(line_btns, text="Remove",    command=self._del_line).pack(side="left")
        ttk.Button(line_panel, text="Save Script", command=self._save_dlg).pack(pady=4)

    # ---- NPC helpers ----
    def _refresh_npc_list(self):
        self._npc_lb.delete(0, "end")
        for k in self._npcs:
            self._npc_lb.insert("end", k)

    def _on_npc_select(self, _=None):
        sel = self._npc_lb.curselection()
        if not sel:
            return
        key = self._npc_lb.get(sel[0])
        self._selected_npc = key
        d = self._npcs[key]
        self._nv_id.set(key)
        self._nv_name.set(d.get("name", key))
        self._nv_sprite.set(d.get("sprite", f"npc_{key}"))
        self._nv_color.set(d.get("color", [220, 190, 130]))
        self._nv_w.set(float(d.get("width", 28)))
        self._nv_h.set(float(d.get("height", 52)))

    def _new_npc(self):
        key = simpledialog.askstring("New NPC Type", "Enter NPC type ID (e.g. 'merchant'):")
        if not key:
            return
        key = key.strip().lower().replace(" ", "_")
        if key in self._npcs:
            messagebox.showerror("Error", f"'{key}' already exists.")
            return
        self._npcs[key] = {"sprite": f"npc_{key}", "name": key.title(),
                           "color": [220, 190, 130], "width": 28, "height": 52}
        self._refresh_npc_list()
        keys = list(self._npcs.keys())
        self._npc_lb.selection_set(keys.index(key))
        self._on_npc_select()

    def _del_npc(self):
        if not self._selected_npc:
            return
        if not messagebox.askyesno("Delete", f"Delete NPC type '{self._selected_npc}'?"):
            return
        del self._npcs[self._selected_npc]
        self._selected_npc = None
        self._refresh_npc_list()
        _save(self._npc_path, self._npcs)

    def _save_npc(self):
        key = self._nv_id.get().strip().lower().replace(" ", "_")
        if not key:
            return
        entry = {
            "sprite": self._nv_sprite.get() or f"npc_{key}",
            "name":   self._nv_name.get() or key.title(),
            "color":  self._nv_color.get(),
            "width":  int(self._nv_w.get()),
            "height": int(self._nv_h.get()),
        }
        if self._selected_npc and self._selected_npc != key:
            del self._npcs[self._selected_npc]
        self._npcs[key] = entry
        self._selected_npc = key
        _save(self._npc_path, self._npcs)
        self._refresh_npc_list()
        keys = list(self._npcs.keys())
        self._npc_lb.selection_set(keys.index(key))
        messagebox.showinfo("Saved", f"NPC type '{key}' saved.")

    # ---- Dialogue helpers ----
    def _refresh_dlg_list(self):
        self._dlg_lb.delete(0, "end")
        for k in self._dlgs:
            self._dlg_lb.insert("end", k)

    def _on_dlg_select(self, _=None):
        sel = self._dlg_lb.curselection()
        if not sel:
            return
        key = self._dlg_lb.get(sel[0])
        self._selected_dlg = key
        self._dlg_id_var.set(key)
        self._line_lb.delete(0, "end")
        for line in self._dlgs.get(key, []):
            self._line_lb.insert("end", line)

    def _new_dlg(self):
        key = simpledialog.askstring("New Script", "Enter dialogue script ID (e.g. 'merchant_01'):")
        if not key:
            return
        key = key.strip().lower().replace(" ", "_")
        if key in self._dlgs:
            messagebox.showerror("Error", f"'{key}' already exists.")
            return
        self._dlgs[key] = ["Hello, traveller!"]
        self._refresh_dlg_list()
        keys = list(self._dlgs.keys())
        self._dlg_lb.selection_set(keys.index(key))
        self._on_dlg_select()

    def _del_dlg(self):
        if not self._selected_dlg:
            return
        if not messagebox.askyesno("Delete", f"Delete script '{self._selected_dlg}'?"):
            return
        del self._dlgs[self._selected_dlg]
        self._selected_dlg = None
        self._refresh_dlg_list()
        _save(self._dlg_path, self._dlgs)

    def _add_line(self):
        text = simpledialog.askstring("Add Line", "Enter dialogue line:")
        if text:
            self._line_lb.insert("end", text)

    def _edit_line(self):
        sel = self._line_lb.curselection()
        if not sel:
            return
        old = self._line_lb.get(sel[0])
        new = simpledialog.askstring("Edit Line", "Edit:", initialvalue=old)
        if new is not None:
            self._line_lb.delete(sel[0])
            self._line_lb.insert(sel[0], new)

    def _del_line(self):
        sel = self._line_lb.curselection()
        if sel:
            self._line_lb.delete(sel[0])

    def _move_up(self):
        sel = self._line_lb.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        v = self._line_lb.get(i)
        self._line_lb.delete(i)
        self._line_lb.insert(i - 1, v)
        self._line_lb.selection_set(i - 1)

    def _move_dn(self):
        sel = self._line_lb.curselection()
        if not sel or sel[0] >= self._line_lb.size() - 1:
            return
        i = sel[0]
        v = self._line_lb.get(i)
        self._line_lb.delete(i)
        self._line_lb.insert(i + 1, v)
        self._line_lb.selection_set(i + 1)

    def _save_dlg(self):
        key = self._dlg_id_var.get().strip().lower().replace(" ", "_")
        if not key:
            return
        lines = list(self._line_lb.get(0, "end"))
        if self._selected_dlg and self._selected_dlg != key:
            del self._dlgs[self._selected_dlg]
        self._dlgs[key] = lines
        self._selected_dlg = key
        _save(self._dlg_path, self._dlgs)
        self._refresh_dlg_list()
        keys = list(self._dlgs.keys())
        self._dlg_lb.selection_set(keys.index(key))
        messagebox.showinfo("Saved", f"Dialogue script '{key}' saved.")


# ---------------------------------------------------------------------------
# Ability tab
# ---------------------------------------------------------------------------

class AbilityTab(ttk.Frame):
    _TYPES = ("melee", "projectile", "wave", "area", "aura")
    _STATUS = ("", "poison", "burn", "stun", "freeze", "slow")

    def __init__(self, parent):
        super().__init__(parent)
        self._path = DATA_DIR / "abilities.json"
        self._data = _load(self._path) if self._path.exists() else {}
        self._selected = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)
        ttk.Label(left, text="Abilities", font=("", 10, "bold")).pack()
        self._listbox = tk.Listbox(left, width=22, exportselection=False)
        self._listbox.pack(fill="y", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="New",    command=self._new).pack(side="left")
        ttk.Button(btn_row, text="Delete", command=self._delete).pack(side="left", padx=4)

        right = ttk.LabelFrame(self, text="Properties")
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)
        right.columnconfigure(1, weight=1)

        f = right
        row = 0
        self._v_id      = _field(f, row, "ID (key)");    row += 1
        self._v_name    = _field(f, row, "Display name"); row += 1
        self._v_type    = _combo(f, row, "Type", self._TYPES, "melee"); row += 1
        self._v_damage  = _spin(f,  row, "Damage",     0, 9999, 25);    row += 1
        self._v_mana    = _spin(f,  row, "Mana cost",  0, 999,  0);     row += 1
        self._v_cd      = _spin(f,  row, "Cooldown (s)", 0, 60, 0.45, 0.05); row += 1
        self._v_kb      = _spin(f,  row, "Knockback",  0, 9999, 0);    row += 1
        self._v_speed   = _spin(f,  row, "Speed (proj/wave)", 0, 2000, 300); row += 1
        self._v_maxdist = _spin(f,  row, "Max distance", 0, 9999, 500); row += 1
        self._v_radius  = _spin(f,  row, "Radius (area/aura)", 0, 999, 80); row += 1
        self._v_dur     = _spin(f,  row, "Duration (s)", 0, 30, 0.4, 0.1); row += 1
        self._v_dps     = _spin(f,  row, "DPS (aura)", 0, 999, 0); row += 1
        self._v_sound   = _field(f, row, "Sound name"); row += 1

        ttk.Label(f, text="Status effect:", font=("", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=(8, 2)); row += 1
        self._v_se_type = _combo(f, row, "  Type", self._STATUS, ""); row += 1
        self._v_se_dur  = _spin(f,  row, "  Duration (s)", 0, 30, 0, 0.5); row += 1
        self._v_se_dps  = _spin(f,  row, "  DPS (poison/burn)", 0, 999, 0); row += 1
        self._v_se_slow = _spin(f,  row, "  Slow factor (0-1)", 0, 1.0, 0.5, 0.05); row += 1

        ttk.Label(f, text="Color").grid(row=row, column=0, sticky="w", pady=2)
        self._color_btn = ColorButton(f, initial=(255, 220, 50))
        self._color_btn.grid(row=row, column=1, sticky="w", padx=(6, 0)); row += 1

        ttk.Button(f, text="Save Ability", command=self._save_entry).grid(
            row=row, column=0, columnspan=2, pady=10)

    def _refresh_list(self):
        self._listbox.delete(0, "end")
        for k in self._data:
            self._listbox.insert("end", k)

    def _on_select(self, _=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        key = self._listbox.get(sel[0])
        self._selected = key
        d = self._data[key]
        self._v_id.set(key)
        self._v_name.set(d.get("name", key))
        self._v_type.set(d.get("type", "melee"))
        self._v_damage.set(float(d.get("damage", 25)))
        self._v_mana.set(float(d.get("mana_cost", 0)))
        self._v_cd.set(float(d.get("cooldown", 0.45)))
        self._v_kb.set(float(d.get("knockback", 0)))
        self._v_speed.set(float(d.get("speed", 300)))
        self._v_maxdist.set(float(d.get("max_distance", 500)))
        self._v_radius.set(float(d.get("radius", 80)))
        self._v_dur.set(float(d.get("duration", 0.4)))
        self._v_dps.set(float(d.get("damage_per_second", 0)))
        self._v_sound.set(d.get("sound", ""))
        self._color_btn.set(d.get("color", [255, 220, 50]))
        se = d.get("status_effect") or {}
        self._v_se_type.set(se.get("type", ""))
        self._v_se_dur.set(float(se.get("duration", 0)))
        self._v_se_dps.set(float(se.get("damage_per_second", 0)))
        self._v_se_slow.set(float(se.get("slow_factor", 0.5)))

    def _new(self):
        key = simpledialog.askstring("New Ability", "Enter ability ID (e.g. 'frost_bolt'):")
        if not key:
            return
        key = key.strip().lower().replace(" ", "_")
        if key in self._data:
            messagebox.showerror("Error", f"'{key}' already exists.")
            return
        self._data[key] = {"type": "melee", "name": key.replace("_", " ").title(),
                           "damage": 25, "cooldown": 0.45, "color": [255, 220, 50]}
        self._refresh_list()
        keys = list(self._data.keys())
        self._listbox.selection_set(keys.index(key))
        self._on_select()

    def _delete(self):
        if not self._selected:
            return
        if not messagebox.askyesno("Delete", f"Delete ability '{self._selected}'?"):
            return
        del self._data[self._selected]
        self._selected = None
        self._refresh_list()
        _save(self._path, self._data)

    def _save_entry(self):
        key = self._v_id.get().strip().lower().replace(" ", "_")
        if not key:
            messagebox.showerror("Error", "ID cannot be empty.")
            return
        entry = {
            "type":    self._v_type.get(),
            "name":    self._v_name.get() or key,
            "damage":  int(self._v_damage.get()),
            "cooldown": round(self._v_cd.get(), 3),
            "color":   self._color_btn.get(),
        }
        if self._v_mana.get() > 0:
            entry["mana_cost"] = int(self._v_mana.get())
        if self._v_kb.get() > 0:
            entry["knockback"] = int(self._v_kb.get())
        ab_type = entry["type"]
        if ab_type in ("projectile", "wave"):
            entry["speed"] = int(self._v_speed.get())
        if ab_type == "wave":
            entry["max_distance"] = int(self._v_maxdist.get())
            entry["height"] = 35
        if ab_type in ("area", "aura"):
            entry["radius"] = int(self._v_radius.get())
            entry["duration"] = round(self._v_dur.get(), 2)
        if ab_type == "aura" and self._v_dps.get() > 0:
            entry["damage_per_second"] = int(self._v_dps.get())
        if self._v_sound.get():
            entry["sound"] = self._v_sound.get().strip()

        se_type = self._v_se_type.get()
        if se_type:
            se = {"type": se_type, "duration": round(self._v_se_dur.get(), 2)}
            if se_type in ("poison", "burn") and self._v_se_dps.get() > 0:
                se["damage_per_second"] = int(self._v_se_dps.get())
            if se_type == "slow":
                se["slow_factor"] = round(self._v_se_slow.get(), 2)
            entry["status_effect"] = se

        if self._selected and self._selected != key:
            del self._data[self._selected]
        self._data[key] = entry
        self._selected = key
        _save(self._path, self._data)
        self._refresh_list()
        keys = list(self._data.keys())
        self._listbox.selection_set(keys.index(key))
        messagebox.showinfo("Saved", f"Ability '{key}' saved.")


# ---------------------------------------------------------------------------
# Zone tab — visual canvas editor
# ---------------------------------------------------------------------------

class ZoneTab(ttk.Frame):
    # Canvas scale: world px → canvas px
    SX = 0.12   # x: 10 000 world → 1 200 canvas
    SY = 0.55   # y:   720 world →   396 canvas

    # Element colors (canvas fill)
    _CLR = {
        "platform":   "#8C6438",
        "enemy":      "#C85050",
        "save_point": "#50C8B4",
        "exit":       "#32B464",
        "building":   "#A08050",
        "npc":        "#C8BE8C",
        "item_drop":  "#8888FF",
        "spawn":      "#80FFFF",
    }

    _TOOLS = ("select", "platform", "enemy", "npc", "save_point",
              "item_drop", "exit", "building")

    def __init__(self, parent):
        super().__init__(parent)
        # Load reference data for dropdowns
        self._items    = _load(DATA_DIR / "items.json")    if (DATA_DIR / "items.json").exists()   else {}
        self._enemies  = _load(DATA_DIR / "enemies.json")  if (DATA_DIR / "enemies.json").exists() else {}
        self._npctypes = _load(DATA_DIR / "npcs.json")     if (DATA_DIR / "npcs.json").exists()    else {}
        self._dialogues= _load(DATA_DIR / "dialogue.json") if (DATA_DIR / "dialogue.json").exists()else {}

        self._zone_path: Path | None = None
        self._zone: dict = self._blank_zone()
        self._elements: list = []    # [{type, data, cid}]
        self._selected_idx: int | None = None
        self._drag_start = None      # (canvas_x, canvas_y) for platform drag
        self._rubber_id  = None      # canvas ID of rubber-band rect
        self._tool = tk.StringVar(value="select")

        self._build_ui()

    # ------------------------------------------------------------------
    # Blank zone template
    # ------------------------------------------------------------------

    def _blank_zone(self) -> dict:
        return {
            "id": "new_zone", "spawn": [200, 596],
            "bg_color": [30, 30, 40], "music": None,
            "platforms": [], "enemies": [], "save_points": [],
            "item_drops": [], "npcs": [], "exits": [], "buildings": [],
        }

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Top bar: file controls + zone meta
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 2))

        ttk.Button(top, text="New Zone",  command=self._new_zone).pack(side="left")
        ttk.Button(top, text="Open Zone", command=self._open_zone).pack(side="left", padx=4)
        ttk.Button(top, text="Save Zone", command=self._save_zone).pack(side="left")
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Label(top, text="ID:").pack(side="left")
        self._v_id = tk.StringVar(value="new_zone")
        ttk.Entry(top, textvariable=self._v_id, width=14).pack(side="left", padx=2)

        ttk.Label(top, text="Spawn X:").pack(side="left", padx=(8, 0))
        self._v_sx = tk.StringVar(value="200")
        ttk.Entry(top, textvariable=self._v_sx, width=6).pack(side="left", padx=2)
        ttk.Label(top, text="Y:").pack(side="left")
        self._v_sy = tk.StringVar(value="596")
        ttk.Entry(top, textvariable=self._v_sy, width=6).pack(side="left", padx=2)

        ttk.Label(top, text="BG color:").pack(side="left", padx=(8, 0))
        self._bg_btn = ColorButton(top, initial=(30, 30, 40))
        self._bg_btn.pack(side="left")

        ttk.Label(top, text="Music:").pack(side="left", padx=(8, 0))
        self._v_music = tk.StringVar()
        ttk.Entry(top, textvariable=self._v_music, width=14).pack(side="left", padx=2)

        # Toolbar row
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=2)
        ttk.Label(toolbar, text="Tool:").pack(side="left")
        labels = {
            "select": "↖ Select", "platform": "▭ Platform", "enemy": "☠ Enemy",
            "npc": "☺ NPC", "save_point": "✦ Save Pt", "item_drop": "◆ Item Drop",
            "exit": "→ Exit", "building": "⌂ Building",
        }
        for val in self._TOOLS:
            ttk.Radiobutton(toolbar, text=labels[val], variable=self._tool,
                            value=val).pack(side="left", padx=3)

        # Canvas + scrollbars
        canvas_frame = ttk.Frame(self, relief="sunken", borderwidth=1)
        canvas_frame.pack(fill="both", expand=True, padx=8, pady=4)

        self._canvas = tk.Canvas(canvas_frame, bg="#1a1a2a", cursor="crosshair",
                                 scrollregion=(0, 0, 10000 * self.SX, 720 * self.SY))
        h_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal",
                                 command=self._canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient="vertical",
                                 command=self._canvas.yview)
        self._canvas.config(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        h_scroll.pack(side="bottom", fill="x")
        v_scroll.pack(side="right",  fill="y")
        self._canvas.pack(fill="both", expand=True)

        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",        self._on_drag)
        self._canvas.bind("<ButtonRelease-1>",  self._on_release)
        self._canvas.bind("<Delete>",           self._on_delete)
        self._canvas.bind("<BackSpace>",        self._on_delete)
        self._canvas.focus_set()

        # Properties panel (bottom)
        self._prop_frame = ttk.LabelFrame(self, text="Selected element — properties")
        self._prop_frame.pack(fill="x", padx=8, pady=(0, 8))
        self._prop_label = ttk.Label(self._prop_frame,
                                     text="Click an element to select it.")
        self._prop_label.pack(anchor="w", padx=8, pady=4)

        # Status bar
        self._status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status, relief="sunken",
                  anchor="w").pack(fill="x", padx=8, pady=(0, 4))

    # ------------------------------------------------------------------
    # World ↔ canvas coordinate helpers
    # ------------------------------------------------------------------

    def _wx(self, cx: float) -> int:
        return int(self._canvas.canvasx(cx) / self.SX)

    def _wy(self, cy: float) -> int:
        return int(self._canvas.canvasy(cy) / self.SY)

    def _cx(self, wx: float) -> float:
        return wx * self.SX

    def _cy(self, wy: float) -> float:
        return wy * self.SY

    # ------------------------------------------------------------------
    # Canvas draw
    # ------------------------------------------------------------------

    def _redraw(self):
        self._canvas.delete("all")
        self._elements.clear()
        self._selected_idx = None

        z = self._zone

        # Spawn marker
        sx, sy = z["spawn"]
        self._canvas.create_oval(
            self._cx(sx) - 5, self._cy(sy) - 5,
            self._cx(sx) + 5, self._cy(sy) + 5,
            fill=self._CLR["spawn"], outline="white", tags="spawn")

        # Platforms
        for d in z.get("platforms", []):
            self._draw_element("platform", d)

        # Save points
        for d in z.get("save_points", []):
            self._draw_element("save_point", d)

        # Exits
        for d in z.get("exits", []):
            self._draw_element("exit", d)

        # Buildings
        for d in z.get("buildings", []):
            self._draw_element("building", d)

        # NPCs
        for d in z.get("npcs", []):
            self._draw_element("npc", d)

        # Item drops
        for d in z.get("item_drops", []):
            self._draw_element("item_drop", d)

        # Enemies
        for d in z.get("enemies", []):
            self._draw_element("enemy", d)

        self._status.set(
            f"Zone: {z.get('id','?')} | "
            f"Platforms: {len(z.get('platforms',[]))} | "
            f"Enemies: {len(z.get('enemies',[]))} | "
            f"NPCs: {len(z.get('npcs',[]))} | "
            f"Drops: {len(z.get('item_drops',[]))}"
        )

    def _draw_element(self, etype: str, data: dict):
        clr = self._CLR.get(etype, "#888888")
        idx = len(self._elements)
        tag = f"elem_{idx}"

        if etype in ("platform", "save_point", "exit", "building"):
            x1 = self._cx(data["x"])
            y1 = self._cy(data["y"])
            x2 = self._cx(data["x"] + data["w"])
            y2 = self._cy(data["y"] + data["h"])
            cid = self._canvas.create_rectangle(
                x1, y1, x2, y2, fill=clr, outline="white", width=1, tags=tag)
        else:
            # Point element: draw as circle + label
            ex = data.get("x", 0)
            ey = data.get("y", 0)
            r  = 6
            cx = self._cx(ex)
            cy = self._cy(ey)
            cid = self._canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=clr, outline="white", width=1, tags=tag)
            label = data.get("type", etype[:3])
            self._canvas.create_text(cx, cy - r - 4, text=label,
                                     fill="white", font=("", 8), tags=tag)

        self._elements.append({"type": etype, "data": data, "cid": cid})
        self._canvas.tag_bind(tag, "<ButtonPress-1>", lambda e, i=idx: self._select_elem(i))

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def _on_press(self, event):
        tool = self._tool.get()
        wx, wy = self._wx(event.x), self._wy(event.y)
        cx, cy = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)

        if tool == "select":
            # Let tag bindings handle it
            self._canvas.focus_set()
            return

        if tool in ("platform", "exit"):
            # Start rubber-band drag
            self._drag_start = (cx, cy, wx, wy)
        else:
            # Immediate placement with dialog
            self._place_element(tool, wx, wy)

    def _on_drag(self, event):
        if self._drag_start is None:
            return
        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)
        if self._rubber_id:
            self._canvas.delete(self._rubber_id)
        x0, y0 = self._drag_start[0], self._drag_start[1]
        tool = self._tool.get()
        clr = self._CLR.get(tool, "#888888")
        self._rubber_id = self._canvas.create_rectangle(
            x0, y0, cx, cy, outline=clr, width=2, dash=(4, 2))

    def _on_release(self, event):
        if self._drag_start is None:
            return
        if self._rubber_id:
            self._canvas.delete(self._rubber_id)
            self._rubber_id = None

        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)
        x0, y0, wx0, wy0 = self._drag_start
        wx1 = self._wx(event.x)
        wy1 = self._wy(event.y)
        self._drag_start = None

        # Normalise so (x0,y0) is top-left
        x = min(wx0, wx1)
        y = min(wy0, wy1)
        w = abs(wx1 - wx0)
        h = abs(wy1 - wy0)
        if w < 4 or h < 4:
            return

        tool = self._tool.get()
        if tool == "platform":
            self._zone.setdefault("platforms", []).append({"x": x, "y": y, "w": w, "h": h})
            self._redraw()
        elif tool == "exit":
            self._add_exit_dialog(x, y, w, h)

    def _on_delete(self, _=None):
        if self._selected_idx is None:
            return
        elem = self._elements[self._selected_idx]
        etype = elem["type"]
        data  = elem["data"]
        # Remove from zone data
        key_map = {
            "platform":   "platforms",
            "save_point": "save_points",
            "exit":       "exits",
            "building":   "buildings",
            "npc":        "npcs",
            "item_drop":  "item_drops",
            "enemy":      "enemies",
        }
        lst = self._zone.get(key_map.get(etype, etype + "s"), [])
        if data in lst:
            lst.remove(data)
        self._selected_idx = None
        self._redraw()
        self._clear_props()

    # ------------------------------------------------------------------
    # Element selection + properties
    # ------------------------------------------------------------------

    def _select_elem(self, idx: int):
        # Clear old highlight
        if self._selected_idx is not None:
            try:
                old = self._elements[self._selected_idx]
                self._canvas.itemconfig(old["cid"], outline="white", width=1)
            except Exception:
                pass

        self._selected_idx = idx
        elem = self._elements[idx]
        self._canvas.itemconfig(elem["cid"], outline="#FFE020", width=2)
        self._show_props(elem["type"], elem["data"])

    def _clear_props(self):
        for w in self._prop_frame.winfo_children():
            w.destroy()
        ttk.Label(self._prop_frame, text="Click an element to select it.").pack(
            anchor="w", padx=8, pady=4)

    def _show_props(self, etype: str, data: dict):
        for w in self._prop_frame.winfo_children():
            w.destroy()

        f = ttk.Frame(self._prop_frame)
        f.pack(fill="x", padx=8, pady=4)
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text=f"Type: {etype}", font=("", 9, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

        vars_ = {}

        def add(col_offset, row_, label, key, is_int=True):
            ttk.Label(f, text=label).grid(row=row_, column=col_offset * 2, sticky="e", padx=4)
            v = tk.StringVar(value=str(data.get(key, 0)))
            ttk.Entry(f, textvariable=v, width=8).grid(
                row=row_, column=col_offset * 2 + 1, sticky="w")
            vars_[key] = (v, is_int)

        row = 1
        if etype in ("platform", "save_point", "exit", "building"):
            add(0, row, "X:", "x"); add(1, row, "Y:", "y"); row += 1
            add(0, row, "W:", "w"); add(1, row, "H:", "h"); row += 1
        else:
            add(0, row, "X:", "x"); add(1, row, "Y:", "y"); row += 1

        if etype == "enemy":
            ttk.Label(f, text="Type:").grid(row=row, column=0, sticky="e", padx=4)
            v = tk.StringVar(value=data.get("type", "basic"))
            ttk.Combobox(f, textvariable=v, values=list(self._enemies.keys()),
                         width=12, state="readonly").grid(row=row, column=1, sticky="w")
            vars_["type"] = (v, False); row += 1

        if etype == "npc":
            ttk.Label(f, text="Type:").grid(row=row, column=0, sticky="e", padx=4)
            v_t = tk.StringVar(value=data.get("type", "villager"))
            ttk.Combobox(f, textvariable=v_t, values=list(self._npctypes.keys()),
                         width=12, state="readonly").grid(row=row, column=1, sticky="w")
            vars_["type"] = (v_t, False)
            ttk.Label(f, text="Dialogue ID:").grid(row=row, column=2, sticky="e", padx=4)
            v_d = tk.StringVar(value=data.get("dialogue_id", ""))
            ttk.Combobox(f, textvariable=v_d, values=list(self._dialogues.keys()),
                         width=14).grid(row=row, column=3, sticky="w")
            vars_["dialogue_id"] = (v_d, False); row += 1

        if etype == "item_drop":
            ttk.Label(f, text="Item ID:").grid(row=row, column=0, sticky="e", padx=4)
            v_i = tk.StringVar(value=data.get("item_id", "wood"))
            ttk.Combobox(f, textvariable=v_i, values=list(self._items.keys()),
                         width=14).grid(row=row, column=1, sticky="w")
            vars_["item_id"] = (v_i, False)
            ttk.Label(f, text="Qty:").grid(row=row, column=2, sticky="e", padx=4)
            v_q = tk.StringVar(value=str(data.get("quantity", 1)))
            ttk.Entry(f, textvariable=v_q, width=5).grid(row=row, column=3, sticky="w")
            vars_["quantity"] = (v_q, True); row += 1

        if etype == "exit":
            ttk.Label(f, text="Target zone:").grid(row=row, column=0, sticky="e", padx=4)
            v_tz = tk.StringVar(value=data.get("target_zone", "zone_02"))
            zones = [p.stem for p in ZONES_DIR.glob("*.json")] if ZONES_DIR.exists() else []
            ttk.Combobox(f, textvariable=v_tz, values=zones, width=16).grid(
                row=row, column=1, sticky="w")
            vars_["target_zone"] = (v_tz, False)
            ttk.Label(f, text="Spawn override X:").grid(row=row, column=2, sticky="e", padx=4)
            so = data.get("spawn_override") or [None, None]
            v_sox = tk.StringVar(value=str(so[0]) if so[0] is not None else "")
            ttk.Entry(f, textvariable=v_sox, width=7).grid(row=row, column=3, sticky="w")
            vars_["_spawn_x"] = (v_sox, False); row += 1
            ttk.Label(f, text="Spawn override Y:").grid(row=row, column=0, sticky="e", padx=4)
            v_soy = tk.StringVar(value=str(so[1]) if so[1] is not None else "")
            ttk.Entry(f, textvariable=v_soy, width=7).grid(row=row, column=1, sticky="w")
            vars_["_spawn_y"] = (v_soy, False); row += 1

        if etype == "building":
            for lbl, key in [("Target zone:", "target_zone"), ("Label:", "label"),
                              ("Door X:", "door_x"), ("Door Y:", "door_y"),
                              ("Door W:", "door_w"), ("Door H:", "door_h")]:
                ttk.Label(f, text=lbl).grid(row=row, column=0, sticky="e", padx=4)
                is_int = lbl.startswith("Door")
                v = tk.StringVar(value=str(data.get(key, "")))
                ttk.Entry(f, textvariable=v, width=14).grid(row=row, column=1, sticky="w")
                vars_[key] = (v, is_int); row += 1

        def apply():
            for key, (v, is_int) in vars_.items():
                val = v.get().strip()
                if key.startswith("_spawn"):
                    continue
                if is_int and val:
                    try:
                        data[key] = int(val)
                    except ValueError:
                        pass
                elif val:
                    data[key] = val

            # Handle spawn_override for exit
            if "_spawn_x" in vars_ and "_spawn_y" in vars_:
                sx_str = vars_["_spawn_x"][0].get().strip()
                sy_str = vars_["_spawn_y"][0].get().strip()
                if sx_str and sy_str:
                    try:
                        data["spawn_override"] = [int(sx_str), int(sy_str)]
                    except ValueError:
                        pass
                else:
                    data.pop("spawn_override", None)

            self._redraw()

        ttk.Button(f, text="Apply", command=apply).grid(
            row=row, column=0, columnspan=4, pady=6)

    # ------------------------------------------------------------------
    # Placement dialogs
    # ------------------------------------------------------------------

    def _place_element(self, tool: str, wx: int, wy: int):
        if tool == "save_point":
            self._zone.setdefault("save_points", []).append(
                {"x": wx - 30, "y": wy - 32, "w": 60, "h": 64})
            self._redraw()
            return

        if tool == "enemy":
            self._add_enemy_dialog(wx, wy)
        elif tool == "npc":
            self._add_npc_dialog(wx, wy)
        elif tool == "item_drop":
            self._add_drop_dialog(wx, wy)
        elif tool == "building":
            self._add_building_dialog(wx, wy)

    def _add_enemy_dialog(self, wx, wy):
        win = tk.Toplevel(self)
        win.title("Place Enemy")
        win.grab_set()
        f = ttk.Frame(win, padding=12)
        f.pack()
        types = list(self._enemies.keys()) or ["basic", "fast", "heavy"]
        v_type = _combo(f, 0, "Enemy type", types, types[0] if types else "basic")
        v_x    = _spin(f, 1, "X (world)", 0, 99999, wx)
        v_y    = _spin(f, 2, "Y (world)", 0, 9999, wy)

        def ok():
            self._zone.setdefault("enemies", []).append(
                {"type": v_type.get(), "x": int(v_x.get()), "y": int(v_y.get())})
            self._redraw()
            win.destroy()

        ttk.Button(f, text="Place", command=ok).grid(row=3, column=0, columnspan=2, pady=8)

    def _add_npc_dialog(self, wx, wy):
        win = tk.Toplevel(self)
        win.title("Place NPC")
        win.grab_set()
        f = ttk.Frame(win, padding=12)
        f.pack()
        types   = list(self._npctypes.keys()) or ["villager"]
        dlg_ids = list(self._dialogues.keys()) or []
        shops   = list((_load(DATA_DIR / "shops.json")
                        if (DATA_DIR / "shops.json").exists() else {}).keys())

        v_type = _combo(f, 0, "NPC type",    types,   types[0] if types else "villager")
        v_dlg  = _combo(f, 1, "Dialogue ID", [""] + dlg_ids, "")
        v_shop = _combo(f, 2, "Shop ID",     [""] + shops,   "")
        v_x    = _spin(f,  3, "X (world)",   0, 99999, wx)
        v_y    = _spin(f,  4, "Y (world)",   0, 9999,  wy)

        def ok():
            entry = {"type": v_type.get(), "x": int(v_x.get()), "y": int(v_y.get())}
            if v_dlg.get():
                entry["dialogue_id"] = v_dlg.get()
            if v_shop.get():
                entry["shop_id"] = v_shop.get()
            self._zone.setdefault("npcs", []).append(entry)
            self._redraw()
            win.destroy()

        ttk.Button(f, text="Place", command=ok).grid(row=5, column=0, columnspan=2, pady=8)

    def _add_drop_dialog(self, wx, wy):
        win = tk.Toplevel(self)
        win.title("Place Item Drop")
        win.grab_set()
        f = ttk.Frame(win, padding=12)
        f.pack()
        items = list(self._items.keys()) or ["wood"]
        v_item = _combo(f, 0, "Item ID", items, items[0] if items else "wood")
        v_qty  = _spin(f, 1, "Quantity", 1, 999, 1)
        v_x    = _spin(f, 2, "X (world)", 0, 99999, wx)
        v_y    = _spin(f, 3, "Y (world)", 0, 9999, wy)

        def ok():
            self._zone.setdefault("item_drops", []).append({
                "item_id": v_item.get(), "quantity": int(v_qty.get()),
                "x": int(v_x.get()), "y": int(v_y.get())
            })
            self._redraw()
            win.destroy()

        ttk.Button(f, text="Place", command=ok).grid(row=4, column=0, columnspan=2, pady=8)

    def _add_exit_dialog(self, x, y, w, h):
        win = tk.Toplevel(self)
        win.title("Zone Exit")
        win.grab_set()
        f = ttk.Frame(win, padding=12)
        f.pack()
        zones = [p.stem for p in ZONES_DIR.glob("*.json")] if ZONES_DIR.exists() else []
        v_tz = _combo(f, 0, "Target zone", zones, zones[0] if zones else "zone_02")
        v_sox= _field(f, 1, "Spawn override X (blank=spawn)", "")
        v_soy= _field(f, 2, "Spawn override Y", "")

        def ok():
            entry = {"x": x, "y": y, "w": w, "h": h, "target_zone": v_tz.get()}
            sx, sy = v_sox.get().strip(), v_soy.get().strip()
            if sx and sy:
                try:
                    entry["spawn_override"] = [int(sx), int(sy)]
                except ValueError:
                    pass
            self._zone.setdefault("exits", []).append(entry)
            self._redraw()
            win.destroy()

        ttk.Button(f, text="Add Exit", command=ok).grid(row=3, column=0, columnspan=2, pady=8)

    def _add_building_dialog(self, wx, wy):
        win = tk.Toplevel(self)
        win.title("Place Building")
        win.grab_set()
        f = ttk.Frame(win, padding=12)
        f.pack()
        zones = [p.stem for p in ZONES_DIR.glob("*.json")] if ZONES_DIR.exists() else []
        v_w   = _spin(f, 0, "Building width",   20, 2000, 200)
        v_h   = _spin(f, 1, "Building height",  20, 1000, 180)
        v_dw  = _spin(f, 2, "Door width",        10, 200,  40)
        v_dh  = _spin(f, 3, "Door height",       10, 300,  64)
        v_tz  = _combo(f, 4, "Target zone", zones, zones[0] if zones else "")
        v_lbl = _field(f, 5, "Label (optional)", "")

        def ok():
            bw, bh = int(v_w.get()), int(v_h.get())
            dw, dh = int(v_dw.get()), int(v_dh.get())
            bx, by = wx - bw // 2, wy - bh
            entry = {
                "x": bx, "y": by, "w": bw, "h": bh,
                "door_x": bx + (bw - dw) // 2,
                "door_y": by + bh - dh,
                "door_w": dw, "door_h": dh,
                "target_zone": v_tz.get(),
            }
            if v_lbl.get().strip():
                entry["label"] = v_lbl.get().strip()
            self._zone.setdefault("buildings", []).append(entry)
            self._redraw()
            win.destroy()

        ttk.Button(f, text="Place Building", command=ok).grid(
            row=6, column=0, columnspan=2, pady=8)

    # ------------------------------------------------------------------
    # Zone file management
    # ------------------------------------------------------------------

    def _new_zone(self):
        self._zone = self._blank_zone()
        self._zone_path = None
        self._v_id.set("new_zone")
        self._v_sx.set("200")
        self._v_sy.set("596")
        self._bg_btn.set([30, 30, 40])
        self._v_music.set("")
        self._redraw()

    def _open_zone(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            initialdir=str(ZONES_DIR),
            title="Open Zone",
            filetypes=[("Zone JSON", "*.json")],
        )
        if not path:
            return
        try:
            z = _load(Path(path))
        except Exception as e:
            messagebox.showerror("Error", f"Could not load zone:\n{e}")
            return
        self._zone = z
        self._zone_path = Path(path)
        self._v_id.set(z.get("id", Path(path).stem))
        spawn = z.get("spawn", [200, 596])
        self._v_sx.set(str(spawn[0]))
        self._v_sy.set(str(spawn[1]))
        self._bg_btn.set(z.get("bg_color", [30, 30, 40]))
        self._v_music.set(z.get("music") or "")
        self._redraw()

    def _save_zone(self):
        # Pull meta from top bar into zone dict
        try:
            self._zone["id"]     = self._v_id.get().strip() or "new_zone"
            self._zone["spawn"]  = [int(self._v_sx.get()), int(self._v_sy.get())]
            self._zone["bg_color"] = self._bg_btn.get()
            music = self._v_music.get().strip()
            self._zone["music"]  = music if music else None
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid spawn value: {e}")
            return

        if self._zone_path is None:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                initialdir=str(ZONES_DIR),
                title="Save Zone As",
                defaultextension=".json",
                filetypes=[("Zone JSON", "*.json")],
                initialfile=f"{self._zone['id']}.json",
            )
            if not path:
                return
            self._zone_path = Path(path)

        # Ensure the zones directory exists
        self._zone_path.parent.mkdir(parents=True, exist_ok=True)
        _save(self._zone_path, self._zone)
        messagebox.showinfo("Saved", f"Zone saved to:\n{self._zone_path}")


# ---------------------------------------------------------------------------
# Shop tab
# ---------------------------------------------------------------------------

class ShopTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._path = DATA_DIR / "shops.json"
        self._data = _load(self._path) if self._path.exists() else {}
        self._items = _load(DATA_DIR / "items.json") if (DATA_DIR / "items.json").exists() else {}
        self._selected = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)
        ttk.Label(left, text="Shops", font=("", 10, "bold")).pack()
        self._listbox = tk.Listbox(left, width=20, exportselection=False)
        self._listbox.pack(fill="y", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="New",    command=self._new).pack(side="left")
        ttk.Button(btn_row, text="Delete", command=self._delete).pack(side="left", padx=4)

        right = ttk.LabelFrame(self, text="Shop Properties")
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)
        right.columnconfigure(1, weight=1)

        f = right
        self._v_id       = _field(f, 0, "Shop ID (key)")
        self._v_name     = _field(f, 1, "Display name")
        self._v_buyrate  = _spin(f,  2, "Buy rate (sell multiplier)", 0.0, 1.0, 0.5, 0.05)

        ttk.Label(f, text="Inventory:", font=("", 9, "bold")).grid(
            row=3, column=0, sticky="w", pady=(10, 2))

        inv_frame = ttk.Frame(f)
        inv_frame.grid(row=4, column=0, columnspan=2, sticky="ew")

        self._inv_tree = ttk.Treeview(
            inv_frame, columns=("item", "price", "stock"), show="headings", height=8)
        self._inv_tree.heading("item",  text="Item ID")
        self._inv_tree.heading("price", text="Price (g)")
        self._inv_tree.heading("stock", text="Stock (-1=∞)")
        self._inv_tree.column("item",  width=160)
        self._inv_tree.column("price", width=80)
        self._inv_tree.column("stock", width=80)
        self._inv_tree.pack(side="left", fill="x", expand=True)

        btns = ttk.Frame(inv_frame)
        btns.pack(side="left", padx=(4, 0))
        ttk.Button(btns, text="+", width=3, command=self._add_item).pack(pady=2)
        ttk.Button(btns, text="−", width=3, command=self._del_item).pack()

        ttk.Button(f, text="Save Shop", command=self._save_entry).grid(
            row=5, column=0, columnspan=2, pady=10)

    def _refresh_list(self):
        self._listbox.delete(0, "end")
        for k in self._data:
            self._listbox.insert("end", k)

    def _on_select(self, _=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        key = self._listbox.get(sel[0])
        self._selected = key
        d = self._data[key]
        self._v_id.set(key)
        self._v_name.set(d.get("name", key))
        self._v_buyrate.set(float(d.get("buy_rate", 0.5)))
        self._inv_tree.delete(*self._inv_tree.get_children())
        for entry in d.get("inventory", []):
            self._inv_tree.insert("", "end", values=(
                entry["item_id"], entry["price"], entry.get("stock", -1)))

    def _new(self):
        key = simpledialog.askstring("New Shop", "Enter shop ID (e.g. 'blacksmith'):")
        if not key:
            return
        key = key.strip().lower().replace(" ", "_")
        if key in self._data:
            messagebox.showerror("Error", f"'{key}' already exists.")
            return
        self._data[key] = {"name": key.replace("_", " ").title(),
                           "buy_rate": 0.5, "inventory": []}
        self._refresh_list()
        keys = list(self._data.keys())
        self._listbox.selection_set(keys.index(key))
        self._on_select()

    def _delete(self):
        if not self._selected:
            return
        if not messagebox.askyesno("Delete", f"Delete shop '{self._selected}'?"):
            return
        del self._data[self._selected]
        self._selected = None
        self._refresh_list()
        _save(self._path, self._data)

    def _add_item(self):
        win = tk.Toplevel(self)
        win.title("Add Shop Item")
        win.grab_set()
        f = ttk.Frame(win, padding=12)
        f.pack()
        items = list(self._items.keys()) or []
        v_item  = _combo(f, 0, "Item ID", items, items[0] if items else "")
        v_price = _spin(f,  1, "Price (gold)", 1, 9999, 10)
        v_stock = _spin(f,  2, "Stock (-1 = unlimited)", -1, 999, -1)

        def ok():
            self._inv_tree.insert("", "end", values=(
                v_item.get(), int(v_price.get()), int(v_stock.get())))
            win.destroy()

        ttk.Button(f, text="Add", command=ok).grid(row=3, column=0, columnspan=2, pady=8)

    def _del_item(self):
        sel = self._inv_tree.selection()
        if sel:
            self._inv_tree.delete(sel[0])

    def _save_entry(self):
        key = self._v_id.get().strip().lower().replace(" ", "_")
        if not key:
            messagebox.showerror("Error", "ID cannot be empty.")
            return
        inventory = []
        for row_id in self._inv_tree.get_children():
            vals = self._inv_tree.item(row_id, "values")
            inventory.append({"item_id": vals[0], "price": int(vals[1]),
                               "stock": int(vals[2])})
        entry = {
            "name":      self._v_name.get() or key,
            "buy_rate":  round(self._v_buyrate.get(), 2),
            "inventory": inventory,
        }
        if self._selected and self._selected != key:
            del self._data[self._selected]
        self._data[key] = entry
        self._selected = key
        _save(self._path, self._data)
        self._refresh_list()
        keys = list(self._data.keys())
        self._listbox.selection_set(keys.index(key))
        messagebox.showinfo("Saved", f"Shop '{key}' saved.")


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class EditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Survival Game — Content Editor")
        self.geometry("1260x800")
        self.minsize(900, 600)

        # Style
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Notebook with all tabs
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        nb.add(EnemyTab(nb),   text="  Enemies  ")
        nb.add(ItemTab(nb),    text="  Items  ")
        nb.add(RecipeTab(nb),  text="  Recipes  ")
        nb.add(NPCTab(nb),     text="  NPCs  ")
        nb.add(AbilityTab(nb), text="  Abilities  ")
        nb.add(ShopTab(nb),    text="  Shops  ")
        nb.add(ZoneTab(nb),    text="  Zone Editor  ")

        # Menu bar
        menu = tk.Menu(self)
        self.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.quit)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Ensure data directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ZONES_DIR.mkdir(parents=True, exist_ok=True)

    app = EditorApp()
    app.mainloop()
