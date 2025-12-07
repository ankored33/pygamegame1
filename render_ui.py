import pygame
import config as C
from render_utils import draw_text, draw_text_centered, format_weights, format_distribution

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
    
    # Load Button
    load_btn_rect = pygame.Rect(button_rect.x, button_rect.bottom + 20, button_rect.width, 40)
    pygame.draw.rect(screen, C.GREY, load_btn_rect)
    pygame.draw.rect(screen, C.WHITE, load_btn_rect, 2)
    load_text = font.render("ロード", True, C.WHITE)
    load_text_rect = load_text.get_rect(center=load_btn_rect.center)
    screen.blit(load_text, load_text_rect)
    
    state.menu_load_btn_rect = load_btn_rect; 

    state.menu_load_btn_rect = load_btn_rect; 

    # Map Gen Params Controls
    start_y = load_btn_rect.bottom + 20
    
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


def render_loading(screen, font):
    load_text = font.render("ロード中...", True, C.WHITE)
    load_rect = load_text.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2))
    screen.blit(load_text, load_rect)


def render_unit_list(screen, font, state):
    """Render unit list buttons in the top-right corner"""
    if not state.units:
        return
    
    # Button dimensions
    btn_width = C.UNIT_BUTTON_WIDTH
    btn_height = C.UNIT_BUTTON_HEIGHT
    btn_spacing = C.UNIT_BUTTON_SPACING
    start_x = C.SCREEN_WIDTH - btn_width - 12
    start_y = C.TOP_BAR_HEIGHT + 12
    
    # Store button rects for click handling
    if not hasattr(state, 'unit_button_rects'):
        state.unit_button_rects = []
    state.unit_button_rects.clear()
    
    for i, unit in enumerate(state.units):
        btn_y = start_y + i * (btn_height + btn_spacing)
        btn_rect = pygame.Rect(start_x, btn_y, btn_width, btn_height)
        
        # Store rect with unit reference
        state.unit_button_rects.append((btn_rect, unit))
        
        # Button background color based on selection and unit type
        unit_color = C.UNIT_COLORS.get(unit.unit_type, (150, 150, 150))
        if unit.selected:
            # Brighter when selected
            bg_color = tuple(min(255, c + 50) for c in unit_color)
            border_color = C.WHITE
            border_width = 2
        else:
            # Darker when not selected
            bg_color = tuple(max(0, c - 50) for c in unit_color)
            border_color = (100, 100, 100)
            border_width = 1
        
        # Draw button
        pygame.draw.rect(screen, bg_color, btn_rect)
        pygame.draw.rect(screen, border_color, btn_rect, border_width)
        
        # Unit name and info
        unit_name = C.UNIT_NAMES.get(unit.unit_type, unit.unit_type)
        
        # Determine status and region
        ux, uy = int(unit.x), int(unit.y)
        region_id = "?"
        if 0 <= ux < C.BASE_GRID_WIDTH and 0 <= uy < C.BASE_GRID_HEIGHT:
            region_id = state.region_grid[uy][ux]
            
        status = "待機"
        if unit.target_region_id is not None:
            status = "移動" # or Exploring
            if unit.unit_type == "explorer":
                status = "探索"
        elif unit.unit_type == "conquistador" and unit.conquering_region_id is not None:
            status = "征服"
            
        # Draw text
        # Draw text
        # Combine Name and Status into one line
        # "UnitName (RID:X) [Status]"
        full_text = f"{unit_name} (RID:{region_id})   [{status}]"
        
        text_surf = font.render(full_text, True, C.WHITE)
        tw, th = text_surf.get_size()
        
        # Scale down if too wide
        max_w = btn_width - 10
        if tw > max_w:
            scale = max_w / tw
            # Limit scale to avoid unreadable text (e.g. min 0.6)
            scale = max(0.6, scale)
            scaled_surf = pygame.transform.smoothscale(text_surf, (int(tw * scale), int(th * scale)))
            text_rect = scaled_surf.get_rect(center=btn_rect.center)
            screen.blit(scaled_surf, text_rect)
        else:
            text_rect = text_surf.get_rect(center=btn_rect.center)
            screen.blit(text_surf, text_rect)


def render_top_bar(screen, font, state):
    bar_rect = pygame.Rect(0, 0, C.SCREEN_WIDTH, C.TOP_BAR_HEIGHT)
    
    # Background
    pygame.draw.rect(screen, (40, 40, 40), bar_rect)
    pygame.draw.line(screen, C.WHITE, (0, C.TOP_BAR_HEIGHT), (C.SCREEN_WIDTH, C.TOP_BAR_HEIGHT), 1)
    
    pad = 12
    # Resources (Left)
    # Food
    food_text = f"食料: {state.food}"
    draw_text(screen, font, food_text, pad, 6, color=(255, 200, 150))
    
    # Gold
    gold_text = f"黄金: {state.gold}"
    draw_text(screen, font, gold_text, pad + 120, 6, color=(255, 215, 0))
    
    # Time (Right)
    if state.is_paused:
        status_text = "一時停止"
        spinner = "||"
    else:
        status_text = "進行中"
        spinner_idx = int(state.game_time / 15) % 4
        spinner = ["|", "／", "－", "＼"][spinner_idx]
        
    time_text = f"Day: {state.day}  {spinner}  ({status_text})"
    time_surf = font.render(time_text, True, C.WHITE)
    time_rect = time_surf.get_rect(right=C.SCREEN_WIDTH - pad, centery=C.TOP_BAR_HEIGHT // 2)
    screen.blit(time_surf, time_rect)
    
    # Save Button (Top Right, left of time?)
    # Or maybe extreme right if time is centered? Time is right-aligned.
    # Let's put Save button to the left of time
    save_btn_rect = pygame.Rect(time_rect.left - 60, 4, 50, 24)
    pygame.draw.rect(screen, C.GREY, save_btn_rect)
    pygame.draw.rect(screen, C.WHITE, save_btn_rect, 1)
    
    save_text = font.render("保存", True, C.WHITE)
    # Scale down if needed, but 2 chars should fit
    save_text_rect = save_text.get_rect(center=save_btn_rect.center)
    screen.blit(save_text, save_text_rect)
    
    state.game_save_btn_rect = save_btn_rect;


def render_panel(screen, font, state, hover_tile=None):
    # Adjust panel rect to start below top bar? 
    # Actually panel is full height on the left, but top bar is on top.
    # So we just draw panel normally, but maybe start text lower.
    panel_rect = pygame.Rect(0, 0, C.INFO_PANEL_WIDTH, C.SCREEN_HEIGHT)
    pygame.draw.rect(screen, C.DARK_GREY, panel_rect)

    pad = 12
    lh = 22
    # Start lower to account for top bar (approx 32px)
    current_y = pad + 32 
    
    if state.player_region_id is not None:
        draw_text(screen, font, f"自領域 ID: {state.player_region_id}", pad, current_y)
        current_y += lh
        draw_text(screen, font, f"タイル数: {len(state.player_region_mask)}", pad, current_y)
        current_y += lh

    current_y += lh # spacer

    # Selected Unit Info
    selected_units = [u for u in state.units if u.selected]
    if selected_units:
        unit = selected_units[0]
        unit_name = C.UNIT_NAMES.get(unit.unit_type, unit.unit_type)
        draw_text(screen, font, "選択ユニット", pad, current_y)
        current_y += lh
        draw_text(screen, font, f"タイプ: {unit_name}", pad, current_y)
        current_y += lh
        draw_text(screen, font, f"位置: ({int(unit.x)}, {int(unit.y)})", pad, current_y)
        current_y += lh
        if unit.target_region_id is not None:
            draw_text(screen, font, f"目標: リージョン {unit.target_region_id}", pad, current_y)
            current_y += lh
        current_y += lh # spacer

    draw_text(screen, font, "選択リージョン", pad, current_y)
    current_y += lh
    if state.selected_region is not None and state.selected_region >= 0 and state.region_info:
        info = state.region_info[state.selected_region]
        draw_text(screen, font, f"ID: {state.selected_region}", pad, current_y)
        current_y += lh
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
            
            # Check for resource node at this tile
            # OPTIMIZED: Use O(1) map lookup
            if hasattr(state, 'resource_map') and (hx, hy) in state.resource_map:
                node = state.resource_map[(hx, hy)]
                res_config = C.RESOURCE_TYPES.get(node.type, {})
                res_name = res_config.get("display_name", node.type)
                draw_text(screen, font, f"資源: {res_name} ({node.development}/{node.max_development})", pad, current_y)
                current_y += lh
            elif hasattr(state, 'resource_nodes'): # Fallback for backward compat if map missing
                for node in state.resource_nodes:
                    if node.x == hx and node.y == hy:
                        res_config = C.RESOURCE_TYPES.get(node.type, {})
                        res_name = res_config.get("display_name", node.type)
                        draw_text(screen, font, f"資源: {res_name} ({node.development}/{node.max_development})", pad, current_y)
                        current_y += lh
                        break


def render_save_load_menu(screen, font, state, is_save_mode=True):
    """
    Render the Save/Load menu with slots.
    is_save_mode: True for Save Menu, False for Load Menu
    """
    # Overlay background
    overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    
    # Centered Panel
    panel_w, panel_h = 420, 360
    panel_rect = pygame.Rect((C.SCREEN_WIDTH - panel_w) // 2, (C.SCREEN_HEIGHT - panel_h) // 2, panel_w, panel_h)
    
    pygame.draw.rect(screen, C.DARK_GREY, panel_rect)
    pygame.draw.rect(screen, C.WHITE, panel_rect, 2)
    
    # Title
    title_text = "ゲームを保存" if is_save_mode else "ゲームをロード"
    title_surf = font.render(title_text, True, C.WHITE)
    title_rect = title_surf.get_rect(midtop=(panel_rect.centerx, panel_rect.top + 20))
    screen.blit(title_surf, title_rect)
    
    # Slots
    import save_manager
    slots = [0, 1, 2, 3] # 0 = Auto/Quick
    
    start_y = title_rect.bottom + 30
    slot_height = 44
    slot_spacing = 12
    
    if not hasattr(state, 'save_load_rects'):
        state.save_load_rects = []
    state.save_load_rects.clear()
    
    mouse_pos = pygame.mouse.get_pos()
    
    for slot_id in slots:
        slot_rect = pygame.Rect(panel_rect.left + 24, start_y, panel_w - 48, slot_height)
        
        # Get metadata
        meta = save_manager.get_save_metadata(slot_id)
        
        # Draw slot button
        is_hovered = slot_rect.collidepoint(mouse_pos)
        col = (100, 100, 100) if is_hovered else C.GREY
        pygame.draw.rect(screen, col, slot_rect)
        pygame.draw.rect(screen, C.WHITE, slot_rect, 1)
        
        # Text
        slot_name_map = {0: "オート/クイック", 1: "スロット 1", 2: "スロット 2", 3: "スロット 3"}
        slot_name = slot_name_map.get(slot_id, f"Slot {slot_id}")
        
        if meta and meta.get("exists"):
            day_str = f"Day {meta.get('day')}"
            date_str = meta.get('date').split(" ")[0] # Just date
            info_text = f"{slot_name}: {day_str} ({date_str})"
        else:
            info_text = f"{slot_name}: ---"
            
        draw_text_centered(screen, font, info_text, slot_rect)
        
        state.save_load_rects.append((slot_rect, slot_id))
        start_y += slot_height + slot_spacing
        
    # Back Button
    back_width = 120
    back_rect = pygame.Rect((C.SCREEN_WIDTH - back_width) // 2, panel_rect.bottom - 50, back_width, 36)
    
    is_hovered = back_rect.collidepoint(mouse_pos)
    col = (100, 100, 100) if is_hovered else C.GREY
    
    pygame.draw.rect(screen, col, back_rect)
    pygame.draw.rect(screen, C.WHITE, back_rect, 1)
    draw_text_centered(screen, font, "キャンセル", back_rect)
    
    state.save_load_back_rect = back_rect
