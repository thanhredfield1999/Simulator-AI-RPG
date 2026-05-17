"""
Drawing utilities and sprite rendering.
"""

import pygame
import math
from typing import Tuple, List

from colors import UI_BG, UI_TEXT, UI_ACCENT, UI_PANEL, UI_BORDER


class SpriteRenderer:
    def __init__(self, screen: pygame.Surface, pixel_size: int = 8):
        self.screen = screen
        self.pixel_size = pixel_size

    def draw_pixel(self, sx: int, sy: int, color: Tuple[int, int, int],
                   size: int = 0) -> None:
        if size <= 0:
            size = self.pixel_size
        pygame.draw.rect(self.screen, color,
                         (sx, sy, size, size))

    def draw_entity(self, sx: int, sy: int, color: Tuple[int, int, int],
                    damage_flash: bool = False, selected: bool = False) -> None:
        s = self.pixel_size
        if damage_flash:
            flash_color = (255, 255, 255)
            pygame.draw.rect(self.screen, flash_color, (sx, sy, s, s))
        else:
            pygame.draw.rect(self.screen, color, (sx, sy, s, s))

        if selected:
            pygame.draw.rect(self.screen, (255, 255, 255),
                             (sx, sy, s, s), 1)

    def draw_terrain_pixel(self, sx: int, sy: int, color: Tuple[int, int, int],
                           brightness: float = 1.0) -> None:
        r = int(color[0] * brightness)
        g = int(color[1] * brightness)
        b = int(color[2] * brightness)
        pygame.draw.rect(self.screen, (r, g, b),
                         (sx, sy, self.pixel_size, self.pixel_size))

    def draw_grid_line(self, sx1: int, sy1: int, sx2: int, sy2: int) -> None:
        pygame.draw.line(self.screen, (40, 40, 50), (sx1, sy1), (sx2, sy2))

    def draw_circle(self, cx: int, cy: int, radius: int, color: Tuple[int, int, int],
                    width: int = 1) -> None:
        pygame.draw.circle(self.screen, color, (cx, cy), radius, width)

    def draw_text(self, text: str, sx: int, sy: int,
                  font: pygame.font.Font, color: Tuple[int, int, int] = UI_TEXT,
                  bg: Tuple[int, int, int] = None) -> None:
        surf = font.render(text, True, color)
        if bg:
            surf.set_alpha(180)
        self.screen.blit(surf, (sx, sy))


def draw_ui_panel(surface: pygame.Surface, x: int, y: int,
                   w: int, h: int, border_color: Tuple[int, int, int] = UI_BORDER,
                   bg_color: Tuple[int, int, int] = UI_PANEL) -> None:
    pygame.draw.rect(surface, bg_color, (x, y, w, h))
    pygame.draw.rect(surface, border_color, (x, y, w, h), 1)


def draw_progress_bar(surface: pygame.Surface, x: int, y: int,
                       w: int, h: int, fill: float,
                       bg_color: Tuple[int, int, int] = (30, 30, 40),
                       fill_color: Tuple[int, int, int] = (100, 200, 100)) -> None:
    pygame.draw.rect(surface, bg_color, (x, y, w, h))
    fw = int(w * min(1.0, max(0.0, fill)))
    if fw > 0:
        pygame.draw.rect(surface, fill_color, (x, y, fw, h))
    pygame.draw.rect(surface, (80, 80, 100), (x, y, w, h), 1)
