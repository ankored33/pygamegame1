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
    
    def update(self, game_speed: float):
        """Update unit state (movement, etc)"""
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
