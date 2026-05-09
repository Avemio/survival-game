"""
systems/assets.py
Central asset manager — loads sprites and sounds from the assets/ folder at startup.
All methods fail silently when files are missing so the game always runs,
even with no assets installed.

Naming conventions:
  Sprites  → assets/sprites/{name}.png   (e.g. player.png, enemy_basic.png)
  Sounds   → assets/sounds/{name}.wav or .ogg
  Music    → assets/sounds/{zone_id}.ogg  (referenced from zone JSON "music" field)

Access via the module-level singleton:
    from game.systems.assets import get as _assets
    _assets().play("enemy_hit")
    surf = _assets().get_sprite("player")
"""

import pygame
from pathlib import Path
from game.settings import VOLUME, MUSIC_VOLUME

_ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"
_SPRITE_EXTS = (".png", ".jpg", ".jpeg")
_SOUND_EXTS  = (".wav", ".ogg", ".mp3")


class AssetManager:
    def __init__(self):
        self._sprites: dict[str, pygame.Surface] = {}
        self._sounds:  dict[str, pygame.mixer.Sound] = {}
        self._current_music: str | None = None

        self._load_sprites()
        self._load_sounds()
        self._apply_volume()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_sprites(self):
        # convert_alpha() requires an active display surface
        if not pygame.display.get_surface():
            return
        folder = _ASSETS_DIR / "sprites"
        if not folder.exists():
            return
        for ext in _SPRITE_EXTS:
            for path in folder.glob(f"*{ext}"):
                try:
                    surf = pygame.image.load(str(path))
                    self._sprites[path.stem] = (
                        surf.convert_alpha() if surf.get_flags() & pygame.SRCALPHA
                        else surf.convert()
                    )
                except Exception:
                    pass

    def _load_sounds(self):
        if not pygame.mixer.get_init():
            return
        folder = _ASSETS_DIR / "sounds"
        if not folder.exists():
            return
        for ext in _SOUND_EXTS:
            for path in folder.glob(f"*{ext}"):
                # Skip music tracks (long files played via pygame.mixer.music)
                try:
                    self._sounds[path.stem] = pygame.mixer.Sound(str(path))
                except Exception:
                    pass

    def _apply_volume(self):
        for snd in self._sounds.values():
            snd.set_volume(VOLUME)

    # ------------------------------------------------------------------
    # Sprites
    # ------------------------------------------------------------------

    def get_sprite(self, name: str) -> pygame.Surface | None:
        """Return the loaded Surface for `name`, or None if not found."""
        return self._sprites.get(name)

    def get_sprite_scaled(self, name: str, w: int, h: int) -> pygame.Surface | None:
        """Return the sprite scaled to (w, h), or None if not found."""
        raw = self._sprites.get(name)
        if raw is None:
            return None
        return pygame.transform.scale(raw, (w, h))

    # ------------------------------------------------------------------
    # Sound effects
    # ------------------------------------------------------------------

    def play(self, name: str):
        """Play a sound effect by name. Does nothing if the file wasn't loaded."""
        snd = self._sounds.get(name)
        if snd:
            snd.play()

    def set_sfx_volume(self, volume: float):
        for snd in self._sounds.values():
            snd.set_volume(max(0.0, min(1.0, volume)))

    # ------------------------------------------------------------------
    # Music
    # ------------------------------------------------------------------

    def play_music(self, track_name: str):
        """Start a looping background track. Does nothing if file not found."""
        if not pygame.mixer.get_init() or track_name == self._current_music:
            return
        folder = _ASSETS_DIR / "sounds"
        for ext in _SOUND_EXTS:
            path = folder / (track_name + ext)
            if path.exists():
                try:
                    pygame.mixer.music.load(str(path))
                    pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    pygame.mixer.music.play(-1)
                    self._current_music = track_name
                except Exception:
                    pass
                return

    def stop_music(self):
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self._current_music = None


# ------------------------------------------------------------------
# Module-level singleton — import and call from anywhere
# ------------------------------------------------------------------

_instance: AssetManager | None = None


def get() -> AssetManager:
    """Return the shared AssetManager. Creates it on first call."""
    global _instance
    if _instance is None:
        _instance = AssetManager()
    return _instance
