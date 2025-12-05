import pickle
import os
import random
from typing import Optional, Tuple
import config as C
import cache_manager
import mapgen as mg
from state import GameState
from unit import Explorer, Colonist, Diplomat, Conquistador
from resource_gen import generate_resource_nodes

def generate_world(state: GameState):
    state.selected_region = None
    
    # Try to load debug map if enabled
    if state.use_debug_map:
        if load_map_state(state, "debug_map.pkl"):
            print("Loaded debug map state.")
            # Ensure zoom mode is set correctly after load
            state.zoom_mode = True
            state.zoom_region_id = state.player_region_id
            
            # Recalculate zoom origin
            if state.player_region_mask:
                xs = [p[0] for p in state.player_region_mask]
                ys = [p[1] for p in state.player_region_mask]
                cx = (min(xs) + max(xs)) // 2
                cy = (min(ys) + max(ys)) // 2
                
                scale = C.ZOOM_SCALE
                view_w = (C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH) // (C.TILE_SIZE * scale)
                view_h = C.SCREEN_HEIGHT // (C.TILE_SIZE * scale)
                
                ox = cx - view_w // 2
                oy = cy - view_h // 2
                
                ox = max(0, min(C.BASE_GRID_WIDTH - view_w, ox))
                oy = max(0, min(C.BASE_GRID_HEIGHT - view_h, oy))
                
                state.zoom_origin = (ox, oy)
            return

    print("Generating new world...")
    g, edge_side = mg.generate_biome_map(elev_freq=state.gen_elev_freq, humid_freq=state.gen_humid_freq)
    px, py = mg.choose_player_start(g, edge_side)
    state.player_region_mask = mg.build_player_region_mask(g, px, py, edge_side, 20, 30)
    state.player_grid_x, state.player_grid_y = px, py
    seeds = mg.pick_region_seeds(g, (px, py))
    reg_grid, seeds = mg.assign_regions(g, seeds)

    # プレイヤー領域以外のID0を修正
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if reg_grid[y][x] == 0 and (x, y) not in state.player_region_mask:
                best_id = None
                best_dist = 1e9
                for idx, (sx, sy) in enumerate(seeds[1:], start=1):
                    dx = sx - x
                    dy = sy - y
                    d = dx * dx + dy * dy
                    if d < best_dist:
                        best_dist = d
                        best_id = idx
                reg_grid[y][x] = best_id

    for (mx, my) in state.player_region_mask:
        reg_grid[my][mx] = 0

    # Fix seeds that are now inside player region
    # After overriding player mask, some region seeds might be inside player region
    # Move them to their region's centroid
    for idx in range(1, len(seeds)):  # Skip player seed (idx=0)
        sx, sy = seeds[idx]
        
        # Check if seed is in player mask
        if (sx, sy) in state.player_region_mask:
            # Find all tiles of this region (excluding player mask)
            region_tiles = []
            for y in range(C.BASE_GRID_HEIGHT):
                for x in range(C.BASE_GRID_WIDTH):
                    if reg_grid[y][x] == idx and (x, y) not in state.player_region_mask:
                        region_tiles.append((x, y))
            
            if region_tiles:
                # Use find_valid_seed to get best position (centroid or nearest)
                new_sx, new_sy = mg.find_valid_seed(region_tiles)
                seeds[idx] = (new_sx, new_sy)
                print(f"Relocated seed {idx} from ({sx},{sy}) to ({new_sx},{new_sy})")
            else:
                # Region has no tiles outside player mask - this shouldn't happen
                # but if it does, keep the seed where it is
                print(f"Warning: Region {idx} has no tiles outside player mask")

    reg_grid, seeds = mg.add_water_regions(g, reg_grid, seeds)
    info = mg.summarize_regions(g, reg_grid, seeds)

    state.biome_grid = g
    state.region_seeds = seeds
    state.region_grid = reg_grid
    state.region_info = info
    state.player_region_id = 0
    state.coast_edge = edge_side
    
    # Initialize exploration state
    for rid, r_info in enumerate(state.region_info):
        r_info["explored"] = False
    
    # Start in zoom mode centered on player region
    state.zoom_mode = True
    state.zoom_region_id = 0

    if state.player_region_mask:
        xs = [p[0] for p in state.player_region_mask]
        ys = [p[1] for p in state.player_region_mask]
        state.player_region_center = ((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2)
    else:
        state.player_region_center = (state.player_grid_x, state.player_grid_y)

    # Calculate zoom origin to center on player region
    if state.player_region_mask:
        xs = [p[0] for p in state.player_region_mask]
        ys = [p[1] for p in state.player_region_mask]
        cx = (min(xs) + max(xs)) // 2
        cy = (min(ys) + max(ys)) // 2
        
        scale = C.ZOOM_SCALE
        view_w = (C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH) // (C.TILE_SIZE * scale)
        view_h = C.SCREEN_HEIGHT // (C.TILE_SIZE * scale)
        
        ox = cx - view_w // 2
        oy = cy - view_h // 2
        
        ox = max(0, min(C.BASE_GRID_WIDTH - view_w, ox))
        oy = max(0, min(C.BASE_GRID_HEIGHT - view_h, oy))
        
        state.zoom_origin = (ox, oy)
        state.zoom_bounds = (min(xs), min(ys), max(xs), max(ys))
    else:
        state.zoom_origin = (0, 0)
        state.zoom_bounds = (0, 0, 0, 0)
    
    cache_manager.invalidate_all(state)
    
    # Initialize fog grid (False = hidden)
    state.fog_grid = [[False for _ in range(C.BASE_GRID_WIDTH)] for _ in range(C.BASE_GRID_HEIGHT)]
    
    # Reveal SEA and 1 tile around it
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if g[y][x] == "SEA":
                # Reveal this SEA tile and 1 tile in all directions
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                            state.fog_grid[ny][nx] = True
    
    # Reveal player start region
    if state.player_region_mask:
        for (mx, my) in state.player_region_mask:
            state.fog_grid[my][mx] = True
            # Reveal neighbors too for smoother look
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = mx + dx, my + dy
                    if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                        state.fog_grid[ny][nx] = True
    else:
        # Fallback if no mask
        cx, cy = state.player_region_center
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                    state.fog_grid[ny][nx] = True

    # Spawn initial units at player start (4 units at different positions)
    state.units = []
    cx, cy = state.player_region_center
    
    # Find 4 different positions in player region
    player_tiles = list(state.player_region_mask)
    if len(player_tiles) >= 4:
        # Use random positions from player region
        positions = random.sample(player_tiles, 4)
    else:
        # Fallback: use center with small offsets
        positions = [
            (cx, cy),
            (cx + 1, cy) if (cx + 1, cy) in state.player_region_mask else (cx, cy),
            (cx, cy + 1) if (cx, cy + 1) in state.player_region_mask else (cx, cy),
            (cx + 1, cy + 1) if (cx + 1, cy + 1) in state.player_region_mask else (cx, cy),
        ]
    
    # Create units
    explorer = Explorer(x=float(positions[0][0]), y=float(positions[0][1]))
    colonist = Colonist(x=float(positions[1][0]), y=float(positions[1][1]))
    diplomat = Diplomat(x=float(positions[2][0]), y=float(positions[2][1]))
    conquistador = Conquistador(x=float(positions[3][0]), y=float(positions[3][1]))
    
    state.units = [explorer, colonist, diplomat, conquistador]
    
    # Reveal fog around all initial units
    for unit in state.units:
        for (tx, ty) in unit.get_vision_tiles():
            state.fog_grid[ty][tx] = True
        
    state.selected_region = state.player_region_id
    
    # Generate resource nodes
    state.resource_nodes = generate_resource_nodes(state.biome_grid, state.region_grid, state.region_seeds)
    
    # Calculate initial player resources
    calculate_player_resources(state)
    
    # Check for fully explored regions (including player region)
    check_all_regions_explored(state)
    
    # Always save newly generated map as debug map for future use
    save_map_state(state, "debug_map.pkl")


def save_map_state(state: GameState, filename: str):
    """Save the current map state to a file for debug purposes"""
    data = {
        "biome_grid": state.biome_grid,
        "region_seeds": state.region_seeds,
        "region_grid": state.region_grid,
        "region_info": state.region_info,
        "coast_edge": state.coast_edge,
        "player_region_id": state.player_region_id,
        "player_region_mask": state.player_region_mask,
        "player_region_center": state.player_region_center,
        "player_grid_x": state.player_grid_x,
        "player_grid_y": state.player_grid_y,
        "adjacent_regions_cache": state.adjacent_regions_cache
    }
    try:
        with open(filename, "wb") as f:
            pickle.dump(data, f)
        print(f"Debug map saved to {filename}")
    except Exception as e:
        print(f"Failed to save debug map: {e}")


def load_map_state(state: GameState, filename: str) -> bool:
    """Load map state from a file. Returns True if successful."""
    if not os.path.exists(filename):
        return False
        
    try:
        with open(filename, "rb") as f:
            data = pickle.load(f)
            
        state.biome_grid = data["biome_grid"]
        state.region_seeds = data["region_seeds"]
        state.region_grid = data["region_grid"]
        state.region_info = data["region_info"]
        state.coast_edge = data["coast_edge"]
        state.player_region_id = data["player_region_id"]
        state.player_region_mask = data["player_region_mask"]
        state.player_region_center = data["player_region_center"]
        state.player_grid_x = data["player_grid_x"]
        state.player_grid_y = data["player_grid_y"]
        state.adjacent_regions_cache = data.get("adjacent_regions_cache") # Might be missing in old saves
        
        # Reset explored status since fog is reset
        if state.region_info:
            for r_info in state.region_info:
                r_info["explored"] = False
        
        # Reset other state
        state.selected_region = state.player_region_id
        state.highlight_frames_remaining = 0
        state.zoom_mode = True
        state.zoom_region_id = 0
        
        # Calculate zoom origin
        if state.player_region_mask:
            xs = [p[0] for p in state.player_region_mask]
            ys = [p[1] for p in state.player_region_mask]
            cx = (min(xs) + max(xs)) // 2
            cy = (min(ys) + max(ys)) // 2
            
            scale = C.ZOOM_SCALE
            view_w = (C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH) // (C.TILE_SIZE * scale)
            view_h = C.SCREEN_HEIGHT // (C.TILE_SIZE * scale)
            
            ox = cx - view_w // 2
            oy = cy - view_h // 2
            
            ox = max(0, min(C.BASE_GRID_WIDTH - view_w, ox))
            oy = max(0, min(C.BASE_GRID_HEIGHT - view_h, oy))
            
            state.zoom_origin = (ox, oy)
            state.zoom_bounds = (min(xs), min(ys), max(xs), max(ys))
        else:
            state.zoom_origin = (0, 0)
            state.zoom_bounds = (0, 0, 0, 0)
            
        cache_manager.invalidate_all(state)
        
        # Reset fog
        state.fog_grid = [[False for _ in range(C.BASE_GRID_WIDTH)] for _ in range(C.BASE_GRID_HEIGHT)]
        
        # Reveal SEA and 1 tile around it
        for y in range(C.BASE_GRID_HEIGHT):
            for x in range(C.BASE_GRID_WIDTH):
                if state.biome_grid[y][x] == "SEA":
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                                state.fog_grid[ny][nx] = True
        
        # Reveal player region
        if state.player_region_mask:
            for (mx, my) in state.player_region_mask:
                state.fog_grid[my][mx] = True
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = mx + dx, my + dy
                        if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                            state.fog_grid[ny][nx] = True
                            
        # Spawn explorer
        state.units = []
        cx, cy = state.player_region_center
        explorer = Explorer(x=float(cx), y=float(cy))
        state.units.append(explorer)
        
        for (tx, ty) in explorer.get_vision_tiles():
            state.fog_grid[ty][tx] = True
            
        # Check for fully explored regions
        check_all_regions_explored(state)
            
        print(f"Debug map loaded from {filename}")
        return True
    except Exception as e:
        print(f"Failed to load debug map: {e}")
        return False


def build_adjacent_regions_cache(state: GameState):
    """Build cache of regions adjacent to player region"""
    adjacent = set()
    adjacent.add(state.player_region_id)  # Player region itself is considered "adjacent"
    
    for px, py in state.player_region_mask:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = px + dx, py + dy
            if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                neighbor_rid = state.region_grid[ny][nx]
                if neighbor_rid != -1 and neighbor_rid != state.player_region_id:
                    adjacent.add(neighbor_rid)
    
    # Check if player region is an island (only adjacent to water regions)
    # If so, add the nearest land region
    has_land_neighbor = False
    for rid in adjacent:
        if rid != state.player_region_id and state.region_info and rid < len(state.region_info):
            # Check if this region has any land tiles
            region_info = state.region_info[rid]
            if "biomes" in region_info:
                for biome, percentage in region_info["biomes"].items():
                    if biome not in ("SEA", "LAKE") and percentage > 0:
                        has_land_neighbor = True
                        break
            if has_land_neighbor:
                break
    
    # If no land neighbors (island), find nearest land region
    if not has_land_neighbor and state.region_info:
        nearest_land_rid = None
        nearest_distance = float('inf')
        
        # Calculate center of player region
        if state.player_region_mask:
            player_xs = [p[0] for p in state.player_region_mask]
            player_ys = [p[1] for p in state.player_region_mask]
            player_cx = sum(player_xs) / len(player_xs)
            player_cy = sum(player_ys) / len(player_ys)
            
            # Check all regions
            for rid, info in enumerate(state.region_info):
                if rid == state.player_region_id or rid in adjacent:
                    continue
                
                # Check if this is a land region
                has_land = False
                if "biomes" in info:
                    for biome, percentage in info["biomes"].items():
                        if biome not in ("SEA", "LAKE") and percentage > 0:
                            has_land = True
                            break
                
                if has_land and rid < len(state.region_seeds):
                    # Calculate distance from player center to this region's seed
                    seed_x, seed_y = state.region_seeds[rid]
                    distance = ((seed_x - player_cx) ** 2 + (seed_y - player_cy) ** 2) ** 0.5
                    
                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest_land_rid = rid
            
            # Add nearest land region to adjacent
            if nearest_land_rid is not None:
                adjacent.add(nearest_land_rid)
                print(f"Island detected: Added nearest land region {nearest_land_rid} (distance: {nearest_distance:.1f})")
    
    state.adjacent_regions_cache = adjacent


def is_adjacent_to_player_region(state: GameState, target_rid: int) -> bool:
    """Check if region is adjacent to player region (uses cache)"""
    # Build cache if not exists
    if state.adjacent_regions_cache is None:
        build_adjacent_regions_cache(state)
    
    return target_rid in state.adjacent_regions_cache


def calculate_player_resources(state: GameState):
    """
    Calculate player's food and gold from resource nodes in their territory.
    Food = sum of development from FISH, FARM, ANIMAL nodes
    Gold = sum of development from GOLD, SILVER nodes
    """
    food = 0
    gold = 0
    
    for node in state.resource_nodes:
        # Check if node is in player territory
        if (node.x, node.y) in state.player_region_mask:
            if node.type in ("FISH", "FARM", "ANIMAL"):
                food += node.development
            elif node.type in ("GOLD", "SILVER"):
                gold += node.development
    
    state.food = food
    state.gold = gold


def get_region_center(state: GameState, region_id: int) -> Optional[Tuple[int, int]]:
    """Get the center point of a region (uses region seed)"""
    if not state.region_seeds or region_id >= len(state.region_seeds):
        return None
    
    # Return the region seed position (the white tile shown on map)
    return state.region_seeds[region_id]


def check_all_regions_explored(state: GameState):
    """Check all regions and mark them as explored if all their tiles are revealed."""
    if not state.region_info or not state.fog_grid or not state.region_grid:
        return

    # Reset explored status
    for r_info in state.region_info:
        r_info["explored"] = False
        r_info["_revealed_count"] = 0 # Temporary counter

    # Count revealed tiles
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            rid = state.region_grid[y][x]
            if rid is not None and rid >= 0 and rid < len(state.region_info):
                if state.fog_grid[y][x]:
                    state.region_info[rid]["_revealed_count"] = state.region_info[rid].get("_revealed_count", 0) + 1

    # Check against total size
    for r_info in state.region_info:
        if r_info["size"] > 0 and r_info.get("_revealed_count", 0) == r_info["size"]:
            r_info["explored"] = True
        
        # Clean up temporary counter
        if "_revealed_count" in r_info:
            del r_info["_revealed_count"]
