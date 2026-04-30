"""
entities/item_drop.py
A world item — sits on the ground until the player walks over it.
Owns: rect, item_id, quantity, color, alive flag.
Does NOT own: inventory logic (engine calls inventory.add on pickup),
              item definitions (color is passed in at construction).
"""

import pygame


class ItemDrop:
    SIZE = 20   # square side length in pixels

    def __init__(self, x, y, item_id, quantity, color):
        """
        x, y     — top-left world position
        item_id  — key into items.json (e.g. "wood")
        quantity — how many of this item the drop contains
        color    — RGB tuple looked up from item_defs by the creator
        """
        self.rect             = pygame.Rect(x, y, self.SIZE, self.SIZE)
        self.item_id          = item_id
        self.quantity         = quantity
        self.color            = color
        self.alive            = True
        self.zone_drop_index  = None   # set to an int for zone-defined drops,
                                       # None for enemy drops (don't persist)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen, camera):
        r = camera.apply_tuple(self.rect)
        pygame.draw.rect(screen, self.color,      r)
        pygame.draw.rect(screen, (255, 255, 255), r, 1)
