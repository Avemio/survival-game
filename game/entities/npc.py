"""
entities/npc.py
A non-player character — stands in the world, shows a prompt when the player
is close, and starts a dialogue when the player presses E.
Owns: rect, name, color, dialogue lines, interaction-prompt drawing.
Does NOT own: dialogue rendering (ui/dialogue.py), triggering logic (engine).
"""

import pygame


class NPC:
    def __init__(self, x, y, npc_def, dialogue_lines):
        """
        x, y           — top-left world position
        npc_def        — dict from npcs.json (name, color, width, height)
        dialogue_lines — ordered list of strings from dialogue.json
        """
        w = npc_def.get("width",  28)
        h = npc_def.get("height", 52)

        self.rect           = pygame.Rect(x, y, w, h)
        self.name           = npc_def.get("name",  "???")
        self.color          = tuple(npc_def.get("color", [200, 190, 140]))
        self.dialogue_lines = dialogue_lines   # list[str]

        # Font for the "[E] Talk" overhead prompt — created once
        self._prompt_font = pygame.font.SysFont(None, 18)

        # Rect expanded horizontally for proximity checks so the player
        # doesn't have to pixel-perfectly overlap to see the prompt / trigger
        self._interact_rect = self.rect.inflate(80, 0)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, camera, player_rect):
        """
        player_rect — used only to decide whether to show the prompt;
                      the NPC doesn't move so no other player state is needed.
        """
        # Body
        pygame.draw.rect(screen, self.color, camera.apply(self.rect))

        # Overhead "[E] Talk" prompt when the player is within interact range
        if self._interact_rect.colliderect(player_rect) and self.dialogue_lines:
            r   = camera.apply(self.rect)
            txt = "[E] Talk"

            # Shadow first (1 px offset, black) for contrast against any background
            shadow_surf = self._prompt_font.render(txt, True, (0, 0, 0))
            main_surf   = self._prompt_font.render(txt, True, (255, 255, 255))

            px = r.centerx - main_surf.get_width() // 2
            py = r.top - main_surf.get_height() - 5

            screen.blit(shadow_surf, (px + 1, py + 1))
            screen.blit(main_surf,   (px,     py))
