from dataclasses import dataclass, field
from typing import Optional, Set, Tuple, List
import config as C


@dataclass
class ResourceNode:
    x: int
    y: int
    type: str  # "FISH", "FARM", "GOLD", "SILVER", "ANIMAL"
    development: int = 0
    max_development: int = 1  # 1, 2 (5%), or 3 (0.1%)


@dataclass
class GameState:
    # player / region state
    player_grid_x: int = C.BASE_GRID_WIDTH // 2
    player_grid_y: int = C.BASE_GRID_HEIGHT // 2
    player_region_id: Optional[int] = None
    player_region_mask: Set[Tuple[int, int]] = field(default_factory=set)
    player_region_center: Tuple[int, int] = (0, 0)
    selected_region: Optional[int] = None
    adjacent_regions_cache: Optional[Set[int]] = None  # Cache of regions adjacent to player region
    
    # resources
    food: int = 0
    gold: int = 0
    
    # UI state
    confirm_dialog: Optional[dict] = None # {message, on_yes, on_no}

    # screen state
    screen_state: str = "menu"  # menu, loading, game
    loading_frames_remaining: int = 0

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
    resource_nodes: List[ResourceNode] = field(default_factory=list)
    resource_map: dict = field(default_factory=dict)  # (x, y) -> ResourceNode for O(1) lookup

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
    zoom_full_map_cache: Optional[object] = None  # Full map at zoom scale (no fog)
    zoom_fog_layer: Optional[object] = None  # Fog overlay at zoom scale
    selected_region_overlay_cache: Optional[object] = None  # Cached overlay for selected region (world view)
    selected_region_overlay_zoom_cache: Optional[object] = None  # Cached overlay for selected region (zoom view)
    
    # units
    units: List = field(default_factory=list)
    
    # territory expansion (conquistador)
    territory_expansion_regions: dict = field(default_factory=dict)  # {region_id: {"tiles": set(), "progress": int}}
    
    # double-click detection
    last_click_time: float = 0.0
    last_click_pos: Tuple[int, int] = (0, 0)
    DOUBLE_CLICK_TIME: float = 0.3  # seconds
    
    # menu state
    use_debug_map: bool = C.DEBUG_LOAD_MAP
    
    # map gen parameters
    gen_elev_freq: float = C.elev_freq
    gen_humid_freq: float = C.humid_freq
    
    # =========================
    # Multi-faction system
    # =========================
    factions: List = field(default_factory=list)  # List of Faction objects
    player_faction_id: int = 0  # ID of the player's faction (always 0)
    
    # Backward compatibility properties
    @property
    def player_region_mask_compat(self):
        """Backward compatibility: returns player faction's territory"""
        if self.factions and len(self.factions) > self.player_faction_id:
            return self.factions[self.player_faction_id].territory_mask
        return self.player_region_mask
    
    def get_faction_at_tile(self, x: int, y: int):
        """Get the faction that owns a specific tile, or None"""
        for faction in self.factions:
            if faction.owns_tile(x, y):
                return faction
        return None

    def __getstate__(self):
        """Custom pickling to exclude surfaces and callbacks"""
        state = self.__dict__.copy()
        
        # Exclude Surfaces and other non-picklable objects
        # We set them to None explicitly in the copied dict so they aren't saved
        keys_to_exclude = [
            'map_surface', 
            'fog_surface', 
            'zoom_full_map_cache', 
            'zoom_fog_layer', 
            'selected_region_overlay_cache',
            'selected_region_overlay_zoom_cache'
        ]
        
        for key in keys_to_exclude:
            if key in state:
                state[key] = None
                
        # Handle confirm_dialog which might contain lambdas
        if 'confirm_dialog' in state:
            state['confirm_dialog'] = None

        return state

    def __setstate__(self, state):
        """Custom unpickling to restore state"""
        self.__dict__.update(state)
        
        # Ensure excluded keys are at least None (though they should be from getstate)
        # This is also a good place to reset any temporary caches
        self.map_surface = None
        self.fog_surface = None
        self.zoom_full_map_cache = None
        self.zoom_fog_layer = None
        self.selected_region_overlay_cache = None
        self.selected_region_overlay_zoom_cache = None
        self.confirm_dialog = None
        
        # Reset ephemeral caches
        self.adjacent_regions_cache = None
        if hasattr(self, '_region_tiles_cache'):
            delattr(self, '_region_tiles_cache')
        if hasattr(self, '_cached_selected_region_id'):
            delattr(self, '_cached_selected_region_id')
        if hasattr(self, '_cached_selected_region_id_zoom'):
            delattr(self, '_cached_selected_region_id_zoom')
        if hasattr(self, '_cached_debug_info'):
            delattr(self, '_cached_debug_info')
            
        # Rebuild resource_map if missing (backward compatibility)
        if hasattr(self, 'resource_nodes') and not hasattr(self, 'resource_map'):
            self.resource_map = { (n.x, n.y): n for n in self.resource_nodes }
        elif hasattr(self, 'resource_nodes') and not self.resource_map:
             # Even if attribute exists, might be empty if we just loaded an old save
             # that was "migrated" by pickle loading into default values? 
             # Actually defaults are not applied on unpickle.
             # So we just check if it's empty but nodes exist.
             self.resource_map = { (n.x, n.y): n for n in self.resource_nodes }

