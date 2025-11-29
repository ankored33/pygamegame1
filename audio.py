import pygame

current_music = None
_mixer_ready = False


def ensure_mixer():
    global _mixer_ready
    if not _mixer_ready:
        try:
            pygame.mixer.init()
            _mixer_ready = True
        except Exception:
            _mixer_ready = False


def play_music(path: str):
    global current_music
    ensure_mixer()
    if not _mixer_ready or not path:
        return
    if current_music == path:
        return
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(0.1)
        pygame.mixer.music.play(-1)
        current_music = path
    except Exception:
        current_music = None


