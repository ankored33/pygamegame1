import math
import pygame
import config as C
import mapgen as mg


def draw_text(screen, font, line, x, y, color=C.WHITE):
    surf = font.render(line, True, color)
    screen.blit(surf, (x, y))


def format_weights(weights: dict):
    if not weights:
        return "なし"
    return " / ".join(f"{k}:{v}" for k, v in weights.items())


def format_distribution(dist: dict):
    if not dist:
        return "なし"
    items = sorted(dist.items(), key=lambda kv: kv[1], reverse=True)
    return " / ".join(f"{C.BIOME_NAMES.get(k, k)} {v}%" for k, v in items)


def render_menu(screen, font, button_rect, state):
    title = "Tile Exploration - Biomes"
    t_surf = font.render(title, True, C.WHITE)
    t_rect = t_surf.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 - 80))
    screen.blit(t_surf, t_rect)

    # Start Button
    pygame.draw.rect(screen, C.GREY, button_rect)
    pygame.draw.rect(screen, C.WHITE, button_rect, 2)
    btn_text = font.render("スタート", True, C.WHITE)
    btn_rect = btn_text.get_rect(center=button_rect.center)
    screen.blit(btn_text, btn_rect)
    
    # Debug Map Toggle
    toggle_rect = pygame.Rect(button_rect.x, button_rect.bottom + 20, button_rect.width, 40)
    bg_col = (100, 150, 100) if state.use_debug_map else C.GREY
    pygame.draw.rect(screen, bg_col, toggle_rect)
    pygame.draw.rect(screen, C.WHITE, toggle_rect, 2)
    
    toggle_text = f"デバッグマップ: {'ON' if state.use_debug_map else 'OFF'}"
    t_surf = font.render(toggle_text, True, C.WHITE)
    t_rect = t_surf.get_rect(center=toggle_rect.center)
    screen.blit(t_surf, t_rect)
    
    # Store rect in state for click handling (hacky but works)
    state.debug_map_toggle_rect = toggle_rect

    # Map Gen Params Controls
    start_y = toggle_rect.bottom + 20
    
    # Elev Freq
    lbl_surf = font.render(f"標高ノイズ: {state.gen_elev_freq:.3f}", True, C.WHITE)
    screen.blit(lbl_surf, (button_rect.x, start_y + 10))
    
    minus_rect = pygame.Rect(button_rect.right - 80, start_y, 30, 30)
    plus_rect = pygame.Rect(button_rect.right - 40, start_y, 30, 30)
    
    pygame.draw.rect(screen, C.GREY, minus_rect)
    pygame.draw.rect(screen, C.WHITE, minus_rect, 1)
    draw_text_centered(screen, font, "-", minus_rect)
    
    pygame.draw.rect(screen, C.GREY, plus_rect)
    pygame.draw.rect(screen, C.WHITE, plus_rect, 1)
    draw_text_centered(screen, font, "+", plus_rect)
    
    state.elev_minus_rect = minus_rect
    state.elev_plus_rect = plus_rect
    
    start_y += 40
    
    # Humid Freq
    lbl_surf = font.render(f"湿度ノイズ: {state.gen_humid_freq:.3f}", True, C.WHITE)
    screen.blit(lbl_surf, (button_rect.x, start_y + 10))
    
    minus_rect = pygame.Rect(button_rect.right - 80, start_y, 30, 30)
    plus_rect = pygame.Rect(button_rect.right - 40, start_y, 30, 30)
    
    pygame.draw.rect(screen, C.GREY, minus_rect)
    pygame.draw.rect(screen, C.WHITE, minus_rect, 1)
    draw_text_centered(screen, font, "-", minus_rect)
    
    pygame.draw.rect(screen, C.GREY, plus_rect)
    pygame.draw.rect(screen, C.WHITE, plus_rect, 1)
    draw_text_centered(screen, font, "+", plus_rect)
    
    state.humid_minus_rect = minus_rect
    state.humid_plus_rect = plus_rect


def draw_text_centered(screen, font, text, rect):
    surf = font.render(text, True, C.WHITE)
    r = surf.get_rect(center=rect.center)
    screen.blit(surf, r)


def render_loading(screen, font):
    load_text = font.render("ロード中...", True, C.WHITE)
    load_rect = load_text.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2))
    screen.blit(load_text, load_rect)


def render_panel(screen, font, state, hover_tile=None):
    panel_rect = pygame.Rect(0, 0, C.INFO_PANEL_WIDTH, C.SCREEN_HEIGHT)
    pygame.draw.rect(screen, C.DARK_GREY, panel_rect)

    pad = 12
    lh = 22
    current_y = pad
    
    # Time / Status
    if state.is_paused:
        status_text = "一時停止中"
        spinner = "||"
    else:
        status_text = "進行中"
        # Simple spinner based on game_time
        # Rotate every 15 ticks (approx 4 times per second at 60fps)
        spinner_idx = int(state.game_time / 15) % 4
        spinner = ["|", "／", "－", "＼"][spinner_idx]
        
    draw_text(screen, font, f"Day: {state.day}  {spinner}  ({status_text})", pad, current_y)
    current_y += lh * 2
    
    draw_text(screen, font, "プレイヤー", pad, current_y)
    current_y += lh
    draw_text(screen, font, f"位置: ({state.player_grid_x}, {state.player_grid_y})", pad, current_y)
    current_y += lh
    if state.player_region_id is not None:
        draw_text(screen, font, f"自領域 ID: {state.player_region_id}", pad, current_y)
        current_y += lh
        draw_text(screen, font, f"タイル数: {len(state.player_region_mask)}", pad, current_y)
        current_y += lh

    current_y += lh # spacer
    draw_text(screen, font, "選択リージョン", pad, current_y)
    current_y += lh
    if state.selected_region is not None and state.selected_region >= 0 and state.region_info:
        info = state.region_info[state.selected_region]
        draw_text(screen, font, f"ID: {state.selected_region}", pad, current_y)
        current_y += lh
        draw_text(screen, font, "バイオーム: -", pad, current_y)
        current_y += lh
        draw_text(screen, font, f"大きさ: {info['size']} セル", pad, current_y)
        current_y += lh
        
        # Helper to wrap text
        def draw_wrapped(label, text):
            nonlocal current_y
            full_text = f"{label}: {text}"
            
            # Simple character count wrapping (approximate)
            # Assuming ~10 chars fit in one line with label, or ~18 chars without
            # This is a rough heuristic. For better wrapping, we'd need to measure text width.
            max_chars = 18 
            
            if len(full_text) <= max_chars:
                draw_text(screen, font, full_text, pad, current_y)
                current_y += lh
            else:
                # Split into lines
                draw_text(screen, font, f"{label}:", pad, current_y)
                current_y += lh
                
                # Split value text by comma
                parts = text.split(" / ")
                line = ""
                for part in parts:
                    if len(line) + len(part) + 3 > max_chars: # +3 for " / "
                        if line:
                            draw_text(screen, font, f"  {line}", pad, current_y)
                            current_y += lh
                        line = part
                    else:
                        if line:
                            line += " / " + part
                        else:
                            line = part
                if line:
                    draw_text(screen, font, f"  {line}", pad, current_y)
                    current_y += lh

        draw_wrapped("資源", format_weights(info['resources']))
        draw_wrapped("危険", format_weights(info['dangers']))
        draw_wrapped("構成", format_distribution(info['distribution']))
    else:
        draw_text(screen, font, "未選択", pad, current_y)
        current_y += lh

    if hover_tile:
        current_y += lh # spacer
        hx, hy = hover_tile
        
        # Check fog
        is_fogged = False
        if not state.debug_fog_off and state.fog_grid and not state.fog_grid[hy][hx]:
            is_fogged = True
            
        draw_text(screen, font, "タイル情報", pad, current_y)
        current_y += lh
        draw_text(screen, font, f"座標: ({hx}, {hy})", pad, current_y)
        current_y += lh
        
        if is_fogged:
            draw_text(screen, font, "未探索", pad, current_y)
            current_y += lh
        else:
            rid = state.region_grid[hy][hx]
            b = state.biome_grid[hy][hx]
            draw_text(screen, font, f"バイオーム: {C.BIOME_NAMES.get(b, b)}", pad, current_y)
            current_y += lh
            draw_text(screen, font, f"リージョンID: {rid}", pad, current_y)
            current_y += lh


def render_zoom(screen, font, state):
    scale = C.ZOOM_SCALE
    map_origin_x = C.INFO_PANEL_WIDTH
    map_origin_y = 0
    view_x0 = max(0, state.zoom_origin[0])
    view_y0 = max(0, state.zoom_origin[1])
    view_w = (C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH) // (C.TILE_SIZE * scale) + 2
    view_h = C.SCREEN_HEIGHT // (C.TILE_SIZE * scale) + 2
    view_x1 = min(C.BASE_GRID_WIDTH - 1, view_x0 + view_w)
    view_y1 = min(C.BASE_GRID_HEIGHT - 1, view_y0 + view_h)

    # Create a transparent surface for grid lines to support alpha blending
    grid_surface = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
    
    # Pass 1: Draw tiles and grid lines
    if state.biome_grid and state.region_grid:
        for y in range(view_y0, view_y1 + 1):
            for x in range(view_x0, view_x1 + 1):
                # Fog check
                if not state.debug_fog_off and state.fog_grid and not state.fog_grid[y][x]:
                    px = map_origin_x + (x - view_x0) * C.TILE_SIZE * scale
                    py = map_origin_y + (y - view_y0) * C.TILE_SIZE * scale
                    rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                    pygame.draw.rect(screen, (0, 0, 0), rect)
                    continue

                b = state.biome_grid[y][x]
                color = C.BIOME_COLORS.get(b, C.GREY)
                rid = state.region_grid[y][x]
                if rid == state.player_region_id:
                    color = tuple(min(255, c + 40) for c in color)
                px = map_origin_x + (x - view_x0) * C.TILE_SIZE * scale
                py = map_origin_y + (y - view_y0) * C.TILE_SIZE * scale
                rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                pygame.draw.rect(screen, color, rect)
                
                # Draw grid lines (right and bottom only) with 50% transparency
                grid_color = (160, 160, 160, 128)
                pygame.draw.line(grid_surface, grid_color, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1), 1)
                pygame.draw.line(grid_surface, grid_color, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1), 1)

    # Blit grid surface onto screen
    screen.blit(grid_surface, (0, 0))

    # Pass 2: Draw borders (Region and Faction)
    if state.biome_grid and state.region_grid:
        for y in range(view_y0, view_y1 + 1):
            for x in range(view_x0, view_x1 + 1):
                # Fog check (skip borders if fogged)
                if not state.debug_fog_off and state.fog_grid and not state.fog_grid[y][x]:
                    continue
                
                rid = state.region_grid[y][x]
                px = map_origin_x + (x - view_x0) * C.TILE_SIZE * scale
                py = map_origin_y + (y - view_y0) * C.TILE_SIZE * scale
                rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)

                # Region boundaries (unified yellow)
                if x + 1 <= view_x1 and state.region_grid[y][x + 1] != rid:
                    pygame.draw.line(screen, C.ZOOM_REGION_BORDER_COLOR, (rect.right, rect.top), (rect.right, rect.bottom), 4)
                if y + 1 <= view_y1 and state.region_grid[y + 1][x] != rid:
                    pygame.draw.line(screen, C.ZOOM_REGION_BORDER_COLOR, (rect.left, rect.bottom), (rect.right, rect.bottom), 4)
                
                # Faction borders (gold, thicker)
                is_player = (rid == state.player_region_id)
                faction_border_color = C.FACTION_BORDER_COLOR
                faction_border_width = 6
                
                if x + 1 <= view_x1:
                    rid_r = state.region_grid[y][x + 1]
                    is_player_r = (rid_r == state.player_region_id)
                    if is_player != is_player_r:
                        pygame.draw.line(screen, faction_border_color, (rect.right, rect.top), (rect.right, rect.bottom), faction_border_width)
                
                if y + 1 <= view_y1:
                    rid_d = state.region_grid[y + 1][x]
                    is_player_d = (rid_d == state.player_region_id)
                    if is_player != is_player_d:
                        pygame.draw.line(screen, faction_border_color, (rect.left, rect.bottom), (rect.right, rect.bottom), faction_border_width)

    mx, my = pygame.mouse.get_pos()
    hover_tile = None
    if mx >= map_origin_x:
        tx = (mx - map_origin_x) // (C.TILE_SIZE * scale) + view_x0
        ty = (my - map_origin_y) // (C.TILE_SIZE * scale) + view_y0
        if view_x0 <= tx <= view_x1 and view_y0 <= ty <= view_y1:
            hover_tile = (tx, ty)
            
            # Hover highlight for explorable regions (only when explorer is selected)
            selected_units = [u for u in state.units if u.selected]
            if selected_units:
                hover_rid = state.region_grid[ty][tx]
                
                # Build adjacent regions cache if needed
                from game1 import build_adjacent_regions_cache
                if state.adjacent_regions_cache is None:
                    build_adjacent_regions_cache(state)
                
                # Check if hovering over an adjacent (explorable) region that is fogged
                if (state.adjacent_regions_cache and 
                    hover_rid in state.adjacent_regions_cache and 
                    hover_rid != state.player_region_id and
                    not state.debug_fog_off and
                    state.fog_grid and
                    not state.fog_grid[ty][tx]):
                    
                    # Draw lighter overlay on fogged tiles of this region in view
                    for y in range(view_y0, view_y1 + 1):
                        for x in range(view_x0, view_x1 + 1):
                            if (state.region_grid[y][x] == hover_rid and 
                                state.fog_grid and 
                                not state.fog_grid[y][x]):
                                px = map_origin_x + (x - view_x0) * C.TILE_SIZE * scale
                                py = map_origin_y + (y - view_y0) * C.TILE_SIZE * scale
                                rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                                pygame.draw.rect(screen, (60, 60, 60), rect)
            
            # Yellow border for hovered tile
            hx = map_origin_x + (tx - view_x0) * C.TILE_SIZE * scale
            hy = map_origin_y + (ty - view_y0) * C.TILE_SIZE * scale
            pygame.draw.rect(screen, (255, 255, 0), (hx, hy, C.TILE_SIZE * scale, C.TILE_SIZE * scale), 2)

    if state.highlight_frames_remaining > 0:
        cx, cy = state.player_region_center
        if view_x0 <= cx <= view_x1 and view_y0 <= cy <= view_y1:
            center_px = map_origin_x + (cx - view_x0) * C.TILE_SIZE * scale + (C.TILE_SIZE * scale) // 2
            center_py = map_origin_y + (cy - view_y0) * C.TILE_SIZE * scale + (C.TILE_SIZE * scale) // 2
            base_radius = max(int(math.sqrt(max(1, len(state.player_region_mask))) * C.TILE_SIZE * scale * 0.3), C.TILE_SIZE * scale)
            pulsate = int(3 * math.sin((C.HIGHLIGHT_FRAMES - state.highlight_frames_remaining) * 0.2))
            radius = base_radius + pulsate
            pygame.draw.circle(screen, (255, 240, 0), (center_px, center_py), radius, 3)
            pygame.draw.circle(screen, (255, 255, 255), (center_px, center_py), max(1, radius - 4), 1)

    # Render units in zoom view
    for unit in state.units:
        ux = int(unit.x)
        uy = int(unit.y)
        if view_x0 <= ux <= view_x1 and view_y0 <= uy <= view_y1:
            unit_px = map_origin_x + (ux - view_x0) * C.TILE_SIZE * scale + (C.TILE_SIZE * scale) // 2
            unit_py = map_origin_y + (uy - view_y0) * C.TILE_SIZE * scale + (C.TILE_SIZE * scale) // 2
            
            # Draw unit circle
            color = (0, 200, 255) if unit.selected else (100, 200, 255)
            radius = (C.TILE_SIZE * scale) // 2
            pygame.draw.circle(screen, color, (unit_px, unit_py), radius, 0)
            pygame.draw.circle(screen, (255, 255, 255), (unit_px, unit_py), radius, 2)

    render_panel(screen, font, state, hover_tile=hover_tile)

    # Render Confirmation Dialog (Same as render_main)
    if state.confirm_dialog:
        # Overlay
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))
        
        # Dialog Box
        dialog_w, dialog_h = 400, 200
        dialog_x = (C.SCREEN_WIDTH - dialog_w) // 2
        dialog_y = (C.SCREEN_HEIGHT - dialog_h) // 2
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        
        pygame.draw.rect(screen, C.WHITE, dialog_rect)
        pygame.draw.rect(screen, C.BLACK, dialog_rect, 2)
        
        # Message
        msg = state.confirm_dialog.get("message", "Confirm?")
        msg_surf = font.render(msg, True, C.BLACK)
        msg_rect = msg_surf.get_rect(center=(dialog_x + dialog_w // 2, dialog_y + 60))
        screen.blit(msg_surf, msg_rect)
        
        # Buttons
        btn_w, btn_h = 100, 40
        yes_rect = pygame.Rect(dialog_x + 60, dialog_y + 120, btn_w, btn_h)
        no_rect = pygame.Rect(dialog_x + dialog_w - 60 - btn_w, dialog_y + 120, btn_w, btn_h)
        
        # Store rects in state for click handling
        state.confirm_dialog["yes_rect"] = yes_rect
        state.confirm_dialog["no_rect"] = no_rect
        
        pygame.draw.rect(screen, (200, 255, 200), yes_rect)
        pygame.draw.rect(screen, C.BLACK, yes_rect, 1)
        yes_text = font.render("はい", True, C.BLACK)
        yes_text_rect = yes_text.get_rect(center=yes_rect.center)
        screen.blit(yes_text, yes_text_rect)
        
        pygame.draw.rect(screen, (255, 200, 200), no_rect)
        pygame.draw.rect(screen, C.BLACK, no_rect, 1)
        no_text = font.render("いいえ", True, C.BLACK)
        no_text_rect = no_text.get_rect(center=no_rect.center)
        screen.blit(no_text, no_text_rect)


def pre_render_map(state):
    """
    Render the entire map to a surface and store it in state.map_surface.
    """
    if not state.biome_grid or not state.region_grid:
        return

    width = C.BASE_GRID_WIDTH * C.TILE_SIZE
    height = C.BASE_GRID_HEIGHT * C.TILE_SIZE
    surf = pygame.Surface((width, height))
    
    # Draw tiles
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            b = state.biome_grid[y][x]
            color = C.BIOME_COLORS.get(b, C.GREY)
            rid = state.region_grid[y][x]
            if rid == state.player_region_id:
                color = tuple(min(255, c + 40) for c in color)
            
            rect = pygame.Rect(x * C.TILE_SIZE, y * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE)
            pygame.draw.rect(surf, color, rect)

    # Draw region boundaries
    boundary_color = C.REGION_BORDER_COLOR
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            rid = state.region_grid[y][x]
            if x + 1 < C.BASE_GRID_WIDTH:
                rid_r = state.region_grid[y][x + 1]
                if rid != rid_r:
                    x0 = (x + 1) * C.TILE_SIZE
                    y0 = y * C.TILE_SIZE
                    pygame.draw.line(surf, boundary_color, (x0, y0), (x0, y0 + C.TILE_SIZE), 1)
            if y + 1 < C.BASE_GRID_HEIGHT:
                rid_d = state.region_grid[y + 1][x]
                if rid != rid_d:
                    x0 = x * C.TILE_SIZE
                    y0 = (y + 1) * C.TILE_SIZE
                    pygame.draw.line(surf, boundary_color, (x0, y0), (x0 + C.TILE_SIZE, y0), 1)
    
    # Draw faction borders (thicker, colored)
    # For now, only player faction exists
    faction_border_color = C.FACTION_BORDER_COLOR  # Gold color for player faction
    faction_border_width = 3
    
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            rid = state.region_grid[y][x]
            is_player = (rid == state.player_region_id)
            
            # Check right neighbor
            if x + 1 < C.BASE_GRID_WIDTH:
                rid_r = state.region_grid[y][x + 1]
                is_player_r = (rid_r == state.player_region_id)
                
                # Draw faction border if one side is player and other is not
                if is_player != is_player_r:
                    x0 = (x + 1) * C.TILE_SIZE
                    y0 = y * C.TILE_SIZE
                    pygame.draw.line(surf, faction_border_color, (x0, y0), (x0, y0 + C.TILE_SIZE), faction_border_width)
            
            # Check bottom neighbor
            if y + 1 < C.BASE_GRID_HEIGHT:
                rid_d = state.region_grid[y + 1][x]
                is_player_d = (rid_d == state.player_region_id)
                
                # Draw faction border if one side is player and other is not
                if is_player != is_player_d:
                    x0 = x * C.TILE_SIZE
                    y0 = (y + 1) * C.TILE_SIZE
                    pygame.draw.line(surf, faction_border_color, (x0, y0), (x0 + C.TILE_SIZE, y0), faction_border_width)
    
    state.map_surface = surf


def update_fog_surface(state):
    """
    Update state.fog_surface based on state.fog_grid.
    We create a black surface and punch holes (alpha=0) where visible.
    """
    if not state.fog_grid:
        return

    width = C.BASE_GRID_WIDTH * C.TILE_SIZE
    height = C.BASE_GRID_HEIGHT * C.TILE_SIZE
    
    # If surface doesn't exist, create it
    if state.fog_surface is None:
        state.fog_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        state.fog_surface.fill((0, 0, 0, 255)) # Opaque black
        
        # Initial punch
        for y in range(C.BASE_GRID_HEIGHT):
            for x in range(C.BASE_GRID_WIDTH):
                if state.fog_grid[y][x]:
                    rect = pygame.Rect(x * C.TILE_SIZE, y * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE)
                    # Clear alpha to 0
                    state.fog_surface.fill((0, 0, 0, 0), rect)


def render_main(screen, font, state, back_button_rect):
    if state.biome_grid and state.region_grid:
        # Check if cache exists, if not create it
        if state.map_surface is None:
            pre_render_map(state)
        
        # Blit the cached map
        if state.map_surface:
            screen.blit(state.map_surface, (C.INFO_PANEL_WIDTH, 0))

        # Fog of War
        if not state.debug_fog_off:
            if state.fog_surface is None:
                update_fog_surface(state)
            if state.fog_surface:
                screen.blit(state.fog_surface, (C.INFO_PANEL_WIDTH, 0))
        
        # Hover highlight for explorable regions (only when explorer is selected)
        selected_units = [u for u in state.units if u.selected]
        if selected_units:
            mx, my = pygame.mouse.get_pos()
            if mx >= C.INFO_PANEL_WIDTH:
                hover_gx = (mx - C.INFO_PANEL_WIDTH) // C.TILE_SIZE
                hover_gy = my // C.TILE_SIZE
                
                if 0 <= hover_gx < C.BASE_GRID_WIDTH and 0 <= hover_gy < C.BASE_GRID_HEIGHT:
                    hover_rid = state.region_grid[hover_gy][hover_gx]
                    
                    # Build adjacent regions cache if needed
                    from game1 import build_adjacent_regions_cache
                    if state.adjacent_regions_cache is None:
                        build_adjacent_regions_cache(state)
                    
                    # Check if hovering over an adjacent (explorable) region that is fogged
                    if (state.adjacent_regions_cache and 
                        hover_rid in state.adjacent_regions_cache and 
                        hover_rid != state.player_region_id):
                        
                        # Check if this region has any fog
                        has_fog = False
                        if state.fog_grid:
                            for y in range(C.BASE_GRID_HEIGHT):
                                for x in range(C.BASE_GRID_WIDTH):
                                    if state.region_grid[y][x] == hover_rid and not state.fog_grid[y][x]:
                                        has_fog = True
                                        break
                                if has_fog:
                                    break
                        
                        # Draw lighter overlay on fogged tiles of this region
                        if has_fog:
                            hover_surface = pygame.Surface((C.BASE_GRID_WIDTH * C.TILE_SIZE, C.BASE_GRID_HEIGHT * C.TILE_SIZE), pygame.SRCALPHA)
                            for y in range(C.BASE_GRID_HEIGHT):
                                for x in range(C.BASE_GRID_WIDTH):
                                    if state.region_grid[y][x] == hover_rid and not state.fog_grid[y][x]:
                                        rect = pygame.Rect(x * C.TILE_SIZE, y * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE)
                                        hover_surface.fill((60, 60, 60, 255), rect)  # Lighter gray, same alpha
                            screen.blit(hover_surface, (C.INFO_PANEL_WIDTH, 0))

        # Dynamic highlights (Selection)
        if state.selected_region is not None:
            highlight_color = (255, 220, 0)
            for y in range(C.BASE_GRID_HEIGHT):
                for x in range(C.BASE_GRID_WIDTH):
                    rid = state.region_grid[y][x]
                    if rid == state.selected_region:
                         # Check neighbors for boundary
                        if x + 1 < C.BASE_GRID_WIDTH and state.region_grid[y][x+1] != rid:
                             x0 = C.INFO_PANEL_WIDTH + (x + 1) * C.TILE_SIZE
                             y0 = y * C.TILE_SIZE
                             pygame.draw.line(screen, highlight_color, (x0, y0), (x0, y0 + C.TILE_SIZE), 2)
                        if x > 0 and state.region_grid[y][x-1] != rid:
                             x0 = C.INFO_PANEL_WIDTH + x * C.TILE_SIZE
                             y0 = y * C.TILE_SIZE
                             pygame.draw.line(screen, highlight_color, (x0, y0), (x0, y0 + C.TILE_SIZE), 2)
                        if y + 1 < C.BASE_GRID_HEIGHT and state.region_grid[y+1][x] != rid:
                             x0 = C.INFO_PANEL_WIDTH + x * C.TILE_SIZE
                             y0 = (y + 1) * C.TILE_SIZE
                             pygame.draw.line(screen, highlight_color, (x0, y0), (x0 + C.TILE_SIZE, y0), 2)
                        if y > 0 and state.region_grid[y-1][x] != rid:
                             x0 = C.INFO_PANEL_WIDTH + x * C.TILE_SIZE
                             y0 = y * C.TILE_SIZE
                             pygame.draw.line(screen, highlight_color, (x0, y0), (x0 + C.TILE_SIZE, y0), 2)

    if state.region_seeds:
        for idx, (sx, sy) in enumerate(state.region_seeds):
            # Only draw seeds if visible or fog off
            if not state.debug_fog_off and state.fog_grid and not state.fog_grid[sy][sx]:
                continue
                
            if idx == state.player_region_id:
                color = (255, 220, 0)
            elif idx == state.selected_region:
                color = (255, 200, 0)
            else:
                color = C.WHITE
            rect = pygame.Rect(C.INFO_PANEL_WIDTH + sx * C.TILE_SIZE, sy * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE)
            pygame.draw.rect(screen, color, rect)

    if state.highlight_frames_remaining > 0:
        cx, cy = state.player_region_center
        center_px = C.INFO_PANEL_WIDTH + cx * C.TILE_SIZE + C.TILE_SIZE // 2
        center_py = cy * C.TILE_SIZE + C.TILE_SIZE // 2
        base_radius = max(int(math.sqrt(max(1, len(state.player_region_mask))) * C.TILE_SIZE * 1.2), C.TILE_SIZE * 3)
        pulsate = int(3 * math.sin((C.HIGHLIGHT_FRAMES - state.highlight_frames_remaining) * 0.2))
        radius = base_radius + pulsate
        pygame.draw.circle(screen, (255, 240, 0), (center_px, center_py), radius, 3)
        pygame.draw.circle(screen, (255, 255, 255), (center_px, center_py), max(1, radius - 4), 1)

    # Render units
    for unit in state.units:
        unit_px = C.INFO_PANEL_WIDTH + int(unit.x * C.TILE_SIZE) + C.TILE_SIZE // 2
        unit_py = int(unit.y * C.TILE_SIZE) + C.TILE_SIZE // 2
        
        # Draw unit circle
        color = (0, 200, 255) if unit.selected else (100, 200, 255)
        pygame.draw.circle(screen, color, (unit_px, unit_py), C.TILE_SIZE // 2, 0)
        pygame.draw.circle(screen, (255, 255, 255), (unit_px, unit_py), C.TILE_SIZE // 2, 1)
        
        # Draw movement target if exists
        if unit.target_x is not None and unit.target_y is not None:
            target_px = C.INFO_PANEL_WIDTH + int(unit.target_x * C.TILE_SIZE) + C.TILE_SIZE // 2
            target_py = int(unit.target_y * C.TILE_SIZE) + C.TILE_SIZE // 2
            pygame.draw.line(screen, (200, 200, 0), (unit_px, unit_py), (target_px, target_py), 1)
            pygame.draw.circle(screen, (255, 255, 0), (target_px, target_py), 3, 0)

    player_rect = pygame.Rect(
        C.INFO_PANEL_WIDTH + state.player_grid_x * C.TILE_SIZE,
        state.player_grid_y * C.TILE_SIZE,
        C.TILE_SIZE,
        C.TILE_SIZE,
    )
    pygame.draw.rect(screen, C.WHITE, player_rect)

    render_panel(screen, font, state)

    pygame.draw.rect(screen, C.GREY, back_button_rect)
    pygame.draw.rect(screen, C.WHITE, back_button_rect, 1)
    back_text = font.render("スタートに戻る", True, C.WHITE)
    back_rect = back_text.get_rect(center=back_button_rect.center)
    screen.blit(back_text, back_rect)
    
    # Debug Fog Button
    debug_btn_rect = pygame.Rect(C.SCREEN_WIDTH - 110, C.SCREEN_HEIGHT - 40, 100, 30)
    bg_col = C.GREY if not state.debug_fog_off else (150, 50, 50)
    pygame.draw.rect(screen, bg_col, debug_btn_rect)
    pygame.draw.rect(screen, C.WHITE, debug_btn_rect, 1)
    fog_status = "Fog: ON" if not state.debug_fog_off else "Fog: OFF"
    fog_text = font.render(fog_status, True, C.WHITE)
    fog_rect = fog_text.get_rect(center=debug_btn_rect.center)
    screen.blit(fog_text, fog_rect)
    
    # Render Confirmation Dialog
    if state.confirm_dialog:
        # Overlay
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))
        
        # Dialog Box
        dialog_w, dialog_h = 400, 200
        dialog_x = (C.SCREEN_WIDTH - dialog_w) // 2
        dialog_y = (C.SCREEN_HEIGHT - dialog_h) // 2
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        
        pygame.draw.rect(screen, C.WHITE, dialog_rect)
        pygame.draw.rect(screen, C.BLACK, dialog_rect, 2)
        
        # Message
        msg = state.confirm_dialog.get("message", "Confirm?")
        msg_surf = font.render(msg, True, C.BLACK)
        msg_rect = msg_surf.get_rect(center=(dialog_x + dialog_w // 2, dialog_y + 60))
        screen.blit(msg_surf, msg_rect)
        
        # Buttons
        btn_w, btn_h = 100, 40
        yes_rect = pygame.Rect(dialog_x + 60, dialog_y + 120, btn_w, btn_h)
        no_rect = pygame.Rect(dialog_x + dialog_w - 60 - btn_w, dialog_y + 120, btn_w, btn_h)
        
        # Store rects in state for click handling (hacky but works for now)
        state.confirm_dialog["yes_rect"] = yes_rect
        state.confirm_dialog["no_rect"] = no_rect
        
        pygame.draw.rect(screen, (200, 255, 200), yes_rect)
        pygame.draw.rect(screen, C.BLACK, yes_rect, 1)
        yes_text = font.render("はい", True, C.BLACK)
        yes_text_rect = yes_text.get_rect(center=yes_rect.center)
        screen.blit(yes_text, yes_text_rect)
        
        pygame.draw.rect(screen, (255, 200, 200), no_rect)
        pygame.draw.rect(screen, C.BLACK, no_rect, 1)
        no_text = font.render("いいえ", True, C.BLACK)
        no_text_rect = no_text.get_rect(center=no_rect.center)
        screen.blit(no_text, no_text_rect)
