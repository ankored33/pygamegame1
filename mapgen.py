import math
import random
from typing import List, Tuple, Dict
import config as C

# Noise seeds
noise_seed_elev = random.randrange(1_000_000)
noise_seed_humid = random.randrange(1_000_000)
noise_seed_voronoi = random.randrange(1_000_000)
noise_seed_boundary = random.randrange(1_000_000)

# domain warp seeds
warp_seed_x = random.randrange(1_000_000)
warp_seed_y = random.randrange(1_000_000)


def _hash_val(seed: int, ix: int, iy: int) -> float:
    rnd = random.Random(seed + ix * 374761393 + iy * 668265263)
    return rnd.random()


def _smoothstep(t: float) -> float:
    return t * t * (3 - 2 * t)


def value_noise(seed: int, x: float, y: float) -> float:
    x0 = int(x)
    y0 = int(y)
    x1 = x0 + 1
    y1 = y0 + 1
    sx = _smoothstep(x - x0)
    sy = _smoothstep(y - y0)

    n00 = _hash_val(seed, x0, y0)
    n10 = _hash_val(seed, x1, y0)
    n01 = _hash_val(seed, x0, y1)
    n11 = _hash_val(seed, x1, y1)

    ix0 = n00 + (n10 - n00) * sx
    ix1 = n01 + (n11 - n01) * sx
    return ix0 + (ix1 - ix0) * sy


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def fbm(seed: int, x: float, y: float, freq: float, octaves=3, lacunarity=2.0, gain=0.5):
    amp = 1.0
    total = 0.0
    max_total = 0.0
    fx = x * freq
    fy = y * freq
    for _ in range(octaves):
        total += value_noise(seed, fx, fy) * amp
        max_total += amp
        amp *= gain
        fx *= lacunarity
        fy *= lacunarity
    return clamp01(total / max_total)


def classify_biome(elev: float, humid: float, jitter: float = 0.0) -> str:
    if elev < 0.32:
        return "LAKE"
    if elev > 0.85:
        return "ALPINE"
    if elev > 0.70:
        return "MOUNTAIN"
    if humid > 0.78 + jitter and elev < 0.55:
        return "SWAMP"
    if humid > 0.62:
        return "FOREST"
    if humid > 0.45:
        return "GRASSLAND"
    # Low humidity = arid
    if humid < 0.30:
        return "ARID"
    return "GRASSLAND"


def generate_biome_map(elev_freq=C.elev_freq, humid_freq=C.humid_freq):
    # Generate new seeds for each map generation
    noise_seed_elev = random.randrange(1_000_000)
    noise_seed_humid = random.randrange(1_000_000)
    noise_seed_boundary = random.randrange(1_000_000)
    warp_seed_x = random.randrange(1_000_000)
    warp_seed_y = random.randrange(1_000_000)

    biome_grid: List[List[str]] = []
    for y in range(C.BASE_GRID_HEIGHT):
        row_b = []
        for x in range(C.BASE_GRID_WIDTH):
            wx = value_noise(warp_seed_x, x * C.warp_freq, y * C.warp_freq) * C.warp_amp
            wy = value_noise(warp_seed_y, x * C.warp_freq, y * C.warp_freq) * C.warp_amp
            sx = x + wx
            sy = y + wy
            e = fbm(noise_seed_elev, sx, sy, elev_freq, octaves=4, gain=0.55)
            h = fbm(noise_seed_humid, sx + 1000, sy - 500, humid_freq, octaves=3, gain=0.6)
            swamp_jitter = (value_noise(noise_seed_boundary, x * 0.25, y * 0.25) - 0.5) * 0.15
            row_b.append(classify_biome(e, h, swamp_jitter))
        biome_grid.append(row_b)
    
    # Store boundary seed for sea generation use
    # Force one edge to SEA with variable width and jaggedness
    edge_side = random.choice(["top", "bottom", "left", "right"])
    sea_width = random.randint(15, 45)
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if edge_side == "top":
                dist = y
            elif edge_side == "bottom":
                dist = C.BASE_GRID_HEIGHT - 1 - y
            elif edge_side == "left":
                dist = x
            else:
                dist = C.BASE_GRID_WIDTH - 1 - x
            n1 = (value_noise(noise_seed_boundary, x * C.SEA_JITTER_FREQ, y * C.SEA_JITTER_FREQ) - 0.5) * C.SEA_JITTER_AMP
            n2 = (value_noise(noise_seed_boundary + 999, x * C.SEA_JITTER_FREQ * 0.4, y * C.SEA_JITTER_FREQ * 0.4) - 0.5) * (C.SEA_JITTER_AMP * 0.6)
            jitter = int(n1 + n2)
            if dist <= sea_width + jitter:
                biome_grid[y][x] = "SEA"

    # Merge lakes touching sea into sea (iterate until stable)
    changed = True
    while changed:
        changed = False
        for y in range(C.BASE_GRID_HEIGHT):
            for x in range(C.BASE_GRID_WIDTH):
                if biome_grid[y][x] != "LAKE":
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                        if biome_grid[ny][nx] == "SEA":
                            biome_grid[y][x] = "SEA"
                            changed = True
                            break

    # Convert isolated SEA components (not touching border) to LAKE
    visited = [[False for _ in range(C.BASE_GRID_WIDTH)] for _ in range(C.BASE_GRID_HEIGHT)]
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if visited[y][x] or biome_grid[y][x] != "SEA":
                continue
            stack = [(x, y)]
            comp = []
            touches_border = False
            while stack:
                cx, cy = stack.pop()
                if visited[cy][cx] or biome_grid[cy][cx] != "SEA":
                    continue
                visited[cy][cx] = True
                comp.append((cx, cy))
                if cx == 0 or cy == 0 or cx == C.BASE_GRID_WIDTH - 1 or cy == C.BASE_GRID_HEIGHT - 1:
                    touches_border = True
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                        if not visited[ny][nx] and biome_grid[ny][nx] == "SEA":
                            stack.append((nx, ny))
            if not touches_border:
                for cx, cy in comp:
                    biome_grid[cy][cx] = "LAKE"

    def is_water(nx, ny):
        return 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT and biome_grid[ny][nx] in ("SEA", "LAKE")

    # Beach pass
    original_biome = [row[:] for row in biome_grid]
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if biome_grid[y][x] in ("SEA", "LAKE"):
                continue
            neighbors = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
            if any(is_water(nx, ny) for nx, ny in neighbors):
                biome_grid[y][x] = "BEACH"

    # Beach expansion (30% chance to extend 1 tile)
    current_beaches = []
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if biome_grid[y][x] == "BEACH":
                current_beaches.append((x, y))
    
    for bx, by in current_beaches:
        # Check neighbors
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = bx + dx, by + dy
            if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                if biome_grid[ny][nx] not in ("SEA", "LAKE", "BEACH"):
                    if random.random() < 0.3:
                        biome_grid[ny][nx] = "BEACH"

    # ensure orthogonal beaches
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if biome_grid[y][x] not in ("SEA", "LAKE"):
                continue
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    if biome_grid[ny][nx] == "BEACH":
                        ox = x + dx
                        oy = y
                        if 0 <= ox < C.BASE_GRID_WIDTH and 0 <= oy < C.BASE_GRID_HEIGHT:
                            if biome_grid[oy][ox] not in ("SEA", "LAKE"):
                                biome_grid[oy][ox] = "BEACH"
                        ox = x
                        oy = y + dy
                        if 0 <= ox < C.BASE_GRID_WIDTH and 0 <= oy < C.BASE_GRID_HEIGHT:
                            if biome_grid[oy][ox] not in ("SEA", "LAKE"):
                                biome_grid[oy][ox] = "BEACH"

    # coastal non-beach patches
    coastal_land = []
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if biome_grid[y][x] == "BEACH":
                if is_water(x - 1, y) or is_water(x + 1, y) or is_water(x, y - 1) or is_water(x, y + 1):
                    coastal_land.append((x, y))
    random.shuffle(coastal_land)
    patch_count = min(8, len(coastal_land) // 20)
    for _ in range(patch_count):
        if not coastal_land:
            break
        sx, sy = coastal_land.pop()
        target = random.randint(4, 10)
        stack = [(sx, sy)]
        visited_patch = set()
        while stack and target > 0:
            cx, cy = stack.pop()
            if (cx, cy) in visited_patch:
                continue
            visited_patch.add((cx, cy))
            if biome_grid[cy][cx] != "BEACH":
                continue
            base_val = original_biome[cy][cx] if original_biome[cy][cx] not in ("SEA", "LAKE") else "GRASSLAND"
            biome_grid[cy][cx] = base_val
            target -= 1
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    if biome_grid[ny][nx] == "BEACH":
                        stack.append((nx, ny))

    # land smoothing
    smoothed = [row[:] for row in biome_grid]
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if biome_grid[y][x] in ("SEA", "LAKE"):
                continue
            neighbors = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    if biome_grid[ny][nx] not in ("SEA", "LAKE"):
                        neighbors.append(biome_grid[ny][nx])
            if neighbors:
                majority = max(set(neighbors), key=neighbors.count)
                smoothed[y][x] = majority
    
    # Volcano generation - must have exactly 1 volcano per map
    # Strategy: Find the ALPINE tile with the most ALPINE neighbors.
    # If no ALPINE, find MOUNTAIN with most MOUNTAIN neighbors, etc.
    
    candidates = []
    # Collect all land tiles with their biome and neighbor stats
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if smoothed[y][x] in ("SEA", "LAKE"):
                continue
            
            my_biome = smoothed[y][x]
            alpine_neighbors = 0
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    if smoothed[ny][nx] == "ALPINE":
                        alpine_neighbors += 1
            
            candidates.append({
                "pos": (x, y),
                "biome": my_biome,
                "alpine_neighbors": alpine_neighbors
            })
    
    if candidates:
        # Sort candidates:
        # Priority 1: Is ALPINE
        # Priority 2: Number of ALPINE neighbors (descending)
        # Priority 3: Is MOUNTAIN
        def sort_key(c):
            is_alpine = 1 if c["biome"] == "ALPINE" else 0
            is_mountain = 1 if c["biome"] == "MOUNTAIN" else 0
            return (is_alpine, c["alpine_neighbors"], is_mountain)
        
        candidates.sort(key=sort_key, reverse=True)
        
        # Pick the best candidate
        best = candidates[0]
        vx, vy = best["pos"]
        
        # Set Volcano
        smoothed[vy][vx] = "VOLCANO"
        
        # Enforce Alpine surroundings
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = vx + dx, vy + dy
            if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                # Don't overwrite water if we can help it? 
                # The user said "surrounded by Alpine", implying land.
                # If it's near water, we should probably turn water into Alpine to ensure the condition.
                smoothed[ny][nx] = "ALPINE"
    
    return smoothed, edge_side


def find_coastal_land(biome_grid):
    candidates = []
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if biome_grid[y][x] in ("SEA", "LAKE"):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    if biome_grid[ny][nx] == "SEA":
                        candidates.append((x, y))
                        break
    return candidates


def choose_player_start(biome_grid, edge_side):
    coastal = find_coastal_land(biome_grid)
    if coastal:
        return random.choice(coastal)
    land = [(x, y) for y in range(C.BASE_GRID_HEIGHT) for x in range(C.BASE_GRID_WIDTH) if biome_grid[y][x] not in ("SEA", "LAKE")]
    if land:
        return random.choice(land)
    return C.BASE_GRID_WIDTH // 2, C.BASE_GRID_HEIGHT // 2


def build_player_region_mask(biome_grid, start_x, start_y, edge_side, target_min=20, target_max=30):
    target = random.randint(target_min, target_max)
    visited = set()
    queue = [(start_x, start_y)]
    mask = set()
    neighbors = []
    while queue and len(mask) < target:
        x, y = queue.pop(0)
        if (x, y) in visited:
            continue
        visited.add((x, y))
        if biome_grid[y][x] in ("SEA", "LAKE"):
            continue
        mask.add((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                if (nx, ny) not in visited and biome_grid[ny][nx] not in ("SEA", "LAKE"):
                    queue.append((nx, ny))
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    if biome_grid[ny][nx] not in ("SEA", "LAKE"):
                        neighbors.append((nx, ny))
    while len(mask) < target and neighbors:
        nx, ny = neighbors.pop(random.randrange(len(neighbors)))
        if (nx, ny) not in mask and biome_grid[ny][nx] not in ("SEA", "LAKE"):
            mask.add((nx, ny))
    if len(mask) < target:
        extra = []
        for y in range(C.BASE_GRID_HEIGHT):
            for x in range(C.BASE_GRID_WIDTH):
                if biome_grid[y][x] in ("SEA", "LAKE") or (x, y) in mask:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                    nx, ny = x + dx, y + dy
                    if (nx, ny) in mask:
                        extra.append((x, y))
                        break
        random.shuffle(extra)
        for x, y in extra:
            if len(mask) >= target:
                break
            mask.add((x, y))

    def has_coast(m):
        for (mx, my) in m:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = mx + dx, my + dy
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    if biome_grid[ny][nx] == "SEA":
                        return True
        return False

    if not has_coast(mask):
        coastal = find_coastal_land(biome_grid)
        if coastal:
            sx, sy = random.choice(coastal)
            return build_player_region_mask(biome_grid, sx, sy, edge_side, target_min, target_max)
    return mask


def pick_region_seeds(biome_grid, player_seed):
    seeds = []
    seed_count = random.randint(C.REGION_SEED_MIN, C.REGION_SEED_MAX)
    seeds.append(player_seed)
    seen = {player_seed}
    attempts = seed_count * 30
    while len(seeds) < seed_count and attempts > 0:
        attempts -= 1
        x = random.randrange(C.BASE_GRID_WIDTH)
        y = random.randrange(C.BASE_GRID_HEIGHT)
        if biome_grid[y][x] in ("SEA", "LAKE") or (x, y) in seen:
            continue
        too_close = False
        for sx, sy in seeds:
            if max(abs(sx - x), abs(sy - y)) < 3:
                too_close = True
                break
        if too_close:
            continue
        seeds.append((x, y))
        seen.add((x, y))
    return seeds


def assign_regions(biome_grid, seeds):
    region_grid = [[-1 for _ in range(C.BASE_GRID_WIDTH)] for _ in range(C.BASE_GRID_HEIGHT)]
    
    # Voronoi generation
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if biome_grid[y][x] in ("SEA", "LAKE"):
                continue
            best_id = None
            best_dist = 1e9
            noise_jitter = value_noise(noise_seed_voronoi, x * C.voronoi_freq, y * C.voronoi_freq) * C.REGION_NOISE_WEIGHT
            for idx, (sx, sy) in enumerate(seeds):
                dx = sx - x
                dy = sy - y
                d = math.sqrt(dx * dx + dy * dy) + noise_jitter
                if d < best_dist:
                    best_dist = d
                    best_id = idx
            region_grid[y][x] = best_id
            
    # Smoothing
    smoothed = [row[:] for row in region_grid]
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if biome_grid[y][x] in ("SEA", "LAKE"):
                continue
            neighbors = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    if biome_grid[ny][nx] not in ("SEA", "LAKE"):
                        neighbors.append(region_grid[ny][nx])
            if neighbors:
                majority = max(set(neighbors), key=neighbors.count)
                smoothed[y][x] = majority
    
    # Post-process to fix disjoint regions
    smoothed, seeds = process_disjoint_regions(smoothed, biome_grid, seeds)
    
    # Merge small isolated regions (enclaves)
    smoothed, seeds = merge_small_isolated_regions(smoothed, biome_grid, seeds)
    
    return smoothed, seeds


def merge_small_isolated_regions(region_grid, biome_grid, seeds):
    """
    Merge small regions (<= 30 tiles) into the nearest land region.
    Player region (ID=0) is never merged.
    """
    height = len(region_grid)
    width = len(region_grid[0])
    threshold = 30
    
    # 1. Identify regions and their properties
    region_stats = {} # rid -> {tiles: [], neighbors: set()}
    
    for y in range(height):
        for x in range(width):
            rid = region_grid[y][x]
            if rid == -1: continue
            
            if rid not in region_stats:
                region_stats[rid] = {"tiles": [], "neighbors": set()}
            
            region_stats[rid]["tiles"].append((x, y))
            
            # Check neighbors
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    n_rid = region_grid[ny][nx]
                    if n_rid != -1 and n_rid != rid:
                        region_stats[rid]["neighbors"].add(n_rid)
    
    # 2. Find candidates for merging (all small regions except player region)
    merge_candidates = []
    for rid, stats in region_stats.items():
        if rid == 0:  # Skip player region
            continue
        if len(stats["tiles"]) <= threshold:
            merge_candidates.append(rid)
            
    # 3. Merge candidates
    for rid in merge_candidates:
        # First try to merge with direct neighbors
        neighbors = region_stats[rid]["neighbors"]
        if neighbors:
            # Choose the largest neighbor
            best_neighbor = None
            best_size = 0
            for n_rid in neighbors:
                if n_rid in region_stats:
                    size = len(region_stats[n_rid]["tiles"])
                    if size > best_size:
                        best_size = size
                        best_neighbor = n_rid
            
            if best_neighbor is not None:
                # Merge into best neighbor
                for tx, ty in region_stats[rid]["tiles"]:
                    region_grid[ty][tx] = best_neighbor
                continue
        
        # If no direct neighbors, find nearest land tile of another region using BFS
        queue = list(region_stats[rid]["tiles"])
        visited = set(queue)
        found = False
        nearest_rid = -1
        
        idx = 0
        while idx < len(queue):
            cx, cy = queue[idx]
            idx += 1
            
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if (nx, ny) in visited:
                        continue
                    
                    visited.add((nx, ny))
                    target_rid = region_grid[ny][nx]
                    
                    if target_rid != -1 and target_rid != rid:
                        # Found nearest land!
                        nearest_rid = target_rid
                        found = True
                        break
                    
                    queue.append((nx, ny))
            if found:
                break
        
        if found and nearest_rid != -1:
            # Merge
            for tx, ty in region_stats[rid]["tiles"]:
                region_grid[ty][tx] = nearest_rid
                
    return region_grid, seeds



def process_disjoint_regions(region_grid, biome_grid, seeds):
    """
    Identify disjoint components of each region.
    - Largest component keeps the ID.
    - Small components (< threshold) are merged into neighbors.
    - Large components (>= threshold) get a new ID.
    """
    height = len(region_grid)
    width = len(region_grid[0])
    threshold = 10 # Minimum size to be a separate region
    
    # We need to handle IDs dynamically as we add new ones
    # First, let's map current IDs to their cells
    # But strictly speaking, we should iterate over the grid to find connected components
    
    visited = [[False for _ in range(width)] for _ in range(height)]
    new_region_grid = [row[:] for row in region_grid]
    
    # We will process region by region? No, just find all components
    components = [] # List of (rid, [(x, y), ...])
    
    for y in range(height):
        for x in range(width):
            if biome_grid[y][x] in ("SEA", "LAKE") or visited[y][x]:
                continue
            
            rid = region_grid[y][x]
            if rid == -1: continue
            
            # BFS to find component
            comp = []
            queue = [(x, y)]
            visited[y][x] = True
            comp.append((x, y))
            
            idx = 0
            while idx < len(queue):
                cx, cy = queue[idx]
                idx += 1
                
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if not visited[ny][nx] and region_grid[ny][nx] == rid:
                            visited[ny][nx] = True
                            queue.append((nx, ny))
                            comp.append((nx, ny))
            
            components.append((rid, comp))
            
    # Group components by original RID
    regions_comps = {}
    for rid, comp in components:
        if rid not in regions_comps:
            regions_comps[rid] = []
        regions_comps[rid].append(comp)
        
    next_id = len(seeds)
    
    for rid, comps in regions_comps.items():
        # Sort by size, descending
        comps.sort(key=len, reverse=True)
        
        # Largest component keeps the ID
        # (We don't need to do anything for the first one as new_region_grid already has rid)
        
        # Process other components
        for i in range(1, len(comps)):
            comp = comps[i]
            if len(comp) >= threshold:
                # Assign new ID
                new_id = next_id
                next_id += 1
                
                # Calculate new seed (centroid)
                sx = sum(p[0] for p in comp) // len(comp)
                sy = sum(p[1] for p in comp) // len(comp)
                seeds.append((sx, sy))
                
                for cx, cy in comp:
                    new_region_grid[cy][cx] = new_id
            else:
                # Merge into neighbor
                # Find most frequent neighbor ID
                neighbor_ids = []
                for cx, cy in comp:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            n_rid = new_region_grid[ny][nx] # Use new grid to chain merges? Or old?
                            # Use new_region_grid to allow merging into already processed regions?
                            # But risky if we merge into something that is about to change.
                            # Let's use region_grid for neighbor lookup, but exclude own rid
                            n_rid_old = region_grid[ny][nx]
                            if n_rid_old != -1 and n_rid_old != rid:
                                neighbor_ids.append(n_rid_old)
                
                if neighbor_ids:
                    target_rid = max(set(neighbor_ids), key=neighbor_ids.count)
                    for cx, cy in comp:
                        new_region_grid[cy][cx] = target_rid
                else:
                    # No neighbors? (Isolated small island)
                    # Keep original ID or make new? Let's make new to be safe, or keep original.
                    # If we keep original, it remains a disjoint part (which we wanted to avoid).
                    # But if it's an island, maybe it's fine?
                    # The user said "disjointed regions ... separated by water".
                    # If it's an island, it IS separated by water.
                    # Maybe "disjointed" meant "part of Red region is here, and another part is way over there".
                    # So if it's an island, it should probably be a NEW region.
                    new_id = next_id
                    next_id += 1
                    sx = sum(p[0] for p in comp) // len(comp)
                    sy = sum(p[1] for p in comp) // len(comp)
                    seeds.append((sx, sy))
                    for cx, cy in comp:
                        new_region_grid[cy][cx] = new_id

    return new_region_grid, seeds


def summarize_regions(biome_grid, region_grid, seeds):
    region_info = []
    counts = []
    for _ in range(len(seeds)):
        region_info.append({"biome": None, "resources": {}, "dangers": {}, "size": 0, "seed": None, "distribution": {}, "neighbors": set()})
        counts.append({})

    for idx, seed in enumerate(seeds):
        region_info[idx]["seed"] = seed

    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            rid = region_grid[y][x]
            if rid is None or rid < 0 or rid >= len(region_info):
                continue
            b = biome_grid[y][x]
            region_info[rid]["size"] += 1
            counts[rid][b] = counts[rid].get(b, 0) + 1
            
            # Check neighbors for adjacency graph
            # Check right and bottom to avoid duplicates (and boundary checks)
            for dx, dy in ((1, 0), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    n_rid = region_grid[ny][nx]
                    if n_rid != -1 and n_rid != rid:
                        region_info[rid]["neighbors"].add(n_rid)
                        region_info[n_rid]["neighbors"].add(rid)

    for rid, info in enumerate(region_info):
        dist = {}
        for biome_name, ct in counts[rid].items():
            if info["size"] > 0:
                dist[biome_name] = round(ct / info["size"] * 100)
        info["distribution"] = dist
    return region_info


def add_water_regions(biome_grid, region_grid, seeds):
    next_id = len(seeds)
    visited = [[False for _ in range(C.BASE_GRID_WIDTH)] for _ in range(C.BASE_GRID_HEIGHT)]
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if visited[y][x] or region_grid[y][x] != -1:
                continue
            if biome_grid[y][x] not in ("SEA", "LAKE"):
                continue
            stack = [(x, y)]
            comp = []
            while stack:
                cx, cy = stack.pop()
                if visited[cy][cx] or region_grid[cy][cx] != -1:
                    continue
                if biome_grid[cy][cx] not in ("SEA", "LAKE"):
                    continue
                visited[cy][cx] = True
                comp.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                        if not visited[ny][nx]:
                            stack.append((nx, ny))
            if comp:
                for cx, cy in comp:
                    region_grid[cy][cx] = next_id
                avg_x = sum(p[0] for p in comp) // len(comp)
                avg_y = sum(p[1] for p in comp) // len(comp)
                seeds.append((avg_x, avg_y))
                next_id += 1
    return region_grid, seeds


def jitter_point(x: float, y: float):
    jx = (value_noise(noise_seed_boundary, x * C.BOUNDARY_NOISE_FREQ, y * C.BOUNDARY_NOISE_FREQ) - 0.5) * C.BOUNDARY_NOISE_WEIGHT
    jy = (value_noise(noise_seed_boundary + 12345, x * C.BOUNDARY_NOISE_FREQ, y * C.BOUNDARY_NOISE_FREQ) - 0.5) * C.BOUNDARY_NOISE_WEIGHT
    return x + jx, y + jy

