import pickle
import os
import random
import config as C
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

    reg_grid, seeds = mg.add_water_regions(g, reg_grid, seeds)
    info = mg.summarize_regions(g, reg_grid, seeds)

    state.biome_grid = g
    state.region_seeds = seeds
    state.region_grid = reg_grid
    state.region_info = info
    state.player_region_id = 0
    state.coast_edge = edge_side
    state.highlight_frames_remaining = 0  # Disabled highlight circle
    
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
    
    state.map_surface = None
    state.fog_surface = None
    
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
    
    # Save debug map if enabled
    if state.use_debug_map:
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
            
        state.map_surface = None
        state.fog_surface = None
        
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
