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

# Colors
BG_COLOR      = (30,  30,  40)   # dark background
PLAYER_COLOR  = (100, 180, 255)  # blue — player rectangle
PLATFORM_COLOR = (140, 100, 60)  # brown — platforms
MARKER_COLOR  = (80,  80,  80)   # gray — world marker rectangles (debug)
WHITE         = (255, 255, 255)
RED           = (220, 50,  50)
GREEN         = (50,  200, 50)
