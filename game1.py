import pygame

import config as C
import mapgen as mg
import audio
from state import GameState
import render
from unit import Explorer


def load_jp_font(size=18):
    candidates = ["meiryo", "msgothic", "noto sans cjk jp", "noto sans jp", "arialunicode", None]
    for name in candidates:
        try:
            fnt = pygame.font.SysFont(name, size)
            if fnt:
                return fnt
        except Exception:
            continue
    return pygame.font.Font(None, size)


def generate_world(state: GameState):
    state.selected_region = None
    g, edge_side = mg.generate_biome_map()
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

    # Spawn initial explorer unit at player start
    state.units = []
    cx, cy = state.player_region_center
    explorer = Explorer(x=float(cx), y=float(cy))
    state.units.append(explorer)
    
    # Reveal fog around initial explorer
    for (tx, ty) in explorer.get_vision_tiles():
        state.fog_grid[ty][tx] = True
        
    state.selected_region = state.player_region_id


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
        
        # Left click = select unit or region
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
            
            # Region selection logic
            rid = state.region_grid[gy][gx]
            
            # Check if region is fully explored
            is_fully_explored = True
            if not state.debug_fog_off and state.fog_grid:
                # Check all tiles in this region
                # Optimization: We could cache this, but for now iterate
                for y in range(C.BASE_GRID_HEIGHT):
                    for x in range(C.BASE_GRID_WIDTH):
                        if state.region_grid[y][x] == rid:
                            if not state.fog_grid[y][x]:
                                is_fully_explored = False
                                break
                    if not is_fully_explored:
                        break
            
            if not is_fully_explored:
                # Cannot select unexplored region
                return

            if state.selected_region == rid and rid is not None and rid >= 0:
                # Check if it's SEA
                clicked_biome = state.biome_grid[gy][gx]
                if clicked_biome == "SEA":
                    # Do not zoom into SEA
                    return
                    
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
                state.selected_region = rid


def main():
    pygame.init()
    screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
    pygame.display.set_caption("Tile Exploration - Biome Regions")
    pygame.font.init()
    font = load_jp_font(18)

    state = GameState()

    button_width = 220
    button_height = 64
    button_rect = pygame.Rect(
        (C.SCREEN_WIDTH - button_width) // 2,
        (C.SCREEN_HEIGHT - button_height) // 2,
        button_width,
        button_height,
    )
    back_button_rect = pygame.Rect(12, C.SCREEN_HEIGHT - 48, 160, 36)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if state.screen_state == "menu":
                    if button_rect.collidepoint(mx, my):
                        state.screen_state = "loading"
                        state.loading_frames_remaining = C.LOADING_DELAY_FRAMES
                else:
                    if state.zoom_mode:
                        handle_zoom_click(state, mx, my, event.button)
                        continue
                    handle_world_click(state, mx, my, back_button_rect, event.button)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and state.zoom_mode:
                    state.zoom_mode = False
                    state.zoom_region_id = None
                elif event.key == pygame.K_SPACE:
                    state.is_paused = not state.is_paused

        screen.fill(C.BLACK)

        if state.screen_state == "menu":
            audio.play_music(C.BGM_MENU)
            render.render_menu(screen, font, button_rect)

        elif state.screen_state == "loading":
            audio.play_music(C.BGM_MENU)
            render.render_loading(screen, font)
            if state.loading_frames_remaining > 0:
                state.loading_frames_remaining -= 1
                if state.loading_frames_remaining == 0:
                    generate_world(state)
                    state.screen_state = "game"
        else:
            audio.play_music(C.BGM_GAME)
            
            # Game Loop Logic
            if not state.is_paused:
                state.game_time += state.game_speed
                if state.game_time >= 1000: # 1 day per 1000 ticks (approx 16 sec at 60fps)
                    state.game_time -= 1000
                    state.day += 1
                
                # Update units
                for unit in state.units:
                    unit.update(state.game_speed, state)
                    
                    # Reveal fog based on unit vision
                    if state.fog_grid:
                        revealed_any = False
                        for (tx, ty) in unit.get_vision_tiles():
                            if not state.fog_grid[ty][tx]:
                                state.fog_grid[ty][tx] = True
                                revealed_any = True
                        
                        # Invalidate fog surface to force redraw if anything revealed
                        if revealed_any:
                            state.fog_surface = None
            
            if state.zoom_mode and state.zoom_region_id is not None:
                render.render_zoom(screen, font, state)
            else:
                render.render_main(screen, font, state, back_button_rect)

        pygame.display.flip()
        if state.screen_state == "game" and state.highlight_frames_remaining > 0:
            state.highlight_frames_remaining -= 1
        if state.zoom_mode:
            keys = pygame.key.get_pressed()
            move_x = 0
            move_y = 0
            if keys[pygame.K_a]:
                move_x -= 1
            if keys[pygame.K_d]:
                move_x += 1
            if keys[pygame.K_w]:
                move_y -= 1
            if keys[pygame.K_s]:
                move_y += 1
            if move_x or move_y:
                ox, oy = state.zoom_origin
                ox = max(0, min(C.BASE_GRID_WIDTH - 1, ox + move_x))
                oy = max(0, min(C.BASE_GRID_HEIGHT - 1, oy + move_y))
                state.zoom_origin = (ox, oy)

    pygame.quit()


if __name__ == "__main__":
    main()
