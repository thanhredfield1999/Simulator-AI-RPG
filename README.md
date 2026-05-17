# NanoRealm: Pixel Warfare — Web Edition

A pixel simulation game where every pixel has its own AI brain. Two factions — Humans and Monsters — build, gather, and battle in an endless day/night cycle. Runs in your browser.

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Controls

| Input | Action |
|-------|--------|
| Mouse drag | Pan camera |
| Scroll wheel | Zoom in/out |
| W/A/S/D | Pan camera |
| G | Toggle grid |
| M | Toggle minimap |
| P | Pause / Resume |
| 1x / 2x / 5x buttons | Game speed |

## Gameplay

- **Day (60s)**: Humans gather resources and build walls. Monsters rest in lairs.
- **Night (60s)**: Monsters swarm out to hunt. Humans defend their homes.
- Watch the ecosystem evolve — each pixel thinks for itself.

## Project Structure

```
pixel-warfare/
├── app.py              # Flask server + game logic + AI
├── templates/
│   └── index.html      # HTML5 Canvas frontend
├── requirements.txt    # Flask + Flask-CORS
└── README.md
```

## How It Works

- **Server**: Flask runs Python game logic on a background thread (30 ticks/sec). AI decisions run every 12 ticks. Combat resolves every 6 ticks.
- **Client**: HTML5 Canvas fetches `/api/state`, `/api/entities`, `/api/terrain` at 60fps and renders the world.
- **AI**: Each entity has a Finite State Machine. Humans choose between idle/scouting/gathering/building/defending. Monsters choose between hunting/attacking/building_lair/wandering.
