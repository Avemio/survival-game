#!/usr/bin/env python3
"""
package.py  —  Build distributable packages for the game and/or editor.

Usage:
  python package.py game          Build dist/survival-game/
  python package.py editor        Build dist/survival-game-editor/
  python package.py all           Build both
  python package.py game --zip    Also create dist/survival-game.zip
  python package.py editor --zip  Also create dist/survival-game-editor.zip
  python package.py all --zip     Build and zip both

The packages are completely self-contained:
  survival-game/         — everything needed to play (Python + pygame-ce only)
  survival-game-editor/  — standalone editor (Python stdlib only, no pygame)
"""

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)
    print(f"  + {dst.relative_to(DIST)}")


def _zip(folder: Path):
    zip_path = folder.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in folder.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(folder.parent))
    size_mb = zip_path.stat().st_size / 1_048_576
    print(f"  -> {zip_path.relative_to(ROOT)}  ({size_mb:.1f} MB)")


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    print(f"  + {path.relative_to(DIST)}")


# ---------------------------------------------------------------------------
# Game package
# ---------------------------------------------------------------------------

def build_game(make_zip: bool = False):
    out = DIST / "survival-game"
    out.mkdir(parents=True, exist_ok=True)
    print(f"\nBuilding game package -> {out.relative_to(ROOT)}/")

    _copy(ROOT / "main.py",         out / "main.py")
    _copy(ROOT / "game",            out / "game")
    _copy(ROOT / "data",            out / "data")

    assets = ROOT / "assets"
    if assets.exists():
        _copy(assets, out / "assets")

    # requirements.txt  (game only needs pygame-ce)
    _write(out / "requirements.txt", "pygame-ce>=2.5.0\n")

    # README
    _write(out / "README.txt", """
Survival Game
=============

Requirements
------------
Python 3.11 or later
pygame-ce (Community Edition)

Install dependencies
--------------------
  pip install -r requirements.txt

Run the game
------------
  python main.py

Controls
--------
  WASD / Arrows  Move + jump
  Z              Attack
  Q / R          Use ability
  Hold X         Draw bow  (release to fire)
  F              Use / equip selected item
  1-8            Hotbar slots
  I              Inventory
  J              Quest log
  C              Crafting menu
  E              Talk / Shop / Open chest
  Esc            Pause

See GAME_GUIDE.md for the full guide.
""")

    if (ROOT / "GAME_GUIDE.md").exists():
        _copy(ROOT / "GAME_GUIDE.md", out / "GAME_GUIDE.md")

    if make_zip:
        print(f"  Zipping...")
        _zip(out)

    print(f"  Done.  Run:  python dist/survival-game/main.py")


# ---------------------------------------------------------------------------
# Editor package
# ---------------------------------------------------------------------------

def build_editor(make_zip: bool = False):
    out = DIST / "survival-game-editor"
    out.mkdir(parents=True, exist_ok=True)
    print(f"\nBuilding editor package -> {out.relative_to(ROOT)}/")

    # The editor is a single self-contained script
    _copy(ROOT / "tools" / "editor.py", out / "editor.py")

    if (ROOT / "EDITOR_GUIDE.md").exists():
        _copy(ROOT / "EDITOR_GUIDE.md", out / "EDITOR_GUIDE.md")

    # requirements.txt — editor uses only stdlib (tkinter ships with Python)
    _write(out / "requirements.txt", "# No third-party packages required.\n# Tkinter is included with Python 3 on Windows and macOS.\n# Linux: sudo apt install python3-tk\n")

    _write(out / "README.txt", """
Survival Game — Content Editor
================================

Requirements
------------
Python 3.11 or later
Tkinter (included with Python on Windows/macOS; on Linux: sudo apt install python3-tk)
No other packages required.

Run the editor
--------------
  python editor.py

First run
---------
The editor will ask you to select the 'data' folder inside a game installation.
Example:  C:/survival-game/data

The path is saved to editor_config.json next to editor.py.
To point at a different game installation: File -> Change game data folder...

You can also pass the data path directly on the command line:
  python editor.py C:/survival-game/data

See EDITOR_GUIDE.md for the full guide.
""")

    if make_zip:
        print(f"  Zipping...")
        _zip(out)

    print(f"  Done.  Run:  python dist/survival-game-editor/editor.py")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = [a.lower() for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        raise SystemExit(0)

    make_zip = "--zip" in args
    targets  = [a for a in args if not a.startswith("-")]

    if not targets:
        print("Error: specify 'game', 'editor', or 'all'.")
        print(__doc__)
        raise SystemExit(1)

    DIST.mkdir(exist_ok=True)

    for target in targets:
        if target in ("game", "all"):
            build_game(make_zip)
        if target in ("editor", "all"):
            build_editor(make_zip)

    print(f"\nAll done.  Output in:  {DIST.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
