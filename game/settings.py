"""
settings.py
All constants and tuning values for the game.
Nothing imports from the game into this file — it has no dependencies.
Change values here to affect the whole game without touching logic.
"""

# Display
SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
FPS           = 60
TITLE         = "Survival Game"

# World
WORLD_WIDTH  = 10000   # total pixel width of the world
WORLD_HEIGHT = 720     # matches screen height for now
PLATFORM_BUCKET_SIZE = 512   # px per spatial bucket column — reduce for denser zones

# Player
PLAYER_SPEED  = 280    # horizontal pixels per second (dt-based — was 5 pre-M2)
PLAYER_WIDTH  = 32
PLAYER_HEIGHT = 64

# Physics
GRAVITY         = 1900  # pixels per second squared — pulls player down each frame
JUMP_FORCE      = 580   # initial upward velocity on tap (lower = shorter tap jump)
JUMP_HOLD_FORCE = 900   # extra upward force per second while holding — compensates for lower tap
MAX_JUMP_TIME   = 0.29  # max seconds jump can extend — tap+hold total restores original max height
MAX_FALL_SPEED  = 1400  # terminal velocity — prevents infinite acceleration

# Player stats
PLAYER_MAX_HEALTH = 100

# Combat
ATTACK_DAMAGE   = 25    # damage per swing
ATTACK_WIDTH    = 55    # horizontal reach of the hitbox
ATTACK_HEIGHT   = 64    # vertical size — matches player height
ATTACK_DURATION = 0.18  # seconds the hitbox stays active per swing
ATTACK_COOLDOWN = 0.45  # seconds before player can swing again

# Enemy base stats (specific enemies override these via enemies.json)
ENEMY_WIDTH        = 40
ENEMY_HEIGHT       = 60
ENEMY_HEALTH       = 100
HIT_FLASH_DURATION = 0.12   # seconds enemy flashes white after taking damage

# Enemy AI
ENEMY_SPEED           = 80     # patrol speed px/s
ENEMY_CHASE_SPEED     = 180    # chase speed px/s (outrunnable at player 280 but not by much)
ENEMY_AGGRO_RANGE     = 300    # px: player within this triggers chase
ENEMY_DEAGGRO_RANGE   = 500    # px: player beyond this, return to patrol
ENEMY_ATTACK_RANGE    = 65     # px: begin wind-up when this close horizontally
ENEMY_ATTACK_DAMAGE   = 15     # hp per hit (player max = 100)
ENEMY_ATTACK_COOLDOWN = 1.5    # seconds between enemy swings
ENEMY_PATROL_RADIUS   = 200    # px: max distance enemy wanders from its spawn X
ENEMY_ACTIVE_RADIUS   = 2000   # px: skip update() for enemies beyond this distance from player
ENEMY_WINDUP_COLOR    = (255, 160,  30)  # orange — winding up to swing
ENEMY_ATTACK_COLOR    = (255,  80,  50)  # red-orange — enemy hitbox outline (debug)

# HUD layout
HUD_HEALTH_X      = 20     # distance from left edge
HUD_HEALTH_Y      = 20     # distance from top edge
HUD_HEALTH_W      = 200    # full bar width
HUD_HEALTH_H      = 18     # bar height
HOTBAR_SLOTS      = 8      # number of hotbar slots
HOTBAR_SLOT_SIZE  = 48     # width and height of each slot
HOTBAR_SLOT_GAP   = 4      # gap between slots
HOTBAR_Y_OFFSET   = 10     # distance from bottom edge

# Colors
BG_COLOR       = (30,  30,  40)   # dark background
PLAYER_COLOR   = (100, 180, 255)  # blue — player rectangle
PLATFORM_COLOR = (140, 100, 60)   # brown — platforms
ATTACK_COLOR   = (255, 220, 50)   # yellow — attack hitbox outline
ENEMY_COLOR    = (200, 80,  80)   # red — enemy rectangle
ENEMY_HIT_COLOR = (255, 255, 255) # white — enemy flash on hit
MARKER_COLOR   = (80,  80,  80)   # gray — world marker rectangles (debug)
WHITE          = (255, 255, 255)
RED            = (220, 50,  50)
GREEN          = (50,  200, 50)

# Save point colors
SAVE_POINT_COLOR        = (80,  200, 180)   # teal — idle
SAVE_POINT_ACTIVE_COLOR = (200, 255, 240)   # bright teal — flash on save

# Zone exit portal
EXIT_COLOR        = (50,  180, 100)   # green — zone exit rect
EXIT_BORDER_COLOR = (120, 240, 160)   # bright green — portal border

# Dialogue box
DIALOGUE_PANEL_BG     = (18,  18,  28)
DIALOGUE_PANEL_BORDER = (90,  90,  120)
DIALOGUE_NAME_COLOR   = (220, 200, 80)    # yellow — speaker name
DIALOGUE_TEXT_COLOR   = (220, 220, 230)   # near-white — body text
DIALOGUE_HINT_COLOR   = (110, 110, 130)   # muted — "E Continue" hint

# Crafting menu
CRAFT_PANEL_W          = 440
CRAFT_PANEL_H          = 420
CRAFT_PANEL_BG         = (22,  22,  32)
CRAFT_PANEL_BORDER     = (90,  90,  120)
CRAFT_TITLE_COLOR      = (220, 200, 80)    # yellow — matches hotbar selected
CRAFT_RECIPE_COLOR     = (210, 210, 220)   # near-white — craftable name
CRAFT_RECIPE_DIM       = (90,  90,  100)   # grey — name when not craftable
CRAFT_SELECTED_BG      = (45,  45,  65)    # highlighted row background
CRAFT_INGREDIENT_OK    = (90,  210, 100)   # green — have enough
CRAFT_INGREDIENT_MISS  = (210, 90,  90)    # red — not enough
CRAFT_FOOTER_COLOR     = (120, 120, 140)   # muted — controls hint

# Death / respawn
DEATH_OVERLAY_DURATION = 2.0            # seconds before respawn
DEATH_TEXT_COLOR       = (255, 60, 60)  # bright red — "YOU DIED" text

# Projectiles (arrows)
ARROW_SPEED       = 550    # px/s initial launch speed
ARROW_GRAVITY     = 550    # px/s² — lighter than player gravity for a graceful arc
ARROW_DAMAGE      = 20     # hp per hit
ARROW_WIDTH       = 14     # px — visual / hitbox width
ARROW_HEIGHT      = 4      # px — visual / hitbox height
ARROW_ANGLE_MAX   = 60     # max degrees above/below horizontal
ARROW_ANGLE_SPEED = 90     # degrees per second while adjusting aim
ARROW_COLOR       = (220, 200, 120)   # warm yellow — arrow in flight

# Aim indicator
AIM_PREVIEW_STEPS  = 20    # number of dots in the trajectory preview
AIM_PREVIEW_STEP_T = 0.055 # seconds per step (covers ~1.1s of flight time)
AIM_DOT_COLOR      = (255, 255, 140)  # pale yellow dots

# HUD colors
HUD_HEALTH_BG      = (80,  20,  20)   # dark red — empty bar background
HUD_HEALTH_FG      = (220, 50,  50)   # bright red — health fill
HUD_HEALTH_BORDER  = (200, 200, 200)  # light grey — bar outline
HOTBAR_BG          = (40,  40,  50)   # dark — slot background
HOTBAR_BORDER      = (100, 100, 120)  # grey — slot border
HOTBAR_SELECTED    = (220, 200, 80)   # yellow — selected slot highlight

# Audio — overridden by config.json
VOLUME       = 0.8   # sound effect volume (0.0 – 1.0)
MUSIC_VOLUME = 0.5   # music volume (0.0 – 1.0)

# Inventory
INVENTORY_SLOTS = 32  # total slots; hotbar shows first HOTBAR_SLOTS of these

# Mana / ability system
PLAYER_MAX_MANA    = 100
MANA_REGEN_RATE    = 5.0    # mana per second
ABILITY_SLOT_COUNT = 2      # number of Q/R ability slots

# Combat feel
HITSTOP_DURATION = 0.05     # seconds of physics freeze when landing a hit (3 frames @60fps)

# XP / level system
XP_BASE        = 100    # XP required to reach level 2
XP_SCALE       = 1.5    # multiplier applied each level (level 3 needs 150, level 4 needs 225, …)
MAX_LEVEL      = 50
LEVEL_UP_HP    = 15     # max_health bonus gained per level-up
LEVEL_UP_MANA  = 10     # max_mana bonus gained per level-up
XP_BAR_H      = 6
XP_BAR_BG     = (15,  15,  50)
XP_BAR_FG     = (80, 100, 255)
XP_BAR_BORDER = (100, 120, 220)
MANA_BAR_H      = 12
MANA_BAR_BG     = (20,  20,  80)
MANA_BAR_FG     = (60, 120, 255)
MANA_BAR_BORDER = (100, 140, 255)

# Ability slot HUD (Q / R slots displayed next to hotbar)
ABILITY_SLOT_SIZE = 40

# Status effect colors (used by HUD flash)
STATUS_COLORS = {
    "poison": (80,  200, 80),
    "burn":   (255, 120, 20),
    "stun":   (255, 255, 80),
    "freeze": (120, 200, 255),
    "slow":   (150, 100, 200),
}

# ------------------------------------------------------------------
# config.json override — applied last so user settings win
# ------------------------------------------------------------------
import json as _json
from pathlib import Path as _Path
_cfg = {}   # ensure always defined so del below never fails
try:
    _cfg = _json.loads((_Path(__file__).parent.parent / "config.json").read_text())
    _res = _cfg.get("resolution")
    if isinstance(_res, list) and len(_res) == 2:
        SCREEN_WIDTH  = int(_res[0])
        SCREEN_HEIGHT = int(_res[1])
    if "fps" in _cfg:
        FPS = int(_cfg["fps"])
    if "volume" in _cfg:
        VOLUME = float(_cfg["volume"])
    if "music_volume" in _cfg:
        MUSIC_VOLUME = float(_cfg["music_volume"])
except Exception:
    pass
del _cfg, _json, _Path
