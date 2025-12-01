import pygame

# =========================
# Core settings
# =========================
BASE_GRID_WIDTH = 260  # (1280 - 240) / 4 = 260 tiles
BASE_GRID_HEIGHT = 180  # 720 / 4 = 180 tiles
TILE_SIZE = 4
INFO_PANEL_WIDTH = 240

SCREEN_WIDTH = INFO_PANEL_WIDTH + BASE_GRID_WIDTH * TILE_SIZE
SCREEN_HEIGHT = BASE_GRID_HEIGHT * TILE_SIZE

# Region / generation settings
REGION_SEED_MIN = 113  # 94 * 1.2
REGION_SEED_MAX = 150  # 125 * 1.2
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
BGM_MENU = "assets/bgm_menu.ogg"
BGM_GAME = "assets/bgm_game.ogg"

# Colors
WHITE = (255, 255, 255)
GREY = (80, 80, 80)
DARK_GREY = (40, 40, 40)
BLACK = (0, 0, 0)

# Border colors
REGION_BORDER_COLOR = (100, 100, 100)  # Gray for region boundaries
FACTION_BORDER_COLOR = (255, 105, 180) # Pink for faction boundaries
ZOOM_REGION_BORDER_COLOR = (255, 220, 0)  # Yellow for region boundaries in zoom mode

BIOME_COLORS = {
    "SEA": (30, 80, 180),
    "LAKE": (120, 200, 255),
    "BEACH": (230, 220, 170),
    "GRASSLAND": (90, 180, 70),
    "FOREST": (30, 120, 50),
    "MOUNTAIN": (120, 110, 100),
    "SNOW": (230, 240, 250),
    "SWAMP": (70, 120, 90),
}

BIOME_NAMES = {
    "SEA": "海",
    "LAKE": "湖",
    "BEACH": "砂浜",
    "GRASSLAND": "草原",
    "FOREST": "森",
    "MOUNTAIN": "山岳",
    "SNOW": "雪原",
    "SWAMP": "湿地",
}

BIOME_RESOURCE_WEIGHTS = {
    "SEA": {"魚": 3},
    "LAKE": {"魚": 2},
    "BEACH": {"魚": 2},
    "GRASSLAND": {"食料": 3},
    "FOREST": {"木材": 3, "狩猟": 2},
    "MOUNTAIN": {"鉱石": 3, "鉄": 2},
    "SNOW": {"希少資源": 1},
    "SWAMP": {"薬草": 3},
}

BIOME_DANGER_WEIGHTS = {
    "SEA": {"嵐": 3, "移動制限": 3},
    "LAKE": {"移動制限": 2},
    "BEACH": {"嵐": 2, "移動制限": 2},
    "GRASSLAND": {"低": 1},
    "FOREST": {"野獣": 2, "道迷い": 1},
    "MOUNTAIN": {"厳しい天候": 3, "通行困難": 3},
    "SNOW": {"低体温": 3, "吹雪": 3},
    "SWAMP": {"病気": 3, "移動制限": 4},
}
