"""
Color palette for NanoRealm: Pixel Warfare
Each entity type has a unique color identity.
"""

# Entity Colors (R, G, B)
HUMAN     = (34,  255, 85)    # Bright green - the survivors
MONSTER   = (255, 34,  34)    # Crimson red - the hunters
ANIMAL    = (255, 255, 51)    # Golden yellow - prey & resources
TREE      = (0,   140, 0)     # Forest green - wood resource
ROCK      = (128, 128, 128)   # Stone gray - stone resource
WALL      = (139, 90,  43)    # Saddle brown - structure
DOOR      = (255, 165, 0)    # Orange - entry point
TORCH     = (255, 140, 0)     # Dark orange - light source
SPAWNER   = (75,  0,   130)   # Indigo - monster origin
GROUND    = (50,  50,  50)    # Dark gray - empty ground
GRASS     = (30,  80,  30)    # Dark green - terrain
WATER     = (30,  90,  200)   # Deep blue - water
LAIR      = (100, 30,  30)    # Dark red - monster territory

# UI Colors
UI_BG        = (15,  15,  20)
UI_PANEL     = (25,  25,  35)
UI_BORDER    = (60,  60,  80)
UI_TEXT      = (220, 220, 220)
UI_ACCENT    = (100, 180, 255)
UI_NIGHT     = (10,  10,  40)
UI_DAY       = (60,  50,  20)

# Day/Night overlay alpha
NIGHT_ALPHA = 120
DUSK_ALPHA  = 60
DAWN_ALPHA  = 30

# Human team warm colors
HUMAN_COLORS = [
    (34,  255, 85),   # Default green
    (50,  220, 120),  # Light green
    (20,  200, 60),   # Dark green
]

# Monster team dark colors
MONSTER_COLORS = [
    (255, 34,  34),   # Default red
    (220, 60,  60),   # Dark red
    (200, 20,  20),   # Blood red
]
