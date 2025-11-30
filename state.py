from dataclasses import dataclass, field
from typing import Optional, Set, Tuple, List
import config as C


@dataclass
class GameState:
    # player / region state
    player_grid_x: int = C.BASE_GRID_WIDTH // 2
    player_grid_y: int = C.BASE_GRID_HEIGHT // 2
    player_region_id: Optional[int] = None
    player_region_mask: Set[Tuple[int, int]] = field(default_factory=set)
    player_region_center: Tuple[int, int] = (0, 0)
    selected_region: Optional[int] = None
    
    # UI state
    confirm_dialog: Optional[dict] = None # {message, on_yes, on_no}

    # screen state
    screen_state: str = "menu"  # menu, loading, game
    loading_frames_remaining: int = 0
    highlight_frames_remaining: int = 0

    # zoom
    zoom_mode: bool = False
    zoom_region_id: Optional[int] = None
    zoom_origin: Tuple[int, int] = (0, 0)
    zoom_bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)

    # world data
    biome_grid: Optional[List[List[str]]] = None
    region_seeds: Optional[List[Tuple[int, int]]] = None
    region_grid: Optional[List[List[int]]] = None
    region_info: Optional[List[dict]] = None
    coast_edge: Optional[str] = None

    # flags
    pending_generate: bool = False
    
    # game loop state
    game_time: float = 0.0
    day: int = 1
    is_paused: bool = True
    game_speed: float = 1.0
    
    # fog of war
    fog_grid: Optional[List[List[bool]]] = None
    fog_surface: Optional[object] = None
    debug_fog_off: bool = False
    
    # rendering cache
    map_surface: Optional[object] = None
    
    # units
    units: List = field(default_factory=list)

