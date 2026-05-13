"""
world/scene.py
Base class for game scenes (zones, interiors, future title/cutscene scenes).
Defines the lifecycle hooks: on_enter, on_exit.
Does NOT own: rendering, player state, or transition logic — those stay in engine/world.
"""


class Scene:
    """Minimal base for any distinct game area or mode."""

    zone_id: str = ""

    def on_enter(self) -> None:
        """Called when the player enters this scene. Override to play music, spawn entities, etc."""
        pass

    def on_exit(self) -> None:
        """Called just before leaving this scene. Override to save state, stop music, etc."""
        pass
