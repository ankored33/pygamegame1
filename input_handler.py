import pygame
import time
import config as C
from state import GameState
from game_system import build_adjacent_regions_cache

def handle_zoom_click(state: GameState, mx: int, my: int, button: int):
    # Handle Confirmation Dialog
    if state.confirm_dialog:
        if button == 1: # Left click
            if state.confirm_dialog["yes_rect"].collidepoint(mx, my):
                state.confirm_dialog["on_yes"]()
                state.confirm_dialog = None
            elif state.confirm_dialog["no_rect"].collidepoint(mx, my):
                state.confirm_dialog["on_no"]()
                state.confirm_dialog = None
        return

    scale = C.ZOOM_SCALE
    map_origin_x = C.INFO_PANEL_WIDTH
    view_x0 = max(0, state.zoom_origin[0])
    view_y0 = max(0, state.zoom_origin[1])
    view_w = (C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH) // (C.TILE_SIZE * scale) + 2
    view_h = C.SCREEN_HEIGHT // (C.TILE_SIZE * scale) + 2
    view_x1 = min(C.BASE_GRID_WIDTH - 1, view_x0 + view_w)
    view_y1 = min(C.BASE_GRID_HEIGHT - 1, view_y0 + view_h)
    
    if mx >= map_origin_x:
        gx = (mx - map_origin_x) // (C.TILE_SIZE * scale) + view_x0
        gy = (my // (C.TILE_SIZE * scale)) + view_y0
        
        if view_x0 <= gx <= view_x1 and view_y0 <= gy <= view_y1:
            # Right click
            if button == 3:
                # Check if fogged
                is_fogged = not state.fog_grid[gy][gx] if state.fog_grid else False
                
                if is_fogged:
                    # Automated exploration if adjacent to ANY selected unit
                    target_rid = state.region_grid[gy][gx]
                    
                    selected_units = [u for u in state.units if u.selected]
                    if not selected_units:
                        return

                    can_explore = False
                    for unit in selected_units:
                        ux, uy = int(unit.x), int(unit.y)
                        if 0 <= ux < C.BASE_GRID_WIDTH and 0 <= uy < C.BASE_GRID_HEIGHT:
                            unit_rid = state.region_grid[uy][ux]
                            # Check if target is same or neighbor
                            if unit_rid == target_rid:
                                can_explore = True
                                break
                            if state.region_info and unit_rid < len(state.region_info):
                                if target_rid in state.region_info[unit_rid]["neighbors"]:
                                    can_explore = True
                                    break
                    
                    if can_explore:
                        def start_exploration():
                            for unit in selected_units:
                                unit.target_region_id = target_rid
                                unit.target_x = None
                                unit.target_y = None
                        
                        def cancel_exploration():
                            pass
                            
                        state.confirm_dialog = {
                            "message": f"リージョン {target_rid} を探索しますか？",
                            "on_yes": start_exploration,
                            "on_no": cancel_exploration
                        }
                return

            # Left click = select unit
            clicked_unit = False
            for unit in state.units:
                ux = int(unit.x)
                uy = int(unit.y)
                if ux == gx and uy == gy:
                    unit.selected = not unit.selected
                    clicked_unit = True
                    break
            
            if not clicked_unit:
                # Check for region seed click
                clicked_seed = False
                if state.region_seeds:
                    for idx, (sx, sy) in enumerate(state.region_seeds):
                        # Check visibility (fog)
                        if not state.debug_fog_off and state.fog_grid and not state.fog_grid[sy][sx]:
                            continue
                        
                        # Skip SEA and LAKE
                        if state.biome_grid[sy][sx] in ("SEA", "LAKE"):
                            continue

                        if sx == gx and sy == gy:
                            state.selected_region = idx
                            clicked_seed = True
                            break

                if not clicked_seed:
                    # Deselect all units if clicked on empty space
                    for unit in state.units:
                        unit.selected = False


def handle_world_click(state: GameState, mx: int, my: int, back_button_rect: pygame.Rect, button: int):
    # Handle Confirmation Dialog
    if state.confirm_dialog:
        if button == 1: # Left click
            if state.confirm_dialog["yes_rect"].collidepoint(mx, my):
                state.confirm_dialog["on_yes"]()
                state.confirm_dialog = None
            elif state.confirm_dialog["no_rect"].collidepoint(mx, my):
                state.confirm_dialog["on_no"]()
                state.confirm_dialog = None
        return

    # Debug Fog Toggle (Bottom Right)
    debug_btn_rect = pygame.Rect(C.SCREEN_WIDTH - 110, C.SCREEN_HEIGHT - 40, 100, 30)
    if debug_btn_rect.collidepoint(mx, my):
        state.debug_fog_off = not state.debug_fog_off
        return
        
    if back_button_rect.collidepoint(mx, my):
        state.screen_state = "menu"
        state.biome_grid = None
        state.region_grid = None
        state.region_seeds = None
        state.region_info = None
        state.selected_region = None
        return
    if mx < C.INFO_PANEL_WIDTH:
        return
    if state.biome_grid is None or state.region_grid is None:
        return
    
    gx = (mx - C.INFO_PANEL_WIDTH) // C.TILE_SIZE
    gy = my // C.TILE_SIZE
    
    if 0 <= gx < C.BASE_GRID_WIDTH and 0 <= gy < C.BASE_GRID_HEIGHT:
        # Right click = automated exploration
        if button == 3:  # Right mouse button
            target_rid = state.region_grid[gy][gx]
            
            # Check if any unit is selected
            selected_units = [u for u in state.units if u.selected]
            if not selected_units:
                return

            can_explore = False
            for unit in selected_units:
                ux, uy = int(unit.x), int(unit.y)
                if 0 <= ux < C.BASE_GRID_WIDTH and 0 <= uy < C.BASE_GRID_HEIGHT:
                    unit_rid = state.region_grid[uy][ux]
                    # Check if target is same or neighbor
                    if unit_rid == target_rid:
                        can_explore = True
                        break
                    if state.region_info and unit_rid < len(state.region_info):
                        if target_rid in state.region_info[unit_rid]["neighbors"]:
                            can_explore = True
                            break
            
            if not can_explore:
                return
                
            def start_exploration():
                for unit in selected_units:
                    unit.target_region_id = target_rid
                    unit.target_x = None # Reset current target to force recalculation
                    unit.target_y = None
            
            def cancel_exploration():
                pass
                
            state.confirm_dialog = {
                "message": f"リージョン {target_rid} を探索しますか？",
                "on_yes": start_exploration,
                "on_no": cancel_exploration
            }
            return
        
        # Left click = select unit or double-click to zoom
        # Check if clicking on a unit
        clicked_unit = False
        for unit in state.units:
            ux = int(unit.x)
            uy = int(unit.y)
            if ux == gx and uy == gy:
                # Toggle selection
                unit.selected = not unit.selected
                clicked_unit = True
                break
        
        if not clicked_unit:
            # Deselect all units
            for unit in state.units:
                unit.selected = False
            
            # Double-click detection for zoom
            current_time = time.time()
            rid = state.region_grid[gy][gx]
            
            # Check if this is a double-click on the same position
            is_double_click = False
            if (current_time - state.last_click_time) < state.DOUBLE_CLICK_TIME:
                # Check if clicked on same position (within tolerance)
                dx = abs(gx - state.last_click_pos[0])
                dy = abs(gy - state.last_click_pos[1])
                if dx <= 1 and dy <= 1:  # Allow 1 tile tolerance
                    is_double_click = True
            
            # Update last click tracking
            state.last_click_time = current_time
            state.last_click_pos = (gx, gy)
            
            if is_double_click and rid is not None and rid >= 0:
                # Zoom into the region (no fog check needed)
                state.zoom_mode = True
                state.zoom_region_id = rid
                xs = []
                ys = []
                for yy in range(C.BASE_GRID_HEIGHT):
                    for xx in range(C.BASE_GRID_WIDTH):
                        if state.region_grid[yy][xx] == rid:
                            xs.append(xx)
                            ys.append(yy)
                if xs and ys:
                    xmin, xmax = min(xs), max(xs)
                    ymin, ymax = min(ys), max(ys)
                    state.zoom_bounds = (xmin, ymin, xmax, ymax)
                    
                    # Center on the region seed (generation start point)
                    if state.region_seeds and rid < len(state.region_seeds):
                        sx, sy = state.region_seeds[rid]
                        
                        # Calculate view size in tiles
                        scale = C.ZOOM_SCALE
                        view_w = (C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH) // (C.TILE_SIZE * scale)
                        view_h = C.SCREEN_HEIGHT // (C.TILE_SIZE * scale)
                        
                        # Calculate origin to center the seed
                        ox = sx - view_w // 2
                        oy = sy - view_h // 2
                        
                        # Clamp to map bounds
                        ox = max(0, min(C.BASE_GRID_WIDTH - view_w, ox))
                        oy = max(0, min(C.BASE_GRID_HEIGHT - view_h, oy))
                        
                        state.zoom_origin = (ox, oy)
                    else:
                        # Fallback to bounding box top-left if seed not found
                        state.zoom_origin = (max(0, xmin - C.ZOOM_MARGIN), max(0, ymin - C.ZOOM_MARGIN))
            else:
                # Single click - check if region is fully explored before allowing selection
                is_fully_explored = True
                if not state.debug_fog_off and state.fog_grid:
                    # Check all tiles in this region
                    for y in range(C.BASE_GRID_HEIGHT):
                        for x in range(C.BASE_GRID_WIDTH):
                            if state.region_grid[y][x] == rid:
                                if not state.fog_grid[y][x]:
                                    is_fully_explored = False
                                    break
                        if not is_fully_explored:
                            break
                
                # Only allow selection of fully explored regions
                if is_fully_explored:
                    state.selected_region = rid
