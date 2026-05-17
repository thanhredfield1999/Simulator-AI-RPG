"""
NanoRealm: Pixel Warfare — Web Version
Flask web server with game state and real-time API.
Each pixel has its own AI brain, running server-side.
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import random
import math
import time
import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum

app = Flask(__name__, template_folder="templates")
CORS(app)

WORLD_WIDTH = 100
WORLD_HEIGHT = 100


# ─── Colors ───────────────────────────────────────────────────────────────────
class C:
    HUMAN    = "#22FF55"
    MONSTER  = "#FF2222"
    ANIMAL   = "#FFFF33"
    TREE     = "#008C00"
    ROCK     = "#808080"
    WALL_H   = "#8B5A2B"
    WALL_M   = "#961E1E"
    DOOR     = "#FFA500"
    TORCH    = "#FF8C00"
    SPAWNER  = "#4B0082"
    GROUND   = "#323232"
    GRASS    = "#1E501E"
    WATER    = "#1E5AC8"
    LAIR     = "#641E1E"
    GRID     = "#1A1A28"
    BG       = "#050510"


# ─── Entity Types ─────────────────────────────────────────────────────────────
class EType(Enum):
    HUMAN   = "human"
    MONSTER = "monster"
    ANIMAL  = "animal"
    TREE    = "tree"
    ROCK    = "rock"
    WALL    = "wall"
    DOOR    = "door"
    TORCH   = "torch"
    SPAWNER = "spawner"
    LAIR    = "lair"
    GRASS   = "grass"
    WATER   = "water"


ENTITY_COLORS: Dict[EType, str] = {
    EType.HUMAN:   C.HUMAN,
    EType.MONSTER: C.MONSTER,
    EType.ANIMAL:  C.ANIMAL,
    EType.TREE:    C.TREE,
    EType.ROCK:    C.ROCK,
    EType.WALL:    C.WALL_H,
    EType.DOOR:    C.DOOR,
    EType.TORCH:   C.TORCH,
    EType.SPAWNER: C.SPAWNER,
    EType.LAIR:    C.LAIR,
}

ENTITY_HP: Dict[EType, int] = {
    EType.HUMAN: 3, EType.MONSTER: 3, EType.ANIMAL: 2,
    EType.TREE: 5, EType.ROCK: 8, EType.WALL: 10,
    EType.DOOR: 2, EType.TORCH: 1, EType.SPAWNER: 50,
    EType.LAIR: 3,
}


# ─── Entity ───────────────────────────────────────────────────────────────────
@dataclass
class Entity:
    id: int
    type: EType
    x: float
    y: float
    hp: int
    max_hp: int
    team: str = "neutral"
    state: str = "idle"
    home_x: Optional[float] = None
    home_y: Optional[float] = None
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    attack_cd: int = 0
    in_combat: bool = False

    def is_alive(self) -> bool:
        return self.hp > 0

    def dist(self, ox: float, oy: float) -> float:
        return math.sqrt((self.x - ox) ** 2 + (self.y - oy) ** 2)

    def can_move(self) -> bool:
        return self.type not in (EType.TREE, EType.ROCK, EType.WALL,
                                  EType.DOOR, EType.TORCH, EType.SPAWNER,
                                  EType.LAIR, EType.GRASS, EType.WATER)

    def step_toward(self, tx: float, ty: float) -> None:
        if not self.can_move():
            return
        dx, dy = tx - self.x, ty - self.y
        d = math.sqrt(dx * dx + dy * dy)
        if d < 0.01:
            return
        nx = self.x + dx / d * 0.15
        ny = self.y + dy / d * 0.15
        self.x = max(0, min(WORLD_WIDTH - 1, nx))
        self.y = max(0, min(WORLD_HEIGHT - 1, ny))

    def step_away(self, fx: float, fy: float) -> None:
        if not self.can_move():
            return
        dx, dy = self.x - fx, self.y - fy
        d = math.sqrt(dx * dx + dy * dy)
        if d < 0.01:
            angle = random.uniform(0, 2 * math.pi)
            dx, dy = math.cos(angle), math.sin(angle)
            d = 1
        nx = self.x + dx / d * 0.15
        ny = self.y + dy / d * 0.15
        self.x = max(0, min(WORLD_WIDTH - 1, nx))
        self.y = max(0, min(WORLD_HEIGHT - 1, ny))

    def set_home(self) -> None:
        if self.home_x is None:
            self.home_x, self.home_y = self.x, self.y

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "hp": self.hp,
            "max_hp": self.max_hp,
            "team": self.team,
            "state": self.state,
            "in_combat": self.in_combat,
            "home_x": round(self.home_x, 2) if self.home_x is not None else None,
            "home_y": round(self.home_y, 2) if self.home_y is not None else None,
            "attack_cd": self.attack_cd,
        }


# ─── World ────────────────────────────────────────────────────────────────────
class World:
    def __init__(self):
        self.terrain: Dict[Tuple[int, int], str] = {}
        self.entities: Dict[int, Entity] = {}
        self.next_id = 1
        self.time_of_day = 0.0
        self.day_number = 1
        self.day_duration = 60.0
        self.night_duration = 60.0
        self.cycle_len = self.day_duration + self.night_duration
        self._gen_terrain()
        self._spawn_world()
        self.humans_killed = 0
        self.monsters_killed = 0
        self.spawn_timer = 0.0
        self.last_tick = time.time()
        self.tick_count = 0
        self.speed = 1.0
        self.paused = False

    def _gen_terrain(self) -> None:
        centers = [
            (random.randint(5, 25), random.randint(5, 25)),
            (random.randint(75, 95), random.randint(75, 95)),
        ]
        for x in range(WORLD_WIDTH):
            for y in range(WORLD_HEIGHT):
                is_water = False
                for cx, cy in centers:
                    d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                    if d < 8 + random.uniform(-2, 2) and random.random() < 0.8:
                        self.terrain[(x, y)] = "water"
                        is_water = True
                        break
                if not is_water:
                    self.terrain[(x, y)] = "grass" if random.random() < 0.85 else "ground"

    def _spawn_world(self) -> None:
        def add(etype, x, y, team="neutral") -> Entity:
            e = Entity(self.next_id, etype, x, y,
                       ENTITY_HP[etype], ENTITY_HP[etype], team)
            self.entities[self.next_id] = e
            self.next_id += 1
            return e

        # Trees & Rocks
        for _ in range(40):
            x, y = random.randint(2, 97), random.randint(2, 97)
            if not self._occupied(x, y):
                add(EType.TREE, x, y)

        for _ in range(25):
            x, y = random.randint(2, 97), random.randint(2, 97)
            if not self._occupied(x, y):
                add(EType.ROCK, x, y)

        for _ in range(20):
            x, y = random.randint(2, 97), random.randint(2, 97)
            if not self._occupied(x, y):
                add(EType.ANIMAL, x, y)

        # Humans (left zone)
        hx, hy = random.randint(15, 30), random.randint(15, 80)
        h_colors = ["#22FF55", "#32DC78", "#14C850"]
        for i in range(12):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, 8)
            ex = hx + math.cos(angle) * dist
            ey = hy + math.sin(angle) * dist
            e = add(EType.HUMAN, ex, ey, "human")
            e.home_x = hx + random.uniform(-5, 5)
            e.home_y = hy + random.uniform(-5, 5)

        # Human walls
        for angle in [0, math.pi/2, math.pi, 3*math.pi/2]:
            bx, by = hx + math.cos(angle) * 3, hy + math.sin(angle) * 3
            add(EType.WALL, bx, by, "human")

        # Monsters (right zone)
        mx, my = random.randint(70, 85), random.randint(15, 80)
        add(EType.SPAWNER, mx, my, "monster")
        m_colors = ["#FF2222", "#DC3232", "#C81414"]
        for i in range(8):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, 6)
            ex = mx + math.cos(angle) * dist
            ey = my + math.sin(angle) * dist
            e = add(EType.MONSTER, ex, ey, "monster")
            e.home_x = mx + random.uniform(-3, 3)
            e.home_y = my + random.uniform(-3, 3)

        # Monster lairs
        for angle in [0, math.pi/2, math.pi, 3*math.pi/2, math.pi/4, 3*math.pi/4]:
            if random.random() < 0.6:
                bx = mx + math.cos(angle) * 2.5
                by = my + math.sin(angle) * 2.5
                add(EType.LAIR, bx, by, "monster")

    def _occupied(self, x: float, y: float, r: float = 1.5) -> bool:
        for e in self.entities.values():
            if e.is_alive() and e.dist(x, y) < r:
                return True
        return False

    def is_passable(self, x: float, y: float) -> bool:
        t = self.terrain.get((int(x), int(y)), "grass")
        return t != "water"

    def add_entity(self, etype: EType, x: float, y: float,
                   team: str = "neutral") -> Entity:
        e = Entity(self.next_id, etype, x, y,
                   ENTITY_HP[etype], ENTITY_HP[etype], team)
        self.entities[self.next_id] = e
        self.next_id += 1
        return e

    def get_nearby(self, x: float, y: float, r: float = 5) -> List[Entity]:
        return [e for e in self.entities.values() if e.is_alive() and e.dist(x, y) <= r]

    def remove_dead(self) -> None:
        dead = [i for i, e in self.entities.items() if not e.is_alive()]
        for i in dead:
            del self.entities[i]

    @property
    def is_night(self) -> bool:
        elapsed = self.time_of_day - self.day_duration
        if elapsed < 0:
            return False
        frac = elapsed / self.night_duration
        return 0.15 < frac < 0.85

    @property
    def night_alpha(self) -> int:
        if not self.is_night:
            elapsed = self.time_of_day - self.day_duration
            frac = elapsed / self.night_duration if elapsed > 0 else 0
            if frac < 0.15:
                return int(frac / 0.15 * 100)
            if frac > 0.85:
                return int((1 - frac) / 0.15 * 100)
        return 0

    def get_phase(self) -> str:
        if self.time_of_day < self.day_duration:
            return "Day"
        frac = (self.time_of_day - self.day_duration) / self.night_duration
        if frac < 0.15:
            return "Dusk"
        if frac > 0.85:
            return "Dawn"
        return "Night"

    def get_time_display(self) -> str:
        frac = self.time_of_day / self.cycle_len
        hour = int(frac * 24)
        minute = int((frac * 24 - hour) * 60)
        return f"{hour:02d}:{minute:02d}"

    def get_brightness(self) -> float:
        if self.is_night:
            return 0.3
        frac = self.time_of_day / self.cycle_len
        if frac >= 1.0:
            return 0.3
        return 0.7 + 0.3 * min(1.0, (self.time_of_day / self.day_duration))

    def count_team(self, team: str) -> Dict[EType, int]:
        counts: Dict[EType, int] = {}
        for e in self.entities.values():
            if e.is_alive() and e.team == team:
                counts[e.type] = counts.get(self.type, 0) + 1
        return counts

    def tick(self, dt: float) -> None:
        if self.paused:
            return

        self.time_of_day += dt * self.speed
        if self.time_of_day >= self.cycle_len:
            self.time_of_day -= self.cycle_len
            self.day_number += 1

        self.tick_count += 1

        # ── AI Update every 12 ticks ──
        if self.tick_count % 12 == 0:
            self._ai_update()

        # ── Combat every 6 ticks ──
        if self.tick_count % 6 == 0:
            self._combat_update()

        # ── Spawn monsters at night ──
        if self.is_night:
            self.spawn_timer += dt * self.speed
            if self.spawn_timer > 8.0:
                self.spawn_timer = 0.0
                spawners = [e for e in self.entities.values()
                            if e.is_alive() and e.type == EType.SPAWNER]
                for sp in spawners:
                    nearby = [e for e in self.get_nearby(sp.x, sp.y, 5)
                              if e.is_alive() and e.type == EType.MONSTER]
                    if len(nearby) < 5:
                        angle = random.uniform(0, 2 * math.pi)
                        dist = random.uniform(1.5, 3.0)
                        e = self.add_entity(EType.MONSTER,
                                            sp.x + math.cos(angle) * dist,
                                            sp.y + math.sin(angle) * dist,
                                            "monster")
                        e.home_x = sp.x
                        e.home_y = sp.y

        # ── Human respawn ──
        humans = [e for e in self.entities.values() if e.is_alive() and e.type == EType.HUMAN]
        if len(humans) < 8:
            if humans:
                leader = random.choice(humans)
                angle = random.uniform(0, 2 * math.pi)
                e = self.add_entity(EType.HUMAN,
                                    leader.home_x + math.cos(angle) * random.uniform(3, 6),
                                    leader.home_y + math.sin(angle) * random.uniform(3, 6),
                                    "human")
                e.home_x = leader.home_x
                e.home_y = leader.home_y

        # ── Tree regrowth ──
        if self.tick_count % 60 == 0:
            trees = [e for e in self.entities.values() if e.is_alive() and e.type == EType.TREE]
            if len(trees) < 30:
                for _ in range(3):
                    tx, ty = random.randint(2, 97), random.randint(2, 97)
                    if self.is_passable(tx, ty) and not self._occupied(tx, ty):
                        self.add_entity(EType.TREE, tx, ty)
                        break

        # ── Animal reproduction ──
        if self.tick_count % 90 == 0:
            animals = [e for e in self.entities.values() if e.is_alive() and e.type == EType.ANIMAL]
            if len(animals) < 15:
                parent = random.choice(animals)
                angle = random.uniform(0, 2 * math.pi)
                ax, ay = parent.x + math.cos(angle) * 3, parent.y + math.sin(angle) * 3
                if self.is_passable(ax, ay) and not self._occupied(ax, ay):
                    self.add_entity(EType.ANIMAL, ax, ay)

        # ── Torch at night ──
        if self.is_night and self.tick_count % 30 == 0:
            humans = [e for e in self.entities.values() if e.is_alive() and e.type == EType.HUMAN]
            if humans:
                leader = random.choice(humans)
                if leader.home_x is not None:
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(2, 4)
                    tx, ty = leader.home_x + math.cos(angle) * dist, leader.home_y + math.sin(angle) * dist
                    nearby = [e for e in self.get_nearby(tx, ty, 1)
                              if e.is_alive() and e.type == EType.TORCH]
                    if not nearby:
                        self.add_entity(EType.TORCH, tx, ty, "human")

        # ── Update attack cooldowns ──
        for e in self.entities.values():
            if e.attack_cd > 0:
                e.attack_cd -= 1

        self.remove_dead()

    def _ai_update(self) -> None:
        for e in list(self.entities.values()):
            if not e.is_alive():
                continue
            e.set_home()

            if e.type == EType.HUMAN:
                self._ai_human(e)
            elif e.type == EType.MONSTER:
                self._ai_monster(e)
            elif e.type == EType.ANIMAL:
                self._ai_animal(e)

    def _ai_human(self, e: Entity) -> None:
        nearby = self.get_nearby(e.x, e.y, 6)
        monsters = [x for x in nearby if x.is_alive() and x.type == EType.MONSTER]
        resources = [x for x in nearby if x.is_alive() and x.type in (EType.TREE, EType.ROCK, EType.ANIMAL)]
        walls = [x for x in nearby if x.is_alive() and x.type in (EType.WALL, EType.DOOR)]

        # Danger
        if monsters and e.dist(monsters[0].x, monsters[0].y) < 3:
            target = monsters[0]
            if e.dist(target.x, target.y) < 1.5:
                e.state = "attacking"
            else:
                e.step_toward(target.x, target.y)
                e.state = "defending"
            return

        if self.is_night:
            if e.home_x is not None and e.dist(e.home_x, e.home_y) > 2:
                e.step_toward(e.home_x, e.home_y)
                e.state = "returning_home"
            else:
                e.state = "defending"
            return

        # Daytime
        if not resources and not walls:
            angle = random.uniform(0, 2 * math.pi)
            tx = e.x + math.cos(angle) * random.uniform(1, 3)
            ty = e.y + math.sin(angle) * random.uniform(1, 3)
            if self.is_passable(tx, ty):
                e.step_toward(tx, ty)
            e.state = "scouting"

        elif resources and random.random() < 0.6:
            target = resources[0]
            if e.dist(target.x, target.y) < 1.2:
                target.hp -= 1
                e.state = "gathering"
            else:
                e.step_toward(target.x, target.y)
                e.state = "gathering"
        else:
            if walls and random.random() < 0.4:
                w = random.choice(walls)
                if self.is_passable(w.x + 1, w.y) and not self._occupied(w.x + 1, w.y, 0.5):
                    self.add_entity(EType.WALL, w.x + 1, w.y, "human")
                e.state = "building"
            else:
                angle = random.uniform(0, 2 * math.pi)
                tx = e.x + math.cos(angle) * random.uniform(1, 2)
                ty = e.y + math.sin(angle) * random.uniform(1, 2)
                if self.is_passable(tx, ty):
                    e.step_toward(tx, ty)
                e.state = "idle"

    def _ai_monster(self, e: Entity) -> None:
        nearby = self.get_nearby(e.x, e.y, 8)
        humans = [x for x in nearby if x.is_alive() and x.type == EType.HUMAN]
        lairs = [x for x in nearby if x.is_alive() and x.type == EType.LAIR]

        if self.is_night:
            if humans:
                target = humans[0]
                if e.dist(target.x, target.y) < 1.5:
                    e.state = "attacking"
                else:
                    e.step_toward(target.x, target.y)
                    e.state = "hunting"
        else:
            # Daytime - build lair or wander
            if not lairs:
                angle = random.uniform(0, 2 * math.pi)
                hx, hy = e.home_x or e.x, e.home_y or e.y
                for radius in [1, 2, 3]:
                    bx = hx + math.cos(angle) * radius
                    by = hy + math.sin(angle) * radius
                    if not self._occupied(bx, by, 0.5):
                        self.add_entity(EType.LAIR, bx, by, "monster")
                        break
                e.state = "building_lair"
            else:
                angle = random.uniform(0, 2 * math.pi)
                tx = e.x + math.cos(angle) * 0.5
                ty = e.y + math.sin(angle) * 0.5
                if self.is_passable(tx, ty):
                    e.step_toward(tx, ty)
                e.state = "resting"

    def _ai_animal(self, e: Entity) -> None:
        nearby = self.get_nearby(e.x, e.y, 4)
        threats = [x for x in nearby if x.is_alive() and x.type in (EType.HUMAN, EType.MONSTER)]
        if threats:
            t = threats[0]
            e.step_away(t.x, t.y)
            e.state = "fleeing"
        else:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0.3, 1.0)
            tx = e.x + math.cos(angle) * dist
            ty = e.y + math.sin(angle) * dist
            if self.is_passable(tx, ty):
                e.step_toward(tx, ty)
            e.state = "grazing"

    def _combat_update(self) -> None:
        # Humans attack nearby monsters
        for human in list(self.entities.values()):
            if not (human.is_alive() and human.type == EType.HUMAN):
                continue
            nearby = self.get_nearby(human.x, human.y, 2)
            for target in nearby:
                if target.is_alive() and target.type == EType.MONSTER and human.attack_cd == 0:
                    target.hp -= 1
                    human.attack_cd = 15
                    human.in_combat = True
                    if target.hp <= 0:
                        self.monsters_killed += 1

        # Monsters attack nearby humans
        for monster in list(self.entities.values()):
            if not (monster.is_alive() and monster.type == EType.MONSTER):
                continue
            nearby = self.get_nearby(monster.x, monster.y, 2)
            for target in nearby:
                if target.is_alive() and target.type == EType.HUMAN and monster.attack_cd == 0:
                    target.hp -= 1
                    monster.attack_cd = 15
                    monster.in_combat = True
                    if target.hp <= 0:
                        self.humans_killed += 1

    def get_state(self) -> dict:
        human_counts = {}
        monster_counts = {}
        for e in self.entities.values():
            if e.is_alive():
                if e.team == "human":
                    human_counts[e.type.value] = human_counts.get(e.type.value, 0) + 1
                elif e.team == "monster":
                    monster_counts[e.type.value] = monster_counts.get(e.type.value, 0) + 1

        return {
            "day": self.day_number,
            "phase": self.get_phase(),
            "time": self.get_time_display(),
            "brightness": self.get_brightness(),
            "night_alpha": self.night_alpha,
            "humans": human_counts,
            "monsters": monster_counts,
            "humans_killed": self.humans_killed,
            "monsters_killed": self.monsters_killed,
            "speed": self.speed,
            "paused": self.paused,
        }

    def get_entities(self) -> List[dict]:
        return [e.to_dict() for e in self.entities.values() if e.is_alive()]

    def get_terrain(self) -> dict:
        return {f"{k[0]},{k[1]}": v for k, v in self.terrain.items()}


# ─── Flask Routes ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    return jsonify(world.get_state())


@app.route("/api/entities")
def api_entities():
    return jsonify(world.get_entities())


@app.route("/api/terrain")
def api_terrain():
    return jsonify(world.get_terrain())


@app.route("/api/control", methods=["POST"])
def api_control():
    data = request.json or {}
    action = data.get("action", "")
    if action == "pause":
        world.paused = not world.paused
    elif action == "speed":
        world.speed = float(data.get("speed", 1.0))
    return jsonify({"ok": True})


# ─── Background Tick Thread ──────────────────────────────────────────────────
def game_loop():
    while True:
        now = time.time()
        dt = min(now - world.last_tick, 0.1)
        world.last_tick = now
        world.tick(dt)
        time.sleep(1 / 30)  # 30 game ticks/sec


# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    world = World()
    t = threading.Thread(target=game_loop, daemon=True)
    t.start()
    print("=" * 50)
    print("NanoRealm: Pixel Warfare — Web Edition")
    print("Open http://127.0.0.1:5000 in your browser")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
