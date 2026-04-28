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
PLAYER_SPEED  = 5
PLAYER_WIDTH  = 32
PLAYER_HEIGHT = 64

# Colors
BG_COLOR     = (30,  30,  40)   # dark background
PLAYER_COLOR = (100, 180, 255)  # blue — player rectangle
MARKER_COLOR = (80,  80,  80)   # gray — world marker rectangles (debug)
WHITE        = (255, 255, 255)
RED          = (220, 50,  50)
GREEN        = (50,  200, 50)
