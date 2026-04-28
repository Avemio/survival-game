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
