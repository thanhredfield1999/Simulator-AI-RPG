"""
Entity system for NanoRealm: Pixel Warfare
Every pixel is an entity with position, HP, color, and AI state.
"""

import random
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

from colors import (
    HUMAN, MONSTER, ANIMAL, TREE, ROCK, WALL, DOOR,
    TORCH, SPAWNER, GROUND, GRASS, WATER, LAIR,
    HUMAN_COLORS, MONSTER_COLORS,
)


class EntityType(Enum):
    HUMAN = "human"
    MONSTER = "monster"
    ANIMAL = "animal"
    TREE = "tree"
    ROCK = "rock"
    WALL = "wall"
    DOOR = "door"
    TORCH = "torch"
    SPAWNER = "spawner"
    GROUND = "ground"
    GRASS = "grass"
    WATER = "water"
    LAIR = "lair"


@dataclass
class EntityStats:
    max_hp: int
    color: Tuple[int, int, int]
    speed: int          # tiles per action
    attack: int
    defense: int
    resource_value: int
    can_move: bool = True
    is_structure: bool = False
    is_resource: bool = False
    is_building: bool = False


ENTITY_STATS: Dict[EntityType, EntityStats] = {
    EntityType.HUMAN:    EntityStats(3,  HUMAN,    1, 1, 0, 0, True,  False, False, False),
    EntityType.MONSTER:  EntityStats(3,  MONSTER,  1, 1, 0, 0, True,  False, False, False),
    EntityType.ANIMAL:   EntityStats(2,  ANIMAL,   1, 0, 0, 1, True,  False, True,  False),
    EntityType.TREE:     EntityStats(5,  TREE,     0, 0, 0, 2, False, False, True,  False),
    EntityType.ROCK:     EntityStats(8,  ROCK,     0, 0, 0, 3, False, False, True,  False),
    EntityType.WALL:     EntityStats(10, WALL,     0, 0, 1, 0, False, True,  False, True),
    EntityType.DOOR:     EntityStats(2,  DOOR,     0, 0, 0, 0, False, True,  False, True),
    EntityType.TORCH:   EntityStats(1,  TORCH,    0, 0, 0, 0, False, True,  False, True),
    EntityType.SPAWNER:  EntityStats(50, SPAWNER,  0, 0, 0, 0, False, True,  False, True),
    EntityType.GROUND:   EntityStats(999,GROUND,   0, 0, 0, 0, False, False, False, False),
    EntityType.GRASS:    EntityStats(999,GRASS,    0, 0, 0, 0, False, False, False, False),
    EntityType.WATER:    EntityStats(999,WATER,    0, 0, 0, 0, False, False, False, False),
    EntityType.LAIR:     EntityStats(3,  LAIR,     0, 0, 0, 0, False, True,  False, True),
}


@dataclass
class Entity:
    id: int
    entity_type: EntityType
    x: float
    y: float
    hp: int
    max_hp: int
    color: Tuple[int, int, int]
    speed: int
    attack: int
    defense: int
    can_move: bool
    is_structure: bool
    is_resource: bool
    is_building: bool
    resource_value: int
    home_x: Optional[float] = None
    home_y: Optional[float] = None
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    state: str = "idle"
    state_timer: int = 0
    team: str = "neutral"
    energy: int = 100
    age: int = 0
    in_combat: bool = False
    carrying: int = 0
    inventory: Dict[str, int] = field(default_factory=dict)
    attack_cooldown: int = 0
    last_damage_from: Optional[int] = None

    @classmethod
    def create(cls, entity_id: int, entity_type: EntityType, x: float, y: float,
               team: str = "neutral", color_override: Optional[Tuple[int, int, int]] = None) -> "Entity":
        stats = ENTITY_STATS[entity_type]
        color = color_override or stats.color
        return cls(
            id=entity_id,
            entity_type=entity_type,
            x=x, y=y,
            hp=stats.max_hp,
            max_hp=stats.max_hp,
            color=color,
            speed=stats.speed,
            attack=stats.attack,
            defense=stats.defense,
            can_move=stats.can_move,
            is_structure=stats.is_structure,
            is_resource=stats.is_resource,
            is_building=stats.is_building,
            resource_value=stats.resource_value,
            team=team,
        )

    def take_damage(self, amount: int, attacker_id: Optional[int] = None) -> bool:
        effective = max(1, amount - self.defense)
        self.hp -= effective
        self.last_damage_from = attacker_id
        self.in_combat = True
        self.state_timer = 0
        return self.hp <= 0

    def is_alive(self) -> bool:
        return self.hp > 0

    def distance_to(self, other: "Entity") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def distance_to_pos(self, x: float, y: float) -> float:
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

    def move_towards(self, tx: float, ty: float) -> None:
        if not self.can_move:
            return
        dx = tx - self.x
        dy = ty - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 0.01:
            return
        step = self.speed / dist
        nx = self.x + dx * step
        ny = self.y + dy * step
        self.x = max(0, min(99, nx))
        self.y = max(0, min(99, ny))

    def move_away(self, fx: float, fy: float) -> None:
        if not self.can_move:
            return
        dx = self.x - fx
        dy = self.y - fy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 0.01:
            angle = random.uniform(0, 2 * math.pi)
            dx, dy = math.cos(angle), math.sin(angle)
            dist = 1
        step = self.speed / dist
        nx = self.x + dx * step
        ny = self.y + dy * step
        self.x = max(0, min(99, nx))
        self.y = max(0, min(99, ny))

    def set_home_if_none(self) -> None:
        if self.home_x is None:
            self.home_x = self.x
            self.home_y = self.y

    def tick(self) -> None:
        self.age += 1
        self.state_timer += 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.in_combat and self.state_timer > 30:
            self.in_combat = False


class EntityManager:
    def __init__(self):
        self.entities: Dict[int, Entity] = {}
        self.next_id = 1
        self.grid: Dict[Tuple[int, int], List[int]] = {}

    def add(self, entity: Entity) -> Entity:
        entity.id = self.next_id
        self.next_id += 1
        self.entities[entity.id] = entity
        self._grid_add(entity)
        return entity

    def remove(self, entity: Entity) -> None:
        self._grid_remove(entity)
        self.entities.pop(entity.id, None)

    def _grid_add(self, entity: Entity) -> None:
        key = (int(entity.x), int(entity.y))
        if key not in self.grid:
            self.grid[key] = []
        if entity.id not in self.grid[key]:
            self.grid[key].append(entity.id)

    def _grid_remove(self, entity: Entity) -> None:
        key = (int(entity.x), int(entity.y))
        if key in self.grid and entity.id in self.grid[key]:
            self.grid[key].remove(entity.id)

    def update_grid(self, entity: Entity) -> None:
        self._grid_remove(entity)
        self._grid_add(entity)

    def get_nearby(self, x: float, y: float, radius: int = 3) -> List[Entity]:
        result = []
        for gx in range(max(0, int(x) - radius), min(100, int(x) + radius + 1)):
            for gy in range(max(0, int(y) - radius), min(100, int(y) + radius + 1)):
                for eid in self.grid.get((gx, gy), []):
                    e = self.entities.get(eid)
                    if e and e.is_alive():
                        result.append(e)
        return result

    def get_entities_in_radius(self, x: float, y: float, radius: float) -> List[Entity]:
        result = []
        for entity in self.entities.values():
            if entity.is_alive() and entity.distance_to_pos(x, y) <= radius:
                result.append(entity)
        return result

    def get_by_type(self, entity_type: EntityType) -> List[Entity]:
        return [e for e in self.entities.values() if e.is_alive() and e.entity_type == entity_type]

    def get_by_team(self, team: str) -> List[Entity]:
        return [e for e in self.entities.values() if e.is_alive() and e.team == team]

    def get_spawners(self) -> List[Entity]:
        return [e for e in self.entities.values() if e.is_alive() and e.entity_type == EntityType.SPAWNER]

    def count_alive(self) -> Dict[EntityType, int]:
        counts: Dict[EntityType, int] = {}
        for e in self.entities.values():
            if e.is_alive():
                counts[e.entity_type] = counts.get(e.entity_type, 0) + 1
        return counts

    def respawn_entity(self, entity_type: EntityType, x: float, y: float,
                       team: str = "neutral",
                       color_override: Optional[Tuple[int, int, int]] = None) -> Entity:
        entity = Entity.create(self.next_id, entity_type, x, y, team, color_override)
        return self.add(entity)
