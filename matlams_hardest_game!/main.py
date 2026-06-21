"""Entry point: window, main loop and the top-level state machine.

Run from this folder:  python main.py
Controls: Arrows/WASD move, R restart the level, Esc back to menu.
"""

import json
import os
import sys

import pygame

import audio
import config as C
from levels import LEVELS, validate_levels
from game import Level, WON
from menu import MainMenu, LevelSelect, SettingsMenu, draw_background

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress.json")


def load_progress():
    """Return (unlocked, total_deaths, beaten). `beaten` is True once level 20
    has ever been cleared."""
    try:
        with open(PROGRESS_FILE) as f:
            d = json.load(f)
        return (max(1, int(d.get("unlocked", 1))),
                max(0, int(d.get("total_deaths", 0))),
                bool(d.get("beaten", False)))
    except (OSError, ValueError, KeyError):
        return 1, 0, False


def save_progress(unlocked, total_deaths, beaten):
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump({"unlocked": unlocked, "total_deaths": total_deaths,
                       "beaten": beaten}, f)
    except OSError:
        pass


def make_screen():
    """Windowed SCALED display: fixed game resolution, vsync'd, and ready to be
    scaled up to fill the screen via toggle_fullscreen()."""
    try:
        return pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT),
                                       pygame.SCALED, vsync=1)
    except pygame.error:
        return pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SCALED)


def apply_fullscreen(want, screen):
    """Toggle the display to match `want` (SCALED scales the game to fill the
    screen, keeping aspect). toggle_fullscreen keeps `screen` valid and avoids the
    freeze that re-calling set_mode causes."""
    if bool(screen.get_flags() & pygame.FULLSCREEN) != want:
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass


def draw_overlay(screen, lines, sub=None):
    """Dim the screen and draw centered banner text."""
    overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))
    y = C.SCREEN_HEIGHT // 2 - 30 * (len(lines) - 1)
    for i, (text, size, color) in enumerate(lines):
        C.draw_text(screen, text, size, color, center=(C.SCREEN_WIDTH // 2, y))
        y += size + 16
    if sub:
        C.draw_text(screen, sub, 24, C.WHITE,
                    center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT - 70))


def main():
    pygame.init()
    validate_levels()
    audio.init()
    audio.start_music()
    # Windowed SCALED display, then go fullscreen if that was saved on.
    screen = make_screen()
    apply_fullscreen(audio.get_fullscreen(), screen)
    pygame.display.set_caption(C.TITLE)
    clock = pygame.time.Clock()
    total = len(LEVELS)

    unlocked, total_deaths, beaten = load_progress()
    unlocked = min(unlocked, total)

    state = "menu"
    menu = MainMenu(unlocked, total)
    select = None
    settings = None
    settings_return = "menu"      # where the settings screen returns to (menu/playing)
    level = None
    complete_timer = 0.0
    next_idx = 0
    stage_msg = None              # (title, subtitle) shown on the stage-clear screen

    def start_level(idx):
        nonlocal level, state
        level = Level(LEVELS[idx], idx, total)
        state = "playing"

    def go_menu():
        nonlocal menu, state
        save_progress(unlocked, total_deaths, beaten)
        menu = MainMenu(unlocked, total)
        state = "menu"

    running = True
    while running:
        dt = min(clock.tick(C.FPS) / 1000.0, 0.05)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            elif state == "menu":
                action = menu.handle_event(e)
                if action == "play":
                    # Once the game is beaten, PLAY restarts from level 1
                    # instead of dropping the player back on the final level.
                    start_level(0 if beaten else unlocked - 1)
                elif action == "select":
                    select = LevelSelect(total, unlocked)
                    state = "select"
                elif action == "settings":
                    settings = SettingsMenu()
                    settings_return = "menu"
                    state = "settings"
                elif action == "quit":
                    running = False

            elif state == "select":
                action = select.handle_event(e)
                if action == "back":
                    go_menu()
                elif isinstance(action, tuple) and action[0] == "level":
                    start_level(action[1])

            elif state == "settings":
                action = settings.handle_event(e)
                if action == "reset":
                    unlocked, total_deaths, beaten = 1, 0, False
                    save_progress(unlocked, total_deaths, beaten)
                    menu = MainMenu(unlocked, total)
                elif action == "fullscreen":
                    apply_fullscreen(audio.get_fullscreen(), screen)
                elif action == "back":
                    if settings_return == "playing":
                        state = "playing"
                    else:
                        go_menu()

            elif state == "playing":
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        go_menu()
                    elif e.key == pygame.K_r:
                        level.restart()
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if level.menu_rect and level.menu_rect.inflate(20, 12).collidepoint(e.pos):
                        go_menu()
                    elif level.settings_rect and level.settings_rect.collidepoint(e.pos):
                        settings = SettingsMenu()
                        settings_return = "playing"
                        state = "settings"

            elif state == "stagecomplete":
                if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    start_level(next_idx)

            elif state == "gamecomplete":
                if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    go_menu()

        # --- update ---------------------------------------------------------
        if state == "playing":
            keys = pygame.key.get_pressed()
            before = level.deaths
            result = level.update(dt, keys)
            total_deaths += level.deaths - before
            if result == WON:
                idx = level.index
                unlocked = max(unlocked, min(idx + 2, total))
                if idx + 1 >= total:
                    beaten = True
                save_progress(unlocked, total_deaths, beaten)
                if idx + 1 >= total:                            # beat the final level
                    audio.play("stage_complete")
                    state = "gamecomplete"
                elif (idx + 1) % C.LEVELS_PER_STAGE == 0:       # cleared a 5-level stage
                    audio.play("stage_complete")
                    next_idx = idx + 1
                    stage_msg = C.STAGE_CLEAR_MESSAGES[idx // C.LEVELS_PER_STAGE]
                    state = "stagecomplete"
                else:                                           # on to the next level
                    audio.play("level_complete")
                    next_idx = idx + 1
                    complete_timer = 1.3
                    state = "complete"
        elif state == "complete":
            complete_timer -= dt
            if complete_timer <= 0:
                start_level(next_idx)

        # --- draw -----------------------------------------------------------
        if state == "menu":
            menu.draw(screen)
        elif state == "select":
            select.draw(screen)
        elif state == "settings":
            settings.draw(screen)
        elif state in ("playing", "complete"):
            level.draw(screen)
            if state == "complete":
                draw_overlay(screen, [("LEVEL COMPLETE!", 56, C.GREEN)])
        elif state == "stagecomplete":
            draw_background(screen)                  # normal menu background, not the level
            title, subtitle = stage_msg
            cx = C.SCREEN_WIDTH // 2
            cy = C.SCREEN_HEIGHT // 2 - 30
            C.draw_text(screen, title, 56, (20, 20, 30), center=(cx + 3, cy + 3))
            C.draw_text(screen, title, 56, C.GREEN, center=(cx, cy))
            if subtitle:
                C.draw_text(screen, subtitle, 30, (30, 30, 55), center=(cx, cy + 56))
            C.draw_text(screen, "Press any key to continue", 24, (35, 35, 60),
                        center=(cx, C.SCREEN_HEIGHT - 70))
        elif state == "gamecomplete":
            screen.fill(C.LAVENDER)
            title, subtitle = C.STAGE_CLEAR_MESSAGES[-1]   # final stage message
            lines = [(title, 56, C.YELLOW)]
            if subtitle:
                lines.append((subtitle, 34, C.WHITE))
            lines.append((f"Total deaths: {total_deaths}", 34, C.WHITE))
            draw_overlay(screen, lines, sub="Press any key to return to the menu")

        pygame.display.flip()

    save_progress(unlocked, total_deaths, beaten)
    pygame.quit()
    sys.exit()

text_path = "../eviltext.txt"

def get_text():
    with open(text_path, "r") as f:
        string = f.read()
    return string


def get_info(origin, frame, screen_type):
    return


if __name__ == "__main__":
    main()
