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
