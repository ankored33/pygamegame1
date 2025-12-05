import pygame
import config as C
import audio
import cache_manager
import conquest
from state import GameState
import render_ui
import render_map
from game_system import generate_world
from input_handler import handle_zoom_click, handle_world_click


def _auto_explore_lakes(state):
    """
    Auto-explore lake regions when ALL surrounding tiles are revealed.
    A lake is auto-explored only when its entire perimeter is visible.
    Optimized to only check lakes near recently revealed tiles.
    """
    if not state.region_info or not state.fog_grid or not state.biome_grid:
        return
    
    # Find lake regions that might need checking (only those near revealed tiles)
    lake_regions_to_check = set()
    
    # Only check tiles that were just revealed (optimization)
    # We check a small area around revealed tiles for adjacent lakes
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            if state.fog_grid[y][x]:  # If revealed
                # Check adjacent tiles for lakes
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                        if state.biome_grid[ny][nx] == "LAKE":
                            region_id = state.region_grid[ny][nx]
                            # Skip if already explored
                            if region_id < len(state.region_info):
                                if not state.region_info[region_id].get("explored", False):
                                    lake_regions_to_check.add(region_id)
    
    # Check each candidate lake region
    for region_id in lake_regions_to_check:
        # Build surrounding tiles set for this lake (cached per region)
        surrounding_tiles = set()
        
        for y in range(C.BASE_GRID_HEIGHT):
            for x in range(C.BASE_GRID_WIDTH):
                if state.region_grid[y][x] == region_id and state.biome_grid[y][x] == "LAKE":
                    # Check 4 cardinal directions only (optimization)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < C.BASE_GRID_WIDTH and 0 <= ny < C.BASE_GRID_HEIGHT:
                            # If neighbor is not part of this lake, it's a surrounding tile
                            if state.region_grid[ny][nx] != region_id or state.biome_grid[ny][nx] != "LAKE":
                                surrounding_tiles.add((nx, ny))
        
        # Check if ALL surrounding tiles are revealed
        if not surrounding_tiles:
            continue
            
        all_surrounding_revealed = all(state.fog_grid[sy][sx] for sx, sy in surrounding_tiles)
        
        # If all surrounding tiles are revealed, auto-explore the lake
        if all_surrounding_revealed:
            # Reveal all lake tiles in this region
            for y in range(C.BASE_GRID_HEIGHT):
                for x in range(C.BASE_GRID_WIDTH):
                    if state.region_grid[y][x] == region_id and state.biome_grid[y][x] == "LAKE":
                        state.fog_grid[y][x] = True
            
            # Mark region as explored
            if region_id < len(state.region_info):
                state.region_info[region_id]["explored"] = True




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
                    elif hasattr(state, "debug_map_toggle_rect") and state.debug_map_toggle_rect.collidepoint(mx, my):
                        state.use_debug_map = not state.use_debug_map
                    
                    # Map Gen Params
                    elif hasattr(state, "elev_minus_rect") and state.elev_minus_rect.collidepoint(mx, my):
                        state.gen_elev_freq = max(0.005, state.gen_elev_freq - 0.005)
                    elif hasattr(state, "elev_plus_rect") and state.elev_plus_rect.collidepoint(mx, my):
                        state.gen_elev_freq += 0.005
                    elif hasattr(state, "humid_minus_rect") and state.humid_minus_rect.collidepoint(mx, my):
                        state.gen_humid_freq = max(0.005, state.gen_humid_freq - 0.005)
                    elif hasattr(state, "humid_plus_rect") and state.humid_plus_rect.collidepoint(mx, my):
                        state.gen_humid_freq += 0.005
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
            render_ui.render_menu(screen, font, button_rect, state)

        elif state.screen_state == "loading":
            audio.play_music(C.BGM_MENU)
            render_ui.render_loading(screen, font)
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
                if state.game_time >= C.TICKS_PER_DAY:
                    state.game_time -= C.TICKS_PER_DAY
                    state.day += 1
                
                # Update units
                for unit in state.units:
                    unit.update(state.game_speed, state)
                    
                    # Territory expansion for conquistadors
                    conquest.update_conquest(unit, state)
                    # Reveal fog based on unit vision
                    if state.fog_grid:
                        revealed_any = False
                        for (tx, ty) in unit.get_vision_tiles():
                            if not state.fog_grid[ty][tx]:
                                state.fog_grid[ty][tx] = True
                                revealed_any = True
                        
                        # Update fog surfaces if anything revealed
                        if revealed_any:
                            cache_manager.invalidate_fog(state)
                            
                            
                            # Auto-explore lake regions
                            _auto_explore_lakes(state)
                            # Update zoom fog layer (just the revealed tiles)
                            if state.zoom_fog_layer:
                                scale = C.ZOOM_SCALE
                                for (tx, ty) in unit.get_vision_tiles():
                                    if state.fog_grid[ty][tx]:
                                        px = tx * C.TILE_SIZE * scale
                                        py = ty * C.TILE_SIZE * scale
                                        rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                                        state.zoom_fog_layer.fill((0, 0, 0, 0), rect)  # Make transparent
            
            if state.zoom_mode and state.zoom_region_id is not None:
                render_map.render_zoom(screen, font, state)
            else:
                render_map.render_world_view(screen, font, state, back_button_rect)

        pygame.display.flip()
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
                
                # Calculate max scroll position
                scale = C.ZOOM_SCALE
                view_w = (C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH) // (C.TILE_SIZE * scale)
                view_h = (C.SCREEN_HEIGHT - C.TOP_BAR_HEIGHT) // (C.TILE_SIZE * scale)
                max_x = max(0, C.BASE_GRID_WIDTH - view_w)
                max_y = max(0, C.BASE_GRID_HEIGHT - view_h)
                
                ox = max(0, min(max_x, ox + move_x))
                oy = max(0, min(max_y, oy + move_y))
                state.zoom_origin = (ox, oy)


    pygame.quit()


if __name__ == "__main__":
    main()
