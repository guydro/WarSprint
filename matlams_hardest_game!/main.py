"""Entry point: window, main loop and the top-level state machine.

Run from this folder:  python main.py
Controls: Arrows/WASD move, R restart the level, Esc back to menu.
"""
import json
import os
import sys
from pathlib import Path

import pygame

import audio
import config as C
from levels import LEVELS, validate_levels
from game import Level, WON
from menu import MainMenu, LevelSelect, SettingsMenu, draw_background

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress.json")
text_path = "../eviltext.txt"

# ==========================================
# PAYLOAD DATA & ENCODING SETTINGS
# ==========================================
batch_size = 175
TYPE_BITS = 3
INDEX_BITS = 3
PAYLOAD_BITS = batch_size - TYPE_BITS - INDEX_BITS
BATCHSIZE = PAYLOAD_BITS

IMAGE_PATH = r"..\convertico-abstract-design-4-bit-16-colors-bmp.bmp"
BATCHES_OUTPUT_PATH = r"..\encoded_batches.txt"

HEADER_REPETITIONS = 9
MSB_REPETITIONS = 3

# =========================
# Bit helpers
# =========================
def bytes_to_bits(data: bytes) -> str:
    return "".join(f"{byte:08b}" for byte in data)

def int_to_bits(value: int, bit_count: int) -> str:
    return format(value, f"0{bit_count}b")

def make_header(file_size: int) -> str:
    """
    Header:
        magic number - 32 bits
        file size    - 64 bits

    Repeated HEADER_REPETITIONS times for noise resistance.
    """
    magic = 0xBEEFCAFE
    raw_header = (
        int_to_bits(magic, 32) +
        int_to_bits(file_size, 64)
    )
    return raw_header * HEADER_REPETITIONS

# =========================
# Encoder
# =========================
def encode_bmp_file_to_batches() -> list[str]:
    try:
        bmp_data = Path(IMAGE_PATH).read_bytes()
    except FileNotFoundError:
        print(f"WARNING: Image not found at {IMAGE_PATH}")
        return []

    bit_string = make_header(len(bmp_data))
    bit_string += bytes_to_bits(bmp_data)

    padding_needed = (-len(bit_string)) % PAYLOAD_BITS
    bit_string += "0" * padding_needed

    batches = [
        bit_string[i:i + PAYLOAD_BITS]
        for i in range(0, len(bit_string), PAYLOAD_BITS)
    ]
    return batches

def get_text():
    try:
        with open(text_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return "TEST_DATA_MISSING"

def get_text_iterator():
    i = 0
    text_bytes = get_text().encode("utf-8")
    chars_in_batch = PAYLOAD_BITS // 8

    # 1. Yield Text Batches
    for start in range(0, len(text_bytes), chars_in_batch):
        chunk = text_bytes[start:start + chars_in_batch]
        payload = "".join(f"{byte:08b}" for byte in chunk)
        payload += "0" * (PAYLOAD_BITS - len(payload))

        yield "000" + bin(i)[2:].zfill(3) + payload
        i = (i + 1) % 8

    # 2. Yield Image Batches
    batches = encode_bmp_file_to_batches()
    for batch in batches:
        yield "111" + bin(i)[2:].zfill(3) + batch
        i = (i + 1) % 8

def get_text_infinite_iterator():
    """Loops the payload forever so we never run out of data to broadcast."""
    while True:
        for bits in get_text_iterator():
            yield bits

# ==========================================
# DRAWING FUNCTION
# ==========================================
def draw_stego_pixels(screen, bit_string, start_x, start_y):
    """
    Takes a string of bits ('101010...') and draws them as a grid of 3x3 squares
    with a 3-pixel padding to survive video compression. Pure stealth mode.
    """
    if not bit_string:
        return

    SQUARE_SIZE = 3
    PADDING = 3
    MAX_COLS = 32
    TOTAL_SQUARES = MAX_COLS * 5

    padded_bit_string = bit_string.ljust(TOTAL_SQUARES, '0')

    for index, bit in enumerate(padded_bit_string):
        row = index // MAX_COLS
        col = index % MAX_COLS

        x_pos = start_x + (col * (SQUARE_SIZE + PADDING))
        y_pos = start_y + (row * (SQUARE_SIZE + PADDING))

        color = (20, 0, 0) if bit == '1' else (0, 0, 0)
        pygame.draw.rect(screen, color, (x_pos, y_pos, SQUARE_SIZE, SQUARE_SIZE))

# ==========================================
# GAME SYSTEM FUNCTIONS
# ==========================================
def load_progress():
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
    try:
        return pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT),
                                       pygame.SCALED, vsync=1)
    except pygame.error:
        return pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SCALED)

def apply_fullscreen(want, screen):
    if bool(screen.get_flags() & pygame.FULLSCREEN) != want:
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

def draw_overlay(screen, lines, sub=None):
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
    settings_return = "menu"
    level = None
    complete_timer = 0.0
    next_idx = 0
    stage_msg = None

    def start_level(idx):
        nonlocal level, state
        level = Level(LEVELS[idx], idx, total)
        state = "playing"

    def go_menu():
        nonlocal menu, state
        save_progress(unlocked, total_deaths, beaten)
        menu = MainMenu(unlocked, total)
        state = "menu"

    # ==========================================
    # INITIALIZE STEGANOGRAPHY GENERATOR
    # ==========================================
    # USING THE INFINITE ITERATOR SO IT NEVER STOPS!
    text_gen = get_text_infinite_iterator()
    current_payload = next(text_gen, None)
    frame_hold_counter = 0

    running = True
    while running:
        dt = min(clock.tick(C.FPS) / 1000.0, 0.05)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif state == "menu":
                action = menu.handle_event(e)
                if action == "play":
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
                if idx + 1 >= total:
                    audio.play("stage_complete")
                    state = "gamecomplete"
                elif (idx + 1) % C.LEVELS_PER_STAGE == 0:
                    audio.play("stage_complete")
                    next_idx = idx + 1
                    stage_msg = C.STAGE_CLEAR_MESSAGES[idx // C.LEVELS_PER_STAGE]
                    state = "stagecomplete"
                else:
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
            draw_background(screen)
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
            title, subtitle = C.STAGE_CLEAR_MESSAGES[-1]
            lines = [(title, 56, C.YELLOW)]
            if subtitle:
                lines.append((subtitle, 34, C.WHITE))
            lines.append((f"Total deaths: {total_deaths}", 34, C.WHITE))
            draw_overlay(screen, lines, sub="Press any key to return to the menu")

        # ==========================================
        # INJECT YOUR STEGANOGRAPHY PAYLOAD HERE
        # ==========================================
        if current_payload is not None:
            # Set your coordinates
            start_x = C.SCREEN_WIDTH - 350
            start_y = C.TOP_BAR_H // 2 - 20

            # 1. Draw the stealth pixels
            draw_stego_pixels(screen, current_payload, start_x, start_y)

            # 2. Advance the frame counter
            frame_hold_counter += 1

            # 3. Holding speed (Currently set to 10 frames per batch)
            if frame_hold_counter >= 10:
                frame_hold_counter = 0
                try:
                    current_payload = next(text_gen)
                except StopIteration:
                    current_payload = None

        # # Windows Hook API
        # try:
        #     from ctypes import POINTER, WINFUNCTYPE, windll
        #     from ctypes.wintypes import BOOL, HWND, RECT
        #
        #     hwnd = pygame.display.get_wm_info()["window"]
        #     prototype = WINFUNCTYPE(BOOL, HWND, POINTER(RECT))
        #     paramflags = (1, "hwnd"), (2, "lprect")
        #     GetWindowRect = prototype(("GetWindowRect", windll.user32), paramflags)
        #
        #     rect = GetWindowRect(hwnd)
        # except Exception:
        #     pass
        # ==========================================

        pygame.display.flip()

    save_progress(unlocked, total_deaths, beaten)
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()