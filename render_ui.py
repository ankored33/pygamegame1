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


def render_loading(screen, font):
    load_text = font.render("ロード中...", True, C.WHITE)
    load_rect = load_text.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2))
    screen.blit(load_text, load_rect)


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
            
            # Check for resource node at this tile
            for node in state.resource_nodes:
                if node.x == hx and node.y == hy:
                    resource_names = {
                        "FISH": "魚",
                        "FARM": "耕作地",
                        "GOLD": "金",
                        "SILVER": "銀",
                        "ANIMAL": "動物"
                    }
                    res_name = resource_names.get(node.type, node.type)
                    draw_text(screen, font, f"資源: {res_name} ({node.development}/{node.max_development})", pad, current_y)
                    current_y += lh
                    break
