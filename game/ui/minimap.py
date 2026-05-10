"""
ui/minimap.py
Compact minimap drawn in the top-right corner of the HUD.
Shows the player's position relative to: save points, zone exits, NPCs, enemies.
All surfaces built once at init; only the player/enemy dots are dynamic.
Does NOT own: game state — reads engine references each draw() call.
"""

import pygame
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT

# Map panel dimensions
_W      = 180    # map drawable area width  (px on screen)
_H      = 40     # map drawable area height (px on screen)
_PAD    = 8      # gap from screen edge
_MARGIN = 4      # inner padding around drawn content

# Dot sizes
_PLAYER_R  = 3
_ENEMY_R   = 2
_ICON_R    = 2

# Colors
_BG_COLOR      = (15,  15,  25, 180)   # semi-transparent panel
_BORDER_COLOR  = (60,  60,  90)
_PLAYER_COLOR  = (80, 200, 255)
_ENEMY_COLOR   = (220, 60,  60)
_SAVE_COLOR    = (60, 200, 170)
_EXIT_COLOR    = (60, 200, 90)
_NPC_COLOR     = (220, 200, 80)
_CHEST_COLOR   = (200, 160, 40)
_SPAWN_COLOR   = (120, 255, 120)


class Minimap:
    def __init__(self):
        # Panel position — top-right corner
        self._px = SCREEN_WIDTH  - _W - _PAD
        self._py = _PAD

        # Pre-built background surface (semi-transparent)
        self._bg = pygame.Surface((_W, _H), pygame.SRCALPHA)
        self._bg.fill(_BG_COLOR)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, engine):
        """engine is passed each frame so the minimap always reflects live state."""
        world = engine.world
        player = engine.player

        # Determine world extents for scaling
        world_w = max(world.world_w, 800)
        world_h = max(world.world_h, 400)

        draw_w = _W - _MARGIN * 2
        draw_h = _H - _MARGIN * 2
        px = self._px
        py = self._py

        # Background + border
        screen.blit(self._bg, (px, py))
        pygame.draw.rect(screen, _BORDER_COLOR, (px, py, _W, _H), 1)

        # Helper: world → minimap screen coords
        def wx(x): return px + _MARGIN + int(x / world_w * draw_w)
        def wy(y): return py + _MARGIN + int(y / world_h * draw_h)

        # Save points (teal squares)
        for sp in engine.save_points:
            sx, sy = wx(sp.rect.centerx), wy(sp.rect.centery)
            pygame.draw.rect(screen, _SAVE_COLOR, (sx - 2, sy - 2, 4, 4))

        # Zone exits (green triangles / small lines)
        for ex in engine.exits:
            sx, sy = wx(ex.rect.centerx), wy(ex.rect.centery)
            pygame.draw.circle(screen, _EXIT_COLOR, (sx, sy), _ICON_R)

        # Chests (gold dots)
        for ch in engine.chests:
            if not ch.open:
                sx, sy = wx(ch.rect.centerx), wy(ch.rect.centery)
                pygame.draw.circle(screen, _CHEST_COLOR, (sx, sy), _ICON_R)

        # NPCs (yellow dots)
        for npc in engine.npcs:
            sx, sy = wx(npc.rect.centerx), wy(npc.rect.centery)
            pygame.draw.circle(screen, _NPC_COLOR, (sx, sy), _ICON_R)

        # Enemies (red dots — shown when close to player or visible)
        for en in engine.enemies:
            if en.alive:
                sx, sy = wx(en.rect.centerx), wy(en.rect.centery)
                pygame.draw.circle(screen, _ENEMY_COLOR, (sx, sy), _ENEMY_R)

        # Player (bright blue, drawn last so always visible)
        sx, sy = wx(player.rect.centerx), wy(player.rect.centery)
        pygame.draw.circle(screen, _PLAYER_COLOR, (sx, sy), _PLAYER_R)
        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), _PLAYER_R, 1)
