"""
tools/generate_sprites.py
Generates character sprite animations via the Pixellab API and wires them
directly into the game's assets/sprites/ and data/sprites/ directories.

Usage:
    python tools/generate_sprites.py --name player --type player --description "A seasoned assassin..."
    python tools/generate_sprites.py --name enemy_basic --type enemy --description "A tired city guard..."

API key is read from .pixellab_key in the project root.
"""

import argparse
import base64
import json
import sys
from io import BytesIO
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Run: pip install requests")

try:
    from PIL import Image
except ImportError:
    sys.exit("Run: pip install pillow")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT       = Path(__file__).parent.parent
ASSET_DIR  = ROOT / "assets" / "sprites"
CONFIG_DIR = ROOT / "data"   / "sprites"
KEY_FILE   = ROOT / ".pixellab_key"

API_BASE   = "https://api.pixellab.ai/v2"


def _load_key() -> str:
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    sys.exit(f"API key not found. Create {KEY_FILE} containing your Pixellab key.")


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _b64_to_png(b64) -> bytes:
    # API returns either a plain string or {"type":"base64","base64":"...","format":"png"}
    if isinstance(b64, dict):
        b64 = b64.get("base64", "")
    return base64.b64decode(b64)


def _mirror_png(png_bytes: bytes) -> bytes:
    img = Image.open(BytesIO(png_bytes)).transpose(Image.FLIP_LEFT_RIGHT)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _to_ref(png_bytes: bytes) -> dict:
    return {"type": "base64", "base64": base64.b64encode(png_bytes).decode(), "format": "png"}


def animate(key: str, description: str, action: str, direction: str,
            width: int, height: int, reference: bytes) -> list[bytes]:
    """Call /animate-with-text; return list of PNG bytes (one per frame)."""
    print(f"    API call: animate '{action}' facing {direction}...", end=" ", flush=True)
    resp = requests.post(
        f"{API_BASE}/animate-with-text",
        headers=_headers(key),
        json={
            "description":   description,
            "action":        action,
            "view":          "side",
            "direction":     direction,
            "image_size":    {"width": width, "height": height},
            "reference_image": _to_ref(reference),
        },
        timeout=120,
    )
    resp.raise_for_status()
    data   = resp.json()
    frames = [_b64_to_png(item) for item in data.get("images", [])]
    print(f"{len(frames)} frames")
    return frames


def static_frame(key: str, description: str, width: int, height: int) -> bytes:
    """Call /create-image-pixen for a single static idle frame."""
    print(f"    API call: static idle frame...", end=" ", flush=True)
    resp = requests.post(
        f"{API_BASE}/create-image-pixen",
        headers=_headers(key),
        json={
            "description":   description,
            "image_size":    {"width": width, "height": height},
            "no_background": True,
            "view":          "side",
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    print("1 frame")
    return _b64_to_png(data.get("image", ""))


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def save(data: bytes, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def save_frames(frames: list[bytes], out_dir: Path, prefix: str) -> int:
    for i, f in enumerate(frames):
        save(f, out_dir / f"{prefix}_{i:03d}.png")
    return len(frames)


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------

# Shared action strings — embed in description context so AI understands style
ACTIONS = {
    "run":    "running, side-scrolling game animation",
    "attack": "attacking with a melee weapon, swinging forward",
    "jump":   "jumping upward, side-scrolling game animation",
}


def generate(name: str, char_type: str, description: str, width: int, height: int):
    key       = _load_key()
    out_dir   = ASSET_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    frame_counts = {}

    # -- Idle (static, mirrored) --
    print("\n  [idle]")
    idle_r = static_frame(key, f"{description}, facing right", width, height)
    save(idle_r, out_dir / "idle_right.png")
    save(_mirror_png(idle_r), out_dir / "idle_left.png")

    # -- Run (east from API, west mirrored) --
    print("\n  [run]")
    run_r = animate(key, description, ACTIONS["run"], "east", width, height, idle_r)
    run_l = [_mirror_png(f) for f in run_r]
    frame_counts["run_right"] = save_frames(run_r, out_dir, "run_right")
    frame_counts["run_left"]  = save_frames(run_l, out_dir, "run_left")

    # -- Attack (east from API, west mirrored) --
    print("\n  [attack]")
    atk_r = animate(key, description, ACTIONS["attack"], "east", width, height, idle_r)
    atk_l = [_mirror_png(f) for f in atk_r]
    frame_counts["attack_right"] = save_frames(atk_r, out_dir, "attack_right")
    frame_counts["attack_left"]  = save_frames(atk_l, out_dir, "attack_left")

    # -- Jump (player only, east from API, west mirrored) --
    jump_count = 0
    if char_type == "player":
        print("\n  [jump]")
        jmp_r = animate(key, description, ACTIONS["jump"], "east", width, height, idle_r)
        jmp_l = [_mirror_png(f) for f in jmp_r]
        frame_counts["jump_right"] = save_frames(jmp_r, out_dir, "jump_right")
        frame_counts["jump_left"]  = save_frames(jmp_l, out_dir, "jump_left")
        jump_count = frame_counts["jump_right"]

    # -- JSON config --
    run_fps = 14.0 if char_type == "player" else 10.0
    atk_fps = 12.0 if char_type == "player" else 10.0

    animations = {
        "run_right":    {"prefix": "run_right",    "frames": frame_counts["run_right"],    "fps": run_fps},
        "run_left":     {"prefix": "run_left",     "frames": frame_counts["run_left"],     "fps": run_fps},
        "attack_right": {"prefix": "attack_right", "frames": frame_counts["attack_right"], "fps": atk_fps},
        "attack_left":  {"prefix": "attack_left",  "frames": frame_counts["attack_left"],  "fps": atk_fps},
    }
    if char_type == "player" and jump_count:
        animations["jump_right"] = {"prefix": "jump_right", "frames": jump_count}
        animations["jump_left"]  = {"prefix": "jump_left",  "frames": jump_count}

    cfg = {
        "base_path":  f"assets/sprites/{name}",
        "fps":        8.0,
        "idle":       {"right": "idle_right.png", "left": "idle_left.png"},
        "animations": animations,
    }

    cfg_path = CONFIG_DIR / f"{name}.json"
    cfg_path.write_text(json.dumps(cfg, indent=2))

    print(f"\n  Saved {len(list(out_dir.iterdir()))} PNGs  ->  assets/sprites/{name}/")
    print(f"  Wrote config                          ->  data/sprites/{name}.json")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Generate sprites via Pixellab API")
    p.add_argument("--name",        required=True,
                   help="Sprite name matching enemies.json 'sprite' field, e.g. enemy_basic")
    p.add_argument("--type",        choices=["player", "enemy"], default="enemy")
    p.add_argument("--description", required=True,
                   help="Character description sent to the AI")
    p.add_argument("--width",  type=int, default=64)
    p.add_argument("--height", type=int, default=64)
    args = p.parse_args()

    print(f"Generating '{args.name}' ({args.type}) at {args.width}×{args.height}px")
    generate(args.name, args.type, args.description, args.width, args.height)
    print("\nDone — run the game to see the new sprites.")


if __name__ == "__main__":
    main()
