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
    items = sorted(dist.items(), key=lambda kv: kv[1], reverse=True)[:3]
    return " / ".join(f"{C.BIOME_NAMES.get(k, k)} {v}%" for k, v in items)


def render_menu(screen, font, button_rect):
    title = "Tile Exploration - Biomes"
    t_surf = font.render(title, True, C.WHITE)
    t_rect = t_surf.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 - 80))
    screen.blit(t_surf, t_rect)

    pygame.draw.rect(screen, C.GREY, button_rect)
    pygame.draw.rect(screen, C.WHITE, button_rect, 2)
    btn_text = font.render("スタート", True, C.WHITE)
    btn_rect = btn_text.get_rect(center=button_rect.center)
    screen.blit(btn_text, btn_rect)


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
        draw_text(screen, font, f"資源: {format_weights(info['resources'])}", pad, current_y)
        current_y += lh
        draw_text(screen, font, f"危険: {format_weights(info['dangers'])}", pad, current_y)
        current_y += lh
        draw_text(screen, font, f"構成: {format_distribution(info['distribution'])}", pad, current_y)
        current_y += lh
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

    hover_tile = None
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
                pygame.draw.rect(screen, (160, 160, 160), rect, 1)
                if x + 1 <= view_x1 and state.region_grid[y][x + 1] != rid:
                    col = (255, 160, 0) if (rid == state.zoom_region_id or state.region_grid[y][x + 1] == state.zoom_region_id) else (255, 200, 120)
                    pygame.draw.line(screen, col, (rect.right, rect.top), (rect.right, rect.bottom), 8)
                if y + 1 <= view_y1 and state.region_grid[y + 1][x] != rid:
                    col = (255, 160, 0) if (rid == state.zoom_region_id or state.region_grid[y + 1][x] == state.zoom_region_id) else (255, 200, 120)
                    pygame.draw.line(screen, col, (rect.left, rect.bottom), (rect.right, rect.bottom), 8)

    mx, my = pygame.mouse.get_pos()
    if mx >= map_origin_x:
        tx = (mx - map_origin_x) // (C.TILE_SIZE * scale) + view_x0
        ty = (my - map_origin_y) // (C.TILE_SIZE * scale) + view_y0
        if view_x0 <= tx <= view_x1 and view_y0 <= ty <= view_y1:
            hover_tile = (tx, ty)
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

    # Draw boundaries
    boundary_color = (0, 0, 0)
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
