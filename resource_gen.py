import random
from typing import List, Tuple
import config as C
from state import ResourceNode


def generate_resource_nodes(biome_grid: List[List[str]], region_grid: List[List[int]], 
                           region_seeds: List[Tuple[int, int]]) -> List[ResourceNode]:
    """
    Generate resource nodes based on biome types.
    
    Rules:
    - BEACH: Fish (1%, single)
    - GRASSLAND/SWAMP: Farm (1%, 3-5 cluster, max 1 per region)
    - MOUNTAIN: Gold/Silver (1%, 3-4 cluster)
    - FOREST: Animal (1%, single)
    - Region centers are excluded from resource generation
    
    Max development: 3 (0.1%), 2 (5%), 1 (94.9%)
    """
    nodes = []
    farm_regions = set()  # Track regions that already have farms
    
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            biome = biome_grid[y][x]
            
            # Skip water biomes
            if biome in ("SEA", "LAKE"):
                continue
            
            # Skip region centers
            if (x, y) in region_seeds:
                continue
            
            # Determine max_development
            rand = random.random()
            if rand < C.MAX_DEV_3_RATE:
                max_dev = 3
            elif rand < C.MAX_DEV_3_RATE + C.MAX_DEV_2_RATE:
                max_dev = 2
            else:
                max_dev = 1
            
            # BEACH: Fish
            if biome == "BEACH" and random.random() < C.RESOURCE_SPAWN_RATES["FISH"]:
                nodes.append(ResourceNode(x, y, "FISH", 0, max_dev))
            
            # FOREST: Animal
            elif biome == "FOREST" and random.random() < C.RESOURCE_SPAWN_RATES["ANIMAL"]:
                nodes.append(ResourceNode(x, y, "ANIMAL", 0, max_dev))
            
            # GRASSLAND/SWAMP: Farm
            elif biome in ("GRASSLAND", "SWAMP") and random.random() < C.RESOURCE_SPAWN_RATES["FARM"]:
                region_id = region_grid[y][x]
                if region_id not in farm_regions:
                    farm_regions.add(region_id)
                    # Create farm cluster (can span both GRASSLAND and SWAMP)
                    cluster_size = random.randint(*C.RESOURCE_CLUSTER_SIZES["FARM"])
                    cluster = _create_cluster(x, y, biome_grid, ["GRASSLAND", "SWAMP"], cluster_size)
                    for cx, cy in cluster:
                        # Each tile in cluster gets its own max_dev roll
                        rand = random.random()
                        if rand < C.MAX_DEV_3_RATE:
                            c_max_dev = 3
                        elif rand < C.MAX_DEV_3_RATE + C.MAX_DEV_2_RATE:
                            c_max_dev = 2
                        else:
                            c_max_dev = 1
                        nodes.append(ResourceNode(cx, cy, "FARM", 0, c_max_dev))
            
            # MOUNTAIN: Gold or Silver
            elif biome == "MOUNTAIN" and random.random() < C.RESOURCE_SPAWN_RATES["GOLD"]:
                resource_type = random.choice(["GOLD", "SILVER"])
                cluster_size = random.randint(*C.RESOURCE_CLUSTER_SIZES[resource_type])
                cluster = _create_cluster(x, y, biome_grid, "MOUNTAIN", cluster_size)
                for cx, cy in cluster:
                    # Each tile in cluster gets its own max_dev roll
                    rand = random.random()
                    if rand < C.MAX_DEV_3_RATE:
                        c_max_dev = 3
                    elif rand < C.MAX_DEV_3_RATE + C.MAX_DEV_2_RATE:
                        c_max_dev = 2
                    else:
                        c_max_dev = 1
                    nodes.append(ResourceNode(cx, cy, resource_type, 0, c_max_dev))
    
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

