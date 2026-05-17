"""
Day-night cycle and world state management.
"""

import math
import random
from typing import Dict, List, Tuple

from colors import GRASS, GROUND, WATER, NIGHT_ALPHA, DUSK_ALPHA, DAWN_ALPHA


class WorldState:
    def __init__(self, width: int = 100, height: int = 100):
        self.width = width
        self.height = height
        self.terrain: Dict[Tuple[int, int], str] = {}
        self._generate_terrain()

        self.day_number = 1
        self.time_of_day = 0.0
        self.DAY_LENGTH = 60.0
        self.NIGHT_LENGTH = 60.0
        self.CYCLE_LENGTH = self.DAY_LENGTH + self.NIGHT_LENGTH

        self.is_night = False
        self.is_dusk = False
        self.is_dawn = False
        self.night_intensity = 0.0

    def _generate_terrain(self) -> None:
        # Simple terrain generation using noise-like patterns
        # Create some water bodies
        water_centers = [
            (random.randint(10, 30), random.randint(10, 30)),
            (random.randint(70, 90), random.randint(70, 90)),
        ]

        for x in range(self.width):
            for y in range(self.height):
                is_water = False
                for cx, cy in water_centers:
                    dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                    if dist < 8 + random.uniform(-2, 2):
                        if random.random() < 0.8:
                            self.terrain[(x, y)] = "water"
                            is_water = True
                            continue

                if not is_water:
                    if random.random() < 0.85:
                        self.terrain[(x, y)] = "grass"
                    else:
                        self.terrain[(x, y)] = "ground"

    def get_terrain_color(self, x: int, y: int) -> Tuple[int, int, int]:
        terrain_type = self.terrain.get((x, y), "grass")
        if terrain_type == "water":
            return WATER
        elif terrain_type == "grass":
            # Add slight variation
            base = GRASS
            v = random.randint(-5, 5)
            return (max(0, min(255, base[0] + v)),
                    max(0, min(255, base[1] + v)),
                    max(0, min(255, base[2] + v)))
        else:
            return GROUND

    def is_passable(self, x: float, y: float) -> bool:
        tx = int(x)
        ty = int(y)
        terrain = self.terrain.get((tx, ty), "grass")
        return terrain != "water"

    def update(self, dt: float) -> None:
        self.time_of_day += dt
        if self.time_of_day >= self.CYCLE_LENGTH:
            self.time_of_day -= self.CYCLE_LENGTH
            self.day_number += 1

        cycle_pos = self.time_of_day / self.CYCLE_LENGTH
        day_frac = self.time_of_day / self.CYCLE_LENGTH

        # Determine phase
        if self.time_of_day < self.DAY_LENGTH:
            # Day phase
            self.is_night = False
            self.is_dusk = False
            self.is_dawn = False
            self.night_intensity = 0.0
        else:
            # Night phase
            night_elapsed = self.time_of_day - self.DAY_LENGTH
            night_frac = night_elapsed / self.NIGHT_LENGTH

            # Dusk (first/last 10%)
            if night_frac < 0.15:
                self.is_dusk = True
                self.is_dawn = False
                self.is_night = False
                self.night_intensity = night_frac / 0.15
            elif night_frac > 0.85:
                self.is_dawn = True
                self.is_dusk = False
                self.is_night = False
                self.night_intensity = (1.0 - night_frac) / 0.15
            else:
                self.is_night = True
                self.is_dusk = False
                self.is_dawn = False
                self.night_intensity = 1.0

    def get_night_overlay_alpha(self) -> int:
        return int(self.night_intensity * NIGHT_ALPHA)

    def get_day_brightness(self) -> float:
        # 1.0 = full brightness, 0.3 = night darkness
        return max(0.3, 1.0 - self.night_intensity * 0.7)

    def get_time_display(self) -> str:
        if self.time_of_day < self.DAY_LENGTH:
            hour = int((self.time_of_day / self.DAY_LENGTH) * 24)
            minute = int(((self.time_of_day / self.DAY_LENGTH) * 24 - hour) * 60)
        else:
            night_elapsed = self.time_of_day - self.DAY_LENGTH
            hour = int((night_elapsed / self.NIGHT_LENGTH) * 24)
            minute = int(((night_elapsed / self.NIGHT_LENGTH) * 24 - hour) * 60)

        return f"{hour:02d}:{minute:02d}"

    def is_daytime(self) -> bool:
        return not self.is_night and not self.is_dusk and self.time_of_day < self.DAY_LENGTH

    def is_monster_active(self) -> bool:
        return self.is_night or self.is_dusk or self.is_dawn

    def get_phase_name(self) -> str:
        if self.is_night:
            return "Night"
        elif self.is_dusk:
            return "Dusk"
        elif self.is_dawn:
            return "Dawn"
        else:
            return "Day"
