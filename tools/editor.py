#!/usr/bin/env python3
"""
Survival Game — Content Editor
Can run standalone (anywhere) or from the project root.

Usage:
  python editor.py               — auto-detects data/ or prompts on first run
  python editor.py /path/to/data — use this data directory directly

Tabs:
  Enemies   — enemies.json  (stats, drops, xp_reward)
  Items     — items.json    (name, color, use effects, sell_value)
  Recipes   — recipes.json
  NPCs      — npcs.json + dialogue.json
  Abilities — abilities.json
  Shops     — shops.json
  Quests    — quests.json
  Zone Editor — data/zones/*.json  (visual canvas with full toolset)

Zone editor controls:
  Tools:    Select  Platform  Enemy  NPC  Save Point  Item Drop
            Exit    Building  Chest
  G         Toggle grid snapping (default 20px)
  Ctrl+Z    Undo (up to 20 steps)
  Ctrl+Y    Redo
  Delete    Remove selected element
  Arrow keys  Nudge selected 1px  (Shift = 10px)
  Escape    Deselect
"""

import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, simpledialog, filedialog
from pathlib import Path
from copy import deepcopy

# ---------------------------------------------------------------------------
# Data-directory resolution — works standalone or inside the project tree
# ---------------------------------------------------------------------------

_EDITOR_DIR  = Path(__file__).parent
_CONFIG_FILE = _EDITOR_DIR / "editor_config.json"


def _resolve_data_dir() -> Path:
    """
    Locate the game's data/ directory.  Priority:
    1. Command-line argument  (python editor.py /some/path/data)
    2. Sibling data/ directory  (in-project: tools/../data)
    3. Saved config            (editor_config.json next to this file)
    4. User dialog             (ask once, save for next time)
    """
    # 1. CLI argument
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.is_dir():
            return p

    # 2. Sibling — works when editor.py is inside tools/ inside the project
    sibling = _EDITOR_DIR.parent / "data"
    if sibling.is_dir():
        return sibling

    # 3. Saved config
    if _CONFIG_FILE.exists():
        try:
            cfg = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            saved = Path(cfg.get("data_dir", ""))
            if saved.is_dir():
                return saved
        except Exception:
            pass

    # 4. Ask the user
    root = tk.Tk(); root.withdraw()
    messagebox.showinfo(
        "Survival Game Editor — First Run",
        "Select the 'data' folder inside your game installation.\n\n"
        "Example:  C:/survival-game/data\n\n"
        "This is only asked once; the path is saved to editor_config.json.",
    )
    chosen = filedialog.askdirectory(title="Select game 'data' folder")
    root.destroy()
    if not chosen:
        messagebox.showerror("Editor", "No data folder selected. Editor cannot start.")
        raise SystemExit(1)

    p = Path(chosen)
    try:
        _CONFIG_FILE.write_text(
            json.dumps({"data_dir": str(p)}, indent=2), encoding="utf-8"
        )
    except Exception:
        pass
    return p


DATA_DIR  = _resolve_data_dir()
ZONES_DIR = DATA_DIR / "zones"

# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _load(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _save(path: Path, data) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)

def _hex(rgb) -> str:
    r, g, b = (max(0, min(255, int(c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"

def _rgb(h: str) -> list:
    h = h.lstrip("#")
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]

# ---------------------------------------------------------------------------
# Reusable form helpers
# ---------------------------------------------------------------------------

class ColorButton(tk.Button):
    def __init__(self, parent, initial=(200, 200, 200), **kw):
        self._color = list(initial)
        super().__init__(parent, command=self._pick, width=5, **kw)
        self._refresh()

    def _pick(self):
        r = colorchooser.askcolor(color=_hex(self._color), title="Pick color")
        if r[1]:
            self._color = _rgb(r[1])
            self._refresh()

    def _refresh(self):
        self.config(bg=_hex(self._color), activebackground=_hex(self._color), text="  ")

    def get(self) -> list:  return list(self._color)
    def set(self, rgb):     self._color = list(rgb); self._refresh()


def _field(parent, row, label, default="", width=24, col=0):
    ttk.Label(parent, text=label).grid(row=row, column=col,   sticky="w", pady=2, padx=4)
    v = tk.StringVar(value=str(default) if default is not None else "")
    ttk.Entry(parent, textvariable=v, width=width).grid(
        row=row, column=col+1, sticky="ew", padx=(4,4), pady=2)
    return v

def _spin(parent, row, label, lo=0, hi=9999, default=0, step=1.0, col=0):
    ttk.Label(parent, text=label).grid(row=row, column=col,   sticky="w", pady=2, padx=4)
    v = tk.DoubleVar(value=float(default))
    tk.Spinbox(parent, textvariable=v, from_=lo, to=hi, increment=step,
               width=10).grid(row=row, column=col+1, sticky="w", padx=(4,4), pady=2)
    return v

def _check(parent, row, label, default=False, col=0):
    ttk.Label(parent, text=label).grid(row=row, column=col,   sticky="w", pady=2, padx=4)
    v = tk.BooleanVar(value=bool(default))
    ttk.Checkbutton(parent, variable=v).grid(row=row, column=col+1, sticky="w", padx=(4,4))
    return v

def _combo(parent, row, label, values=(), default="", width=22, col=0):
    ttk.Label(parent, text=label).grid(row=row, column=col,   sticky="w", pady=2, padx=4)
    v = tk.StringVar(value=str(default) if default is not None else "")
    ttk.Combobox(parent, textvariable=v, values=list(values),
                 state="readonly", width=width).grid(
        row=row, column=col+1, sticky="w", padx=(4,4), pady=2)
    return v

def _combo_e(parent, row, label, values=(), default="", width=22, col=0):
    """Editable combobox (not readonly)."""
    ttk.Label(parent, text=label).grid(row=row, column=col,   sticky="w", pady=2, padx=4)
    v = tk.StringVar(value=str(default) if default is not None else "")
    ttk.Combobox(parent, textvariable=v, values=list(values),
                 width=width).grid(row=row, column=col+1, sticky="w", padx=(4,4), pady=2)
    return v

def _list_ids(path: Path) -> list:
    try:
        return list(_load(path).keys())
    except Exception:
        return []

# ---------------------------------------------------------------------------
# Enemy tab
# ---------------------------------------------------------------------------

class EnemyTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._path = DATA_DIR / "enemies.json"
        self._data = _load(self._path) if self._path.exists() else {}
        self._selected = None
        self._build()
        self._refresh()

    def _build(self):
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(8,4), pady=8)
        ttk.Label(left, text="Enemy Types", font=("",10,"bold")).pack()
        self._lb = tk.Listbox(left, width=18, exportselection=False)
        self._lb.pack(fill="y", expand=True)
        self._lb.bind("<<ListboxSelect>>", self._on_sel)
        br = ttk.Frame(left); br.pack(fill="x", pady=(4,0))
        ttk.Button(br, text="New",    command=self._new).pack(side="left")
        ttk.Button(br, text="Delete", command=self._del).pack(side="left", padx=4)

        right = ttk.LabelFrame(self, text="Properties")
        right.pack(side="left", fill="both", expand=True, padx=(4,8), pady=8)
        right.columnconfigure(1, weight=1)
        f = right; r = 0
        self._v_id     = _field(f,r,"ID (key)");                 r+=1
        self._v_health = _spin(f,r,"Health",          1,9999,100);r+=1
        self._v_xp     = _spin(f,r,"XP reward",       0,9999,25); r+=1
        self._v_w      = _spin(f,r,"Width",            1,200,40);  r+=1
        self._v_h      = _spin(f,r,"Height",           1,400,60);  r+=1
        self._v_speed  = _spin(f,r,"Patrol speed",     0,1000,80); r+=1
        self._v_cspeed = _spin(f,r,"Chase speed",      0,1000,180);r+=1
        self._v_aggro  = _spin(f,r,"Aggro range",      0,2000,300);r+=1
        self._v_deaggro= _spin(f,r,"De-aggro range",   0,3000,500);r+=1
        self._v_atk_r  = _spin(f,r,"Attack range",     0,500,65);  r+=1
        self._v_atk_d  = _spin(f,r,"Attack damage",    0,999,15);  r+=1
        self._v_atk_cd = _spin(f,r,"Attack cooldown",  0.1,10,1.5,0.1); r+=1
        self._v_patrol = _spin(f,r,"Patrol radius",    0,5000,200);r+=1
        self._v_sprite = _field(f,r,"Sprite name","enemy_basic"); r+=1
        ttk.Label(f,text="Drops:",font=("",9,"bold")).grid(
            row=r,column=0,sticky="w",pady=(8,2),padx=4); r+=1
        df = ttk.Frame(f); df.grid(row=r,column=0,columnspan=2,sticky="ew"); r+=1
        self._dtree = ttk.Treeview(df,columns=("item","qty","chance"),show="headings",height=4)
        for col,w in [("item",120),("qty",50),("chance",60)]:
            self._dtree.heading(col,text=col.title()); self._dtree.column(col,width=w)
        self._dtree.pack(side="left",fill="x",expand=True)
        db = ttk.Frame(df); db.pack(side="left",padx=(4,0))
        ttk.Button(db,text="+",width=3,command=self._add_drop).pack(pady=2)
        ttk.Button(db,text="−",width=3,command=self._del_drop).pack()
        ttk.Button(f,text="Save Enemy",command=self._save).grid(
            row=r,column=0,columnspan=2,pady=10)

    def _refresh(self):
        self._lb.delete(0,"end")
        for k in self._data: self._lb.insert("end",k)

    def _on_sel(self,_=None):
        sel = self._lb.curselection()
        if not sel: return
        key = self._lb.get(sel[0]); self._selected = key; d = self._data[key]
        self._v_id.set(key);     self._v_health.set(d.get("health",100))
        self._v_xp.set(d.get("xp_reward",0))
        self._v_w.set(d.get("width",40));      self._v_h.set(d.get("height",60))
        self._v_speed.set(d.get("speed",80));  self._v_cspeed.set(d.get("chase_speed",180))
        self._v_aggro.set(d.get("aggro_range",300)); self._v_deaggro.set(d.get("deaggro_range",500))
        self._v_atk_r.set(d.get("attack_range",65)); self._v_atk_d.set(d.get("attack_damage",15))
        self._v_atk_cd.set(d.get("attack_cooldown",1.5)); self._v_patrol.set(d.get("patrol_radius",200))
        self._v_sprite.set(d.get("sprite","enemy_basic"))
        self._dtree.delete(*self._dtree.get_children())
        for drop in d.get("drops",[]):
            self._dtree.insert("","end",values=(drop.get("item_id",""),drop.get("quantity",1),drop.get("chance",1.0)))

    def _new(self):
        key = simpledialog.askstring("New Enemy","Enemy type ID:")
        if not key: return
        key = key.strip().lower().replace(" ","_")
        if key in self._data: messagebox.showerror("Error",f"'{key}' exists"); return
        self._data[key] = {"sprite":f"enemy_{key}","health":100,"xp_reward":25,"width":40,"height":60,
            "speed":80,"chase_speed":180,"aggro_range":300,"deaggro_range":500,
            "attack_range":65,"attack_damage":15,"attack_cooldown":1.5,"patrol_radius":200,"drops":[]}
        self._refresh(); keys=list(self._data.keys())
        self._lb.selection_set(keys.index(key)); self._on_sel()

    def _del(self):
        if not self._selected: return
        if not messagebox.askyesno("Delete",f"Delete '{self._selected}'?"): return
        del self._data[self._selected]; self._selected=None; self._refresh(); _save(self._path,self._data)

    def _add_drop(self):
        items = _list_ids(DATA_DIR/"items.json")
        win = tk.Toplevel(self); win.title("Add Drop"); win.grab_set()
        f = ttk.Frame(win,padding=12); f.pack()
        v_item  = _combo_e(f,0,"Item ID",items,items[0] if items else "",20)
        v_qty   = _spin(f,1,"Quantity",1,99,1)
        v_chance= _spin(f,2,"Chance",0,1,1.0,0.05)
        def ok():
            self._dtree.insert("","end",values=(v_item.get(),int(v_qty.get()),round(float(v_chance.get()),2)))
            win.destroy()
        ttk.Button(f,text="Add",command=ok).grid(row=3,column=0,columnspan=2,pady=8)

    def _del_drop(self):
        sel=self._dtree.selection()
        if sel: self._dtree.delete(sel[0])

    def _save(self):
        key = self._v_id.get().strip().lower().replace(" ","_")
        if not key: messagebox.showerror("Error","ID empty"); return
        drops=[]
        for rid in self._dtree.get_children():
            v=self._dtree.item(rid,"values")
            drops.append({"item_id":v[0],"quantity":int(v[1]),"chance":float(v[2])})
        entry={"sprite":self._v_sprite.get() or f"enemy_{key}",
               "health":int(self._v_health.get()),"xp_reward":int(self._v_xp.get()),
               "width":int(self._v_w.get()),"height":int(self._v_h.get()),
               "speed":int(self._v_speed.get()),"chase_speed":int(self._v_cspeed.get()),
               "aggro_range":int(self._v_aggro.get()),"deaggro_range":int(self._v_deaggro.get()),
               "attack_range":int(self._v_atk_r.get()),"attack_damage":int(self._v_atk_d.get()),
               "attack_cooldown":round(self._v_atk_cd.get(),2),"patrol_radius":int(self._v_patrol.get()),
               "drops":drops}
        if self._selected and self._selected!=key: del self._data[self._selected]
        self._data[key]=entry; self._selected=key; _save(self._path,self._data)
        self._refresh(); self._lb.selection_set(list(self._data.keys()).index(key))
        messagebox.showinfo("Saved",f"Enemy '{key}' saved.")

# ---------------------------------------------------------------------------
# Item tab
# ---------------------------------------------------------------------------

class ItemTab(ttk.Frame):
    _USE = ("","heal","equip_ability")
    def __init__(self, parent):
        super().__init__(parent)
        self._path = DATA_DIR/"items.json"
        self._data = _load(self._path) if self._path.exists() else {}
        self._selected = None
        self._build(); self._refresh()

    def _build(self):
        left = ttk.Frame(self); left.pack(side="left",fill="y",padx=(8,4),pady=8)
        ttk.Label(left,text="Items",font=("",10,"bold")).pack()
        self._lb=tk.Listbox(left,width=22,exportselection=False)
        self._lb.pack(fill="y",expand=True); self._lb.bind("<<ListboxSelect>>",self._on_sel)
        br=ttk.Frame(left); br.pack(fill="x",pady=(4,0))
        ttk.Button(br,text="New",command=self._new).pack(side="left")
        ttk.Button(br,text="Delete",command=self._del).pack(side="left",padx=4)

        right=ttk.LabelFrame(self,text="Properties")
        right.pack(side="left",fill="both",expand=True,padx=(4,8),pady=8)
        right.columnconfigure(1,weight=1)
        f=right; r=0
        self._v_id   = _field(f,r,"ID (key)");        r+=1
        self._v_name = _field(f,r,"Display name");     r+=1
        ttk.Label(f,text="Color").grid(row=r,column=0,sticky="w",pady=2,padx=4)
        self._color_btn=ColorButton(f,initial=(200,200,200))
        self._color_btn.grid(row=r,column=1,sticky="w",padx=(4,4)); r+=1
        self._v_stack = _check(f,r,"Stackable",True);  r+=1
        self._v_maxst = _spin(f,r,"Max stack",1,9999,99); r+=1
        self._v_sv    = _spin(f,r,"Sell value (gold)",0,9999,0); r+=1
        self._v_use   = _combo(f,r,"Use effect",self._USE,""); r+=1
        self._v_heal  = _spin(f,r,"Heal amount",0,999,0); r+=1
        self._v_abid  = _combo_e(f,r,"Ability ID",_list_ids(DATA_DIR/"abilities.json"),"",20); r+=1
        ttk.Button(f,text="Save Item",command=self._save_entry).grid(row=r,column=0,columnspan=2,pady=10)

    def _refresh(self):
        self._lb.delete(0,"end")
        for k in self._data: self._lb.insert("end",k)

    def _on_sel(self,_=None):
        sel=self._lb.curselection()
        if not sel: return
        key=self._lb.get(sel[0]); self._selected=key; d=self._data[key]
        self._v_id.set(key); self._v_name.set(d.get("name",key))
        self._color_btn.set(d.get("color",[200,200,200]))
        self._v_stack.set(d.get("stackable",False)); self._v_maxst.set(float(d.get("max_stack",1)))
        self._v_sv.set(float(d.get("sell_value",0))); self._v_use.set(d.get("use",""))
        self._v_heal.set(float(d.get("heal_amount",0))); self._v_abid.set(d.get("ability_id",""))

    def _new(self):
        key=simpledialog.askstring("New Item","Item ID:")
        if not key: return
        key=key.strip().lower().replace(" ","_")
        if key in self._data: messagebox.showerror("Error",f"'{key}' exists"); return
        self._data[key]={"name":key.replace("_"," ").title(),"color":[200,200,200],"stackable":True,"max_stack":99}
        self._refresh(); keys=list(self._data.keys())
        self._lb.selection_set(keys.index(key)); self._on_sel()

    def _del(self):
        if not self._selected: return
        if not messagebox.askyesno("Delete",f"Delete '{self._selected}'?"): return
        del self._data[self._selected]; self._selected=None; self._refresh(); _save(self._path,self._data)

    def _save_entry(self):
        key=self._v_id.get().strip().lower().replace(" ","_")
        if not key: messagebox.showerror("Error","ID empty"); return
        entry={"name":self._v_name.get() or key,"color":self._color_btn.get(),
               "stackable":self._v_stack.get(),"max_stack":int(self._v_maxst.get())}
        sv=int(self._v_sv.get())
        if sv>0: entry["sell_value"]=sv
        use=self._v_use.get()
        if use: entry["use"]=use
        if use=="heal": entry["heal_amount"]=int(self._v_heal.get())
        if use=="equip_ability" and self._v_abid.get(): entry["ability_id"]=self._v_abid.get().strip()
        if self._selected and self._selected!=key: del self._data[self._selected]
        self._data[key]=entry; self._selected=key; _save(self._path,self._data)
        self._refresh(); self._lb.selection_set(list(self._data.keys()).index(key))
        messagebox.showinfo("Saved",f"Item '{key}' saved.")

# ---------------------------------------------------------------------------
# Recipe tab
# ---------------------------------------------------------------------------

class RecipeTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._path = DATA_DIR/"recipes.json"
        self._data = _load(self._path) if self._path.exists() else {}
        self._selected = None
        self._build(); self._refresh()

    def _build(self):
        left=ttk.Frame(self); left.pack(side="left",fill="y",padx=(8,4),pady=8)
        ttk.Label(left,text="Recipes",font=("",10,"bold")).pack()
        self._lb=tk.Listbox(left,width=22,exportselection=False)
        self._lb.pack(fill="y",expand=True); self._lb.bind("<<ListboxSelect>>",self._on_sel)
        br=ttk.Frame(left); br.pack(fill="x",pady=(4,0))
        ttk.Button(br,text="New",command=self._new).pack(side="left")
        ttk.Button(br,text="Delete",command=self._del).pack(side="left",padx=4)

        right=ttk.LabelFrame(self,text="Properties")
        right.pack(side="left",fill="both",expand=True,padx=(4,8),pady=8)
        right.columnconfigure(1,weight=1)
        f=right; r=0
        self._v_id     = _field(f,r,"Recipe ID"); r+=1
        self._v_name   = _field(f,r,"Display name"); r+=1
        items=_list_ids(DATA_DIR/"items.json")
        self._v_result = _combo_e(f,r,"Result item",items,"",20); r+=1
        self._v_count  = _spin(f,r,"Result count",1,999,1); r+=1
        ttk.Label(f,text="Ingredients:",font=("",9,"bold")).grid(row=r,column=0,sticky="w",pady=(8,2),padx=4); r+=1
        if_=ttk.Frame(f); if_.grid(row=r,column=0,columnspan=2,sticky="ew"); r+=1
        self._itree=ttk.Treeview(if_,columns=("item","qty"),show="headings",height=5)
        self._itree.heading("item",text="Item ID"); self._itree.heading("qty",text="Qty")
        self._itree.column("item",width=160); self._itree.column("qty",width=70)
        self._itree.pack(side="left",fill="x",expand=True)
        ib=ttk.Frame(if_); ib.pack(side="left",padx=(4,0))
        ttk.Button(ib,text="+",width=3,command=self._add_ing).pack(pady=2)
        ttk.Button(ib,text="−",width=3,command=self._del_ing).pack()
        ttk.Button(f,text="Save Recipe",command=self._save).grid(row=r,column=0,columnspan=2,pady=10)

    def _refresh(self):
        self._lb.delete(0,"end")
        for k in self._data: self._lb.insert("end",k)

    def _on_sel(self,_=None):
        sel=self._lb.curselection()
        if not sel: return
        key=self._lb.get(sel[0]); self._selected=key; d=self._data[key]
        self._v_id.set(key); self._v_name.set(d.get("name",key))
        self._v_result.set(d.get("result","")); self._v_count.set(float(d.get("count",1)))
        self._itree.delete(*self._itree.get_children())
        for iid,qty in d.get("ingredients",{}).items(): self._itree.insert("","end",values=(iid,qty))

    def _new(self):
        key=simpledialog.askstring("New Recipe","Recipe ID:")
        if not key: return
        key=key.strip().lower().replace(" ","_")
        if key in self._data: messagebox.showerror("Error",f"'{key}' exists"); return
        self._data[key]={"name":key.replace("_"," ").title(),"result":key,"count":1,"ingredients":{}}
        self._refresh(); keys=list(self._data.keys())
        self._lb.selection_set(keys.index(key)); self._on_sel()

    def _del(self):
        if not self._selected: return
        if not messagebox.askyesno("Delete",f"Delete '{self._selected}'?"): return
        del self._data[self._selected]; self._selected=None; self._refresh(); _save(self._path,self._data)

    def _add_ing(self):
        items=_list_ids(DATA_DIR/"items.json")
        win=tk.Toplevel(self); win.title("Add Ingredient"); win.grab_set()
        f=ttk.Frame(win,padding=12); f.pack()
        vi=_combo_e(f,0,"Item ID",items,items[0] if items else "",20)
        vq=_spin(f,1,"Quantity",1,999,1)
        def ok():
            self._itree.insert("","end",values=(vi.get(),int(vq.get()))); win.destroy()
        ttk.Button(f,text="Add",command=ok).grid(row=2,column=0,columnspan=2,pady=8)

    def _del_ing(self):
        sel=self._itree.selection()
        if sel: self._itree.delete(sel[0])

    def _save(self):
        key=self._v_id.get().strip().lower().replace(" ","_")
        if not key: messagebox.showerror("Error","ID empty"); return
        ings={}
        for rid in self._itree.get_children():
            v=self._itree.item(rid,"values"); ings[v[0]]=int(v[1])
        entry={"name":self._v_name.get() or key,"result":self._v_result.get().strip(),
               "count":int(self._v_count.get()),"ingredients":ings}
        if self._selected and self._selected!=key: del self._data[self._selected]
        self._data[key]=entry; self._selected=key; _save(self._path,self._data)
        self._refresh(); self._lb.selection_set(list(self._data.keys()).index(key))
        messagebox.showinfo("Saved",f"Recipe '{key}' saved.")

# ---------------------------------------------------------------------------
# NPC tab
# ---------------------------------------------------------------------------

class NPCTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._npc_path=DATA_DIR/"npcs.json"; self._dlg_path=DATA_DIR/"dialogue.json"
        self._npcs=_load(self._npc_path) if self._npc_path.exists() else {}
        self._dlgs=_load(self._dlg_path) if self._dlg_path.exists() else {}
        self._sel_npc=None; self._sel_dlg=None
        self._build(); self._refresh_npc(); self._refresh_dlg()

    def _build(self):
        left=ttk.LabelFrame(self,text="NPC Types (npcs.json)")
        left.pack(side="left",fill="y",padx=(8,4),pady=8)
        self._npc_lb=tk.Listbox(left,width=18,exportselection=False)
        self._npc_lb.pack(fill="y",expand=True); self._npc_lb.bind("<<ListboxSelect>>",self._on_npc_sel)
        br=ttk.Frame(left); br.pack(fill="x",pady=(4,0))
        ttk.Button(br,text="New",command=self._new_npc).pack(side="left")
        ttk.Button(br,text="Delete",command=self._del_npc).pack(side="left",padx=2)
        nf=ttk.LabelFrame(left,text="NPC Properties"); nf.pack(fill="x",padx=4,pady=(8,4))
        self._nv_id=_field(nf,0,"ID")
        self._nv_name=_field(nf,1,"Name")
        self._nv_sprite=_field(nf,2,"Sprite")
        ttk.Label(nf,text="Color").grid(row=3,column=0,sticky="w",pady=2,padx=4)
        self._nv_color=ColorButton(nf,initial=(220,190,130))
        self._nv_color.grid(row=3,column=1,sticky="w",padx=(4,4))
        self._nv_w=_spin(nf,4,"Width",1,200,28)
        self._nv_h=_spin(nf,5,"Height",1,400,52)
        ttk.Button(nf,text="Save NPC",command=self._save_npc).grid(row=6,column=0,columnspan=2,pady=6)

        right=ttk.LabelFrame(self,text="Dialogue Scripts (dialogue.json)")
        right.pack(side="left",fill="both",expand=True,padx=(4,8),pady=8)
        self._dlg_lb=tk.Listbox(right,width=22,exportselection=False)
        self._dlg_lb.pack(side="left",fill="y"); self._dlg_lb.bind("<<ListboxSelect>>",self._on_dlg_sel)
        db=ttk.Frame(right); db.pack(side="left",fill="y",padx=(4,0))
        ttk.Button(db,text="New",command=self._new_dlg).pack(pady=2)
        ttk.Button(db,text="Delete",command=self._del_dlg).pack(pady=2)
        lp=ttk.LabelFrame(right,text="Lines"); lp.pack(side="left",fill="both",expand=True,padx=(8,4),pady=4)
        self._dlg_id_var=tk.StringVar()
        ttk.Label(lp,text="Script ID:").pack(anchor="w")
        ttk.Entry(lp,textvariable=self._dlg_id_var,width=26).pack(fill="x",pady=(0,6))
        self._line_lb=tk.Listbox(lp,height=8,exportselection=False); self._line_lb.pack(fill="both",expand=True)
        lb2=ttk.Frame(lp); lb2.pack(fill="x",pady=4)
        ttk.Button(lb2,text="Add",command=self._add_line).pack(side="left")
        ttk.Button(lb2,text="Edit",command=self._edit_line).pack(side="left",padx=4)
        ttk.Button(lb2,text="↑",command=self._mv_up).pack(side="left")
        ttk.Button(lb2,text="↓",command=self._mv_dn).pack(side="left",padx=2)
        ttk.Button(lb2,text="Remove",command=self._del_line).pack(side="left")
        ttk.Button(lp,text="Save Script",command=self._save_dlg).pack(pady=4)

    def _refresh_npc(self):
        self._npc_lb.delete(0,"end")
        for k in self._npcs: self._npc_lb.insert("end",k)
    def _refresh_dlg(self):
        self._dlg_lb.delete(0,"end")
        for k in self._dlgs: self._dlg_lb.insert("end",k)

    def _on_npc_sel(self,_=None):
        sel=self._npc_lb.curselection()
        if not sel: return
        key=self._npc_lb.get(sel[0]); self._sel_npc=key; d=self._npcs[key]
        self._nv_id.set(key); self._nv_name.set(d.get("name",key))
        self._nv_sprite.set(d.get("sprite",f"npc_{key}")); self._nv_color.set(d.get("color",[220,190,130]))
        self._nv_w.set(float(d.get("width",28))); self._nv_h.set(float(d.get("height",52)))

    def _on_dlg_sel(self,_=None):
        sel=self._dlg_lb.curselection()
        if not sel: return
        key=self._dlg_lb.get(sel[0]); self._sel_dlg=key
        self._dlg_id_var.set(key); self._line_lb.delete(0,"end")
        for l in self._dlgs.get(key,[]): self._line_lb.insert("end",l)

    def _new_npc(self):
        key=simpledialog.askstring("New NPC","NPC type ID:")
        if not key: return
        key=key.strip().lower().replace(" ","_")
        if key in self._npcs: messagebox.showerror("Error",f"'{key}' exists"); return
        self._npcs[key]={"sprite":f"npc_{key}","name":key.title(),"color":[220,190,130],"width":28,"height":52}
        self._refresh_npc(); keys=list(self._npcs.keys()); self._npc_lb.selection_set(keys.index(key)); self._on_npc_sel()

    def _del_npc(self):
        if not self._sel_npc: return
        if not messagebox.askyesno("Delete",f"Delete NPC type '{self._sel_npc}'?"): return
        del self._npcs[self._sel_npc]; self._sel_npc=None; self._refresh_npc(); _save(self._npc_path,self._npcs)

    def _save_npc(self):
        key=self._nv_id.get().strip().lower().replace(" ","_")
        if not key: return
        entry={"sprite":self._nv_sprite.get() or f"npc_{key}","name":self._nv_name.get() or key.title(),
               "color":self._nv_color.get(),"width":int(self._nv_w.get()),"height":int(self._nv_h.get())}
        if self._sel_npc and self._sel_npc!=key: del self._npcs[self._sel_npc]
        self._npcs[key]=entry; self._sel_npc=key; _save(self._npc_path,self._npcs)
        self._refresh_npc(); self._npc_lb.selection_set(list(self._npcs.keys()).index(key))
        messagebox.showinfo("Saved",f"NPC type '{key}' saved.")

    def _new_dlg(self):
        key=simpledialog.askstring("New Script","Script ID:")
        if not key: return
        key=key.strip().lower().replace(" ","_")
        if key in self._dlgs: messagebox.showerror("Error",f"'{key}' exists"); return
        self._dlgs[key]=["Hello, traveller!"]; self._refresh_dlg()
        keys=list(self._dlgs.keys()); self._dlg_lb.selection_set(keys.index(key)); self._on_dlg_sel()

    def _del_dlg(self):
        if not self._sel_dlg: return
        if not messagebox.askyesno("Delete",f"Delete '{self._sel_dlg}'?"): return
        del self._dlgs[self._sel_dlg]; self._sel_dlg=None; self._refresh_dlg(); _save(self._dlg_path,self._dlgs)

    def _add_line(self):
        t=simpledialog.askstring("Add Line","Enter dialogue line:")
        if t: self._line_lb.insert("end",t)
    def _edit_line(self):
        sel=self._line_lb.curselection()
        if not sel: return
        new=simpledialog.askstring("Edit Line","Edit:",initialvalue=self._line_lb.get(sel[0]))
        if new is not None: self._line_lb.delete(sel[0]); self._line_lb.insert(sel[0],new)
    def _del_line(self):
        sel=self._line_lb.curselection()
        if sel: self._line_lb.delete(sel[0])
    def _mv_up(self):
        sel=self._line_lb.curselection()
        if not sel or sel[0]==0: return
        i=sel[0]; v=self._line_lb.get(i); self._line_lb.delete(i); self._line_lb.insert(i-1,v); self._line_lb.selection_set(i-1)
    def _mv_dn(self):
        sel=self._line_lb.curselection()
        if not sel or sel[0]>=self._line_lb.size()-1: return
        i=sel[0]; v=self._line_lb.get(i); self._line_lb.delete(i); self._line_lb.insert(i+1,v); self._line_lb.selection_set(i+1)
    def _save_dlg(self):
        key=self._dlg_id_var.get().strip().lower().replace(" ","_")
        if not key: return
        lines=list(self._line_lb.get(0,"end"))
        if self._sel_dlg and self._sel_dlg!=key: del self._dlgs[self._sel_dlg]
        self._dlgs[key]=lines; self._sel_dlg=key; _save(self._dlg_path,self._dlgs)
        self._refresh_dlg(); self._dlg_lb.selection_set(list(self._dlgs.keys()).index(key))
        messagebox.showinfo("Saved",f"Script '{key}' saved.")

# ---------------------------------------------------------------------------
# Ability tab
# ---------------------------------------------------------------------------

class AbilityTab(ttk.Frame):
    _TYPES  = ("melee","projectile","wave","area","aura")
    _STATUS = ("","poison","burn","stun","freeze","slow")
    def __init__(self, parent):
        super().__init__(parent)
        self._path=DATA_DIR/"abilities.json"
        self._data=_load(self._path) if self._path.exists() else {}
        self._selected=None; self._build(); self._refresh()

    def _build(self):
        left=ttk.Frame(self); left.pack(side="left",fill="y",padx=(8,4),pady=8)
        ttk.Label(left,text="Abilities",font=("",10,"bold")).pack()
        self._lb=tk.Listbox(left,width=22,exportselection=False)
        self._lb.pack(fill="y",expand=True); self._lb.bind("<<ListboxSelect>>",self._on_sel)
        br=ttk.Frame(left); br.pack(fill="x",pady=(4,0))
        ttk.Button(br,text="New",command=self._new).pack(side="left")
        ttk.Button(br,text="Delete",command=self._del).pack(side="left",padx=4)

        right=ttk.LabelFrame(self,text="Properties")
        right.pack(side="left",fill="both",expand=True,padx=(4,8),pady=8)
        right.columnconfigure(1,weight=1); right.columnconfigure(3,weight=1)
        f=right; r=0
        self._v_id      = _field(f,r,"ID (key)");      r+=1
        self._v_name    = _field(f,r,"Display name");  r+=1
        self._v_type    = _combo(f,r,"Type",self._TYPES,"melee"); r+=1
        self._v_damage  = _spin(f,r,"Damage",0,9999,25);   r+=1
        self._v_mana    = _spin(f,r,"Mana cost",0,999,0);  r+=1
        self._v_cd      = _spin(f,r,"Cooldown (s)",0,60,0.45,0.05); r+=1
        self._v_kb      = _spin(f,r,"Knockback",0,9999,0); r+=1
        self._v_speed   = _spin(f,r,"Speed (proj/wave)",0,2000,300); r+=1
        self._v_maxdist = _spin(f,r,"Max distance",0,9999,500); r+=1
        self._v_radius  = _spin(f,r,"Radius (area/aura)",0,999,80); r+=1
        self._v_dur     = _spin(f,r,"Duration (s)",0,30,0.4,0.1); r+=1
        self._v_dps     = _spin(f,r,"DPS (aura)",0,999,0); r+=1
        self._v_sound   = _field(f,r,"Sound name"); r+=1
        ttk.Label(f,text="Status effect:",font=("",9,"bold")).grid(row=r,column=0,sticky="w",pady=(8,2),padx=4); r+=1
        self._v_se_type = _combo(f,r,"  Type",self._STATUS,""); r+=1
        self._v_se_dur  = _spin(f,r,"  Duration (s)",0,30,0,0.5); r+=1
        self._v_se_dps  = _spin(f,r,"  DPS (poison/burn)",0,999,0); r+=1
        self._v_se_slow = _spin(f,r,"  Slow factor",0,1.0,0.5,0.05); r+=1
        ttk.Label(f,text="Color").grid(row=r,column=0,sticky="w",pady=2,padx=4)
        self._color_btn=ColorButton(f,initial=(255,220,50))
        self._color_btn.grid(row=r,column=1,sticky="w",padx=(4,4)); r+=1
        ttk.Button(f,text="Save Ability",command=self._save).grid(row=r,column=0,columnspan=2,pady=10)

    def _refresh(self):
        self._lb.delete(0,"end")
        for k in self._data: self._lb.insert("end",k)

    def _on_sel(self,_=None):
        sel=self._lb.curselection()
        if not sel: return
        key=self._lb.get(sel[0]); self._selected=key; d=self._data[key]
        self._v_id.set(key); self._v_name.set(d.get("name",key)); self._v_type.set(d.get("type","melee"))
        self._v_damage.set(float(d.get("damage",25))); self._v_mana.set(float(d.get("mana_cost",0)))
        self._v_cd.set(float(d.get("cooldown",0.45))); self._v_kb.set(float(d.get("knockback",0)))
        self._v_speed.set(float(d.get("speed",300))); self._v_maxdist.set(float(d.get("max_distance",500)))
        self._v_radius.set(float(d.get("radius",80))); self._v_dur.set(float(d.get("duration",0.4)))
        self._v_dps.set(float(d.get("damage_per_second",0))); self._v_sound.set(d.get("sound",""))
        self._color_btn.set(d.get("color",[255,220,50]))
        se=d.get("status_effect") or {}
        self._v_se_type.set(se.get("type","")); self._v_se_dur.set(float(se.get("duration",0)))
        self._v_se_dps.set(float(se.get("damage_per_second",0))); self._v_se_slow.set(float(se.get("slow_factor",0.5)))

    def _new(self):
        key=simpledialog.askstring("New Ability","Ability ID:")
        if not key: return
        key=key.strip().lower().replace(" ","_")
        if key in self._data: messagebox.showerror("Error",f"'{key}' exists"); return
        self._data[key]={"type":"melee","name":key.replace("_"," ").title(),"damage":25,"cooldown":0.45,"color":[255,220,50]}
        self._refresh(); keys=list(self._data.keys()); self._lb.selection_set(keys.index(key)); self._on_sel()

    def _del(self):
        if not self._selected: return
        if not messagebox.askyesno("Delete",f"Delete '{self._selected}'?"): return
        del self._data[self._selected]; self._selected=None; self._refresh(); _save(self._path,self._data)

    def _save(self):
        key=self._v_id.get().strip().lower().replace(" ","_")
        if not key: messagebox.showerror("Error","ID empty"); return
        entry={"type":self._v_type.get(),"name":self._v_name.get() or key,
               "damage":int(self._v_damage.get()),"cooldown":round(self._v_cd.get(),3),"color":self._color_btn.get()}
        if self._v_mana.get()>0: entry["mana_cost"]=int(self._v_mana.get())
        if self._v_kb.get()>0: entry["knockback"]=int(self._v_kb.get())
        t=entry["type"]
        if t in("projectile","wave"): entry["speed"]=int(self._v_speed.get())
        if t=="wave": entry["max_distance"]=int(self._v_maxdist.get()); entry["height"]=35
        if t in("area","aura"): entry["radius"]=int(self._v_radius.get()); entry["duration"]=round(self._v_dur.get(),2)
        if t=="aura" and self._v_dps.get()>0: entry["damage_per_second"]=int(self._v_dps.get())
        if self._v_sound.get(): entry["sound"]=self._v_sound.get().strip()
        se_type=self._v_se_type.get()
        if se_type:
            se={"type":se_type,"duration":round(self._v_se_dur.get(),2)}
            if se_type in("poison","burn") and self._v_se_dps.get()>0: se["damage_per_second"]=int(self._v_se_dps.get())
            if se_type=="slow": se["slow_factor"]=round(self._v_se_slow.get(),2)
            entry["status_effect"]=se
        if self._selected and self._selected!=key: del self._data[self._selected]
        self._data[key]=entry; self._selected=key; _save(self._path,self._data)
        self._refresh(); self._lb.selection_set(list(self._data.keys()).index(key))
        messagebox.showinfo("Saved",f"Ability '{key}' saved.")

# ---------------------------------------------------------------------------
# Shop tab
# ---------------------------------------------------------------------------

class ShopTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._path=DATA_DIR/"shops.json"
        self._data=_load(self._path) if self._path.exists() else {}
        self._items=_load(DATA_DIR/"items.json") if (DATA_DIR/"items.json").exists() else {}
        self._selected=None; self._build(); self._refresh()

    def _build(self):
        left=ttk.Frame(self); left.pack(side="left",fill="y",padx=(8,4),pady=8)
        ttk.Label(left,text="Shops",font=("",10,"bold")).pack()
        self._lb=tk.Listbox(left,width=20,exportselection=False)
        self._lb.pack(fill="y",expand=True); self._lb.bind("<<ListboxSelect>>",self._on_sel)
        br=ttk.Frame(left); br.pack(fill="x",pady=(4,0))
        ttk.Button(br,text="New",command=self._new).pack(side="left")
        ttk.Button(br,text="Delete",command=self._del).pack(side="left",padx=4)

        right=ttk.LabelFrame(self,text="Shop Properties")
        right.pack(side="left",fill="both",expand=True,padx=(4,8),pady=8)
        right.columnconfigure(1,weight=1)
        f=right
        self._v_id      = _field(f,0,"Shop ID"); self._v_name = _field(f,1,"Display name")
        self._v_buyrate = _spin(f,2,"Buy rate (sell multiplier)",0,1,0.5,0.05)
        ttk.Label(f,text="Inventory:",font=("",9,"bold")).grid(row=3,column=0,sticky="w",pady=(10,2),padx=4)
        if_=ttk.Frame(f); if_.grid(row=4,column=0,columnspan=2,sticky="ew")
        self._itree=ttk.Treeview(if_,columns=("item","price","stock"),show="headings",height=8)
        for col,w in [("item",160),("price",80),("stock",80)]:
            self._itree.heading(col,text={"item":"Item ID","price":"Price(g)","stock":"Stock(-1=∞)"}[col])
            self._itree.column(col,width=w)
        self._itree.pack(side="left",fill="x",expand=True)
        ib=ttk.Frame(if_); ib.pack(side="left",padx=(4,0))
        ttk.Button(ib,text="+",width=3,command=self._add_item).pack(pady=2)
        ttk.Button(ib,text="−",width=3,command=self._del_item).pack()
        ttk.Button(f,text="Save Shop",command=self._save).grid(row=5,column=0,columnspan=2,pady=10)

    def _refresh(self):
        self._lb.delete(0,"end")
        for k in self._data: self._lb.insert("end",k)

    def _on_sel(self,_=None):
        sel=self._lb.curselection()
        if not sel: return
        key=self._lb.get(sel[0]); self._selected=key; d=self._data[key]
        self._v_id.set(key); self._v_name.set(d.get("name",key)); self._v_buyrate.set(float(d.get("buy_rate",0.5)))
        self._itree.delete(*self._itree.get_children())
        for e in d.get("inventory",[]): self._itree.insert("","end",values=(e["item_id"],e["price"],e.get("stock",-1)))

    def _new(self):
        key=simpledialog.askstring("New Shop","Shop ID:")
        if not key: return
        key=key.strip().lower().replace(" ","_")
        if key in self._data: messagebox.showerror("Error",f"'{key}' exists"); return
        self._data[key]={"name":key.replace("_"," ").title(),"buy_rate":0.5,"inventory":[]}
        self._refresh(); keys=list(self._data.keys()); self._lb.selection_set(keys.index(key)); self._on_sel()

    def _del(self):
        if not self._selected: return
        if not messagebox.askyesno("Delete",f"Delete '{self._selected}'?"): return
        del self._data[self._selected]; self._selected=None; self._refresh(); _save(self._path,self._data)

    def _add_item(self):
        items=list(self._items.keys())
        win=tk.Toplevel(self); win.title("Add Item"); win.grab_set()
        f=ttk.Frame(win,padding=12); f.pack()
        vi=_combo_e(f,0,"Item ID",items,items[0] if items else "")
        vp=_spin(f,1,"Price (gold)",1,9999,10)
        vs=_spin(f,2,"Stock (-1=unlimited)",-1,999,-1)
        def ok():
            self._itree.insert("","end",values=(vi.get(),int(vp.get()),int(vs.get()))); win.destroy()
        ttk.Button(f,text="Add",command=ok).grid(row=3,column=0,columnspan=2,pady=8)

    def _del_item(self):
        sel=self._itree.selection()
        if sel: self._itree.delete(sel[0])

    def _save(self):
        key=self._v_id.get().strip().lower().replace(" ","_")
        if not key: messagebox.showerror("Error","ID empty"); return
        inv=[]
        for rid in self._itree.get_children():
            v=self._itree.item(rid,"values"); inv.append({"item_id":v[0],"price":int(v[1]),"stock":int(v[2])})
        entry={"name":self._v_name.get() or key,"buy_rate":round(self._v_buyrate.get(),2),"inventory":inv}
        if self._selected and self._selected!=key: del self._data[self._selected]
        self._data[key]=entry; self._selected=key; _save(self._path,self._data)
        self._refresh(); self._lb.selection_set(list(self._data.keys()).index(key))
        messagebox.showinfo("Saved",f"Shop '{key}' saved.")

# ---------------------------------------------------------------------------
# Quest tab  [NEW]
# ---------------------------------------------------------------------------

class QuestTab(ttk.Frame):
    _TYPES = ("kill","kill_any","collect","reach_zone")
    def __init__(self, parent):
        super().__init__(parent)
        self._path=DATA_DIR/"quests.json"
        self._data=_load(self._path) if self._path.exists() else {}
        self._selected=None; self._build(); self._refresh()

    def _build(self):
        left=ttk.Frame(self); left.pack(side="left",fill="y",padx=(8,4),pady=8)
        ttk.Label(left,text="Quests",font=("",10,"bold")).pack()
        self._lb=tk.Listbox(left,width=22,exportselection=False)
        self._lb.pack(fill="y",expand=True); self._lb.bind("<<ListboxSelect>>",self._on_sel)
        br=ttk.Frame(left); br.pack(fill="x",pady=(4,0))
        ttk.Button(br,text="New",command=self._new).pack(side="left")
        ttk.Button(br,text="Delete",command=self._del).pack(side="left",padx=4)

        right=ttk.LabelFrame(self,text="Quest Properties")
        right.pack(side="left",fill="both",expand=True,padx=(4,8),pady=8)
        right.columnconfigure(1,weight=1); right.columnconfigure(3,weight=1)
        f=right; r=0
        self._v_id   = _field(f,r,"Quest ID");       r+=1
        self._v_name = _field(f,r,"Display name");   r+=1
        # Description spans two rows
        ttk.Label(f,text="Description").grid(row=r,column=0,sticky="nw",pady=2,padx=4)
        self._desc_text = tk.Text(f,width=36,height=3,wrap="word")
        self._desc_text.grid(row=r,column=1,columnspan=3,sticky="ew",padx=(4,4),pady=2); r+=1
        self._v_type  = _combo(f,r,"Quest type",self._TYPES,"kill"); r+=1
        items   = _list_ids(DATA_DIR/"items.json")
        enemies = _list_ids(DATA_DIR/"enemies.json")
        zones   = [p.stem for p in ZONES_DIR.glob("*.json")] if ZONES_DIR.exists() else []
        self._v_target = _combo_e(f,r,"Target",enemies+items+zones,"",20); r+=1
        self._v_count  = _spin(f,r,"Count",1,9999,3); r+=1
        self._v_xp     = _spin(f,r,"Reward XP",0,9999,50); r+=1
        self._v_gold   = _spin(f,r,"Reward Gold",0,9999,20); r+=1
        ttk.Button(f,text="Save Quest",command=self._save).grid(row=r,column=0,columnspan=2,pady=10)

    def _refresh(self):
        self._lb.delete(0,"end")
        for k in self._data: self._lb.insert("end",k)

    def _on_sel(self,_=None):
        sel=self._lb.curselection()
        if not sel: return
        key=self._lb.get(sel[0]); self._selected=key; d=self._data[key]
        self._v_id.set(key); self._v_name.set(d.get("name",key))
        self._desc_text.delete("1.0","end"); self._desc_text.insert("1.0",d.get("description",""))
        self._v_type.set(d.get("type","kill")); self._v_target.set(d.get("target",""))
        self._v_count.set(float(d.get("count",3))); self._v_xp.set(float(d.get("reward_xp",50)))
        self._v_gold.set(float(d.get("reward_gold",20)))

    def _new(self):
        key=simpledialog.askstring("New Quest","Quest ID:")
        if not key: return
        key=key.strip().lower().replace(" ","_")
        if key in self._data: messagebox.showerror("Error",f"'{key}' exists"); return
        self._data[key]={"name":key.replace("_"," ").title(),"description":"","type":"kill","target":"basic","count":3,"reward_xp":50,"reward_gold":20}
        self._refresh(); keys=list(self._data.keys()); self._lb.selection_set(keys.index(key)); self._on_sel()

    def _del(self):
        if not self._selected: return
        if not messagebox.askyesno("Delete",f"Delete '{self._selected}'?"): return
        del self._data[self._selected]; self._selected=None; self._refresh(); _save(self._path,self._data)

    def _save(self):
        key=self._v_id.get().strip().lower().replace(" ","_")
        if not key: messagebox.showerror("Error","ID empty"); return
        desc=self._desc_text.get("1.0","end").strip()
        entry={"name":self._v_name.get() or key,"description":desc,"type":self._v_type.get(),
               "count":int(self._v_count.get()),"reward_xp":int(self._v_xp.get()),"reward_gold":int(self._v_gold.get())}
        target=self._v_target.get().strip()
        if target and self._v_type.get()!="kill_any": entry["target"]=target
        if self._selected and self._selected!=key: del self._data[self._selected]
        self._data[key]=entry; self._selected=key; _save(self._path,self._data)
        self._refresh(); self._lb.selection_set(list(self._data.keys()).index(key))
        messagebox.showinfo("Saved",f"Quest '{key}' saved.")

# ---------------------------------------------------------------------------
# Zone Editor — comprehensive visual canvas
# ---------------------------------------------------------------------------

class ZoneTab(ttk.Frame):
    SX = 0.12   # world → canvas scale (x)
    SY = 0.55   # world → canvas scale (y)
    GRID = 20   # default grid cell size (world px)

    _CLR = {
        "platform":   "#8C6438",
        "enemy":      "#C85050",
        "save_point": "#50C8B4",
        "exit":       "#32B464",
        "building":   "#A08050",
        "npc":        "#C8C050",
        "item_drop":  "#8888FF",
        "spawn":      "#80FFFF",
        "chest":      "#D4A020",
    }

    _TOOLS = ("select","platform","enemy","npc","save_point",
              "item_drop","exit","building","chest")

    def __init__(self, parent):
        super().__init__(parent)
        self._items    = _load(DATA_DIR/"items.json")    if (DATA_DIR/"items.json").exists()   else {}
        self._enemies  = _load(DATA_DIR/"enemies.json")  if (DATA_DIR/"enemies.json").exists() else {}
        self._npctypes = _load(DATA_DIR/"npcs.json")     if (DATA_DIR/"npcs.json").exists()    else {}
        self._dialogues= _load(DATA_DIR/"dialogue.json") if (DATA_DIR/"dialogue.json").exists()else {}
        self._shops    = _load(DATA_DIR/"shops.json")    if (DATA_DIR/"shops.json").exists()   else {}
        self._quests   = _load(DATA_DIR/"quests.json")   if (DATA_DIR/"quests.json").exists()  else {}

        self._zone_path: Path | None = None
        self._zone: dict = self._blank_zone()
        self._elements: list = []
        self._selected_idx: int | None = None
        self._drag_start = None
        self._rubber_id  = None
        self._tool = tk.StringVar(value="select")
        self._grid_snap = tk.BooleanVar(value=True)
        self._snap_surface = tk.BooleanVar(value=False)
        self._cursor_var = tk.StringVar(value="Cursor: —")

        # Undo/redo stacks (store deep copies of zone data)
        self._undo_stack: list = []
        self._redo_stack: list = []

        # Clipboard for copy/paste
        self._clipboard: dict | None = None

        # Multi-selection for batch editing
        self._multi_sel_ids:  set  = set()   # id(data) of each selected element
        self._multi_sel_data: list = []      # (etype, data) pairs

        # Layer visibility — populated in _build()
        self._layer_vis: dict = {}

        self._build()

    def _blank_zone(self) -> dict:
        return {"id":"new_zone","spawn":[200,596],"bg_color":[30,30,40],"music":None,
                "platforms":[],"enemies":[],"save_points":[],"item_drops":[],
                "npcs":[],"exits":[],"buildings":[],"chests":[]}

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build(self):
        # ---- Top bar: file + meta ----
        top = ttk.Frame(self); top.pack(fill="x",padx=8,pady=(8,2))
        ttk.Button(top,text="New Zone", command=self._new_zone).pack(side="left")
        ttk.Button(top,text="Open Zone",command=self._open_zone).pack(side="left",padx=4)
        ttk.Button(top,text="Save Zone",command=self._save_zone).pack(side="left")
        ttk.Separator(top,orient="vertical").pack(side="left",fill="y",padx=8)
        ttk.Label(top,text="ID:").pack(side="left")
        self._v_id=tk.StringVar(value="new_zone")
        ttk.Entry(top,textvariable=self._v_id,width=14).pack(side="left",padx=2)
        ttk.Label(top,text="Spawn:").pack(side="left",padx=(8,0))
        self._v_sx=tk.StringVar(value="200"); self._v_sy=tk.StringVar(value="596")
        ttk.Entry(top,textvariable=self._v_sx,width=6).pack(side="left",padx=2)
        ttk.Entry(top,textvariable=self._v_sy,width=6).pack(side="left")
        ttk.Label(top,text="BG:").pack(side="left",padx=(8,0))
        self._bg_btn=ColorButton(top,initial=(30,30,40)); self._bg_btn.pack(side="left")
        ttk.Label(top,text="Music:").pack(side="left",padx=(8,0))
        self._v_music=tk.StringVar()
        ttk.Entry(top,textvariable=self._v_music,width=14).pack(side="left",padx=2)

        # ---- Toolbar ----
        tb = ttk.Frame(self); tb.pack(fill="x",padx=8,pady=2)
        ttk.Label(tb,text="Tool:").pack(side="left")
        labels={"select":"↖ Select","platform":"▭ Platform","enemy":"☠ Enemy","npc":"☺ NPC",
                "save_point":"✦ Save Pt","item_drop":"◆ Item Drop","exit":"→ Exit",
                "building":"⌂ Building","chest":"◻ Chest"}
        for val in self._TOOLS:
            ttk.Radiobutton(tb,text=labels[val],variable=self._tool,value=val).pack(side="left",padx=3)
        ttk.Separator(tb,orient="vertical").pack(side="left",fill="y",padx=8)
        ttk.Checkbutton(tb,text="Grid snap (G)",variable=self._grid_snap).pack(side="left")
        ttk.Checkbutton(tb,text="⊥ Snap Surface",variable=self._snap_surface).pack(side="left",padx=4)
        ttk.Label(tb,text="  ").pack(side="left")
        ttk.Button(tb,text="Undo",command=self._undo).pack(side="left")
        ttk.Button(tb,text="Redo",command=self._redo).pack(side="left",padx=2)
        ttk.Label(tb,text="  ").pack(side="left")
        ttk.Button(tb,text="Validate",command=self._validate).pack(side="left")

        # ---- Layer visibility ----
        lyr = ttk.Frame(self); lyr.pack(fill="x",padx=8,pady=(0,2))
        ttk.Label(lyr,text="Layers:").pack(side="left")
        _layer_order = ("platform","enemy","npc","save_point","item_drop","exit","building","chest")
        _layer_labels = {"platform":"Platforms","enemy":"Enemies","npc":"NPCs",
                         "save_point":"Save Pts","item_drop":"Drops",
                         "exit":"Exits","building":"Buildings","chest":"Chests"}
        for etype in _layer_order:
            var = tk.BooleanVar(value=True)
            self._layer_vis[etype] = var
            ttk.Checkbutton(lyr, text=_layer_labels[etype], variable=var,
                            command=self._redraw).pack(side="left", padx=3)

        # ---- Canvas ----
        cf = ttk.Frame(self,relief="sunken",borderwidth=1)
        cf.pack(fill="both",expand=True,padx=8,pady=4)
        self._canvas=tk.Canvas(cf,bg="#1a1a2a",cursor="crosshair",
                               scrollregion=(0,0,10000*self.SX,720*self.SY))
        hsc=ttk.Scrollbar(cf,orient="horizontal",command=self._canvas.xview)
        vsc=ttk.Scrollbar(cf,orient="vertical",command=self._canvas.yview)
        self._canvas.config(xscrollcommand=hsc.set,yscrollcommand=vsc.set)
        hsc.pack(side="bottom",fill="x"); vsc.pack(side="right",fill="y")
        self._canvas.pack(fill="both",expand=True)
        self._canvas.bind("<ButtonPress-1>",  self._on_press)
        self._canvas.bind("<B1-Motion>",       self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<Delete>",          self._on_delete)
        self._canvas.bind("<BackSpace>",       self._on_delete)
        self._canvas.bind("<Escape>",          lambda e: self._deselect())
        self._canvas.bind("<Motion>",          self._on_motion)
        self._canvas.bind("<KeyPress>",        self._on_key)
        # Ctrl+Z / Ctrl+Y / Ctrl+C / Ctrl+V
        self._canvas.bind("<Control-z>",       lambda e: self._undo())
        self._canvas.bind("<Control-y>",       lambda e: self._redo())
        self._canvas.bind("<Control-Z>",       lambda e: self._undo())
        self._canvas.bind("<Control-Y>",       lambda e: self._redo())
        self._canvas.bind("<Control-c>",       lambda e: self._copy())
        self._canvas.bind("<Control-v>",       lambda e: self._paste())
        self._canvas.bind("<Control-C>",       lambda e: self._copy())
        self._canvas.bind("<Control-V>",       lambda e: self._paste())
        self._canvas.focus_set()

        # ---- Properties panel ----
        self._prop_frame=ttk.LabelFrame(self,text="Selected element — properties")
        self._prop_frame.pack(fill="x",padx=8,pady=(0,2))
        ttk.Label(self._prop_frame,text="Click an element or place one with the toolbar.").pack(
            anchor="w",padx=8,pady=4)

        # ---- Status bar ----
        sbar=ttk.Frame(self); sbar.pack(fill="x",padx=8,pady=(0,4))
        self._status=tk.StringVar(value="Ready")
        ttk.Label(sbar,textvariable=self._status,relief="sunken",anchor="w",width=80).pack(side="left",fill="x",expand=True)
        ttk.Label(sbar,textvariable=self._cursor_var,relief="sunken",anchor="e",width=24).pack(side="right")

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _snap(self, v):
        if self._grid_snap.get():
            g = self.GRID
            return int(round(v / g) * g)
        return int(v)

    def _wx(self, cx): return self._snap(self._canvas.canvasx(cx) / self.SX)
    def _wy(self, cy): return self._snap(self._canvas.canvasy(cy) / self.SY)
    def _cx(self, wx): return wx * self.SX
    def _cy(self, wy): return wy * self.SY

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def _push_undo(self):
        self._undo_stack.append(deepcopy(self._zone))
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack: return
        self._redo_stack.append(deepcopy(self._zone))
        self._zone = self._undo_stack.pop()
        self._selected_idx = None
        self._multi_sel_ids.clear(); self._multi_sel_data.clear()
        self._redraw(); self._clear_props()

    def _redo(self):
        if not self._redo_stack: return
        self._undo_stack.append(deepcopy(self._zone))
        self._zone = self._redo_stack.pop()
        self._selected_idx = None
        self._multi_sel_ids.clear(); self._multi_sel_data.clear()
        self._redraw(); self._clear_props()

    # ------------------------------------------------------------------
    # Canvas redraw
    # ------------------------------------------------------------------

    def _redraw(self):
        self._canvas.delete("all")
        self._elements.clear()
        z = self._zone

        # Grid lines (subtle)
        if self._grid_snap.get():
            for wx in range(0, 10001, self.GRID*5):
                x = self._cx(wx)
                self._canvas.create_line(x, 0, x, 720*self.SY, fill="#222233", width=1)
            for wy in range(0, 721, self.GRID*5):
                y = self._cy(wy)
                self._canvas.create_line(0, y, 10000*self.SX, y, fill="#222233", width=1)

        # Spawn marker
        sx, sy = z["spawn"]
        self._canvas.create_oval(
            self._cx(sx)-5, self._cy(sy)-5, self._cx(sx)+5, self._cy(sy)+5,
            fill=self._CLR["spawn"], outline="white", tags="spawn")
        self._canvas.create_text(self._cx(sx), self._cy(sy)-10, text="spawn", fill=self._CLR["spawn"], font=("",8))

        def _vis(etype):
            v = self._layer_vis.get(etype)
            return v.get() if v is not None else True
        if _vis("platform"):  [self._draw_elem("platform",  d) for d in z.get("platforms",[])]
        if _vis("save_point"):[self._draw_elem("save_point",d) for d in z.get("save_points",[])]
        if _vis("exit"):      [self._draw_elem("exit",      d) for d in z.get("exits",[])]
        if _vis("building"):  [self._draw_elem("building",  d) for d in z.get("buildings",[])]
        if _vis("chest"):     [self._draw_elem("chest",     d) for d in z.get("chests",[])]
        if _vis("npc"):       [self._draw_elem("npc",       d) for d in z.get("npcs",[])]
        if _vis("item_drop"): [self._draw_elem("item_drop", d) for d in z.get("item_drops",[])]
        if _vis("enemy"):     [self._draw_elem("enemy",     d) for d in z.get("enemies",[])]

        # Stats
        z2 = z
        self._status.set(
            f"Zone: {z2.get('id','?')}  |  "
            f"Platforms: {len(z2.get('platforms',[]))}  "
            f"Enemies: {len(z2.get('enemies',[]))}  "
            f"NPCs: {len(z2.get('npcs',[]))}  "
            f"Drops: {len(z2.get('item_drops',[]))}  "
            f"Chests: {len(z2.get('chests',[]))}  "
            f"Exits: {len(z2.get('exits',[]))}"
        )

    def _draw_elem(self, etype, data):
        clr = self._CLR.get(etype, "#888888")
        idx = len(self._elements)
        tag = f"elem_{idx}"

        if etype in ("platform","save_point","exit","building","chest"):
            x1=self._cx(data["x"]); y1=self._cy(data["y"])
            x2=self._cx(data["x"]+data["w"]); y2=self._cy(data["y"]+data["h"])
            cid=self._canvas.create_rectangle(x1,y1,x2,y2,fill=clr,outline="white",width=1,tags=tag)
            if etype=="chest":
                # Small lock icon
                self._canvas.create_text((x1+x2)/2,(y1+y2)/2,text="◻",fill="white",font=("",9),tags=tag)
        else:
            ex=data.get("x",0); ey=data.get("y",0); r=6
            cid=self._canvas.create_oval(
                self._cx(ex)-r,self._cy(ey)-r,self._cx(ex)+r,self._cy(ey)+r,
                fill=clr,outline="white",width=1,tags=tag)
            label=data.get("type",etype[:4])
            self._canvas.create_text(self._cx(ex),self._cy(ey)-r-4,text=label,fill="white",font=("",8),tags=tag)

        if id(data) in self._multi_sel_ids:
            self._canvas.itemconfig(cid, outline="#FF60FF", width=2)
        self._elements.append({"type":etype,"data":data,"cid":cid})
        self._canvas.tag_bind(tag,"<ButtonPress-1>",lambda e,i=idx: self._on_elem_click(e,i))

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def _on_motion(self, event):
        wx=int(self._canvas.canvasx(event.x)/self.SX)
        wy=int(self._canvas.canvasy(event.y)/self.SY)
        self._cursor_var.set(f"x={wx}  y={wy}")

    def _on_press(self, event):
        tool=self._tool.get()
        wx,wy=self._wx(event.x),self._wy(event.y)
        cx=self._canvas.canvasx(event.x); cy=self._canvas.canvasy(event.y)
        if tool=="select": self._canvas.focus_set(); return
        if tool in("platform","exit"):
            self._drag_start=(cx,cy,wx,wy)
        else:
            self._place_element(tool,wx,wy)

    def _on_drag(self, event):
        if self._drag_start is None: return
        cx=self._canvas.canvasx(event.x); cy=self._canvas.canvasy(event.y)
        if self._rubber_id: self._canvas.delete(self._rubber_id)
        x0,y0=self._drag_start[0],self._drag_start[1]
        clr=self._CLR.get(self._tool.get(),"#888")
        self._rubber_id=self._canvas.create_rectangle(x0,y0,cx,cy,outline=clr,width=2,dash=(4,2))

    def _on_release(self, event):
        if self._drag_start is None: return
        if self._rubber_id: self._canvas.delete(self._rubber_id); self._rubber_id=None
        cx=self._canvas.canvasx(event.x); cy=self._canvas.canvasy(event.y)
        x0,y0,wx0,wy0=self._drag_start; self._drag_start=None
        wx1,wy1=self._wx(event.x),self._wy(event.y)
        x=min(wx0,wx1); y=min(wy0,wy1); w=abs(wx1-wx0); h=abs(wy1-wy0)
        if w<4 or h<4: return
        tool=self._tool.get(); self._push_undo()
        if tool=="platform":
            self._zone.setdefault("platforms",[]).append({"x":x,"y":y,"w":w,"h":h})
        elif tool=="exit":
            self._add_exit_dialog(x,y,w,h)
            return  # dialog handles push itself
        self._redraw()

    def _on_elem_click(self, event, idx):
        if event.state & 0x0001:   # Shift held — toggle multi-select
            self._toggle_multi_sel(idx)
        else:
            self._clear_multi_sel()
            self._select_elem(idx)

    def _on_key(self, event):
        if event.keysym in ("g", "G"):
            self._grid_snap.set(not self._grid_snap.get())
            self._redraw(); return
        if self._selected_idx is None: return
        elem=self._elements[self._selected_idx]; data=elem["data"]; step=10 if event.state&1 else 1
        moved=False
        if event.keysym=="Left":   data["x"]=data.get("x",0)-step; moved=True
        elif event.keysym=="Right":data["x"]=data.get("x",0)+step; moved=True
        elif event.keysym=="Up":   data["y"]=data.get("y",0)-step; moved=True
        elif event.keysym=="Down": data["y"]=data.get("y",0)+step; moved=True
        if moved: self._push_undo(); self._redraw(); self._select_elem_by_data(data)

    def _on_delete(self, _=None):
        if self._selected_idx is None: return
        elem=self._elements[self._selected_idx]; etype=elem["type"]; data=elem["data"]
        key_map={"platform":"platforms","save_point":"save_points","exit":"exits",
                 "building":"buildings","npc":"npcs","item_drop":"item_drops",
                 "enemy":"enemies","chest":"chests"}
        lst=self._zone.get(key_map.get(etype,""),[]);
        if data in lst: self._push_undo(); lst.remove(data)
        self._selected_idx=None; self._redraw(); self._clear_props()

    # ------------------------------------------------------------------
    # Element selection + properties
    # ------------------------------------------------------------------

    def _deselect(self):
        if self._selected_idx is not None:
            try:
                old=self._elements[self._selected_idx]
                self._canvas.itemconfig(old["cid"],outline="white",width=1)
            except Exception: pass
        self._selected_idx=None
        self._multi_sel_ids.clear(); self._multi_sel_data.clear()
        self._clear_props()

    def _select_elem(self, idx):
        self._deselect()
        self._selected_idx=idx; elem=self._elements[idx]
        self._canvas.itemconfig(elem["cid"],outline="#FFE020",width=2)
        self._show_props(elem["type"],elem["data"])

    def _select_elem_by_data(self, data):
        for i,e in enumerate(self._elements):
            if e["data"] is data: self._select_elem(i); return

    def _clear_props(self):
        for w in self._prop_frame.winfo_children(): w.destroy()
        ttk.Label(self._prop_frame,text="Click an element to select it.  Arrow keys nudge (Shift=10px).  Delete removes.").pack(anchor="w",padx=8,pady=4)

    def _show_props(self, etype, data):
        for w in self._prop_frame.winfo_children(): w.destroy()
        f=ttk.Frame(self._prop_frame); f.pack(fill="x",padx=8,pady=4)

        ttk.Label(f,text=f"▶ {etype.upper().replace('_',' ')}",font=("",9,"bold")).grid(
            row=0,column=0,columnspan=6,sticky="w",pady=(0,4))

        vars_: dict = {}
        row=1

        def add(label, key, is_int=True, col=0):
            nonlocal row
            ttk.Label(f,text=label).grid(row=row,column=col*2,sticky="e",padx=4)
            v=tk.StringVar(value=str(data.get(key,0) if is_int else data.get(key,"")))
            ttk.Entry(f,textvariable=v,width=8).grid(row=row,column=col*2+1,sticky="w")
            vars_[key]=(v,is_int)
            if col>=2: row+=1

        if etype in("platform","save_point","exit","building","chest"):
            add("X:","x",True,0); add("Y:","y",True,1); add("W:","w",True,2); row+=1
            add("H:","h",True,0)
            if etype=="exit":
                add("Target zone:","target_zone",False,1); row+=1
                ttk.Label(f,text="Spawn override X:").grid(row=row,column=0,sticky="e",padx=4)
                so=data.get("spawn_override") or [None,None]
                v_sox=tk.StringVar(value=str(so[0]) if so and so[0] is not None else "")
                ttk.Entry(f,textvariable=v_sox,width=8).grid(row=row,column=1,sticky="w")
                ttk.Label(f,text="Y:").grid(row=row,column=2,sticky="e",padx=4)
                v_soy=tk.StringVar(value=str(so[1]) if so and len(so)>1 and so[1] is not None else "")
                ttk.Entry(f,textvariable=v_soy,width=8).grid(row=row,column=3,sticky="w")
                vars_["_sox"]=(v_sox,False); vars_["_soy"]=(v_soy,False)
            elif etype=="building":
                add("Target zone:","target_zone",False,1); row+=1
                add("Label:","label",False,0); add("Door X:","door_x",True,1); add("Door Y:","door_y",True,2); row+=1
                add("Door W:","door_w",True,0); add("Door H:","door_h",True,1)
            elif etype=="chest":
                # Show contents list
                row+=1
                ttk.Label(f,text="Contents:").grid(row=row,column=0,sticky="nw",padx=4)
                ct=ttk.Treeview(f,columns=("item","qty"),show="headings",height=3)
                ct.heading("item",text="Item ID"); ct.heading("qty",text="Qty")
                ct.column("item",width=140); ct.column("qty",width=50)
                ct.grid(row=row,column=1,columnspan=3,sticky="ew",padx=(4,0))
                for c in data.get("contents",[]): ct.insert("","end",values=(c.get("item_id",""),c.get("quantity",1)))
                cbf=ttk.Frame(f); cbf.grid(row=row,column=4,padx=(4,0))
                items=list(self._items.keys())
                def add_content():
                    win=tk.Toplevel(self); win.title("Add Item"); win.grab_set()
                    ff=ttk.Frame(win,padding=12); ff.pack()
                    vi=_combo_e(ff,0,"Item ID",items,items[0] if items else "")
                    vq=_spin(ff,1,"Quantity",1,999,1)
                    def ok(): ct.insert("","end",values=(vi.get(),int(vq.get()))); win.destroy()
                    ttk.Button(ff,text="Add",command=ok).grid(row=2,column=0,columnspan=2,pady=8)
                def del_content():
                    sel=ct.selection()
                    if sel: ct.delete(sel[0])
                ttk.Button(cbf,text="+",width=3,command=add_content).pack(pady=2)
                ttk.Button(cbf,text="−",width=3,command=del_content).pack()
                vars_["_ct"]=(ct,False)
        else:
            add("X:","x",True,0); add("Y:","y",True,1); row+=1
            if etype=="enemy":
                types=list(self._enemies.keys())
                ttk.Label(f,text="Type:").grid(row=row,column=0,sticky="e",padx=4)
                v_t=tk.StringVar(value=data.get("type","basic"))
                ttk.Combobox(f,textvariable=v_t,values=types,width=14,state="readonly").grid(row=row,column=1,sticky="w")
                vars_["type"]=(v_t,False)
            elif etype=="npc":
                ntypes=list(self._npctypes.keys()); dlg_ids=[""] + list(self._dialogues.keys())
                shop_ids=[""] + list(self._shops.keys()); quest_ids=[""] + list(self._quests.keys())
                ttk.Label(f,text="Type:").grid(row=row,column=0,sticky="e",padx=4)
                v_t=tk.StringVar(value=data.get("type","villager"))
                ttk.Combobox(f,textvariable=v_t,values=ntypes,width=12,state="readonly").grid(row=row,column=1,sticky="w")
                ttk.Label(f,text="Dialogue:").grid(row=row,column=2,sticky="e",padx=4)
                v_d=tk.StringVar(value=data.get("dialogue_id",""))
                ttk.Combobox(f,textvariable=v_d,values=dlg_ids,width=14).grid(row=row,column=3,sticky="w")
                vars_["type"]=(v_t,False); vars_["dialogue_id"]=(v_d,False); row+=1
                ttk.Label(f,text="Shop ID:").grid(row=row,column=0,sticky="e",padx=4)
                v_s=tk.StringVar(value=data.get("shop_id","") or "")
                ttk.Combobox(f,textvariable=v_s,values=shop_ids,width=14).grid(row=row,column=1,sticky="w")
                ttk.Label(f,text="Gives quest:").grid(row=row,column=2,sticky="e",padx=4)
                v_q=tk.StringVar(value=data.get("gives_quest","") or "")
                ttk.Combobox(f,textvariable=v_q,values=quest_ids,width=14).grid(row=row,column=3,sticky="w")
                vars_["shop_id"]=(v_s,False); vars_["gives_quest"]=(v_q,False)
            elif etype=="item_drop":
                items=list(self._items.keys())
                ttk.Label(f,text="Item:").grid(row=row,column=0,sticky="e",padx=4)
                v_i=tk.StringVar(value=data.get("item_id","wood"))
                ttk.Combobox(f,textvariable=v_i,values=items,width=14).grid(row=row,column=1,sticky="w")
                ttk.Label(f,text="Qty:").grid(row=row,column=2,sticky="e",padx=4)
                v_q=tk.StringVar(value=str(data.get("quantity",1)))
                ttk.Entry(f,textvariable=v_q,width=6).grid(row=row,column=3,sticky="w")
                vars_["item_id"]=(v_i,False); vars_["quantity"]=(v_q,True)

        row+=1

        def apply():
            self._push_undo()
            for key,(v,is_int) in vars_.items():
                if key.startswith("_"): continue
                val=v.get().strip()
                if key in("shop_id","gives_quest","dialogue_id") and not val:
                    data.pop(key,None)
                elif is_int and val:
                    try: data[key]=int(val)
                    except ValueError:
                        messagebox.showwarning("Invalid value",
                            f"'{val}' is not a valid integer for '{key}' — change ignored.")
                elif val:
                    data[key]=val

            if "_sox" in vars_ and "_soy" in vars_:
                sx=vars_["_sox"][0].get().strip(); sy=vars_["_soy"][0].get().strip()
                if sx and sy:
                    try: data["spawn_override"]=[int(sx),int(sy)]
                    except ValueError: pass
                else: data.pop("spawn_override",None)

            if "_ct" in vars_:
                ct=vars_["_ct"][0]
                contents=[]
                for rid in ct.get_children():
                    v=ct.item(rid,"values")
                    try: contents.append({"item_id":v[0],"quantity":int(v[1])})
                    except (ValueError,IndexError): pass
                data["contents"]=contents

            self._redraw()

        ttk.Button(f,text="Apply",command=apply).grid(row=row,column=0,columnspan=6,pady=6)

    # ------------------------------------------------------------------
    # Placement dialogs
    # ------------------------------------------------------------------

    def _place_element(self, tool, wx, wy):
        if tool=="save_point":
            self._push_undo()
            self._zone.setdefault("save_points",[]).append({"x":wx-30,"y":wy-32,"w":60,"h":64})
            self._redraw(); return
        if tool=="enemy":   self._add_enemy_dlg(wx,wy)
        elif tool=="npc":   self._add_npc_dlg(wx,wy)
        elif tool=="item_drop": self._add_drop_dlg(wx,wy)
        elif tool=="building":  self._add_building_dlg(wx,wy)
        elif tool=="chest":     self._add_chest_dlg(wx,wy)

    def _dlg_base(self, title):
        win=tk.Toplevel(self); win.title(title); win.grab_set()
        f=ttk.Frame(win,padding=12); f.pack(); return win,f

    def _add_enemy_dlg(self,wx,wy):
        if self._snap_surface.get(): wy=self._find_surface_y(wx,wy,60)
        win,f=self._dlg_base("Place Enemy")
        types=list(self._enemies.keys()) or ["basic"]
        v_type=_combo(f,0,"Enemy type",types,types[0])
        v_x=_spin(f,1,"X",0,99999,wx); v_y=_spin(f,2,"Y",0,9999,wy)
        def ok():
            self._push_undo()
            self._zone.setdefault("enemies",[]).append({"type":v_type.get(),"x":int(v_x.get()),"y":int(v_y.get())})
            self._redraw(); win.destroy()
        ttk.Button(f,text="Place",command=ok).grid(row=3,column=0,columnspan=2,pady=8)

    def _add_npc_dlg(self,wx,wy):
        win,f=self._dlg_base("Place NPC")
        ntypes=list(self._npctypes.keys()) or ["villager"]
        dlg_ids=[""] + list(self._dialogues.keys())
        shop_ids=[""] + list(self._shops.keys())
        quest_ids=[""] + list(self._quests.keys())
        v_type=_combo(f,0,"NPC type",ntypes,ntypes[0])
        v_dlg =_combo(f,1,"Dialogue ID",dlg_ids,"")
        v_shop=_combo(f,2,"Shop ID",shop_ids,"")
        v_quest=_combo(f,3,"Gives quest",quest_ids,"")
        v_x=_spin(f,4,"X",0,99999,wx); v_y=_spin(f,5,"Y",0,9999,wy)
        def ok():
            self._push_undo()
            entry={"type":v_type.get(),"x":int(v_x.get()),"y":int(v_y.get())}
            if v_dlg.get(): entry["dialogue_id"]=v_dlg.get()
            if v_shop.get(): entry["shop_id"]=v_shop.get()
            if v_quest.get(): entry["gives_quest"]=v_quest.get()
            self._zone.setdefault("npcs",[]).append(entry)
            self._redraw(); win.destroy()
        ttk.Button(f,text="Place",command=ok).grid(row=6,column=0,columnspan=2,pady=8)

    def _add_drop_dlg(self,wx,wy):
        if self._snap_surface.get(): wy=self._find_surface_y(wx,wy,16)
        win,f=self._dlg_base("Place Item Drop")
        items=list(self._items.keys()) or ["wood"]
        v_item=_combo_e(f,0,"Item ID",items,items[0])
        v_qty=_spin(f,1,"Quantity",1,999,1)
        v_x=_spin(f,2,"X",0,99999,wx); v_y=_spin(f,3,"Y",0,9999,wy)
        def ok():
            self._push_undo()
            self._zone.setdefault("item_drops",[]).append({"item_id":v_item.get(),"quantity":int(v_qty.get()),"x":int(v_x.get()),"y":int(v_y.get())})
            self._redraw(); win.destroy()
        ttk.Button(f,text="Place",command=ok).grid(row=4,column=0,columnspan=2,pady=8)

    def _add_exit_dialog(self,x,y,w,h):
        win,f=self._dlg_base("Zone Exit")
        zones=[p.stem for p in ZONES_DIR.glob("*.json")] if ZONES_DIR.exists() else []
        v_tz=_combo_e(f,0,"Target zone",zones,zones[0] if zones else "zone_02")
        v_sox=_field(f,1,"Spawn override X (blank=zone spawn)","")
        v_soy=_field(f,2,"Spawn override Y","")
        def ok():
            self._push_undo()
            entry={"x":x,"y":y,"w":w,"h":h,"target_zone":v_tz.get()}
            sx,sy=v_sox.get().strip(),v_soy.get().strip()
            if sx and sy:
                try: entry["spawn_override"]=[int(sx),int(sy)]
                except ValueError: pass
            self._zone.setdefault("exits",[]).append(entry)
            self._redraw(); win.destroy()
        ttk.Button(f,text="Add Exit",command=ok).grid(row=3,column=0,columnspan=2,pady=8)

    def _add_building_dlg(self,wx,wy):
        win,f=self._dlg_base("Place Building")
        zones=[p.stem for p in ZONES_DIR.glob("*.json")] if ZONES_DIR.exists() else []
        v_w=_spin(f,0,"Building width",20,2000,200); v_h=_spin(f,1,"Building height",20,1000,180)
        v_dw=_spin(f,2,"Door width",10,200,40); v_dh=_spin(f,3,"Door height",10,300,64)
        v_tz=_combo_e(f,4,"Target zone",zones,zones[0] if zones else "")
        v_lbl=_field(f,5,"Label (optional)","")
        def ok():
            self._push_undo()
            bw,bh=int(v_w.get()),int(v_h.get()); dw,dh=int(v_dw.get()),int(v_dh.get())
            bx,by=wx-bw//2,wy-bh
            entry={"x":bx,"y":by,"w":bw,"h":bh,"door_x":bx+(bw-dw)//2,"door_y":by+bh-dh,
                   "door_w":dw,"door_h":dh,"target_zone":v_tz.get()}
            if v_lbl.get().strip(): entry["label"]=v_lbl.get().strip()
            self._zone.setdefault("buildings",[]).append(entry)
            self._redraw(); win.destroy()
        ttk.Button(f,text="Place Building",command=ok).grid(row=6,column=0,columnspan=2,pady=8)

    def _add_chest_dlg(self,wx,wy):
        win,f=self._dlg_base("Place Chest")
        items=list(self._items.keys())
        # Contents editor
        ttk.Label(f,text="Contents:").grid(row=0,column=0,sticky="nw",padx=4)
        ct=ttk.Treeview(f,columns=("item","qty"),show="headings",height=4)
        ct.heading("item",text="Item ID"); ct.heading("qty",text="Qty")
        ct.column("item",width=140); ct.column("qty",width=60)
        ct.grid(row=0,column=1,columnspan=3,padx=4)
        def add_c():
            w2=tk.Toplevel(win); w2.title("Add Content"); w2.grab_set()
            f2=ttk.Frame(w2,padding=10); f2.pack()
            vi=_combo_e(f2,0,"Item",items,items[0] if items else "")
            vq=_spin(f2,1,"Qty",1,99,1)
            def ok2(): ct.insert("","end",values=(vi.get(),int(vq.get()))); w2.destroy()
            ttk.Button(f2,text="Add",command=ok2).grid(row=2,column=0,columnspan=2,pady=6)
        def rem_c():
            sel=ct.selection()
            if sel: ct.delete(sel[0])
        cbf=ttk.Frame(f); cbf.grid(row=0,column=4,padx=(4,0))
        ttk.Button(cbf,text="+",width=3,command=add_c).pack(pady=2)
        ttk.Button(cbf,text="−",width=3,command=rem_c).pack()
        v_x=_spin(f,1,"X",0,99999,wx); v_y=_spin(f,2,"Y",0,9999,wy)
        def ok():
            self._push_undo()
            contents=[]
            for r in ct.get_children():
                v=ct.item(r,"values")
                try: contents.append({"item_id":v[0],"quantity":int(v[1])})
                except (ValueError,IndexError): pass
            self._zone.setdefault("chests",[]).append({"x":int(v_x.get()),"y":int(v_y.get()),"w":48,"h":36,"contents":contents})
            self._redraw(); win.destroy()
        ttk.Button(f,text="Place Chest",command=ok).grid(row=3,column=0,columnspan=5,pady=8)

    # ------------------------------------------------------------------
    # Copy / Paste
    # ------------------------------------------------------------------

    _KEY_MAP = {"platform":"platforms","save_point":"save_points","exit":"exits",
                "building":"buildings","npc":"npcs","item_drop":"item_drops",
                "enemy":"enemies","chest":"chests"}

    def _copy(self):
        if self._selected_idx is None: return
        elem=self._elements[self._selected_idx]
        self._clipboard={"type":elem["type"],"data":deepcopy(elem["data"])}
        self._status.set(f"Copied {elem['type']} — Ctrl+V to paste")

    def _paste(self):
        if self._clipboard is None: return
        self._push_undo()
        etype=self._clipboard["type"]; data=deepcopy(self._clipboard["data"])
        data["x"]=data.get("x",0)+40; data["y"]=data.get("y",0)+40
        self._zone.setdefault(self._KEY_MAP[etype],[]).append(data)
        self._redraw()
        self._select_elem(len(self._elements)-1)

    # ------------------------------------------------------------------
    # Multi-selection (batch editor)
    # ------------------------------------------------------------------

    def _toggle_multi_sel(self, idx):
        elem=self._elements[idx]; etype=elem["type"]; data=elem["data"]
        did=id(data)
        if did in self._multi_sel_ids:
            self._multi_sel_ids.discard(did)
            self._multi_sel_data=[p for p in self._multi_sel_data if id(p[1])!=did]
        else:
            self._multi_sel_ids.add(did)
            self._multi_sel_data.append((etype,data))
        self._selected_idx=None; self._redraw()
        if len(self._multi_sel_data)>=2:
            self._show_batch_props()
        elif len(self._multi_sel_data)==1:
            e=self._multi_sel_data[0]; self._multi_sel_ids.clear(); self._multi_sel_data.clear()
            self._select_elem_by_data(e[1])
        else:
            self._clear_props()

    def _clear_multi_sel(self):
        if self._multi_sel_ids:
            self._multi_sel_ids.clear(); self._multi_sel_data.clear(); self._redraw()

    def _show_batch_props(self):
        for w in self._prop_frame.winfo_children(): w.destroy()
        f=ttk.Frame(self._prop_frame); f.pack(fill="x",padx=8,pady=4)
        n=len(self._multi_sel_data)
        types_set={e for e,_ in self._multi_sel_data}
        same_type=len(types_set)==1; etype=next(iter(types_set)) if same_type else "mixed"
        ttk.Label(f,text=f"▶ {n} {etype.upper().replace('_',' ')} selected" if same_type
                  else f"▶ {n} elements selected (mixed types)",
                  font=("",9,"bold")).grid(row=0,column=0,columnspan=4,sticky="w",pady=(0,6))

        # Type batch apply — enemies only
        if same_type and etype=="enemy":
            ttk.Label(f,text="Set type:").grid(row=1,column=0,sticky="e",padx=4)
            types=list(self._enemies.keys()) or ["basic"]
            v_t=tk.StringVar(value=types[0])
            ttk.Combobox(f,textvariable=v_t,values=types,width=12,state="readonly").grid(row=1,column=1,sticky="w")
            def apply_type():
                self._push_undo()
                for _,d in self._multi_sel_data: d["type"]=v_t.get()
                self._redraw(); self._show_batch_props()
            ttk.Button(f,text="Apply to all",command=apply_type).grid(row=1,column=2,padx=6)

        # ΔX / ΔY shift — any type
        row=2 if (same_type and etype=="enemy") else 1
        ttk.Label(f,text="Shift ΔX:").grid(row=row,column=0,sticky="e",padx=4)
        v_dx=tk.StringVar(value="0")
        ttk.Entry(f,textvariable=v_dx,width=6).grid(row=row,column=1,sticky="w")
        ttk.Label(f,text="ΔY:").grid(row=row,column=2,sticky="e",padx=4)
        v_dy=tk.StringVar(value="0")
        ttk.Entry(f,textvariable=v_dy,width=6).grid(row=row,column=3,sticky="w")
        def apply_shift():
            try: dx,dy=int(v_dx.get()),int(v_dy.get())
            except ValueError: messagebox.showwarning("Invalid","ΔX and ΔY must be integers."); return
            if dx==0 and dy==0: return
            self._push_undo()
            for _,d in self._multi_sel_data:
                d["x"]=d.get("x",0)+dx; d["y"]=d.get("y",0)+dy
            self._redraw(); self._show_batch_props()
        ttk.Button(f,text="Shift all",command=apply_shift).grid(row=row,column=4,padx=6)
        def deselect_all():
            self._multi_sel_ids.clear(); self._multi_sel_data.clear()
            self._redraw(); self._clear_props()
        ttk.Button(f,text="Deselect all",command=deselect_all).grid(row=row+1,column=0,columnspan=5,pady=6)

    # ------------------------------------------------------------------
    # Surface snap helper
    # ------------------------------------------------------------------

    def _find_surface_y(self, wx, wy, entity_height=60):
        best=None
        for p in self._zone.get("platforms",[]):
            # Only consider platforms at or below the click point (Y increases downward)
            if p["x"]<=wx<=p["x"]+p["w"] and p["y"]>=wy:
                if best is None or p["y"]<best: best=p["y"]
        return (best-entity_height) if best is not None else wy

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self):
        z=self._zone; issues=[]
        if not z.get("exits"):        issues.append("⚠ No zone exits — player cannot leave!")
        if not z.get("save_points"):  issues.append("⚠ No save points — player cannot save.")
        if not z.get("enemies") and not z.get("item_drops"): issues.append("ℹ No enemies or drops placed.")
        if z.get("spawn",[0,0])==[0,0]: issues.append("⚠ Spawn is at world origin (0,0) — may be unintentional.")
        # Check for enemies referencing unknown types
        known=set(self._enemies.keys())
        for e in z.get("enemies",[]):
            if e.get("type") not in known: issues.append(f"⚠ Unknown enemy type: '{e.get('type')}'")
        # Check NPC refs
        known_npc=set(self._npctypes.keys())
        for n in z.get("npcs",[]):
            if n.get("type") not in known_npc: issues.append(f"⚠ Unknown NPC type: '{n.get('type')}'")
        known_shop=set(self._shops.keys())
        for n in z.get("npcs",[]):
            if n.get("shop_id") and n["shop_id"] not in known_shop:
                issues.append(f"⚠ Unknown shop ID: '{n['shop_id']}'")
        known_quest=set(self._quests.keys())
        for n in z.get("npcs",[]):
            if n.get("gives_quest") and n["gives_quest"] not in known_quest:
                issues.append(f"⚠ Unknown quest ID: '{n['gives_quest']}'")
        # Spawn reachability checks
        sx,sy=z.get("spawn",[0,0])
        platforms=z.get("platforms",[])
        ground_below=any(p["x"]<=sx<=p["x"]+p["w"] and sy<p["y"]<=sy+300 for p in platforms)
        if not ground_below:
            issues.append("⚠ No platform directly below spawn within 300px — player may fall into void.")
        embedded=any(p["x"]<=sx<=p["x"]+p["w"] and p["y"]<=sy<=p["y"]+p["h"] for p in platforms)
        if embedded:
            issues.append("⚠ Spawn point is inside a platform.")

        if issues:
            messagebox.showwarning("Zone Validation","\n".join(issues))
        else:
            messagebox.showinfo("Zone Validation","✓ No issues found.")

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def _new_zone(self):
        self._zone=self._blank_zone(); self._zone_path=None
        self._v_id.set("new_zone"); self._v_sx.set("200"); self._v_sy.set("596")
        self._bg_btn.set([30,30,40]); self._v_music.set("")
        self._undo_stack.clear(); self._redo_stack.clear()
        self._redraw()

    def _open_zone(self):
        from tkinter import filedialog
        path=filedialog.askopenfilename(initialdir=str(ZONES_DIR),title="Open Zone",filetypes=[("Zone JSON","*.json")])
        if not path: return
        try: z=_load(Path(path))
        except Exception as e: messagebox.showerror("Error",f"Could not load:\n{e}"); return
        self._zone=z; self._zone_path=Path(path)
        self._v_id.set(z.get("id",Path(path).stem))
        sp=z.get("spawn",[200,596])
        self._v_sx.set(str(sp[0])); self._v_sy.set(str(sp[1]))
        self._bg_btn.set(z.get("bg_color",[30,30,40])); self._v_music.set(z.get("music") or "")
        self._undo_stack.clear(); self._redo_stack.clear()
        self._redraw()

    def _save_zone(self):
        try:
            self._zone["id"]=self._v_id.get().strip() or "new_zone"
            self._zone["spawn"]=[int(self._v_sx.get()),int(self._v_sy.get())]
            self._zone["bg_color"]=self._bg_btn.get()
            m=self._v_music.get().strip(); self._zone["music"]=m if m else None
        except ValueError as e: messagebox.showerror("Error",f"Invalid value: {e}"); return
        if self._zone_path is None:
            from tkinter import filedialog
            path=filedialog.asksaveasfilename(initialdir=str(ZONES_DIR),title="Save Zone As",
                defaultextension=".json",filetypes=[("Zone JSON","*.json")],initialfile=f"{self._zone['id']}.json")
            if not path: return
            self._zone_path=Path(path)
        self._zone_path.parent.mkdir(parents=True,exist_ok=True)
        _save(self._zone_path,self._zone)
        messagebox.showinfo("Saved",f"Zone saved to:\n{self._zone_path}")

# ---------------------------------------------------------------------------
# Main application — supports hot-switching between game installations
# ---------------------------------------------------------------------------

_RECENT_MAX = 8   # number of recent installations to remember


def _load_config() -> dict:
    try:
        if _CONFIG_FILE.exists():
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_config(cfg: dict) -> None:
    try:
        _CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception:
        pass


class EditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1300x820"); self.minsize(960, 640)
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except Exception: pass

        self._nb: ttk.Notebook | None = None
        self._recent_menu: tk.Menu | None = None
        self._status_var = tk.StringVar()

        self._build_menu()
        self._build_tabs()
        self._build_statusbar()
        self._update_title()

        # Add current path to recent list on first launch
        _record_recent(str(DATA_DIR))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_menu(self):
        menu = tk.Menu(self); self.config(menu=menu)

        fm = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=fm)
        fm.add_command(label="Browse for game installation...",
                       command=self._browse, accelerator="Ctrl+O")
        self.bind_all("<Control-o>", lambda _: self._browse())

        fm.add_separator()
        self._recent_menu = tk.Menu(fm, tearoff=False)
        fm.add_cascade(label="Recent installations", menu=self._recent_menu)
        self._refresh_recent_menu()

        fm.add_separator()
        fm.add_command(label="Exit", command=self.quit)

    def _build_tabs(self):
        if self._nb:
            self._nb.destroy()
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=4, pady=(4, 0))
        self._nb.add(EnemyTab(self._nb),   text="  Enemies  ")
        self._nb.add(ItemTab(self._nb),    text="  Items  ")
        self._nb.add(RecipeTab(self._nb),  text="  Recipes  ")
        self._nb.add(NPCTab(self._nb),     text="  NPCs  ")
        self._nb.add(AbilityTab(self._nb), text="  Abilities  ")
        self._nb.add(ShopTab(self._nb),    text="  Shops  ")
        self._nb.add(QuestTab(self._nb),   text="  Quests  ")
        self._nb.add(ZoneTab(self._nb),    text="  Zone Editor  ")

    def _build_statusbar(self):
        bar = ttk.Frame(self, relief="sunken")
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self._status_var,
                  anchor="w", padding=(6, 2)).pack(fill="x")

    # ------------------------------------------------------------------
    # Title + status
    # ------------------------------------------------------------------

    def _update_title(self):
        self.title(f"Survival Game Editor  —  {DATA_DIR}")
        self._status_var.set(f"Data folder: {DATA_DIR}")

    # ------------------------------------------------------------------
    # Recent installations menu
    # ------------------------------------------------------------------

    def _refresh_recent_menu(self):
        self._recent_menu.delete(0, "end")
        cfg = _load_config()
        recents = [r for r in cfg.get("recent", []) if Path(r).is_dir()]
        if not recents:
            self._recent_menu.add_command(
                label="(no recent installations)", state="disabled")
            return
        for path in recents:
            # Mark the currently loaded one
            marker = "  *" if Path(path) == DATA_DIR else ""
            label  = f"{path}{marker}"
            self._recent_menu.add_command(
                label=label,
                command=lambda p=path: self._switch_to(p))

    # ------------------------------------------------------------------
    # Switching installations
    # ------------------------------------------------------------------

    def _browse(self):
        chosen = filedialog.askdirectory(
            title="Select the 'data' folder inside your game installation",
            initialdir=str(DATA_DIR) if DATA_DIR.exists() else str(Path.home()),
        )
        if chosen:
            self._switch_to(chosen)

    def _switch_to(self, new_path: str):
        global DATA_DIR, ZONES_DIR
        p = Path(new_path)
        if not p.is_dir():
            messagebox.showerror("Not found",
                                 f"Folder does not exist:\n{new_path}")
            return
        # Confirm if it doesn't look like a game data folder
        if not (p / "enemies.json").exists() and not (p / "items.json").exists():
            if not messagebox.askyesno(
                    "Unusual folder",
                    f"This folder doesn't contain enemies.json or items.json.\n"
                    f"It may not be a game data folder.\n\n"
                    f"Switch anyway?\n\n{new_path}"):
                return

        DATA_DIR  = p
        ZONES_DIR = p / "zones"
        _record_recent(new_path)
        self._build_tabs()          # hot-reload all tabs with new data
        self._update_title()
        self._refresh_recent_menu()


def _record_recent(path: str) -> None:
    """Add path to the recent list in the config file (deduped, capped)."""
    cfg = _load_config()
    recents: list = cfg.get("recent", [])
    if path in recents:
        recents.remove(path)
    recents.insert(0, path)
    cfg["recent"]   = recents[:_RECENT_MAX]
    cfg["data_dir"] = path
    _save_config(cfg)


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ZONES_DIR.mkdir(parents=True, exist_ok=True)
    EditorApp().mainloop()
