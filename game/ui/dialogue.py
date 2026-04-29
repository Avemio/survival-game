"""
ui/dialogue.py
Full-screen dialogue box drawn at the bottom of the screen.
Owns: layout geometry, fonts, word-wrap, speaker name rendering, advance logic.
Does NOT own: dialogue data (entities/npc.py holds lines), trigger logic (engine).

Controls while open:
  E / Space — advance to next line; closes after the last one
"""

import pygame
from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    HOTBAR_SLOT_SIZE, HOTBAR_Y_OFFSET,
    DIALOGUE_PANEL_BG, DIALOGUE_PANEL_BORDER,
    DIALOGUE_NAME_COLOR, DIALOGUE_TEXT_COLOR,
    DIALOGUE_HINT_COLOR,
    WHITE,
)

# Layout
_PANEL_MARGIN  = 40    # horizontal gap between panel and screen edge
_PANEL_H       = 148   # fixed panel height
_PAD_X         = 18    # inner horizontal padding
_PAD_Y         = 12    # inner vertical padding
_NAME_H        = 26    # pixels reserved for the speaker name row
_NAME_GAP      = 6     # gap between name and body text


class DialogueBox:
    def __init__(self):
        self._open        = False
        self._speaker     = ""
        self._raw_lines   = []     # full list of dialogue lines
        self._current     = 0      # index into _raw_lines
        self._wrapped     = []     # word-wrapped version of current line

        # Fonts — created once
        self._font_name = pygame.font.SysFont(None, 22)
        self._font_text = pygame.font.SysFont(None, 20)
        self._font_hint = pygame.font.SysFont(None, 17)

        # Panel geometry — computed once, never changes
        hotbar_top      = SCREEN_HEIGHT - HOTBAR_SLOT_SIZE - HOTBAR_Y_OFFSET
        self._panel_x   = _PANEL_MARGIN
        self._panel_y   = hotbar_top - _PANEL_H - 8
        self._panel_w   = SCREEN_WIDTH - _PANEL_MARGIN * 2
        self._panel_h   = _PANEL_H

        # Width available for body text after internal padding
        self._text_w    = self._panel_w - _PAD_X * 2

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def open(self):
        return self._open

    def start(self, speaker, lines):
        """Begin a conversation. `lines` is a list of strings."""
        if not lines:
            return
        self._speaker   = speaker
        self._raw_lines = lines
        self._current   = 0
        self._open      = True
        self._rebuild_wrap()

    def advance(self):
        """Move to the next line; closes the box after the last one."""
        self._current += 1
        if self._current >= len(self._raw_lines):
            self._open = False
        else:
            self._rebuild_wrap()

    # ------------------------------------------------------------------
    # Draw (called by engine each frame; no-ops when closed)
    # ------------------------------------------------------------------

    def draw(self, screen):
        if not self._open:
            return

        x, y, w, h = self._panel_x, self._panel_y, self._panel_w, self._panel_h

        # Background + border
        pygame.draw.rect(screen, DIALOGUE_PANEL_BG,     (x, y, w, h), border_radius=6)
        pygame.draw.rect(screen, DIALOGUE_PANEL_BORDER, (x, y, w, h), 2, border_radius=6)

        # Speaker name
        name_surf = self._font_name.render(self._speaker, True, DIALOGUE_NAME_COLOR)
        screen.blit(name_surf, (x + _PAD_X, y + _PAD_Y))

        # Divider under name
        div_y = y + _PAD_Y + _NAME_H
        pygame.draw.line(screen, DIALOGUE_PANEL_BORDER,
                         (x + _PAD_X, div_y),
                         (x + w - _PAD_X, div_y))

        # Body text — pre-wrapped lines
        text_y = div_y + _NAME_GAP
        for line in self._wrapped:
            surf = self._font_text.render(line, True, DIALOGUE_TEXT_COLOR)
            screen.blit(surf, (x + _PAD_X, text_y))
            text_y += surf.get_height() + 3

        # Hint — "▼ E" in the bottom-right
        line_num   = self._current + 1
        total      = len(self._raw_lines)
        label      = "[ E ] Close" if line_num == total else "[ E ] Continue"
        hint_surf  = self._font_hint.render(label, True, DIALOGUE_HINT_COLOR)
        screen.blit(hint_surf, (
            x + w - hint_surf.get_width()  - _PAD_X,
            y + h - hint_surf.get_height() - _PAD_Y
        ))

        # Line counter — bottom-left
        counter_surf = self._font_hint.render(f"{line_num} / {total}", True, DIALOGUE_HINT_COLOR)
        screen.blit(counter_surf, (x + _PAD_X, y + h - counter_surf.get_height() - _PAD_Y))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rebuild_wrap(self):
        """Word-wrap the current raw line to fit inside the text column."""
        text = self._raw_lines[self._current]
        self._wrapped = self._wrap_text(text, self._font_text, self._text_w)

    @staticmethod
    def _wrap_text(text, font, max_width):
        """Split `text` into lines that each fit within `max_width` pixels."""
        words        = text.split()
        lines        = []
        current_words = []

        for word in words:
            test = ' '.join(current_words + [word])
            if font.size(test)[0] <= max_width:
                current_words.append(word)
            else:
                if current_words:
                    lines.append(' '.join(current_words))
                current_words = [word]

        if current_words:
            lines.append(' '.join(current_words))

        return lines
