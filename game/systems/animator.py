"""
systems/animator.py
Frame-based sprite animator with per-frame foot alignment.
Owns: frame sequencing, state switching, per-frame foot-y detection for ground alignment.
Does NOT own: asset loading, player state logic, drawing.
"""

import pygame


def _find_foot_y(surf: pygame.Surface) -> int:
    """Return the y-coordinate of the lowest row containing any visible pixel."""
    return surf.get_bounding_rect(min_alpha=8).bottom - 1


class Animator:
    def __init__(self, animations: dict[str, list[pygame.Surface]],
                 fps: float = 10.0,
                 state_fps: dict[str, float] | None = None):
        self._anims     = animations
        self._fps       = fps
        self._state_fps = state_fps or {}
        self._state      = next(iter(animations)) if animations else ""
        self._frame_idx  = 0
        self._frame_time = 0.0
        self._play_once  = False   # True while a one-shot animation is running
        self._done       = False   # True after a one-shot animation reaches its last frame
        # Lowest visible pixel row per frame — used to pin feet to the ground
        self._foot_ys = {
            state: [_find_foot_y(s) for s in frames]
            for state, frames in animations.items()
        }

    def _cur_fps(self) -> float:
        return self._state_fps.get(self._state, self._fps)

    def set_state(self, state: str) -> None:
        """Switch to state and loop it. Clears any active play_once."""
        if state in self._anims and state != self._state:
            self._state      = state
            self._frame_idx  = 0
            self._frame_time = 0.0
            self._play_once  = False
            self._done       = False

    def play_once(self, state: str) -> None:
        """Play state from frame 0, hold on the last frame when done. Does not loop."""
        if state not in self._anims:
            return
        self._state      = state
        self._frame_idx  = 0
        self._frame_time = 0.0
        self._play_once  = True
        self._done       = False

    @property
    def finished(self) -> bool:
        """True after a play_once animation has played through all its frames."""
        return self._done

    def update(self, dt: float) -> None:
        frames = self._anims.get(self._state)
        if not frames:
            return
        if len(frames) == 1:
            self._done = True   # single-frame play_once finishes immediately
            return
        if self._done:
            return
        self._frame_time += dt
        dur = 1.0 / self._cur_fps()
        while self._frame_time >= dur:
            self._frame_time -= dur
            next_idx = self._frame_idx + 1
            if self._play_once and next_idx >= len(frames):
                self._frame_idx = len(frames) - 1  # hold on last frame
                self._done      = True
                return
            self._frame_idx = next_idx % len(frames)

    @property
    def surface(self) -> pygame.Surface | None:
        frames = self._anims.get(self._state)
        if not frames:
            return None
        return frames[self._frame_idx % len(frames)]

    @property
    def foot_y(self) -> int:
        """Y-pixel of the lowest visible pixel in the current frame, or -1 if unknown."""
        ys = self._foot_ys.get(self._state, [])
        if not ys:
            return -1
        return ys[self._frame_idx % len(ys)]
