"""Global constants, colors and small helpers for the game."""

import pygame

# --- Window -----------------------------------------------------------------
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 640
FPS = 60
TITLE = "The Matlam's Hardest Game"

# A tile is the basic grid unit used to author levels.
TILE = 40

# Height of the black HUD bar at the top of the screen while playing.
TOP_BAR_H = 44

# --- Colors -----------------------------------------------------------------
LAVENDER = (170, 170, 240)          # background / "void"
FLOOR_LIGHT = (245, 245, 255)       # checker tile A
FLOOR_DARK = (222, 222, 245)        # checker tile B
BORDER = (0, 0, 0)                   # arena outline + wall fill
WALL = (40, 40, 60)

GREEN = (115, 240, 120)             # start / end zones
GREEN_DARK = (70, 180, 75)
RED = (230, 30, 30)                 # player fill
RED_DARK = (150, 0, 0)              # player outline
BLUE = (30, 60, 230)                # enemy fill
BLUE_DARK = (10, 20, 110)           # enemy outline
CHASER = (175, 60, 210)             # homing-enemy fill (purple: stands apart from blue)
CHASER_DARK = (95, 25, 130)         # homing-enemy outline
YELLOW = (250, 215, 40)             # coin fill
YELLOW_DARK = (180, 140, 0)         # coin outline

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (120, 120, 120)
GREY_DARK = (70, 70, 70)
CHECKPOINT = (255, 150, 60)         # mid-level checkpoint marker (orange)

# --- Stages -----------------------------------------------------------------
LEVELS_PER_STAGE = 5                  # 20 levels split into 4 stages of 5

# ============================================================================
# EDIT ME -- the message shown after you clear each 5-level stage.
# One (TITLE, SUBTITLE) entry per stage, in order:
#   index 0 -> shown after level 5      index 2 -> shown after level 15
#   index 1 -> shown after level 10     index 3 -> the game-complete screen (level 20)
# Change the strings to whatever you like. Use "" for SUBTITLE to show one line.
# ============================================================================
STAGE_CLEAR_MESSAGES = [
    ("CO-MATA PLAINS CLEARED!", "Stage 1 of 4 complete - into the Co-ematza"),
    ("CO-EMTZA FOREST CLEARED!",  "Stage 2 of 4 complete - brave the Co-mala"),
    ("CO-MALA INFERNO CLEARED!",   "Stage 3 of 4 complete - enter the Comat Sagaz"),
    ("COMAT SAGAZ VOID CLEARED!",     "You beat The Matlams's Hardest Game!"),
]

# --- Stage themes -----------------------------------------------------------
# The 20 levels are split into 4 stages of 5. Each stage recolors the void
# background, the checker floor and the walls. Player (red), enemies (blue) and
# coins (yellow) stay constant so the gameplay always reads clearly.
THEMES = [
    {"name": "Co-mata Plains",                     # stages 1-5
     "bg": (170, 170, 240), "floor_a": (245, 245, 255),
     "floor_b": (222, 222, 245), "wall": (40, 40, 60)},
    {"name": "Co-emtza Forest",                      # stages 6-10
     "bg": (66, 150, 96), "floor_a": (232, 248, 232),
     "floor_b": (206, 236, 210), "wall": (28, 78, 44)},
    {"name": "Co-mala Inferno",                       # stages 11-15
     "bg": (200, 112, 64), "floor_a": (255, 243, 222),
     "floor_b": (248, 224, 194), "wall": (108, 44, 20)},
    {"name": "Comat Sagaz Void",                         # stages 16-20
     "bg": (44, 40, 74), "floor_a": (220, 218, 240),
     "floor_b": (196, 194, 224), "wall": (18, 16, 38)},
]


def theme_for(index):
    """Return the stage theme for a 0-based level index (5 levels per stage)."""
    return THEMES[min(index // LEVELS_PER_STAGE, len(THEMES) - 1)]

# --- Gameplay tuning --------------------------------------------------------
PLAYER_SIZE = int(TILE * 0.6)        # side length of the red square
PLAYER_SPEED = 230.0                 # pixels per second
ENEMY_RADIUS = TILE * 0.34
COIN_RADIUS = TILE * 0.22

# Global multiplier on every enemy's speed. Bump for an even more brutal game.
ENEMY_SPEED_SCALE = 1.2

# --- Fonts ------------------------------------------------------------------
_FONT_CACHE = {}
_TEXT_CACHE = {}


def get_font(size, bold=True):
    """Return a cached system font of the requested size."""
    key = (size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = pygame.font.SysFont("trebuchetms,verdana,arial,sans",
                                               size, bold=bold)
    return _FONT_CACHE[key]


def render_text(text, size, color, bold=True):
    """Return a cached rendered text surface (text.render is too slow per-frame)."""
    key = (text, size, color, bold)
    surf = _TEXT_CACHE.get(key)
    if surf is None:
        surf = get_font(size, bold).render(text, True, color)
        _TEXT_CACHE[key] = surf
    return surf


def draw_text(surface, text, size, color, center=None, topleft=None, midleft=None,
              midright=None, bold=True):
    """Render text and blit it at one of the given anchor points."""
    surf = render_text(text, size, color, bold)
    rect = surf.get_rect()
    if center is not None:
        rect.center = center
    elif topleft is not None:
        rect.topleft = topleft
    elif midleft is not None:
        rect.midleft = midleft
    elif midright is not None:
        rect.midright = midright
    surface.blit(surf, rect)
    return rect
