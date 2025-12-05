"""
Cache management module for game rendering caches.
Centralizes cache invalidation logic to avoid code duplication.
"""

def invalidate_all(state):
    """
    Invalidate all rendering caches.
    Use when map data changes (new game, conquest, etc.)
    """
    state.map_surface = None
    state.zoom_full_map_cache = None
    state.zoom_fog_layer = None
    state.selected_region_overlay_cache = None
    state.selected_region_overlay_zoom_cache = None


def invalidate_fog(state):
    """
    Invalidate only fog-related caches.
    Use when fog is revealed but map data hasn't changed.
    """
    state.fog_surface = None
    state.zoom_fog_layer = None


def invalidate_map(state):
    """
    Invalidate map and overlay caches but keep fog.
    Use when territory changes but fog doesn't.
    """
    state.map_surface = None
    state.zoom_full_map_cache = None
    state.selected_region_overlay_cache = None
    state.selected_region_overlay_zoom_cache = None
