"""
Conquest management module for Conquistador units.
Handles territory expansion logic.
"""
import config as C
import cache_manager


def update_conquest(unit, state):
    """
    Update conquest progress for a conquistador unit.
    
    Args:
        unit: The conquistador unit
        state: Game state
    """
    if unit.unit_type != "conquistador" or unit.conquering_region_id is None:
        return
    
    ux, uy = int(unit.x), int(unit.y)
    region_id = unit.conquering_region_id
    
    # Check if we're in the target region
    if state.region_grid[uy][ux] != region_id:
        return
    
    # Check if expansion tracking exists
    if region_id not in state.territory_expansion_regions:
        return
    
    expansion = state.territory_expansion_regions[region_id]
    
    # Check if Conquistador has arrived at the seed location
    # Only start expansion after arrival
    if not expansion.get("arrived_at_seed", False):
        # Check if unit is at or very close to the seed
        if state.region_seeds and region_id < len(state.region_seeds):
            seed_x, seed_y = state.region_seeds[region_id]
            distance_to_seed = ((unit.x - seed_x) ** 2 + (unit.y - seed_y) ** 2) ** 0.5
            
            # Consider arrived if within 0.5 tiles of seed
            if distance_to_seed < 0.5:
                expansion["arrived_at_seed"] = True
            else:
                # Not arrived yet, don't expand
                return
        else:
            # No seed info, assume arrived (fallback)
            expansion["arrived_at_seed"] = True
    
    # Expand once per day (when game_time wraps)
    if state.game_time < state.game_speed:
        _expand_territory(expansion, region_id, (ux, uy), state)
        _check_completion(unit, expansion, region_id, state)


def _expand_territory(expansion, region_id, unit_pos, state):
    """
    Expand territory by adding tiles to player control.
    
    Args:
        expansion: Expansion tracking dict
        region_id: Region being conquered
        unit_pos: (x, y) position of conquistador
        state: Game state
    """
    ux, uy = unit_pos
    
    # Lazy initialization of all_tiles for this region
    if "all_tiles" not in expansion:
        expansion["all_tiles"] = set()
        for y in range(C.BASE_GRID_HEIGHT):
            for x in range(C.BASE_GRID_WIDTH):
                if state.region_grid[y][x] == region_id:
                    expansion["all_tiles"].add((x, y))
    
    # Expand multiple tiles per day
    tiles_added = False
    for _ in range(C.CONQUEST_TILES_PER_DAY):
        owned_in_region = [t for t in expansion["tiles"]]
        
        candidates = []
        if not owned_in_region:
            # INITIAL CONQUEST: Claim the tile under the unit
            if state.region_grid[uy][ux] == region_id:
                candidates.append((ux, uy))
        else:
            # EXISTING LOGIC: Expand from owned tiles
            for (px, py) in expansion["tiles"]:
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = px + dx, py + dy
                    if (0 <= nx < C.BASE_GRID_WIDTH and 
                        0 <= ny < C.BASE_GRID_HEIGHT and
                        state.region_grid[ny][nx] == region_id and
                        (nx, ny) not in state.player_region_mask):
                        candidates.append((nx, ny))
            
            # If no adjacent candidates found, look for disconnected tiles (islands)
            if not candidates:
                unowned = expansion["all_tiles"] - expansion["tiles"]
                unowned = {t for t in unowned if t not in state.player_region_mask}
                
                if unowned:
                    # Pick closest to Conquistador to simulate reaching out
                    best_island_tile = min(unowned, key=lambda t: (t[0]-ux)**2 + (t[1]-uy)**2)
                    candidates.append(best_island_tile)
        
        # Add one tile to territory
        if candidates:
            # Choose closest to conquistador
            best_tile = min(candidates, key=lambda t: (t[0]-ux)**2 + (t[1]-uy)**2)
            state.player_region_mask.add(best_tile)
            expansion["tiles"].add(best_tile)
            expansion["progress"] += 1
            tiles_added = True
        else:
            break  # No more candidates found
    
    # Only invalidate caches if we actually added tiles
    if tiles_added:
        cache_manager.invalidate_map(state)


def _check_completion(unit, expansion, region_id, state):
    """
    Check if conquest is complete and show completion dialog.
    
    Args:
        unit: The conquistador unit
        expansion: Expansion tracking dict
        region_id: Region being conquered
        state: Game state
    """
    if len(expansion["tiles"]) >= len(expansion["all_tiles"]):
        unit.conquering_region_id = None
        
        def close_dialog():
            pass
        
        state.confirm_dialog = {
            "message": f"リージョン {region_id} の征服が完了しました！",
            "on_yes": close_dialog,
            "on_no": close_dialog
        }
