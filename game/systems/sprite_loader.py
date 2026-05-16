"""
systems/sprite_loader.py
Data-driven sprite loader — reads a JSON config and builds an Animator + idle surfaces.
Adding sprites for a new character = drop PNGs in assets/sprites/{name}/, write data/sprites/{name}.json.
Owns: reading sprite config, loading surfaces, building Animator instances.
Does NOT own: entity logic, animation state, drawing.

Config format (data/sprites/{name}.json):
  {
    "base_path": "assets/sprites/player",   # relative to project root
    "fps": 8.0,                             # default fps for all animations
    "idle": {
      "right": "idle_right.png",
      "left":  "idle_left.png"
    },
    "animations": {
      "run_right": { "prefix": "run_right", "frames": 5, "fps": 14.0 },
      "run_left":  { "prefix": "run_left",  "frames": 5, "fps": 14.0 },
      "jump_right":{ "prefix": "jump_right","frames": 7 },
      "jump_left": { "prefix": "jump_left", "frames": 7 }
    }
  }

The "idle" section surfaces are returned separately so callers can draw them directly,
bypassing the Animator state machine (avoids flicker on physics edge cases).
"""

import json
import pygame
from pathlib import Path
from game.systems.animator import Animator

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_SPRITES_DATA = _PROJECT_ROOT / "data" / "sprites"


def _load_surf(base: Path, filename: str) -> "pygame.Surface | None":
    p = base / filename
    try:
        return pygame.image.load(str(p)).convert_alpha() if p.exists() else None
    except Exception:
        return None


def _load_seq(base: Path, prefix: str, count: int) -> "list[pygame.Surface]":
    frames = []
    for i in range(count):
        s = _load_surf(base, f"{prefix}_{i:03d}.png")
        if s is None:
            break
        frames.append(s)
    return frames


def _idle_pair(base: Path, filename: str):
    """Return (Surface, foot_y) or None."""
    s = _load_surf(base, filename)
    if s is None:
        return None
    return (s, s.get_bounding_rect(min_alpha=8).bottom - 1)


def load_character(name: str):
    """Load sprites for character *name* from data/sprites/{name}.json.

    Returns (animator, idle_right, idle_left).
    Each idle value is (Surface, foot_y) or None.
    animator is None if no animation frames were found.
    """
    config_path = _SPRITES_DATA / f"{name}.json"
    if not config_path.exists():
        return None, None, None

    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)

    base         = _PROJECT_ROOT / cfg.get("base_path", f"assets/sprites/{name}")
    default_fps  = float(cfg.get("fps", 8.0))

    anims:     dict = {}
    state_fps: dict = {}
    for state, sc in cfg.get("animations", {}).items():
        frames = _load_seq(base, sc["prefix"], int(sc["frames"]))
        if frames:
            anims[state] = frames
            if "fps" in sc:
                state_fps[state] = float(sc["fps"])

    animator  = Animator(anims, fps=default_fps, state_fps=state_fps) if anims else None

    idle_cfg  = cfg.get("idle", {})
    idle_r    = _idle_pair(base, idle_cfg["right"]) if "right" in idle_cfg else None
    idle_l    = _idle_pair(base, idle_cfg["left"])  if "left"  in idle_cfg else None

    return animator, idle_r, idle_l
