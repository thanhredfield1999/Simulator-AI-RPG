"""
NanoRealm: Pixel Warfare
Main entry point. Each pixel has a mind of its own.
"""

import random
import pygame

from core import Core, WORLD_WIDTH, WORLD_HEIGHT, FPS
from entities import EntityManager, Entity, EntityType
from world import WorldState
from combat import CombatSystem
from ai import update_all_ai
from ui import UI
from sprites import SpriteRenderer
from colors import (
    HUMAN_COLORS, MONSTER_COLORS,
    GROUND, GRASS,
)
from datetime import datetime


def spawn_initial_world(em: EntityManager) -> None:
    random.seed()

    # Spawn trees
    for _ in range(40):
        x = random.randint(2, WORLD_WIDTH - 3)
        y = random.randint(2, WORLD_HEIGHT - 3)
        if em.get_entities_in_radius(x, y, 2):
            continue
        em.respawn_entity(EntityType.TREE, x, y)

    # Spawn rocks
    for _ in range(25):
        x = random.randint(2, WORLD_WIDTH - 3)
        y = random.randint(2, WORLD_HEIGHT - 3)
        if em.get_entities_in_radius(x, y, 2):
            continue
        em.respawn_entity(EntityType.ROCK, x, y)

    # Spawn animals
    for _ in range(20):
        x = random.randint(2, WORLD_WIDTH - 3)
        y = random.randint(2, WORLD_HEIGHT - 3)
        if em.get_entities_in_radius(x, y, 2):
            continue
        em.respawn_entity(EntityType.ANIMAL, x, y)

    # Spawn humans on the left side
    human_zone_x = random.randint(15, 30)
    human_zone_y = random.randint(15, 80)
    for i in range(12):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, 8)
        hx = human_zone_x + math.cos(angle) * dist
        hy = human_zone_y + math.sin(angle) * dist
        color_idx = i % len(HUMAN_COLORS)
        human = em.respawn_entity(EntityType.HUMAN, hx, hy, team="human",
                                  color_override=HUMAN_COLORS[color_idx])
        human.home_x = human_zone_x + random.uniform(-5, 5)
        human.home_y = human_zone_y + random.uniform(-5, 5)

    # Spawn a small human base
    base_x, base_y = human_zone_x, human_zone_y
    for angle in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
        bx = base_x + math.cos(angle) * 3
        by = base_y + math.sin(angle) * 3
        em.respawn_entity(EntityType.WALL, bx, by, team="human")

    # Spawn monsters on the right side
    monster_zone_x = random.randint(70, 85)
    monster_zone_y = random.randint(15, 80)
    for i in range(8):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, 6)
        mx = monster_zone_x + math.cos(angle) * dist
        my = monster_zone_y + math.sin(angle) * dist
        color_idx = i % len(MONSTER_COLORS)
        monster = em.respawn_entity(EntityType.MONSTER, mx, my, team="monster",
                                    color_override=MONSTER_COLORS[color_idx])
        monster.home_x = monster_zone_x + random.uniform(-3, 3)
        monster.home_y = monster_zone_y + random.uniform(-3, 3)

    # Spawn monster spawner
    spawner = em.respawn_entity(EntityType.SPAWNER, monster_zone_x, monster_zone_y, team="monster")

    # Spawn monster lair walls
    for angle in [0, math.pi / 2, math.pi, 3 * math.pi / 2, math.pi / 4, 3 * math.pi / 4]:
        bx = monster_zone_x + math.cos(angle) * 2.5
        by = monster_zone_y + math.sin(angle) * 2.5
        if random.random() < 0.6:
            em.respawn_entity(EntityType.LAIR, bx, by, team="monster")


def main():
    import math

    # Init core
    core = Core(1280, 720)

    # Init world
    world = WorldState(WORLD_WIDTH, WORLD_HEIGHT)

    # Init entity manager
    em = EntityManager()

    # Spawn world
    spawn_initial_world(em)

    # Init systems
    combat = CombatSystem(em)
    ui = UI(core.screen, em, world)
    renderer = SpriteRenderer(core.screen, core.camera.zoom * 8)

    # Track last night state to detect night onset
    last_was_night = False
    spawn_timer = 0.0

    # Main loop
    while core.should_close():
        dt = core.tick()

        if not core.paused:
            scaled_dt = dt * core.speed_multiplier

            # Update world
            world.update(scaled_dt)

            # Update AI
            update_all_ai(em, world, scaled_dt)

            # Update grid positions for moved entities
            for entity in list(em.entities.values()):
                if entity.is_alive():
                    em.update_grid(entity)

            # Combat resolution
            humans = em.get_by_team("human")
            monsters = em.get_by_team("monster")
            combat.resolve_combat(monsters, humans)

            # Monster spawner - spawn at night
            if world.is_monster_active():
                spawn_timer += scaled_dt
                if spawn_timer > 8.0:
                    spawn_timer = 0.0
                    spawners = em.get_spawners()
                    for sp in spawners:
                        nearby_monsters = [e for e in em.get_entities_in_radius(sp.x, sp.y, 5)
                                          if e.entity_type == EntityType.MONSTER and e.is_alive()]
                        if len(nearby_monsters) < 5:
                            angle = random.uniform(0, 2 * math.pi)
                            dist = random.uniform(1.5, 3.0)
                            mx = sp.x + math.cos(angle) * dist
                            my = sp.y + math.sin(angle) * dist
                            color_idx = random.randint(0, len(MONSTER_COLORS) - 1)
                            monster = em.respawn_entity(EntityType.MONSTER, mx, my, team="monster",
                                                       color_override=MONSTER_COLORS[color_idx])
                            monster.home_x = sp.x
                            monster.home_y = sp.y

            # Human respawn
            human_count = len(em.get_by_team("human"))
            if human_count < 8:
                human_spawns = [e for e in em.entities.values()
                               if e.is_alive() and e.entity_type == EntityType.HUMAN]
                if human_spawns:
                    leader = human_spawns[0]
                    angle = random.uniform(0, 2 * math.pi)
                    hx = leader.home_x + math.cos(angle) * random.uniform(3, 6)
                    hy = leader.home_y + math.sin(angle) * random.uniform(3, 6)
                    color_idx = random.randint(0, len(HUMAN_COLORS) - 1)
                    human = em.respawn_entity(EntityType.HUMAN, hx, hy, team="human",
                                              color_override=HUMAN_COLORS[color_idx])
                    human.home_x = leader.home_x
                    human.home_y = leader.home_y

            # Tree regrowth
            tree_count = len(em.get_by_type(EntityType.TREE))
            if tree_count < 30 and random.random() < 0.01:
                tx = random.randint(2, WORLD_WIDTH - 3)
                ty = random.randint(2, WORLD_HEIGHT - 3)
                if world.is_passable(tx, ty):
                    em.respawn_entity(EntityType.TREE, tx, ty)

            # Animal reproduction
            animal_count = len(em.get_by_type(EntityType.ANIMAL))
            if animal_count < 15 and random.random() < 0.005:
                animals = em.get_by_type(EntityType.ANIMAL)
                if animals:
                    parent = random.choice(animals)
                    angle = random.uniform(0, 2 * math.pi)
                    ax = parent.x + math.cos(angle) * 3
                    ay = parent.y + math.sin(angle) * 3
                    if world.is_passable(ax, ay):
                        em.respawn_entity(EntityType.ANIMAL, ax, ay)

            # Combat update
            combat.update(scaled_dt)

            # Build torches at night near human base
            if world.is_night and random.random() < 0.01:
                humans = em.get_by_team("human")
                if humans:
                    leader = humans[0]
                    if leader.home_x is not None:
                        angle = random.uniform(0, 2 * math.pi)
                        dist = random.uniform(2, 4)
                        tx = leader.home_x + math.cos(angle) * dist
                        ty = leader.home_y + math.sin(angle) * dist
                        existing = [e for e in em.get_entities_in_radius(tx, ty, 1)
                                   if e.entity_type == EntityType.TORCH and e.is_alive()]
                        if not existing:
                            em.respawn_entity(EntityType.TORCH, tx, ty, team="human")

        # ---- RENDER ----
        core.fill_screen((5, 5, 10))

        # Calculate visible tiles
        cam = core.camera
        half_w = (core.width / 2) / cam.zoom
        half_h = (core.height / 2) / cam.zoom
        min_tx = max(0, int(cam.x - half_w) - 1)
        max_tx = min(WORLD_WIDTH, int(cam.x + half_w) + 2)
        min_ty = max(0, int(cam.y - half_h) - 1)
        max_ty = min(WORLD_HEIGHT, int(cam.y + half_h) + 2)

        brightness = world.get_day_brightness()
        px = max(1, int(cam.zoom * 8))

        # Draw terrain
        for tx in range(min_tx, max_tx):
            for ty in range(min_ty, max_ty):
                sx, sy = cam.world_to_screen(float(tx), float(ty))
                terrain_color = world.get_terrain_color(tx, ty)
                r = int(terrain_color[0] * brightness)
                g = int(terrain_color[1] * brightness)
                b = int(terrain_color[2] * brightness)
                pygame.draw.rect(core.screen, (r, g, b), (sx, sy, px, px))

        # Draw grid
        if core.show_grid:
            for tx in range(min_tx, max_tx + 1):
                sx, _ = cam.world_to_screen(float(tx), 0)
                _, sy1 = cam.world_to_screen(0, float(min_ty))
                _, sy2 = cam.world_to_screen(0, float(max_ty))
                pygame.draw.line(core.screen, (30, 30, 40), (sx, sy1), (sx, sy2))
            for ty in range(min_ty, max_ty + 1):
                _, sy = cam.world_to_screen(0, float(ty))
                sx1, _ = cam.world_to_screen(float(min_tx), 0)
                sx2, _ = cam.world_to_screen(float(max_tx), 0)
                pygame.draw.line(core.screen, (30, 30, 40), (sx1, sy), (sx2, sy))

        # Draw entities
        drawn: dict = {}
        for entity in list(em.entities.values()):
            if not entity.is_alive():
                continue
            sx, sy = cam.world_to_screen(entity.x, entity.y)

            # Only draw if on screen
            if sx < -px or sx > core.width + px or sy < -px or sy > core.height + px:
                continue

            flash = combat.flash_entity(entity.id)
            color = entity.color

            pygame.draw.rect(core.screen, color, (sx, sy, px, px))

            if flash:
                pygame.draw.rect(core.screen, (255, 255, 255), (sx, sy, px, px))

            # HP bar for entities with HP < max
            if entity.max_hp < 999 and entity.hp < entity.max_hp:
                bar_w = px
                bar_h = 2
                bar_y = sy - 3
                fill = entity.hp / entity.max_hp
                pygame.draw.rect(core.screen, (40, 40, 40), (sx, bar_y, bar_w, bar_h))
                pygame.draw.rect(core.screen, (255, 80, 80), (sx, bar_y, int(bar_w * fill), bar_h))

        # Draw UI
        ui.render(cam, combat, core.fps_display, core.speed_multiplier)

        # Pause overlay
        if core.paused:
            pause_surf = pygame.Surface((core.width, core.height), pygame.SRCALPHA)
            pause_surf.fill((0, 0, 0, 120))
            core.screen.blit(pause_surf, (0, 0))
            txt = core.font_large.render("PAUSED - Press Space to Resume", True, (255, 255, 255))
            core.screen.blit(txt, (core.width // 2 - txt.get_width() // 2,
                                   core.height // 2 - txt.get_height() // 2))

        core.present()

    pygame.quit()


if __name__ == "__main__":
    main()
