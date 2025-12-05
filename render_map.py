import math
import pygame
import config as C
from render_ui import render_panel, render_top_bar, render_unit_list

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
    
    # Draw player territory overlay (semi-transparent)
    if state.player_region_mask:
        overlay_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        for (x, y) in state.player_region_mask:
            rect = pygame.Rect(x * C.TILE_SIZE, y * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE)
            overlay_surface.fill(C.PLAYER_TERRITORY_OVERLAY_COLOR, rect)
        surf.blit(overlay_surface, (0, 0))
    
    # Draw faction borders (thicker, colored)
    # For now, only player faction exists
    faction_border_color = C.FACTION_BORDER_COLOR
    faction_border_width = 3
    
    for y in range(C.BASE_GRID_HEIGHT):
        for x in range(C.BASE_GRID_WIDTH):
            is_player = (x, y) in state.player_region_mask
            
            # Check right neighbor
            if x + 1 < C.BASE_GRID_WIDTH:
                is_player_r = (x + 1, y) in state.player_region_mask
                
                # Draw faction border if one side is player and other is not
                if is_player != is_player_r:
                    x0 = (x + 1) * C.TILE_SIZE
                    y0 = y * C.TILE_SIZE
                    pygame.draw.line(surf, faction_border_color, (x0, y0), (x0, y0 + C.TILE_SIZE), faction_border_width)
            
            # Check bottom neighbor
            if y + 1 < C.BASE_GRID_HEIGHT:
                is_player_d = (x, y + 1) in state.player_region_mask
                
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


def render_zoom(screen, font, state):
    scale = C.ZOOM_SCALE
    map_origin_x = C.INFO_PANEL_WIDTH
    map_origin_y = C.TOP_BAR_HEIGHT
    view_x0 = max(0, state.zoom_origin[0])
    view_y0 = max(0, state.zoom_origin[1])
    view_w = (C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH) // (C.TILE_SIZE * scale) + 2
    view_h = (C.SCREEN_HEIGHT - C.TOP_BAR_HEIGHT) // (C.TILE_SIZE * scale) + 2
    view_x1 = min(C.BASE_GRID_WIDTH - 1, view_x0 + view_w)
    view_y1 = min(C.BASE_GRID_HEIGHT - 1, view_y0 + view_h)

    # Generate full map cache if needed (only once, or when map changes)
    if state.zoom_full_map_cache is None:
        scale = C.ZOOM_SCALE
        full_width = C.BASE_GRID_WIDTH * C.TILE_SIZE * scale
        full_height = C.BASE_GRID_HEIGHT * C.TILE_SIZE * scale
        
        # Create cache surface for full map
        cache_surface = pygame.Surface((full_width, full_height))
        
        # Create a transparent surface for grid lines
        grid_surface = pygame.Surface((full_width, full_height), pygame.SRCALPHA)
        
        # Render all tiles and grid lines
        if state.biome_grid and state.region_grid:
            for y in range(C.BASE_GRID_HEIGHT):
                for x in range(C.BASE_GRID_WIDTH):
                    b = state.biome_grid[y][x]
                    color = C.BIOME_COLORS.get(b, C.GREY)
                    
                    px = x * C.TILE_SIZE * scale
                    py = y * C.TILE_SIZE * scale
                    rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                    pygame.draw.rect(cache_surface, color, rect)
                    
                    # Draw grid lines with 50% transparency
                    grid_color = (160, 160, 160, 128)
                    pygame.draw.line(grid_surface, grid_color, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1), 1)
                    pygame.draw.line(grid_surface, grid_color, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1), 1)
        
        # Blit grid onto cache
        cache_surface.blit(grid_surface, (0, 0))
        
        # Draw player territory overlay (semi-transparent)
        if state.player_region_mask:
            overlay_surface = pygame.Surface((full_width, full_height), pygame.SRCALPHA)
            for (x, y) in state.player_region_mask:
                px = x * C.TILE_SIZE * scale
                py = y * C.TILE_SIZE * scale
                rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                overlay_surface.fill(C.PLAYER_TERRITORY_OVERLAY_COLOR, rect)
            cache_surface.blit(overlay_surface, (0, 0))
        
        # Draw borders
        if state.biome_grid and state.region_grid:
            for y in range(C.BASE_GRID_HEIGHT):
                for x in range(C.BASE_GRID_WIDTH):
                    rid = state.region_grid[y][x]
                    px = x * C.TILE_SIZE * scale
                    py = y * C.TILE_SIZE * scale
                    rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                    
                    # Region boundaries
                    if x + 1 < C.BASE_GRID_WIDTH and state.region_grid[y][x + 1] != rid:
                        pygame.draw.line(cache_surface, C.ZOOM_REGION_BORDER_COLOR, (rect.right, rect.top), (rect.right, rect.bottom), 4)
                    if y + 1 < C.BASE_GRID_HEIGHT and state.region_grid[y + 1][x] != rid:
                        pygame.draw.line(cache_surface, C.ZOOM_REGION_BORDER_COLOR, (rect.left, rect.bottom), (rect.right, rect.bottom), 4)
                    
                    # Faction borders
                    is_player = (x, y) in state.player_region_mask
                    faction_border_color = C.FACTION_BORDER_COLOR
                    faction_border_width = 6
                    
                    if x + 1 < C.BASE_GRID_WIDTH:
                        is_player_r = (x + 1, y) in state.player_region_mask
                        if is_player != is_player_r:
                            pygame.draw.line(cache_surface, faction_border_color, (rect.right, rect.top), (rect.right, rect.bottom), faction_border_width)
                    
                    if y + 1 < C.BASE_GRID_HEIGHT:
                        is_player_d = (x, y + 1) in state.player_region_mask
                        if is_player != is_player_d:
                            pygame.draw.line(cache_surface, faction_border_color, (rect.left, rect.bottom), (rect.right, rect.bottom), faction_border_width)
        
        state.zoom_full_map_cache = cache_surface
    
    # Generate or update fog layer
    if state.zoom_fog_layer is None and state.fog_grid:
        scale = C.ZOOM_SCALE
        full_width = C.BASE_GRID_WIDTH * C.TILE_SIZE * scale
        full_height = C.BASE_GRID_HEIGHT * C.TILE_SIZE * scale
        
        # Create fog layer (black with alpha)
        fog_layer = pygame.Surface((full_width, full_height), pygame.SRCALPHA)
        fog_layer.fill((0, 0, 0, 255))  # Fully opaque black
        
        # Punch holes where fog is revealed
        if not state.debug_fog_off:
            for y in range(C.BASE_GRID_HEIGHT):
                for x in range(C.BASE_GRID_WIDTH):
                    if state.fog_grid[y][x]:
                        px = x * C.TILE_SIZE * scale
                        py = y * C.TILE_SIZE * scale
                        rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                        fog_layer.fill((0, 0, 0, 0), rect)  # Transparent
        else:
            # Debug mode: all transparent
            fog_layer.fill((0, 0, 0, 0))
        
        state.zoom_fog_layer = fog_layer
    
    # Calculate viewport to blit
    view_width_px = C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH
    view_height_px = C.SCREEN_HEIGHT - C.TOP_BAR_HEIGHT
    
    source_x = view_x0 * C.TILE_SIZE * scale
    source_y = view_y0 * C.TILE_SIZE * scale
    source_rect = pygame.Rect(source_x, source_y, view_width_px, view_height_px)
    
    # Blit base map
    if state.zoom_full_map_cache:
        screen.blit(state.zoom_full_map_cache, (map_origin_x, map_origin_y), source_rect)
    
    # Blit fog layer
    if state.zoom_fog_layer and not state.debug_fog_off:
        screen.blit(state.zoom_fog_layer, (map_origin_x, map_origin_y), source_rect)

    mx, my = pygame.mouse.get_pos()
    hover_tile = None
    if mx >= map_origin_x:
        tx = (mx - map_origin_x) // (C.TILE_SIZE * scale) + view_x0
        ty = (my - map_origin_y) // (C.TILE_SIZE * scale) + view_y0
        if view_x0 <= tx <= view_x1 and view_y0 <= ty <= view_y1:
            hover_tile = (tx, ty)
            
            # Hover highlight for explorable regions (only when explorer is selected)
            selected_units = [u for u in state.units if u.selected and u.unit_type == "explorer"]
            if selected_units:
                hover_rid = state.region_grid[ty][tx]
                
                # Build adjacent regions cache if needed
                from game_system import build_adjacent_regions_cache
                if state.adjacent_regions_cache is None:
                    build_adjacent_regions_cache(state)
                
                # Check if hovering over an adjacent (explorable) region
                # We don't strictly require the hovered tile to be fogged anymore, 
                # as long as the region is valid for exploration.
                if (state.adjacent_regions_cache and 
                    hover_rid in state.adjacent_regions_cache and 
                    hover_rid != state.player_region_id):
                    
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



    # Selected region highlight in zoom view
    if state.selected_region is not None:
        # Cache check: rebuild only if selection changed
        if not hasattr(state, '_cached_selected_region_id_zoom') or state._cached_selected_region_id_zoom != state.selected_region:
            state._cached_selected_region_id_zoom = state.selected_region
            
            # Create full-map overlay surface (cached)
            scale = C.ZOOM_SCALE
            full_width = C.BASE_GRID_WIDTH * C.TILE_SIZE * scale
            full_height = C.BASE_GRID_HEIGHT * C.TILE_SIZE * scale
            highlight_surface = pygame.Surface((full_width, full_height), pygame.SRCALPHA)
            highlight_color = (255, 220, 0, 100)  # Yellow with alpha
            
            for y in range(C.BASE_GRID_HEIGHT):
                for x in range(C.BASE_GRID_WIDTH):
                    rid = state.region_grid[y][x]
                    if rid == state.selected_region:
                        px = x * C.TILE_SIZE * scale
                        py = y * C.TILE_SIZE * scale
                        rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                        highlight_surface.fill(highlight_color, rect)
            
            state.selected_region_overlay_zoom_cache = highlight_surface
        
        # Blit cached overlay (only visible portion)
        if state.selected_region_overlay_zoom_cache:
            source_x = view_x0 * C.TILE_SIZE * scale
            source_y = view_y0 * C.TILE_SIZE * scale
            view_width_px = C.SCREEN_WIDTH - C.INFO_PANEL_WIDTH
            view_height_px = C.SCREEN_HEIGHT - C.TOP_BAR_HEIGHT
            source_rect = pygame.Rect(source_x, source_y, view_width_px, view_height_px)
            screen.blit(state.selected_region_overlay_zoom_cache, (map_origin_x, map_origin_y), source_rect)
        
        # Draw border for clarity (only for visible tiles)
        border_color = (255, 220, 0)
        for y in range(view_y0, view_y1 + 1):
            for x in range(view_x0, view_x1 + 1):
                rid = state.region_grid[y][x]
                if rid == state.selected_region:
                    px = map_origin_x + (x - view_x0) * C.TILE_SIZE * scale
                    py = map_origin_y + (y - view_y0) * C.TILE_SIZE * scale
                    rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                    
                    # Check neighbors for boundary
                    if x + 1 <= view_x1 and state.region_grid[y][x + 1] != rid:
                        pygame.draw.line(screen, border_color, (rect.right, rect.top), (rect.right, rect.bottom), 3)
                    if x - 1 >= view_x0 and state.region_grid[y][x - 1] != rid:
                        pygame.draw.line(screen, border_color, (rect.left, rect.top), (rect.left, rect.bottom), 3)
                    if y + 1 <= view_y1 and state.region_grid[y + 1][x] != rid:
                        pygame.draw.line(screen, border_color, (rect.left, rect.bottom), (rect.right, rect.bottom), 3)
                    if y - 1 >= view_y0 and state.region_grid[y - 1][x] != rid:
                        pygame.draw.line(screen, border_color, (rect.left, rect.top), (rect.right, rect.top), 3)

    # Render Region Seeds (Centers)
    if state.region_seeds:
        for idx, (sx, sy) in enumerate(state.region_seeds):
            # Only draw seeds if visible or fog off
            if not state.debug_fog_off and state.fog_grid and not state.fog_grid[sy][sx]:
                continue
            
            # Skip SEA and LAKE
            if state.biome_grid[sy][sx] in ("SEA", "LAKE"):
                continue
            
            # Check if seed is in current view
            if view_x0 <= sx <= view_x1 and view_y0 <= sy <= view_y1:
                if idx == state.player_region_id:
                    color = (255, 220, 0)
                elif idx == state.selected_region:
                    color = (255, 200, 0)
                else:
                    color = C.WHITE
                
                px = map_origin_x + (sx - view_x0) * C.TILE_SIZE * scale
                py = map_origin_y + (sy - view_y0) * C.TILE_SIZE * scale
                rect = pygame.Rect(px, py, C.TILE_SIZE * scale, C.TILE_SIZE * scale)
                pygame.draw.rect(screen, color, rect)

    # Render Resource Nodes (Icons in corner of tiles)
    if state.resource_nodes:
        for node in state.resource_nodes:
            # Only draw if visible or fog off
            if not state.debug_fog_off and state.fog_grid and not state.fog_grid[node.y][node.x]:
                continue
            
            # Check if node is in current view
            if view_x0 <= node.x <= view_x1 and view_y0 <= node.y <= view_y1:
                px = map_origin_x + (node.x - view_x0) * C.TILE_SIZE * scale
                py = map_origin_y + (node.y - view_y0) * C.TILE_SIZE * scale
                
                # Draw icon in top-right corner of tile
                icon_size = max(3, C.TILE_SIZE * scale // 4)
                icon_x = px + C.TILE_SIZE * scale - icon_size - 2
                icon_y = py + 2
                
                # Choose color and shape based on resource type
                if node.type == "FISH":
                    # Blue circle
                    pygame.draw.circle(screen, (50, 150, 255), (icon_x + icon_size//2, icon_y + icon_size//2), icon_size//2)
                elif node.type == "FARM":
                    # Green square
                    pygame.draw.rect(screen, (100, 200, 50), (icon_x, icon_y, icon_size, icon_size))
                elif node.type == "GOLD":
                    # Yellow triangle
                    points = [(icon_x + icon_size//2, icon_y), (icon_x, icon_y + icon_size), (icon_x + icon_size, icon_y + icon_size)]
                    pygame.draw.polygon(screen, (255, 215, 0), points)
                elif node.type == "SILVER":
                    # White diamond
                    points = [(icon_x + icon_size//2, icon_y), (icon_x + icon_size, icon_y + icon_size//2), 
                             (icon_x + icon_size//2, icon_y + icon_size), (icon_x, icon_y + icon_size//2)]
                    pygame.draw.polygon(screen, (230, 230, 230), points)
                elif node.type == "ANIMAL":
                    # Brown circle
                    pygame.draw.circle(screen, (139, 90, 43), (icon_x + icon_size//2, icon_y + icon_size//2), icon_size//2)

    # Render units in zoom view
    for unit in state.units:
        ux = int(unit.x)
        uy = int(unit.y)
        if view_x0 <= ux <= view_x1 and view_y0 <= uy <= view_y1:
            unit_px = map_origin_x + (ux - view_x0) * C.TILE_SIZE * scale + (C.TILE_SIZE * scale) // 2
            unit_py = map_origin_y + (uy - view_y0) * C.TILE_SIZE * scale + (C.TILE_SIZE * scale) // 2
            
            # Draw unit circle
            base_color = C.UNIT_COLORS.get(unit.unit_type, (200, 200, 200))
            color = (0, 255, 255) if unit.selected else base_color
            radius = (C.TILE_SIZE * scale) // 2
            pygame.draw.circle(screen, color, (unit_px, unit_py), radius, 0)
            pygame.draw.circle(screen, (255, 255, 255), (unit_px, unit_py), radius, 2)

    render_panel(screen, font, state, hover_tile=hover_tile)
    render_top_bar(screen, font, state)
    render_unit_list(screen, font, state)

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


def render_world_view(screen, font, state, back_button_rect):
    if state.biome_grid and state.region_grid:
        # Check if cache exists, if not create it
        if state.map_surface is None:
            pre_render_map(state)
        
        # Blit the cached map
        if state.map_surface:
            screen.blit(state.map_surface, (C.INFO_PANEL_WIDTH, C.TOP_BAR_HEIGHT))

        # Fog of War
        if not state.debug_fog_off:
            if state.fog_surface is None:
                update_fog_surface(state)
            if state.fog_surface:
                screen.blit(state.fog_surface, (C.INFO_PANEL_WIDTH, C.TOP_BAR_HEIGHT))
        
        # Hover highlight for explorable regions (only when explorer is selected)
        selected_units = [u for u in state.units if u.selected]
        if selected_units:
            mx, my = pygame.mouse.get_pos()
            if mx >= C.INFO_PANEL_WIDTH and my >= C.TOP_BAR_HEIGHT:
                hover_gx = (mx - C.INFO_PANEL_WIDTH) // C.TILE_SIZE
                hover_gy = (my - C.TOP_BAR_HEIGHT) // C.TILE_SIZE
                
                if 0 <= hover_gx < C.BASE_GRID_WIDTH and 0 <= hover_gy < C.BASE_GRID_HEIGHT:
                    hover_rid = state.region_grid[hover_gy][hover_gx]
                    
                    # Build adjacent regions cache if needed
                    from game_system import build_adjacent_regions_cache
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
                            screen.blit(hover_surface, (C.INFO_PANEL_WIDTH, C.TOP_BAR_HEIGHT))

        # Dynamic highlights (Selection) - Fill entire region with semi-transparent yellow
        if state.selected_region is not None:
            # Cache check: rebuild overlay only if selection changed
            if not hasattr(state, '_cached_selected_region_id') or state._cached_selected_region_id != state.selected_region:
                # Selection changed, rebuild cache
                state._cached_selected_region_id = state.selected_region
                state._cached_selected_region_tiles = []
                
                for y in range(C.BASE_GRID_HEIGHT):
                    for x in range(C.BASE_GRID_WIDTH):
                        if state.region_grid[y][x] == state.selected_region:
                            state._cached_selected_region_tiles.append((x, y))
                
                # Create cached overlay surface
                highlight_surface = pygame.Surface((C.BASE_GRID_WIDTH * C.TILE_SIZE, C.BASE_GRID_HEIGHT * C.TILE_SIZE), pygame.SRCALPHA)
                highlight_color = (255, 220, 0, 100)  # Yellow with alpha
                
                for x, y in state._cached_selected_region_tiles:
                    rect = pygame.Rect(x * C.TILE_SIZE, y * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE)
                    highlight_surface.fill(highlight_color, rect)
                
                state.selected_region_overlay_cache = highlight_surface
            
            # Blit cached overlay
            if state.selected_region_overlay_cache:
                screen.blit(state.selected_region_overlay_cache, (C.INFO_PANEL_WIDTH, C.TOP_BAR_HEIGHT))
            
            # Draw border for clarity (still need to draw every frame, but much faster than filling)
            if hasattr(state, '_cached_selected_region_tiles'):
                border_color = (255, 220, 0)
                for x, y in state._cached_selected_region_tiles:
                    # Check neighbors for boundary
                    if x + 1 < C.BASE_GRID_WIDTH and state.region_grid[y][x+1] != state.selected_region:
                        x0 = C.INFO_PANEL_WIDTH + (x + 1) * C.TILE_SIZE
                        y0 = C.TOP_BAR_HEIGHT + y * C.TILE_SIZE
                        pygame.draw.line(screen, border_color, (x0, y0), (x0, y0 + C.TILE_SIZE), 2)
                    if x > 0 and state.region_grid[y][x-1] != state.selected_region:
                        x0 = C.INFO_PANEL_WIDTH + x * C.TILE_SIZE
                        y0 = C.TOP_BAR_HEIGHT + y * C.TILE_SIZE
                        pygame.draw.line(screen, border_color, (x0, y0), (x0, y0 + C.TILE_SIZE), 2)
                    if y + 1 < C.BASE_GRID_HEIGHT and state.region_grid[y+1][x] != state.selected_region:
                        x0 = C.INFO_PANEL_WIDTH + x * C.TILE_SIZE
                        y0 = C.TOP_BAR_HEIGHT + (y + 1) * C.TILE_SIZE
                        pygame.draw.line(screen, border_color, (x0, y0), (x0 + C.TILE_SIZE, y0), 2)
                    if y > 0 and state.region_grid[y-1][x] != state.selected_region:
                        x0 = C.INFO_PANEL_WIDTH + x * C.TILE_SIZE
                        y0 = C.TOP_BAR_HEIGHT + y * C.TILE_SIZE
                        pygame.draw.line(screen, border_color, (x0, y0), (x0 + C.TILE_SIZE, y0), 2)

    if state.region_seeds:
        for idx, (sx, sy) in enumerate(state.region_seeds):
            # Only draw seeds if visible or fog off
            if not state.debug_fog_off and state.fog_grid and not state.fog_grid[sy][sx]:
                continue
            
            # Skip SEA and LAKE
            if state.biome_grid[sy][sx] in ("SEA", "LAKE"):
                continue
                
            if idx == state.player_region_id:
                color = (255, 220, 0)
            elif idx == state.selected_region:
                color = (255, 200, 0)
            else:
                color = C.WHITE
            rect = pygame.Rect(C.INFO_PANEL_WIDTH + sx * C.TILE_SIZE, C.TOP_BAR_HEIGHT + sy * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE)
            pygame.draw.rect(screen, color, rect)



    # Render units
    for unit in state.units:
        unit_px = C.INFO_PANEL_WIDTH + int(unit.x * C.TILE_SIZE) + C.TILE_SIZE // 2
        unit_py = C.TOP_BAR_HEIGHT + int(unit.y * C.TILE_SIZE) + C.TILE_SIZE // 2
        
        # Draw unit circle
        color = (0, 200, 255) if unit.selected else (100, 200, 255)
        pygame.draw.circle(screen, color, (unit_px, unit_py), C.TILE_SIZE // 2, 0)
        pygame.draw.circle(screen, (255, 255, 255), (unit_px, unit_py), C.TILE_SIZE // 2, 1)
        
        # Draw movement target if exists
        if unit.target_x is not None and unit.target_y is not None:
            target_px = C.INFO_PANEL_WIDTH + int(unit.target_x * C.TILE_SIZE) + C.TILE_SIZE // 2
            target_py = C.TOP_BAR_HEIGHT + int(unit.target_y * C.TILE_SIZE) + C.TILE_SIZE // 2
            pygame.draw.line(screen, (200, 200, 0), (unit_px, unit_py), (target_px, target_py), 1)
            pygame.draw.circle(screen, (255, 255, 0), (target_px, target_py), 3, 0)

    player_rect = pygame.Rect(
        C.INFO_PANEL_WIDTH + state.player_grid_x * C.TILE_SIZE,
        C.TOP_BAR_HEIGHT + state.player_grid_y * C.TILE_SIZE,
        C.TILE_SIZE,
        C.TILE_SIZE,
    )
    pygame.draw.rect(screen, C.WHITE, player_rect)

    render_panel(screen, font, state)
    render_top_bar(screen, font, state)
    render_unit_list(screen, font, state)

    # Debug: Display region count and biome distribution (cached)
    if state.region_info and state.biome_grid:
        # Cache debug info to avoid recalculating every frame
        if not hasattr(state, '_cached_debug_info'):
            land_region_count = 0
            for idx, info in enumerate(state.region_info):
                # Check if this region has any land tiles
                has_land = False
                for y in range(C.BASE_GRID_HEIGHT):
                    for x in range(C.BASE_GRID_WIDTH):
                        if state.region_grid[y][x] == idx:
                            if state.biome_grid[y][x] not in ("SEA", "LAKE"):
                                has_land = True
                                break
                    if has_land:
                        break
                if has_land:
                    land_region_count += 1
            
            # Calculate biome distribution
            biome_counts = {}
            total_tiles = C.BASE_GRID_WIDTH * C.BASE_GRID_HEIGHT
            for y in range(C.BASE_GRID_HEIGHT):
                for x in range(C.BASE_GRID_WIDTH):
                    biome = state.biome_grid[y][x]
                    biome_counts[biome] = biome_counts.get(biome, 0) + 1
        
            # Sort by percentage
            biome_percentages = [(biome, (count / total_tiles) * 100) for biome, count in biome_counts.items()]
            biome_percentages.sort(key=lambda x: x[1], reverse=True)
            
            # Cache the results
            state._cached_debug_info = {
                'land_region_count': land_region_count,
                'biome_percentages': biome_percentages
            }
        
        # Display cached debug info
        debug_y = C.SCREEN_HEIGHT - 250  # Start 250 pixels from bottom
        
        # Region count
        region_count_text = f"陸リージョン数: {state._cached_debug_info['land_region_count']}"
        region_count_surf = font.render(region_count_text, True, C.WHITE)
        screen.blit(region_count_surf, (12, debug_y))
        debug_y += 20
        
        # Biome distribution
        for biome, percentage in state._cached_debug_info['biome_percentages']:
            if percentage >= 1.0:  # Only show biomes with 1% or more
                biome_name = C.BIOME_NAMES.get(biome, biome)
                biome_text = f"{biome_name}: {percentage:.1f}%"
                biome_surf = font.render(biome_text, True, C.WHITE)
                screen.blit(biome_surf, (12, debug_y))
                debug_y += 18

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
