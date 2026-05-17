"""
UI system: HUD, minimap, legend, and speed controls.
"""

import pygame
from typing import Dict, Tuple

from colors import (
    UI_BG, UI_TEXT, UI_ACCENT, UI_PANEL, UI_BORDER,
    HUMAN, MONSTER, ANIMAL, TREE, ROCK, WALL, DOOR,
    TORCH, SPAWNER, GRASS,
)
from entities import EntityManager, EntityType
from world import WorldState
from sprites import SpriteRenderer, draw_ui_panel, draw_progress_bar


LEGEND_ITEMS = [
    (HUMAN,    "Human"),
    (MONSTER,  "Monster"),
    (ANIMAL,   "Animal"),
    (TREE,     "Tree"),
    (ROCK,     "Rock"),
    (WALL,     "Wall"),
    (DOOR,     "Door"),
    (TORCH,    "Torch"),
    (SPAWNER,  "Spawner"),
]


class UI:
    def __init__(self, screen: pygame.Surface, em: EntityManager, world: WorldState,
                 pixel_size: int = 8):
        self.screen = screen
        self.em = em
        self.world = world
        self.pixel_size = pixel_size
        w, h = screen.get_size()
        self.w = w
        self.h = h
        self.font_small = pygame.font.Font(None, 16)
        self.font_medium = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 28)

        # Minimap settings
        self.minimap_w = 140
        self.minimap_h = 140
        self.minimap_x = w - self.minimap_w - 10
        self.minimap_y = 10

    def render(self, camera, combat, fps: int, speed: float) -> None:
        self._render_top_bar()
        self._render_side_stats()
        if camera.show_minimap:
            self._render_minimap(camera)
        self._render_legend()
        self._render_controls()
        self._render_night_overlay(camera)

    def _render_top_bar(self) -> None:
        # Top bar background
        pygame.draw.rect(self.screen, UI_BG, (0, 0, self.w, 36))
        pygame.draw.line(self.screen, UI_BORDER, (0, 36), (self.w, 36))

        # Day / Night indicator
        phase = self.world.get_phase_name()
        phase_color = (50, 50, 100) if self.world.is_night else (200, 150, 50)
        time_str = self.world.get_time_display()
        day_str = f"Day {self.world.day_number}"

        x = 10
        texts = [
            (f"{phase}", phase_color),
            (f"{time_str}", UI_TEXT),
            (f"{day_str}", UI_TEXT),
        ]
        for text, color in texts:
            surf = self.font_medium.render(text, True, color)
            self.screen.blit(surf, (x, 8))
            x += surf.get_width() + 20

        # Speed indicator
        speed_text = f"Speed: {speed:.0f}x"
        surf = self.font_medium.render(speed_text, True, UI_ACCENT)
        self.screen.blit(surf, (x, 8))
        x += surf.get_width() + 20

        # FPS
        fps_text = f"FPS: {fps}"
        surf = self.font_medium.render(fps_text, True, (150, 150, 150))
        self.screen.blit(surf, (x, 8))

    def _render_side_stats(self) -> None:
        counts = self.em.count_alive()

        humans = counts.get(EntityType.HUMAN, 0)
        monsters = counts.get(EntityType.MONSTER, 0)
        animals = counts.get(EntityType.ANIMAL, 0)
        trees = counts.get(EntityType.TREE, 0)
        walls_h = len([e for e in self.em.entities.values() if e.is_alive() and e.entity_type == EntityType.WALL and e.team == "human"])
        walls_m = len([e for e in self.em.entities.values() if e.is_alive() and e.entity_type == EntityType.WALL and e.team == "monster"])

        # Right side panel
        panel_x = self.w - 170
        panel_y = self.minimap_y + self.minimap_h + 10
        panel_w = 160
        panel_h = 200
        draw_ui_panel(self.screen, panel_x, panel_y, panel_w, panel_h)

        y = panel_y + 8
        title = self.font_medium.render("Faction Status", True, UI_ACCENT)
        self.screen.blit(title, (panel_x + 8, y))
        y += 24

        def stat_line(color, label, value):
            pygame.draw.rect(self.screen, color, (panel_x + 8, y + 2, 10, 10))
            lbl = self.font_small.render(label, True, UI_TEXT)
            self.screen.blit(lbl, (panel_x + 24, y))
            val = self.font_small.render(f"{value}", True, UI_ACCENT)
            self.screen.blit(val, (panel_x + panel_w - 30, y))
            return y + 18

        y = stat_line(HUMAN, "Humans", humans)
        y = stat_line(MONSTER, "Monsters", monsters)
        y = stat_line(ANIMAL, "Animals", animals)
        y = stat_line(TREE, "Trees", trees)
        y = stat_line(WALL, "Human Walls", walls_h)
        y = stat_line(WALL, "Monster Walls", walls_m)

        y += 8
        self.screen.blit(self.font_small.render("Human kills:", True, (180, 180, 180)), (panel_x + 8, y))
        self.screen.blit(self.font_small.render(str(combat.humans_killed), True, MONSTER), (panel_x + panel_w - 20, y))
        y += 16
        self.screen.blit(self.font_small.render("Monster kills:", True, (180, 180, 180)), (panel_x + 8, y))
        self.screen.blit(self.font_small.render(str(combat.monsters_killed), True, HUMAN), (panel_x + panel_w - 20, y))

    def _render_minimap(self, camera) -> None:
        x = self.minimap_x
        y = self.minimap_y
        w = self.minimap_w
        h = self.minimap_h

        # Background
        pygame.draw.rect(self.screen, (5, 5, 10), (x, y, w, h))
        pygame.draw.rect(self.screen, UI_BORDER, (x, y, w, h), 1)

        scale_x = w / 100.0
        scale_y = h / 100.0

        # Draw terrain (simplified)
        for (tx, ty), terrain in self.world.terrain.items():
            mx = int(tx * scale_x)
            my = int(ty * scale_y)
            if terrain == "water":
                c = (30, 90, 200)
            elif terrain == "grass":
                c = (20, 50, 20)
            else:
                c = (30, 30, 30)
            pygame.draw.rect(self.screen, c, (x + mx, y + my, max(1, int(scale_x)), max(1, int(scale_y))))

        # Draw entities as dots
        for entity in self.em.entities.values():
            if not entity.is_alive():
                continue
            mx = int(entity.x * scale_x)
            my = int(entity.y * scale_y)
            if entity.entity_type == EntityType.HUMAN:
                c = HUMAN
            elif entity.entity_type == EntityType.MONSTER:
                c = MONSTER
            elif entity.entity_type == EntityType.SPAWNER:
                c = SPAWNER
            elif entity.entity_type == EntityType.WALL:
                c = WALL if entity.team == "human" else (150, 30, 30)
            else:
                continue
            pygame.draw.rect(self.screen, c, (x + mx, y + my, 2, 2))

        # Camera viewport rectangle
        view_w = int((camera.screen_w / camera.zoom) * scale_x / 100 * 100)
        view_h = int((camera.screen_h / camera.zoom) * scale_y / 100 * 100)
        cam_mx = int(camera.x * scale_x)
        cam_my = int(camera.y * scale_y)
        pygame.draw.rect(self.screen, (255, 255, 255),
                        (x + cam_mx - view_w // 2, y + cam_my - view_h // 2, view_w, view_h), 1)

        # Label
        lbl = self.font_small.render("MAP", True, (150, 150, 150))
        self.screen.blit(lbl, (x + 4, y + 4))

    def _render_legend(self) -> None:
        # Bottom left legend
        legend_h = 22
        legend_y = self.h - legend_h - 8
        total_w = len(LEGEND_ITEMS) * 85 + 20

        x = 10
        pygame.draw.rect(self.screen, UI_BG, (x - 4, legend_y - 4, total_w, legend_h + 8))
        pygame.draw.rect(self.screen, UI_BORDER, (x - 4, legend_y - 4, total_w, legend_h + 8), 1)

        for color, name in LEGEND_ITEMS:
            pygame.draw.rect(self.screen, color, (x, legend_y, 12, 12))
            lbl = self.font_small.render(name, True, UI_TEXT)
            self.screen.blit(lbl, (x + 16, legend_y + 1))
            x += 80

    def _render_controls(self) -> None:
        y = self.h - 22 - 8 - 26
        controls = "WASD/Arrows: Pan  |  Scroll: Zoom  |  1/2/3: Speed  |  M: Map  |  G: Grid  |  Space: Pause  |  Q: Quit"
        surf = self.font_small.render(controls, True, (120, 120, 140))
        self.screen.blit(surf, (10, y))

    def _render_night_overlay(self, camera) -> None:
        alpha = self.world.get_night_overlay_alpha()
        if alpha > 0:
            night_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            night_surf.fill((10, 10, 40, alpha))
            self.screen.blit(night_surf, (0, 0))

            # Torch light effect
            torches = [e for e in self.em.entities.values()
                      if e.is_alive() and e.entity_type == EntityType.TORCH]
            for torch in torches:
                sx, sy = camera.world_to_screen(torch.x, torch.y)
                radius = int(40 * camera.zoom)
                torch_surf = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
                for r in range(radius, 0, -3):
                    a = int(80 * (1 - r / radius))
                    pygame.draw.circle(torch_surf, (255, 140, 0, a), (radius, radius), r)
                self.screen.blit(torch_surf, (sx - radius, sy - radius), special_flags=pygame.BLEND_RGBA_ADD)
