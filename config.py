import pygame

# =========================
# Core settings
# =========================
TOP_BAR_HEIGHT = 32
BASE_GRID_WIDTH = 260  # (1280 - 240) / 4 = 260 tiles
BASE_GRID_HEIGHT = 172  # (720 - 32) / 4 = 172 tiles
TILE_SIZE = 4
INFO_PANEL_WIDTH = 240

SCREEN_WIDTH = INFO_PANEL_WIDTH + BASE_GRID_WIDTH * TILE_SIZE
SCREEN_HEIGHT = BASE_GRID_HEIGHT * TILE_SIZE + TOP_BAR_HEIGHT

# Region / generation settings
REGION_SEED_MIN = 113
REGION_SEED_MAX = 135
REGION_NOISE_WEIGHT = 6.0
BOUNDARY_NOISE_WEIGHT = 2.0
BOUNDARY_NOISE_FREQ = 0.12
LOADING_DELAY_FRAMES = 10

# Debug settings
DEBUG_LOAD_MAP = True  # If True, try to load 'debug_map.pkl' on start instead of generating
DEBUG_MAP_FILE = "debug_map.pkl"
SEA_JITTER_AMP = 30
SEA_JITTER_FREQ = 0.15
HIGHLIGHT_FRAMES = 180
ZOOM_SCALE = 5
ZOOM_MARGIN = 3
# noise frequencies and warp
elev_freq = 0.03
humid_freq = 0.05
voronoi_freq = 0.07
warp_freq = 0.04
warp_amp = 6.0

# Audio
BGM_MENU = "assets/bgm/bgm_menu.ogg"
BGM_GAME = "assets/bgm/bgm_game.ogg"

# Colors
WHITE = (255, 255, 255)
GREY = (80, 80, 80)
DARK_GREY = (40, 40, 40)
BLACK = (0, 0, 0)

# Border colors
REGION_BORDER_COLOR = (100, 100, 100)  # Gray for region boundaries
FACTION_BORDER_COLOR = (255, 105, 180) # Pink for faction boundaries
ZOOM_REGION_BORDER_COLOR = (255, 220, 0)  # Yellow for region boundaries in zoom mode

# Territory overlay
PLAYER_TERRITORY_OVERLAY_COLOR = (255, 105, 180, 80)  # Pink with alpha for player territory

BIOME_COLORS = {
    "SEA": (30, 80, 180),
    "LAKE": (120, 200, 255),
    "BEACH": (230, 220, 170),
    "GRASSLAND": (90, 180, 70),
    "FOREST": (30, 120, 50),
    "MOUNTAIN": (120, 110, 100),
    "ALPINE": (230, 240, 250),
    "SWAMP": (70, 120, 90),
    "ARID": (220, 180, 100),
    "VOLCANO": (200, 50, 0),  # Reddish for volcano
}

BIOME_NAMES = {
    "SEA": "海",
    "LAKE": "湖",
    "BEACH": "砂浜",
    "GRASSLAND": "草原",
    "FOREST": "森",
    "MOUNTAIN": "山岳",
    "ALPINE": "高山",
    "SWAMP": "湿地",
    "ARID": "荒れ地",
    "VOLCANO": "火口",
}

# Resource generation settings (data-driven)
# Each resource type can be defined with:
# - biomes: list of biomes where it can spawn
# - spawn_rate: probability of spawning (0.0-1.0)
# - cluster_size: (min, max) for cluster resources, or None for single tile
# - produces: "food" or "gold"
# - region_limit: max clusters per region (None = unlimited)

RESOURCE_TYPES = {
    "FISH": {
        "display_name": "魚",
        "biomes": ["BEACH"],
        "spawn_rate": 0.04,
        "cluster_size": None,  # Single tile
        "produces": "food",
        "region_limit": None,
    },
    "ANIMAL": {
        "display_name": "動物",
        "biomes": ["FOREST"],
        "spawn_rate": 0.01,
        "cluster_size": None,
        "produces": "food",
        "region_limit": None,
    },
    "FARM": {
        "display_name": "耕作地",
        "biomes": ["GRASSLAND", "SWAMP"],
        "spawn_rate": 0.01,
        "cluster_size": (3, 5),
        "produces": "food",
        "region_limit": 1,  # Max 1 farm cluster per region
    },
    "GOLD": {
        "display_name": "金",
        "biomes": ["MOUNTAIN"],
        "spawn_rate": 0.01,
        "cluster_size": (3, 4),
        "produces": "gold",
        "region_limit": None,
    },
    "SILVER": {
        "display_name": "銀",
        "biomes": ["MOUNTAIN"],
        "spawn_rate": 0.01,
        "cluster_size": (3, 4),
        "produces": "gold",
        "region_limit": None,
    },
}

# Max development probabilities
MAX_DEV_3_RATE = 0.001  # 0.1%
MAX_DEV_2_RATE = 0.05   # 5%
# MAX_DEV_1 is the remainder (94.9%)


# Unit Settings
UNIT_COLORS = {
    "explorer": (100, 200, 255),      # Light Blue
    "colonist": (100, 255, 100),      # Light Green
    "diplomat": (255, 100, 255),      # Pink
    "conquistador": (255, 100, 100),  # Light Red
}

UNIT_NAMES = {
    "explorer": "探検家",
    "colonist": "開拓者",
    "diplomat": "外交官",
    "conquistador": "征服者",
}


