import random
from typing import List, Tuple, Dict, Set
import config as C
from state import ResourceNode


def generate_resource_nodes(biome_grid: List[List[str]], region_grid: List[List[int]], 
                           region_seeds: List[Tuple[int, int]]) -> List[ResourceNode]:
    """
    Generate resource nodes based on RESOURCE_TYPES config.
    This is data-driven - add new resources in config.py without changing this code.
    """
    nodes = []
    region_limits: Dict[str, Set[int]] = {}  # Track region limits per resource type
    
    # Pre-calculate Biome -> [ResourceType] map
    # This avoids iterating all 100 resource types for every tile
    biome_resource_map = {}
    for res_type, res_config in C.RESOURCE_TYPES.items():
        if res_config.get("region_limit"):
            region_limits[res_type] = set()
            
        for biome in res_config["biomes"]:
            if biome not in biome_resource_map:
                biome_resource_map[biome] = []
            biome_resource_map[biome].append((res_type, res_config))
    
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            biome = biome_grid[y][x]
            
            # Skip if no resources defined for this biome
            possible_resources = biome_resource_map.get(biome)
            if not possible_resources:
                continue
            
            # Skip region centers
            if (x, y) in region_seeds:
                continue
            
            # Check applicable resources only
            for res_type, res_config in possible_resources:
                # Check spawn rate
                if random.random() >= res_config["spawn_rate"]:
                    continue
                
                # Check region limit
                region_id = region_grid[y][x]
                if res_config.get("region_limit"):
                    if region_id in region_limits[res_type]:
                        continue  # This region already has this resource
                    region_limits[res_type].add(region_id)
                
                # Determine max_development
                rand = random.random()
                if rand < C.MAX_DEV_3_RATE:
                    max_dev = 3
                elif rand < C.MAX_DEV_3_RATE + C.MAX_DEV_2_RATE:
                    max_dev = 2
                else:
                    max_dev = 1
                
                # Generate resource
                cluster_size = res_config.get("cluster_size")
                if cluster_size is None:
                    # Single tile resource
                    nodes.append(ResourceNode(x, y, res_type, 0, max_dev))
                else:
                    # Cluster resource
                    min_size, max_size = cluster_size
                    size = random.randint(min_size, max_size)
                    cluster = _create_cluster(x, y, biome_grid, res_config["biomes"], size)
                    for cx, cy in cluster:
                        # Each tile in cluster gets its own max_dev roll
                        rand = random.random()
                        if rand < C.MAX_DEV_3_RATE:
                            c_max_dev = 3
                        elif rand < C.MAX_DEV_3_RATE + C.MAX_DEV_2_RATE:
                            c_max_dev = 2
                        else:
                            c_max_dev = 1
                        nodes.append(ResourceNode(cx, cy, res_type, 0, c_max_dev))
                
                # Only one resource per tile, so break after first match
                break
    
    return nodes


def _create_cluster(start_x: int, start_y: int, biome_grid: List[List[str]], 
                    target_biomes, target_size: int) -> List[Tuple[int, int]]:
    """
    Create a cluster of tiles of the same biome(s) starting from (start_x, start_y).
    target_biomes can be a string or list of strings.
    Returns list of (x, y) coordinates.
    """
    # Normalize to list
    if isinstance(target_biomes, str):
        target_biomes = [target_biomes]
    
    cluster = [(start_x, start_y)]
    candidates = []
    
    # Add neighbors of start tile
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        nx, ny = start_x + dx, start_y + dy
        if (0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT and
            biome_grid[ny][nx] in target_biomes):
            candidates.append((nx, ny))
    
    # Grow cluster
    while len(cluster) < target_size and candidates:
        # Pick random candidate
        tile = random.choice(candidates)
        candidates.remove(tile)
        
        if tile not in cluster:
            cluster.append(tile)
            
            # Add neighbors of new tile
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = tile[0] + dx, tile[1] + dy
                if (0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT and
                    biome_grid[ny][nx] in target_biomes and
                    (nx, ny) not in cluster and (nx, ny) not in candidates):
                    candidates.append((nx, ny))
    
    return cluster
