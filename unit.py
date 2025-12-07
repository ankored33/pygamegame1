from dataclasses import dataclass
from typing import Optional, Tuple, List
import config as C

# Exploration algorithm scoring weights
# These control the priority of different factors when choosing next exploration target
SCORE_WEIGHT_CLUSTER_SIZE = 1000000  # Priority 1: Prefer small fog clusters
SCORE_WEIGHT_DISTANCE_TO_UNIT = 100  # Priority 2: Prefer fog close to current position
SCORE_WEIGHT_DISTANCE_TO_BASE = 1    # Priority 3: Prefer fog close to base (tiebreaker)



@dataclass
class Unit:
    """Base class for all units"""
    x: float
    y: float
    unit_type: str
    selected: bool = False
    
    # Movement
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    move_speed: float = 0.5  # tiles per frame at normal speed
    
    # Vision
    vision_range: int = 3
    
    # Automated Exploration
    target_region_id: Optional[int] = None
    
    def _handle_exploration_completion(self, state, completed_region_id: int, region_tiles: List[Tuple[int, int]]):
        """Handle completion of region exploration"""
        # Calculate region center using cached region_tiles
        if state.region_seeds and completed_region_id < len(state.region_seeds):
            # Use region seed (white tile)
            region_center_x, region_center_y = state.region_seeds[completed_region_id]
        elif region_tiles:
            # Fallback to centroid
            region_center_x = sum(t[0] for t in region_tiles) // len(region_tiles)
            region_center_y = sum(t[1] for t in region_tiles) // len(region_tiles)
        else:
            region_center_x, region_center_y = int(self.x), int(self.y)
        
        # Show completion dialog with choice
        if not state.confirm_dialog:  # Don't overwrite existing dialog
            def return_to_base():
                if state.player_region_center:
                    bx, by = state.player_region_center
                    self.set_target(float(bx), float(by))
            
            def stay_in_region():
                self.set_target(float(region_center_x), float(region_center_y))
            
            state.confirm_dialog = {
                "message": f"リージョン {completed_region_id} の探索が完了しました！\n出発地に戻りますか？",
                "on_yes": return_to_base,
                "on_no": stay_in_region,
                "yes_rect": None,  # Will be set by renderer
                "no_rect": None
            }
    
    def _find_fog_clusters(self, fog_tiles: List[Tuple[int, int]]) -> List[List[Tuple[int, int]]]:
        """Group fog tiles into connected clusters using BFS"""
        clusters = []
        visited = set()
        fog_set = set(fog_tiles)
        
        for start_node in fog_tiles:
            if start_node in visited:
                continue
            
            # BFS to find cluster
            cluster = []
            queue = [start_node]
            visited.add(start_node)
            cluster.append(start_node)
            
            idx = 0
            while idx < len(queue):
                curr = queue[idx]
                idx += 1
                
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = curr[0] + dx, curr[1] + dy
                    if (nx, ny) in fog_set and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
                        cluster.append((nx, ny))
            
            clusters.append(cluster)
        
        return clusters
    
    def _choose_best_exploration_target(self, clusters: List[List[Tuple[int, int]]], state) -> Optional[Tuple[int, int]]:
        """Choose the best fog tile to explore next based on scoring algorithm"""
        cx, cy = int(self.x), int(self.y)
        base_x, base_y = state.player_region_center if state.player_region_center else (cx, cy)
        
        best_score = 1e9
        best_target = None
        
        for cluster in clusters:
            size = len(cluster)
            
            # Find closest tile in cluster to current position
            min_dist_to_unit = 1e9
            closest_tile = None
            min_dist_to_base = 1e9
            
            for (tx, ty) in cluster:
                # Distance to current position
                d_unit = (tx - cx)**2 + (ty - cy)**2
                # Distance to base
                d_base = (tx - base_x)**2 + (ty - base_y)**2
                
                # Pick tile closest to unit, or if tied, closest to base
                if d_unit < min_dist_to_unit or (d_unit == min_dist_to_unit and d_base < min_dist_to_base):
                    min_dist_to_unit = d_unit
                    closest_tile = (tx, ty)
                    min_dist_to_base = d_base
            
            # Score formula using named constants
            score = (size * SCORE_WEIGHT_CLUSTER_SIZE + 
                    min_dist_to_unit * SCORE_WEIGHT_DISTANCE_TO_UNIT + 
                    min_dist_to_base * SCORE_WEIGHT_DISTANCE_TO_BASE)
            
            if score < best_score:
                best_score = score
                best_target = closest_tile
        
        return best_target
    
    def _update_exploration(self, state):
        """Update automated exploration logic"""
        if self.target_x is not None and self.target_y is not None:
            return  # Already have a target
        
        # Build region tiles cache if not exists
        if not hasattr(state, '_region_tiles_cache'):
            state._region_tiles_cache = {}
            for y in range(C.BASE_GRID_HEIGHT):
                for x in range(C.BASE_GRID_WIDTH):
                    rid = state.region_grid[y][x]
                    if rid not in state._region_tiles_cache:
                        state._region_tiles_cache[rid] = []
                    state._region_tiles_cache[rid].append((x, y))
        
        # Get tiles for target region from cache
        region_tiles = state._region_tiles_cache.get(self.target_region_id, [])
        
        # Collect fogged tiles in target region
        fog_tiles = []
        for x, y in region_tiles:
            if not state.fog_grid[y][x]:
                fog_tiles.append((x, y))
        
        if not fog_tiles:
            # Region fully explored
            completed_region_id = self.target_region_id
            if state.region_info and completed_region_id < len(state.region_info):
                state.region_info[completed_region_id]["explored"] = True
            
            self.target_region_id = None
            self._handle_exploration_completion(state, completed_region_id, region_tiles)
        else:
            # Find best target among fog clusters
            clusters = self._find_fog_clusters(fog_tiles)
            best_target = self._choose_best_exploration_target(clusters, state)
            
            if best_target:
                self.set_target(float(best_target[0]), float(best_target[1]))
    
    def update(self, game_speed: float, state=None):
        """Update unit state (movement, etc)"""
        # Automated exploration logic
        if self.target_region_id is not None and state:
            self._update_exploration(state)

        if self.target_x is not None and self.target_y is not None:
            # Move towards target
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = (dx * dx + dy * dy) ** 0.5
            
            if dist < 0.1:
                # Reached target
                self.x = self.target_x
                self.y = self.target_y
                self.target_x = None
                self.target_y = None
            else:
                # Move towards target
                move_dist = self.move_speed * game_speed
                if move_dist > dist:
                    move_dist = dist
                
                self.x += (dx / dist) * move_dist
                self.y += (dy / dist) * move_dist
    
    def set_target(self, tx: float, ty: float):
        """Set movement target"""
        self.target_x = tx
        self.target_y = ty
    
    def get_vision_tiles(self) -> List[Tuple[int, int]]:
        """Get list of tiles this unit can see"""
        tiles = []
        cx = int(self.x)
        cy = int(self.y)
        
        for dy in range(-self.vision_range, self.vision_range + 1):
            for dx in range(-self.vision_range, self.vision_range + 1):
                # Circular vision
                if dx * dx + dy * dy <= self.vision_range * self.vision_range:
                    tx = cx + dx
                    ty = cy + dy
                    if 0 <= tx < C.BASE_GRID_WIDTH and 0 <= ty < C.BASE_GRID_HEIGHT:
                        tiles.append((tx, ty))
        
        return tiles

    def __getstate__(self):
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)


@dataclass
class Explorer(Unit):
    """Explorer unit - reveals fog of war"""
    def __init__(self, x: float, y: float):
        super().__init__(
            x=x,
            y=y,
            unit_type="explorer",
            move_speed=0.01, # 10 tiles per day (1000 ticks)
            vision_range=2
        )


@dataclass
class Colonist(Unit):
    """Colonist unit - establishes settlements"""
    def __init__(self, x: float, y: float):
        super().__init__(
            x=x,
            y=y,
            unit_type="colonist",
            move_speed=0.01,
            vision_range=2
        )


@dataclass
class Diplomat(Unit):
    """Diplomat unit - handles diplomacy"""
    def __init__(self, x: float, y: float):
        super().__init__(
            x=x,
            y=y,
            unit_type="diplomat",
            move_speed=0.01,
            vision_range=2
        )


@dataclass
class Conquistador(Unit):
    """Conquistador unit - military conquest"""
    conquering_region_id: Optional[int] = None
    
    def __init__(self, x: float, y: float):
        super().__init__(
            x=x,
            y=y,
            unit_type="conquistador",
            move_speed=0.01,
            vision_range=2
        )
        self.conquering_region_id = None
