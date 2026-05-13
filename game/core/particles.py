"""
core/particles.py
Lightweight visual types shared between Engine (draw) and CombatResolver (spawn).
Extracted here to break the circular import that would occur if CombatResolver
imported _Particle/_DamageNumber directly from engine.py.
Does NOT own: game state, update logic (caller iterates the lists held by Engine).
"""

import pygame


class Particle:
    """World-space visual particle — fades and shrinks over its lifetime."""
    __slots__ = ('pos', 'vel', 'color', 'life', 'max_life', 'radius', 'gravity')

    def __init__(self, x, y, vx, vy, color, life, radius, gravity=400.0):
        self.pos      = pygame.math.Vector2(x, y)
        self.vel      = pygame.math.Vector2(vx, vy)
        self.color    = color
        self.life     = life
        self.max_life = life
        self.radius   = radius
        self.gravity  = gravity


class DamageNumber:
    """Floating damage/XP number — drifts upward for 0.75 s then expires."""
    __slots__ = ('x', 'y', 'surf', 'life', 'max_life')

    def __init__(self, x, y, surf):
        self.x        = float(x)
        self.y        = float(y)
        self.surf     = surf
        self.life     = 0.75
        self.max_life = 0.75
