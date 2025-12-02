import pygame
import config as C

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


def draw_text_centered(screen, font, text, rect):
    surf = font.render(text, True, C.WHITE)
    r = surf.get_rect(center=rect.center)
    screen.blit(surf, r)
