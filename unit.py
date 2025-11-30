from dataclasses import dataclass
from typing import Optional, Tuple, List
import config as C


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
    
    def update(self, game_speed: float, state=None):
        """Update unit state (movement, etc)"""
        # Automated exploration logic
        if self.target_region_id is not None and state:
            # Check if we have a current movement target
            if self.target_x is None or self.target_y is None:
                # Find fog clusters in target region
                fog_tiles = []
                cx, cy = int(self.x), int(self.y)
                
                # 1. Collect all fogged tiles in region
                for y in range(C.BASE_GRID_HEIGHT):
                    for x in range(C.BASE_GRID_WIDTH):
                        if state.region_grid[y][x] == self.target_region_id:
                            if not state.fog_grid[y][x]:
                                fog_tiles.append((x, y))
                
                if not fog_tiles:
                    # Region fully explored
                    completed_region_id = self.target_region_id
                    self.target_region_id = None
                    
                    # Calculate region center
                    region_tiles = []
                    for y in range(C.BASE_GRID_HEIGHT):
                        for x in range(C.BASE_GRID_WIDTH):
                            if state.region_grid[y][x] == completed_region_id:
                                region_tiles.append((x, y))
                    
                    if region_tiles:
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
                else:
                    # 2. Cluster fog tiles
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
                    
                    # 3. Score clusters with three-tier priority:
                    # 1) Small clusters (size * 1000000)
                    # 2) Nearest to current position (distance from unit)
                    # 3) Close to base (distance from base)
                    best_score = 1e9
                    best_target = None
                    
                    # Get base position
                    base_x, base_y = state.player_region_center if state.player_region_center else (cx, cy)
                    
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
                        
                        # Score formula: 
                        # Priority 1: size (smaller is better)
                        # Priority 2: distance to unit (closer is better)
                        # Priority 3: distance from base (closer is better)
                        score = size * 1000000 + min_dist_to_unit * 100 + min_dist_to_base
                        
                        if score < best_score:
                            best_score = score
                            best_target = closest_tile
                    
                    if best_target:
                        self.set_target(float(best_target[0]), float(best_target[1]))

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
