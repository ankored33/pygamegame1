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
                    self.target_region_id = None
                    # Return to base
                    if state.player_region_center:
                        bx, by = state.player_region_center
                        self.set_target(float(bx), float(by))
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
                    
                    # 3. Score clusters: (size * 100) + min_dist_to_unit
                    # We want small clusters, but also close ones if sizes are similar
                    best_score = 1e9
                    best_target = None
                    
                    for cluster in clusters:
                        size = len(cluster)
                        
                        # Find closest tile in cluster
                        min_dist = 1e9
                        closest_tile = None
                        for (tx, ty) in cluster:
                            d = (tx - cx)**2 + (ty - cy)**2
                            if d < min_dist:
                                min_dist = d
                                closest_tile = (tx, ty)
                        
                        # Score formula: Prioritize size heavily
                        score = size * 1000 + min_dist
                        
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
