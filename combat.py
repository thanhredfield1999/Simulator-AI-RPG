"""
Combat system: attacks, death, respawn, and spatial hashing.
"""

import random
import math
from typing import List, Dict, Optional, Set

from entities import Entity, EntityManager, EntityType
from colors import MONSTER, HUMAN, SPAWNER, TORCH


class CombatSystem:
    def __init__(self, entity_manager: EntityManager):
        self.em = entity_manager
        self.death_queue: List[Entity] = []
        self.respawn_queue: List[tuple] = []  # (entity_type, x, y, team, timer)
        self.spawn_cooldowns: Dict[int, float] = {}
        self.monsters_to_spawn: Dict[int, int] = {}
        self.humans_killed = 0
        self.monsters_killed = 0
        self.damage_flash: Dict[int, int] = {}

    def queue_death(self, entity: Entity, killed_by: Optional[Entity] = None) -> None:
        if entity not in self.death_queue:
            self.death_queue.append(entity)
        if killed_by:
            if killed_by.team == "monster":
                self.humans_killed += 1
            else:
                self.monsters_killed += 1

    def process_deaths(self) -> None:
        for entity in self.death_queue:
            if entity.id in self.em.entities:
                self.em.remove(entity)
        self.death_queue.clear()

    def queue_respawn(self, entity_type: EntityType, x: float, y: float,
                      team: str = "neutral", delay: float = 5.0,
                      color_override=None) -> None:
        self.respawn_queue.append((entity_type, x, y, team, delay, color_override))

    def update_respawns(self, dt: float) -> None:
        still_queued = []
        for entry in self.respawn_queue:
            entry = list(entry)
            entry[4] -= dt
            if entry[4] <= 0:
                entity_type, x, y, team, _, color_override = entry
                self.em.respawn_entity(entity_type, x, y, team, color_override)
            else:
                still_queued.append(tuple(entry))
        self.respawn_queue = still_queued

    def check_attacks(self, attacker: Entity, targets: List[Entity]) -> None:
        if attacker.attack_cooldown > 0:
            return
        for target in targets:
            if target.id == attacker.id:
                continue
            if not target.is_alive():
                continue
            if attacker.entity_type == EntityType.HUMAN and target.entity_type == EntityType.MONSTER:
                dist = attacker.distance_to(target)
                if dist < 1.5:
                    self._do_attack(attacker, target)
                    return
            elif attacker.entity_type == EntityType.MONSTER and target.entity_type == EntityType.HUMAN:
                dist = attacker.distance_to(target)
                if dist < 1.5:
                    self._do_attack(attacker, target)
                    return

    def _do_attack(self, attacker: Entity, target: Entity) -> None:
        if attacker.attack_cooldown > 0:
            return
        damage = max(1, attacker.attack - target.defense)
        target.take_damage(damage, attacker.id)
        attacker.attack_cooldown = 15
        attacker.state = "attacking"
        attacker.state_timer = 0
        self.damage_flash[target.id] = 5
        if not target.is_alive():
            self.queue_death(target, attacker)

    def resolve_combat(self, monsters: List[Entity], humans: List[Entity]) -> None:
        # Humans attack nearby monsters
        for human in humans:
            if not human.is_alive():
                continue
            nearby = self.em.get_entities_in_radius(human.x, human.y, 2.0)
            monster_targets = [t for t in nearby if t.entity_type == EntityType.MONSTER and t.is_alive()]
            if monster_targets:
                self.check_attacks(human, monster_targets)

        # Monsters attack nearby humans
        for monster in monsters:
            if not monster.is_alive():
                continue
            nearby = self.em.get_entities_in_radius(monster.x, monster.y, 2.0)
            human_targets = [t for t in nearby if t.entity_type == EntityType.HUMAN and t.is_alive()]
            if human_targets:
                self.check_attacks(monster, human_targets)

        # Process deaths
        self.process_deaths()

    def check_entity_deaths(self) -> None:
        for entity in list(self.em.entities.values()):
            if not entity.is_alive() and entity not in self.death_queue:
                self.queue_death(entity)

    def flash_entity(self, entity_id: int) -> bool:
        if entity_id in self.damage_flash:
            self.damage_flash[entity_id] -= 1
            if self.damage_flash[entity_id] <= 0:
                del self.damage_flash[entity_id]
            return True
        return False

    def update(self, dt: float) -> None:
        self.check_entity_deaths()
        self.process_deaths()
        self.update_respawns(dt)
