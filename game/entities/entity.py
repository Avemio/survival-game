"""
entities/entity.py
Base class for all game entities.
Defines the minimum shared interface: alive flag and draw().
Does NOT enforce update() signature — callers vary by entity type
(Player takes platforms, Enemy takes player+platforms, etc.).
"""


class Entity:
    """Minimal base for every drawable, living game object."""
    alive = True  # class-level default; subclasses shadow with self.alive = <bool>

    def draw(self, screen, camera) -> None:
        """Override in subclasses. Called each frame in screen space via camera."""
        pass
