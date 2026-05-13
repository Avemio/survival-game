"""
entities/npc.py
A non-player character — stands in the world, shows a prompt when the player
is close, and starts a dialogue when the player presses E.
Owns: rect, name, color, dialogue lines, interaction-prompt drawing.
Does NOT own: dialogue rendering (ui/dialogue.py), triggering logic (engine).
"""

import pygame
from game.entities.entity   import Entity
from game.systems.assets    import get as _assets

# Module-level font shared by all NPC instances — created once, not per instance
_prompt_font: pygame.font.Font | None = None


def _get_prompt_font() -> pygame.font.Font:
    global _prompt_font
    if _prompt_font is None:
        _prompt_font = pygame.font.SysFont(None, 18)
    return _prompt_font


class NPC(Entity):
    def __init__(self, x, y, npc_def, dialogue_lines, shop_id=None, gives_quest=None):
        """
        x, y           — top-left world position
        npc_def        — dict from npcs.json (name, color, width, height)
        dialogue_lines — ordered list of strings from dialogue.json
        shop_id        — optional shop ID; if set, E opens the shop instead of dialogue
        """
        w = npc_def.get("width",  28)
        h = npc_def.get("height", 52)

        self.rect           = pygame.Rect(x, y, w, h)
        self.name           = npc_def.get("name",  "???")
        self.color          = tuple(npc_def.get("color", [200, 190, 140]))
        self.dialogue_lines = dialogue_lines   # list[str]
        self.shop_id        = shop_id
        self.gives_quest    = gives_quest      # optional quest_id to hand out on interact

        # Sprite — scaled once at init; None = fall back to colored rect
        sprite_name  = npc_def.get("sprite", f"npc_{self.name.lower()}")
        self._sprite = _assets().get_sprite_scaled(sprite_name, w, h)

        # Prompt text and color depend on NPC role
        if shop_id:
            prompt_text  = "[E] Shop"
            prompt_color = (255, 215, 50)   # gold for shopkeepers
        elif dialogue_lines:
            prompt_text  = "[E] Talk"
            prompt_color = (255, 255, 255)
        else:
            prompt_text  = ""
            prompt_color = (255, 255, 255)

        # Pre-built prompt surfaces — use module-level shared font (not per-instance)
        font = _get_prompt_font()
        self._prompt_shadow = font.render(prompt_text, True, (0, 0, 0))
        self._prompt_surf   = font.render(prompt_text, True, prompt_color) \
                              if prompt_text else None

        # Interaction trigger rect: 40 px wider on each side.
        self.interact_rect  = self.rect.inflate(80, 0)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, camera, player_rect):
        """
        player_rect — used only to decide whether to show the prompt;
                      the NPC doesn't move so no other player state is needed.
        """
        # Body
        r = camera.apply_tuple(self.rect)
        if self._sprite:
            screen.blit(self._sprite, (r[0], r[1]))
        else:
            pygame.draw.rect(screen, self.color, r)

        # Overhead prompt when player is within interact range
        if self._prompt_surf and self.interact_rect.colliderect(player_rect):
            # Derive screen-space center/top from the already-computed tuple (no second Rect alloc)
            sw = self._prompt_surf.get_width()
            px = r[0] + r[2] // 2 - sw // 2
            py = r[1] - self._prompt_surf.get_height() - 5
            screen.blit(self._prompt_shadow, (px + 1, py + 1))
            screen.blit(self._prompt_surf,   (px,     py))
