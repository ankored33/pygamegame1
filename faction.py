"""
Faction system for managing multiple powers/factions in the game.
Supports player and AI factions with different types (Empire, Tribe, etc.)
"""
from typing import Set, Dict, List, Optional
from enum import Enum


class FactionType(Enum):
    """Types of factions with different characteristics"""
    EMPIRE = "empire"      # 帝国: 組織的、強力
    TRIBE = "tribe"        # 部族: 機動的、拡張志向
    REPUBLIC = "republic"  # 共和国: 外交的
    HORDE = "horde"        # 遊牧民: 攻撃的、移動重視
    
    @property
    def display_name(self):
        """日本語表示名"""
        names = {
            FactionType.EMPIRE: "帝国",
            FactionType.TRIBE: "部族",
            FactionType.REPUBLIC: "共和国",
            FactionType.HORDE: "遊牧民",
        }
        return names.get(self, "不明")


class Faction:
    """
    Represents a faction (player or AI) in the game.
    
    Attributes:
        faction_id: Unique identifier (0 = player)
        name: Faction name
        faction_type: Type of faction (Empire, Tribe, etc.)
        color: RGB color tuple for territory display
        is_player: Whether this is the player's faction
        territory_mask: Set of (x, y) tiles owned by this faction
        controlled_regions: Set of region IDs controlled
        food: Food resource amount
        gold: Gold resource amount
        units: List of units belonging to this faction
    """
    
    def __init__(
        self,
        faction_id: int,
        name: str,
        faction_type: FactionType,
        color: tuple,
        is_player: bool = False
    ):
        self.faction_id = faction_id
        self.name = name
        self.faction_type = faction_type
        self.color = color  # (R, G, B)
        self.is_player = is_player
        
        # Territory
        self.territory_mask: Set[tuple] = set()  # {(x, y), ...}
        self.controlled_regions: Set[int] = set()  # {region_id, ...}
        
        # Resources
        self.food = 0
        self.gold = 0
        
        # Units
        self.units: List = []  # List of Unit objects
        
        # Diplomacy (for future use)
        self.relations: Dict[int, int] = {}  # {faction_id: relation_value}
        
        # AI controller (for future use)
        self.ai_controller = None
    
    def add_territory(self, x: int, y: int):
        """Add a tile to this faction's territory"""
        self.territory_mask.add((x, y))
    
    def remove_territory(self, x: int, y: int):
        """Remove a tile from this faction's territory"""
        self.territory_mask.discard((x, y))
    
    def owns_tile(self, x: int, y: int) -> bool:
        """Check if this faction owns a specific tile"""
        return (x, y) in self.territory_mask
    
    def add_region(self, region_id: int):
        """Add a region to controlled regions"""
        self.controlled_regions.add(region_id)
    
    def remove_region(self, region_id: int):
        """Remove a region from controlled regions"""
        self.controlled_regions.discard(region_id)
    
    def owns_region(self, region_id: int) -> bool:
        """Check if this faction controls a region"""
        return region_id in self.controlled_regions
    
    def __repr__(self):
        return f"Faction({self.faction_id}, {self.name}, {self.faction_type.display_name}, tiles={len(self.territory_mask)})"
