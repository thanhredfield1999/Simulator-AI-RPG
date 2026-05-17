"""
Core engine: Game loop, grid world, camera, and tick system.
"""

import pygame
import sys
import math
from typing import Optional, Tuple

from colors import UI_BG, UI_TEXT, UI_ACCENT, UI_PANEL, UI_BORDER


# World constants
WORLD_WIDTH = 100
WORLD_HEIGHT = 100
PIXEL_SIZE = 8          # rendering size of each world pixel
DAY_DURATION = 60       # seconds per phase
FPS = 60
GAME_SPEED = 1.0        # 1x = real time, adjustable


class Camera:
    def __init__(self, width: int, height: int):
        self.x = WORLD_WIDTH // 2
        self.y = WORLD_HEIGHT // 2
        self.zoom = 1.0
        self.min_zoom = 0.3
        self.max_zoom = 3.0
        self.screen_w = width
        self.screen_h = height
        self.target_x: Optional[float] = None
        self.target_y: Optional[float] = None

    def screen_to_world(self, sx: int, sy: int) -> Tuple[float, float]:
        wx = sx / self.zoom + self.x - (self.screen_w / 2) / self.zoom
        wy = sy / self.zoom + self.y - (self.screen_h / 2) / self.zoom
        return wx, wy

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        sx = int((wx - self.x) * self.zoom + self.screen_w / 2)
        sy = int((wy - self.y) * self.zoom + self.screen_h / 2)
        return sx, sy

    def world_to_screen_f(self, wx: float, wy: float) -> Tuple[float, float]:
        sx = (wx - self.x) * self.zoom + self.screen_w / 2
        sy = (wy - self.y) * self.zoom + self.screen_h / 2
        return sx, sy

    def pan(self, dx: float, dy: float) -> None:
        self.x = max(0, min(WORLD_WIDTH, self.x + dx))
        self.y = max(0, min(WORLD_HEIGHT, self.y + dy))

    def pan_to(self, wx: float, wy: float) -> None:
        self.x = max(0, min(WORLD_WIDTH, wx))
        self.y = max(0, min(WORLD_HEIGHT, wy))

    def zoom_towards(self, delta: float, sx: int, sy: int) -> None:
        old_zoom = self.zoom
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom + delta))
        if abs(self.zoom - old_zoom) > 0.001:
            wx, wy = self.screen_to_world(sx, sy)
            self.x = wx
            self.y = wy

    def center_on_world(self) -> None:
        self.x = WORLD_WIDTH / 2
        self.y = WORLD_HEIGHT / 2
        self.zoom = 1.0


class Core:
    def __init__(self, width: int = 1280, height: int = 720):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("NanoRealm: Pixel Warfare")
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self.show_grid = False
        self.show_minimap = True
        self.font_small = pygame.font.Font(None, 18)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 32)
        self.width = width
        self.height = height
        self.camera = Camera(width, height)
        self.game_time = 0.0
        self.game_tick = 0
        self.speed_multiplier = 1.0
        self.speed_options = [1.0, 2.0, 5.0]
        self.speed_index = 0
        self.fps_display = 0
        self.fps_counter = 0
        self.fps_timer = 0
        self.dirty_rects: list = []
        self.mouse_pos = (0, 0)
        self.mouse_buttons = (False, False, False)

    def handle_input(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.width = max(800, event.w)
                self.height = max(600, event.h)
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                self.camera.screen_w = self.width
                self.camera.screen_h = self.height
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)
            elif event.type == pygame.MOUSEWHEEL:
                self.camera.zoom_towards(event.y * 0.15, *self.mouse_pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:
                    self.camera.center_on_world()
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
                if event.buttons[0]:
                    dx = -event.rel[0] / self.camera.zoom
                    dy = -event.rel[1] / self.camera.zoom
                    self.camera.pan(dx, dy)

        self.mouse_buttons = pygame.mouse.get_pressed()

    def _handle_keydown(self, key: int) -> None:
        speed_keys = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
        if key in speed_keys:
            self.speed_index = speed_keys[key]
            self.speed_multiplier = self.speed_options[self.speed_index]
        elif key == pygame.K_g:
            self.show_grid = not self.show_grid
        elif key == pygame.K_m:
            self.show_minimap = not self.show_minimap
        elif key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key in (pygame.K_ESCAPE, pygame.K_q):
            self.running = False
        elif key == pygame.K_w or key == pygame.K_UP:
            self.camera.pan(0, -2 / self.camera.zoom)
        elif key == pygame.K_s or key == pygame.K_DOWN:
            self.camera.pan(0, 2 / self.camera.zoom)
        elif key == pygame.K_a or key == pygame.K_LEFT:
            self.camera.pan(-2 / self.camera.zoom, 0)
        elif key == pygame.K_d or key == pygame.K_RIGHT:
            self.camera.pan(2 / self.camera.zoom, 0)

    def update_fps(self, dt: float) -> None:
        self.fps_counter += 1
        self.fps_timer += dt
        if self.fps_timer >= 1.0:
            self.fps_display = self.fps_counter
            self.fps_counter = 0
            self.fps_timer = 0.0

    def tick(self) -> float:
        dt = self.clock.tick(FPS) / 1000.0
        self.update_fps(dt)
        return dt

    def fill_screen(self, color: Tuple[int, int, int]) -> None:
        self.screen.fill(color)

    def present(self) -> None:
        pygame.display.flip()

    def should_close(self) -> bool:
        return not self.running
