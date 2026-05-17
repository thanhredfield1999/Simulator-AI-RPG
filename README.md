# NanoRealm: Pixel Warfare

A pixel simulation game where every pixel has its own AI. Two factions — Humans and Monsters — build, gather, and battle in an endless cycle of day and night.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the game
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrow Keys | Pan camera |
| Mouse Wheel | Zoom in/out |
| 1 / 2 / 3 | Speed 1x / 2x / 5x |
| M | Toggle minimap |
| G | Toggle grid overlay |
| ESC | Pause / Quit |

## Gameplay

- **Day (60s)**: Humans gather resources and build walls. Monsters rest in their lairs.
- **Night (60s)**: Monsters swarm out to hunt. Humans defend their homes.
- Watch the ecosystem evolve — each pixel thinks for itself.

## Project Structure

```
pixel-warfare/
├── main.py       # Entry point & game loop
├── core.py       # Grid, camera, tick system
├── entities.py   # All entity types & colors
├── ai.py         # AI brain for each entity type
├── world.py      # Day-night cycle
├── combat.py     # Combat & death/respawn
├── ui.py         # HUD, minimap, legend
├── colors.py     # Color palette
└── sprites.py    # Drawing utilities
```

## Requirements

- Python 3.10+
- pygame 2.5+
