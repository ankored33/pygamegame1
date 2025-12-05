import pygame
import config as C
import audio
from state import GameState
import render_ui
import render_map
from game_system import generate_world
from input_handler import handle_zoom_click, handle_world_click


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
                if state.game_time >= 1000: # 1 day per 1000 ticks (approx 16 sec at 60fps)
                    state.game_time -= 1000
                    state.day += 1
                
                # Update units
                for unit in state.units:
                    unit.update(state.game_speed, state)
                    
                    # Territory expansion for conquistadors
                    if unit.unit_type == "conquistador" and unit.conquering_region_id is not None:
                        # Check if conquistador is at region center (or very close)
                        ux, uy = int(unit.x), int(unit.y)
                        region_id = unit.conquering_region_id
                        
                        # Check if we're in the target region
                        if state.region_grid[uy][ux] == region_id:
                            # Gradually expand territory
                            if region_id in state.territory_expansion_regions:
                                expansion = state.territory_expansion_regions[region_id]
                                
                                # Expand 10 tiles per day (when game_time wraps)
                                if state.game_time < state.game_speed:  # Just wrapped to new day
                                    tiles_to_add = 10
                                    
                                    # Lazy initialization of all_tiles for this region
                                    if "all_tiles" not in expansion:
                                        expansion["all_tiles"] = set()
                                        for y in range(C.BASE_GRID_HEIGHT):
                                            for x in range(C.BASE_GRID_WIDTH):
                                                if state.region_grid[y][x] == region_id:
                                                    expansion["all_tiles"].add((x, y))

                                    for _ in range(tiles_to_add):
                                        # Check if we have any foothold in this region
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
                                                # Filter out tiles that are already in player_region_mask (from other means?)
                                                # Though expansion["tiles"] should track this region's owned tiles.
                                                # Double check with global mask just in case
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
                                        else:
                                            break # No more candidates found
                                        
                                    # Invalidate caches
                                    state.map_surface = None
                                    state.zoom_full_map_cache = None
                                    state.selected_region_overlay_cache = None
                                    state.selected_region_overlay_zoom_cache = None

                                    # Check for completion
                                    if len(expansion["tiles"]) >= len(expansion["all_tiles"]):
                                        unit.conquering_region_id = None
                                        
                                        def close_dialog():
                                            pass
                                            
                                        state.confirm_dialog = {
                                            "message": f"リージョン {region_id} の征服が完了しました！",
                                            "on_yes": close_dialog,
                                            "on_no": close_dialog
                                        }


                    
                    # Reveal fog based on unit vision
                    if state.fog_grid:
                        revealed_any = False
                        for (tx, ty) in unit.get_vision_tiles():
                            if not state.fog_grid[ty][tx]:
                                state.fog_grid[ty][tx] = True
                                revealed_any = True
                        
                        # Update fog surfaces if anything revealed
                        if revealed_any:
                            state.fog_surface = None
                            
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
