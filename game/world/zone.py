"""
world/zone.py
A single playable area — loads from a JSON file, builds platforms, enemies,
save points, and world item drops.
Owns: platforms, enemies, save_points, item_drops, spawn point, zone id.
Does NOT own: zone transitions (World handles that), AI, or combat.
"""

import json
import pygame
from pathlib import Path
from game.entities.enemy     import Enemy
from game.entities.item_drop import ItemDrop
from game.entities.npc       import NPC
from game.settings import SAVE_POINT_COLOR, SAVE_POINT_ACTIVE_COLOR, EXIT_COLOR, EXIT_BORDER_COLOR, BG_COLOR


class SavePoint:
    FLASH_DURATION = 1.0

    def __init__(self, x, y, w, h):
        self.rect            = pygame.Rect(x, y, w, h)
        self.was_overlapping = False
        self.flash_timer     = 0.0

    def update(self, dt):
        if self.flash_timer > 0:
            self.flash_timer -= dt

    def draw(self, screen, camera):
        color = SAVE_POINT_ACTIVE_COLOR if self.flash_timer > 0 else SAVE_POINT_COLOR
        pygame.draw.rect(screen, color, camera.apply_tuple(self.rect))


class ZoneExit:
    """A trigger rect that transports the player to another zone when touched."""

    def __init__(self, x, y, w, h, target_zone, spawn_override=None):
        self.rect            = pygame.Rect(x, y, w, h)
        self.target_zone     = target_zone
        self.spawn_override  = tuple(spawn_override) if spawn_override else None
        self.was_overlapping = False   # rising-edge guard prevents repeat triggers

    def draw(self, screen, camera):
        r = camera.apply_tuple(self.rect)
        pygame.draw.rect(screen, EXIT_COLOR,        r)
        pygame.draw.rect(screen, EXIT_BORDER_COLOR, r, 2)


class Building:
    """
    An interactable building placed in a zone.
    Press E near the door to enter the interior zone.
    Does NOT own: transition logic (engine._enter_building handles that).
    """

    _BODY_COLOR   = (100, 80,  60)
    _BODY_BORDER  = ( 70, 55,  40)
    _DOOR_COLOR   = ( 55, 35,  18)
    _DOOR_BORDER  = ( 90, 65,  30)

    def __init__(self, x, y, w, h, door_x, door_y, door_w, door_h, target_zone, label=""):
        self.rect          = pygame.Rect(x, y, w, h)
        self.door_rect     = pygame.Rect(door_x, door_y, door_w, door_h)
        self.target_zone   = target_zone
        self.label         = label

        # Wider trigger rect for comfortable E-key detection
        self.interact_rect = pygame.Rect(door_x - 30, door_y, door_w + 60, door_h)

        # Prompt surfaces — created once at init, never in draw()
        self._prompt_font   = pygame.font.SysFont(None, 18)
        self._prompt_shadow = self._prompt_font.render("[E] Enter", True, (0, 0, 0))
        self._prompt_surf   = self._prompt_font.render("[E] Enter", True, (255, 255, 255))

    def draw(self, screen, camera, player_rect):
        # Building body
        r = camera.apply_tuple(self.rect)
        pygame.draw.rect(screen, self._BODY_COLOR,  r)
        pygame.draw.rect(screen, self._BODY_BORDER, r, 2)

        # Door
        dr = camera.apply_tuple(self.door_rect)
        pygame.draw.rect(screen, self._DOOR_COLOR,  dr)
        pygame.draw.rect(screen, self._DOOR_BORDER, dr, 1)

        # Overhead prompt when player is near the door
        if self.interact_rect.colliderect(player_rect):
            pr = camera.apply(self.door_rect)
            px = pr.centerx - self._prompt_surf.get_width()  // 2
            py = pr.top     - self._prompt_surf.get_height() - 5
            screen.blit(self._prompt_shadow, (px + 1, py + 1))
            screen.blit(self._prompt_surf,   (px,     py))


class Zone:
    def __init__(self, path, enemy_types, item_defs, npc_types, dialogue_data):
        """
        path          — pathlib.Path to the zone's JSON file
        enemy_types   — dict from data/enemies.json
        item_defs     — dict from data/items.json (used for item drop colors)
        npc_types     — dict from data/npcs.json
        dialogue_data — dict from data/dialogue.json
        """
        self.id          = "unknown"
        self.platforms   = []
        self.enemies     = []
        self.save_points = []
        self.item_drops  = []
        self.npcs        = []
        self.exits       = []
        self.buildings   = []
        self.spawn       = (0, 0)
        self.bg_color    = BG_COLOR
        self.music       = None

        self._load(Path(path), enemy_types, item_defs, npc_types, dialogue_data)

    def _load(self, path, enemy_types, item_defs, npc_types, dialogue_data):
        with open(path) as f:
            data = json.load(f)

        self.id       = data.get("id", path.stem)
        self.spawn    = tuple(data.get("spawn") or [200, 580])
        self.music    = data.get("music")
        raw_bg        = data.get("bg_color")
        self.bg_color = tuple(raw_bg) if raw_bg else BG_COLOR

        for p in data.get("platforms", []):
            self.platforms.append(
                pygame.Rect(p["x"], p["y"], p["w"], p["h"])
            )

        for e in data.get("enemies", []):
            stats = enemy_types.get(e["type"], {})
            self.enemies.append(Enemy(e["x"], e["y"], stats))

        for sp in data.get("save_points", []):
            self.save_points.append(
                SavePoint(sp["x"], sp["y"], sp["w"], sp["h"])
            )

        for i, d in enumerate(data.get("item_drops", [])):
            color = tuple(item_defs.get(d["item_id"], {}).get("color", [200, 200, 200]))
            drop  = ItemDrop(d["x"], d["y"], d["item_id"], d["quantity"], color)
            drop.zone_drop_index = i   # marks this as a persistent zone drop
            self.item_drops.append(drop)

        for n in data.get("npcs", []):
            npc_def = npc_types.get(n["type"], {})
            lines   = dialogue_data.get(n["dialogue_id"], [])
            self.npcs.append(NPC(n["x"], n["y"], npc_def, lines))

        for ex in data.get("exits", []):
            self.exits.append(ZoneExit(
                ex["x"], ex["y"], ex["w"], ex["h"], ex["target_zone"],
                spawn_override=ex.get("spawn_override"),
            ))

        for b in data.get("buildings", []):
            bx, by, bw, bh = b["x"], b["y"], b["w"], b["h"]
            # Door defaults: centered horizontally at the building base
            door_w = b.get("door_w", 40)
            door_h = b.get("door_h", 64)
            door_x = b.get("door_x", bx + (bw - door_w) // 2)
            door_y = b.get("door_y", by + bh - door_h)
            self.buildings.append(Building(
                bx, by, bw, bh,
                door_x, door_y, door_w, door_h,
                b["target_zone"],
                b.get("label", ""),
            ))
