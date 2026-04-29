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

# Enemy (base stats — specific enemies will override in data later)
ENEMY_WIDTH        = 40
ENEMY_HEIGHT       = 60
ENEMY_HEALTH       = 100
HIT_FLASH_DURATION = 0.12   # seconds enemy flashes red after taking damage

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

# HUD colors
HUD_HEALTH_BG      = (80,  20,  20)   # dark red — empty bar background
HUD_HEALTH_FG      = (220, 50,  50)   # bright red — health fill
HUD_HEALTH_BORDER  = (200, 200, 200)  # light grey — bar outline
HOTBAR_BG          = (40,  40,  50)   # dark — slot background
HOTBAR_BORDER      = (100, 100, 120)  # grey — slot border
HOTBAR_SELECTED    = (220, 200, 80)   # yellow — selected slot highlight
