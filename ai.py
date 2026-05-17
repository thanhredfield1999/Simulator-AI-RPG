"""
AI brain for each entity type using Finite State Machines.
Every pixel thinks for itself.
"""

import random
import math
from typing import List, Optional, Tuple

from entities import Entity, EntityManager, EntityType
from world import WorldState
from colors import WALL, DOOR, TORCH, HUMAN_COLORS, MONSTER_COLORS


# --- Human AI States ---
HUMAN_STATES = {
    "idle": "IDLE",
    "gather": "GATHER",
    "build": "BUILD",
    "defend": "DEFEND",
    "attack": "ATTACK",
    "flee": "FLEE",
    "return_home": "RETURN_HOME",
    "scout": "SCOUT",
}


class HumanAI:
    ACTION_INTERVAL = 8  # ticks between actions

    def __init__(self, world: WorldState, em: EntityManager):
        self.world = world
        self.em = em

    def update(self, entity: Entity) -> None:
        entity.tick()
        if entity.state_timer < self.ACTION_INTERVAL:
            return

        # Set home if not set
        entity.set_home_if_none()

        # State machine
        state = entity.state
        if state == "idle":
            self._idle(entity)
        elif state == "gather":
            self._gather(entity)
        elif state == "build":
            self._build(entity)
        elif state == "defend":
            self._defend(entity)
        elif state == "attack":
            self._attack(entity)
        elif state == "flee":
            self._flee(entity)
        elif state == "return_home":
            self._return_home(entity)
        elif state == "scout":
            self._scout(entity)

        # Transition
        self._evaluate_state(entity)
        entity.state_timer = 0

    def _evaluate_state(self, entity: Entity) -> None:
        nearby = self.em.get_nearby(entity.x, entity.y, 5)
        monsters = [e for e in nearby if e.entity_type == EntityType.MONSTER and e.is_alive()]
        resources = [e for e in nearby if e.is_resource and e.is_alive()]
        walls = [e for e in nearby if e.entity_type in (EntityType.WALL, EntityType.DOOR, EntityType.TORCH)]

        # Danger assessment
        if monsters and entity.distance_to(monsters[0]) < 3:
            entity.state = "defend"
            return

        # Daytime priorities
        if self.world.is_daytime():
            if not resources and not walls:
                entity.state = "scout"
            elif resources and random.random() < 0.6:
                entity.state = "gather"
            elif walls and random.random() < 0.4:
                entity.state = "build"
        else:
            # Nighttime - return home
            if entity.home_x is not None:
                dist_home = entity.distance_to_pos(entity.home_x, entity.home_y)
                if dist_home > 3:
                    entity.state = "return_home"
                else:
                    entity.state = "defend"

    def _idle(self, entity: Entity) -> None:
        angle = random.uniform(0, 2 * math.pi)
        dx = math.cos(angle) * 0.5
        dy = math.sin(angle) * 0.5
        entity.move_towards(entity.x + dx, entity.y + dy)
        if self.world.is_passable(entity.x + dx, entity.y + dy):
            entity.x += dx
            entity.y += dy

    def _gather(self, entity: Entity) -> None:
        nearby = self.em.get_entities_in_radius(entity.x, entity.y, 6)
        resources = sorted(
            [e for e in nearby if e.is_resource and e.is_alive()],
            key=lambda e: entity.distance_to(e)
        )
        if resources:
            target = resources[0]
            dist = entity.distance_to(target)
            if dist < 1.2:
                target.take_damage(1)
                if not target.is_alive():
                    self.em.remove(target)
                    entity.inventory["resources"] = entity.inventory.get("resources", 0) + target.resource_value
            else:
                entity.move_towards(target.x, target.y)
                entity.x = max(0, min(99, entity.x + (target.x - entity.x) * 0.15))
                entity.y = max(0, min(99, entity.y + (target.y - entity.y) * 0.15))
        else:
            self._idle(entity)

    def _build(self, entity: Entity) -> None:
        resources = entity.inventory.get("resources", 0)
        if resources < 1:
            entity.state = "gather"
            return

        # Find a good build spot near home
        home_x = entity.home_x or entity.x
        home_y = entity.home_y or entity.y

        # Try to build a wall nearby
        angle = random.uniform(0, 2 * math.pi)
        for radius in [2, 3, 4]:
            bx = home_x + math.cos(angle) * radius
            by = home_y + math.sin(angle) * radius
            bx = max(0, min(99, bx))
            by = max(0, min(99, by))
            if self.world.is_passable(bx, by):
                occupants = self.em.get_entities_in_radius(bx, by, 0.5)
                if not any(o.is_alive() and o.entity_type not in (EntityType.GRASS, EntityType.GROUND) for o in occupants):
                    # Build wall or door
                    build_type = EntityType.DOOR if random.random() < 0.2 else EntityType.WALL
                    wall = self.em.respawn_entity(build_type, bx, by, team="human")
                    entity.inventory["resources"] -= 1
                    return

        entity.state = "scout"

    def _defend(self, entity: Entity) -> None:
        nearby = self.em.get_entities_in_radius(entity.x, entity.y, 5)
        monsters = [e for e in nearby if e.entity_type == EntityType.MONSTER and e.is_alive()]
        if monsters:
            nearest = min(monsters, key=lambda m: entity.distance_to(m))
            if entity.distance_to(nearest) < 1.5:
                entity.state = "attack"
            else:
                entity.move_towards(nearest.x, nearest.y)
        else:
            entity.state = "idle"

    def _attack(self, entity: Entity) -> None:
        nearby = self.em.get_entities_in_radius(entity.x, entity.y, 3)
        monsters = [e for e in nearby if e.entity_type == EntityType.MONSTER and e.is_alive()]
        if monsters:
            target = min(monsters, key=lambda m: entity.distance_to(m))
            entity.move_towards(target.x, target.y)
            entity.state = "defend"
        else:
            entity.state = "idle"

    def _flee(self, entity: Entity) -> None:
        nearby = self.em.get_entities_in_radius(entity.x, entity.y, 5)
        threats = [e for e in nearby if e.entity_type == EntityType.MONSTER and e.is_alive()]
        if threats:
            nearest = min(threats, key=lambda t: entity.distance_to(t))
            entity.move_away(nearest.x, nearest.y)
        else:
            entity.state = "idle"

    def _return_home(self, entity: Entity) -> None:
        if entity.home_x is not None:
            dist = entity.distance_to_pos(entity.home_x, entity.home_y)
            if dist > 1:
                entity.move_towards(entity.home_x, entity.home_y)
            else:
                entity.state = "defend"
        else:
            entity.state = "idle"

    def _scout(self, entity: Entity) -> None:
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(2, 5)
        tx = entity.x + math.cos(angle) * dist
        ty = entity.y + math.sin(angle) * dist
        tx = max(0, min(99, tx))
        ty = max(0, min(99, ty))
        entity.move_towards(tx, ty)
        entity.state = "idle"


# --- Monster AI States ---
MONSTER_STATES = {
    "idle": "IDLE",
    "hunt": "HUNT",
    "attack": "ATTACK",
    "build_lair": "BUILD_LAIR",
    "wander": "WANDER",
    "retreat": "RETREAT",
}


class MonsterAI:
    ACTION_INTERVAL = 10

    def __init__(self, world: WorldState, em: EntityManager):
        self.world = world
        self.em = em

    def update(self, entity: Entity) -> None:
        entity.tick()
        if entity.state_timer < self.ACTION_INTERVAL:
            return

        entity.set_home_if_none()

        state = entity.state
        if state == "idle":
            self._idle(entity)
        elif state == "hunt":
            self._hunt(entity)
        elif state == "attack":
            self._attack(entity)
        elif state == "build_lair":
            self._build_lair(entity)
        elif state == "wander":
            self._wander(entity)
        elif state == "retreat":
            self._retreat(entity)

        self._evaluate_state(entity)
        entity.state_timer = 0

    def _evaluate_state(self, entity: Entity) -> None:
        nearby = self.em.get_nearby(entity.x, entity.y, 8)
        humans = [e for e in nearby if e.entity_type == EntityType.HUMAN and e.is_alive()]
        lairs = [e for e in nearby if e.entity_type == EntityType.LAIR]

        if self.world.is_monster_active():
            if humans:
                entity.state = "hunt"
            else:
                entity.state = "wander"
        else:
            # Daytime - build lair or rest
            if not lairs:
                entity.state = "build_lair"
            else:
                entity.state = "idle"

    def _hunt(self, entity: Entity) -> None:
        nearby = self.em.get_entities_in_radius(entity.x, entity.y, 8)
        humans = sorted(
            [e for e in nearby if e.entity_type == EntityType.HUMAN and e.is_alive()],
            key=lambda h: entity.distance_to(h)
        )
        if humans:
            target = humans[0]
            dist = entity.distance_to(target)
            if dist < 1.5:
                entity.state = "attack"
            else:
                dx = target.x - entity.x
                dy = target.y - entity.y
                entity.x = max(0, min(99, entity.x + dx * 0.2))
                entity.y = max(0, min(99, entity.y + dy * 0.2))
        else:
            self._wander(entity)

    def _attack(self, entity: Entity) -> None:
        nearby = self.em.get_entities_in_radius(entity.x, entity.y, 2)
        humans = [e for e in nearby if e.entity_type == EntityType.HUMAN and e.is_alive()]
        if humans:
            target = min(humans, key=lambda h: entity.distance_to(h))
            entity.move_towards(target.x, target.y)
        else:
            entity.state = "wander"

    def _build_lair(self, entity: Entity) -> None:
        # Build walls around spawn area
        angle = random.uniform(0, 2 * math.pi)
        home_x = entity.home_x or entity.x
        home_y = entity.home_y or entity.y
        for radius in [1, 2, 3]:
            bx = home_x + math.cos(angle) * radius
            by = home_y + math.sin(angle) * radius
            bx = max(0, min(99, bx))
            by = max(0, min(99, by))
            occupants = self.em.get_entities_in_radius(bx, by, 0.5)
            if not any(o.entity_type in (EntityType.WALL, EntityType.DOOR, EntityType.LAIR) for o in occupants if o.is_alive()):
                self.em.respawn_entity(EntityType.WALL, bx, by, team="monster")
                return
        entity.state = "wander"

    def _wander(self, entity: Entity) -> None:
        angle = random.uniform(0, 2 * math.pi)
        dx = math.cos(angle) * 0.5
        dy = math.sin(angle) * 0.5
        tx = entity.x + dx
        ty = entity.y + dy
        if self.world.is_passable(tx, ty):
            entity.x = max(0, min(99, tx))
            entity.y = max(0, min(99, ty))

    def _retreat(self, entity: Entity) -> None:
        if entity.home_x is not None:
            entity.move_towards(entity.home_x, entity.home_y)
        else:
            entity.state = "wander"


# --- Animal AI States ---
class AnimalAI:
    ACTION_INTERVAL = 15

    def __init__(self, world: WorldState, em: EntityManager):
        self.world = world
        self.em = em

    def update(self, entity: Entity) -> None:
        entity.tick()
        if entity.state_timer < self.ACTION_INTERVAL:
            return

        nearby = self.em.get_nearby(entity.x, entity.y, 4)
        threats = [e for e in nearby if e.entity_type in (EntityType.HUMAN, EntityType.MONSTER) and e.is_alive()]

        if threats:
            nearest = min(threats, key=lambda t: entity.distance_to(t))
            entity.move_away(nearest.x, nearest.y)
            entity.state = "fleeing"
        else:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0.3, 1.0)
            tx = entity.x + math.cos(angle) * dist
            ty = entity.y + math.sin(angle) * dist
            if self.world.is_passable(tx, ty):
                entity.x = max(0, min(99, tx))
                entity.y = max(0, min(99, ty))
            entity.state = "grazing"

        entity.state_timer = 0


def update_all_ai(em: EntityManager, world: WorldState, dt: float) -> None:
    human_ai = HumanAI(world, em)
    monster_ai = MonsterAI(world, em)
    animal_ai = AnimalAI(world, em)

    for entity in list(em.entities.values()):
        if not entity.is_alive():
            continue
        if entity.entity_type == EntityType.HUMAN:
            human_ai.update(entity)
        elif entity.entity_type == EntityType.MONSTER:
            monster_ai.update(entity)
        elif entity.entity_type == EntityType.ANIMAL:
            animal_ai.update(entity)
