"""Title screen and level-select screen, with an animated themed background."""

import math
import pygame

import audio
import config as C
from config import SCREEN_WIDTH as W, SCREEN_HEIGHT as H


# Decorative drifting shapes (Lissajous motion), drawn faintly behind the UI.
# Each: (base_x, base_y, amp_x, amp_y, speed, phase, radius, kind)
_DECOR = [
    (180, 150, 90, 70, 0.45, 0.0, 26, "circle"),
    (850, 200, 110, 80, 0.38, 1.4, 30, "circle"),
    (300, 480, 120, 90, 0.52, 2.6, 22, "circle"),
    (760, 470, 100, 70, 0.41, 0.7, 28, "circle"),
    (520, 120, 140, 60, 0.33, 3.3, 24, "circle"),
    (120, 360, 70, 110, 0.6, 4.1, 18, "coin"),
    (910, 380, 80, 120, 0.55, 1.1, 16, "coin"),
    (480, 520, 130, 50, 0.47, 5.0, 20, "square"),
]


_decor_layer = None


def draw_background(surf, base=C.LAVENDER):
    """Fill `base` colour, then overlay slow drifting translucent game shapes.

    Used for the menus and, with each stage's background colour, for the void
    around the levels so the play area sits on the same animated backdrop.
    """
    global _decor_layer
    surf.fill(base)
    t = pygame.time.get_ticks() / 1000.0
    if _decor_layer is None:                      # reuse one layer across frames
        _decor_layer = pygame.Surface((W, H), pygame.SRCALPHA)
    layer = _decor_layer
    layer.fill((0, 0, 0, 0))
    for bx, by, ax, ay, sp, ph, r, kind in _DECOR:
        x = bx + math.sin(t * sp + ph) * ax
        y = by + math.cos(t * sp * 0.8 + ph) * ay
        if kind == "circle":
            pygame.draw.circle(layer, (*C.BLUE, 55), (x, y), r)
            pygame.draw.circle(layer, (*C.BLUE_DARK, 80), (x, y), r, 4)
        elif kind == "coin":
            pygame.draw.circle(layer, (*C.YELLOW, 70), (x, y), r)
            pygame.draw.circle(layer, (*C.YELLOW_DARK, 90), (x, y), r, 3)
        else:  # square
            rect = pygame.Rect(0, 0, r * 2, r * 2)
            rect.center = (x, y)
            pygame.draw.rect(layer, (*C.RED, 55), rect, border_radius=4)
            pygame.draw.rect(layer, (*C.RED_DARK, 80), rect, width=4, border_radius=4)
    surf.blit(layer, (0, 0))


def _title(surf, top_y):
    """Two-line drop-shadow title."""
    for line, dy, color in [("THE MATLAM'S", 0, C.RED_DARK), ("HARDEST GAME", 64, C.RED)]:
        cx = W // 2
        C.draw_text(surf, line, 64, (20, 20, 30), center=(cx + 4, top_y + dy + 4))
        C.draw_text(surf, line, 64, color, center=(cx, top_y + dy))


def stage_tint(index):
    """A dark, stage-themed button fill for level `index` (white text reads on it)."""
    bg = C.theme_for(index)["bg"]
    return tuple(int(c * 0.45 + 18) for c in bg)


class Button:
    def __init__(self, text, center, size=(330, 62), font_size=34, enabled=True,
                 tint=None):
        self.text = text
        self.rect = pygame.Rect(0, 0, *size)
        self.rect.center = center
        self.font_size = font_size
        self.enabled = enabled
        self.tint = tint              # idle fill override (used for stage colours)
        self.preview = None           # thumbnail Surface shown instead of the number
        self.hover = False

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)

    def draw(self, surf):
        if not self.enabled:
            fill, edge, txt, bw = C.GREY_DARK, C.GREY, C.GREY, 3
        elif self.hover:
            fill, edge, txt, bw = C.GREEN_DARK, C.WHITE, C.WHITE, 4
        else:
            fill, edge, txt, bw = self.tint or (44, 44, 78), (210, 210, 230), C.WHITE, 3
        shadow = self.rect.move(0, 5)
        pygame.draw.rect(surf, (20, 20, 30), shadow, border_radius=12)
        pygame.draw.rect(surf, fill, self.rect, border_radius=12)
        pygame.draw.rect(surf, edge, self.rect, width=bw, border_radius=12)
        if self.preview is not None:
            surf.blit(self.preview, self.preview.get_rect(center=self.rect.center))
            if not self.enabled:                      # dim locked previews
                veil = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                veil.fill((20, 20, 30, 120))
                surf.blit(veil, self.rect.topleft)
            # small number badge (with shadow) so you still know which level it is
            C.draw_text(surf, self.text, 18, (20, 20, 30),
                        topleft=(self.rect.left + 8, self.rect.top + 6))
            C.draw_text(surf, self.text, 18, C.WHITE,
                        topleft=(self.rect.left + 7, self.rect.top + 5))
        else:
            C.draw_text(surf, self.text, self.font_size, txt, center=self.rect.center)
        if self.hover:
            cy = self.rect.centery
            left, right = self.rect.left - 18, self.rect.right + 18
            pygame.draw.polygon(surf, C.WHITE,
                                [(left, cy - 9), (left, cy + 9), (left + 14, cy)])
            pygame.draw.polygon(surf, C.WHITE,
                                [(right, cy - 9), (right, cy + 9), (right - 14, cy)])


class MainMenu:
    def __init__(self, unlocked=0, total=0):
        cx = W // 2
        self.unlocked = unlocked
        self.total = total
        # 4 evenly spaced buttons (76px pitch) with a clear gap between each.
        labels = ["PLAY", "LEVEL SELECT", "SETTINGS", "QUIT"]
        self.buttons = [Button(t, (cx, 288 + i * 76), size=(330, 58))
                        for i, t in enumerate(labels)]
        self.actions = ["play", "select", "settings", "quit"]
        self.sel = 0

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.buttons)
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.buttons)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.actions[self.sel]
            elif e.key == pygame.K_ESCAPE:
                return "quit"
        elif e.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(e.pos):
                    self.sel = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, b in enumerate(self.buttons):
                if b.hit(e.pos):
                    return self.actions[i]
        return None

    def draw(self, surf):
        draw_background(surf)
        _title(surf, 104)
        for i, b in enumerate(self.buttons):
            b.hover = (i == self.sel)
            b.draw(surf)
        if self.total:
            C.draw_text(surf, f"Levels unlocked: {self.unlocked}/{self.total}",
                        24, (40, 40, 70), center=(W // 2, 224))
        C.draw_text(surf, "Move: Arrows / WASD    R: restart    Esc: menu",
                    22, (35, 35, 60), center=(W // 2, H - 64))
        C.draw_text(surf, "Reach the green exit. Dodge the blue circles. Grab every coin.",
                    22, (35, 35, 60), center=(W // 2, H - 34))


class LevelSelect:
    def __init__(self, total, unlocked):
        self.total = total
        # 5 columns keeps 20 levels to 4 rows so the grid fits the window.
        self.cols = 5 if total > 12 else 4
        self.rows = math.ceil(total / self.cols)
        self.sel = 0
        self.back = Button("BACK", (W // 2, H - 56), size=(220, 54), font_size=30)
        self._thumbs = {}             # cached per-level preview thumbnails
        self._build()
        self.set_unlocked(unlocked)

    def _level_thumb(self, i):
        """A small map preview of level `i`, scaled to fit a box. Cached."""
        if i not in self._thumbs:
            from game import Level
            from levels import LEVELS
            lvl = Level(LEVELS[i], i, self.total)
            full = pygame.Surface((W, H))
            lvl.draw(full)            # full level render (themed map + entities)
            # Crop just the grid (this sits below the HUD bar, so the HUD is excluded).
            # Clip to the surface so an oversized grid can never crash subsurface.
            crop = pygame.Rect(lvl.ox, lvl.oy,
                               lvl.cols * C.TILE, lvl.rows * C.TILE).clip(full.get_rect())
            grid = full.subsurface(crop).copy()
            bw, bh = self.buttons[i].rect.size
            avail_w, avail_h = bw - 12, bh - 12
            gw, gh = grid.get_size()
            scale = min(avail_w / gw, avail_h / gh)
            thumb = pygame.transform.smoothscale(
                grid, (max(1, int(gw * scale)), max(1, int(gh * scale))))
            self._thumbs[i] = thumb
        return self._thumbs[i]

    def _build(self):
        bw, bh, gap = (150, 84, 22) if self.cols == 5 else (150, 100, 28)
        grid_w = self.cols * bw + (self.cols - 1) * gap
        grid_h = self.rows * bh + (self.rows - 1) * gap
        x0 = (W - grid_w) // 2 + bw // 2
        # Centre the grid in the band between the title and the BACK button.
        y0 = max(178, (H - 70 - grid_h) // 2 + bh // 2)
        self.buttons = []
        for i in range(self.total):
            r, c = divmod(i, self.cols)
            center = (x0 + c * (bw + gap), y0 + r * (bh + gap))
            self.buttons.append(Button(str(i + 1), center, size=(bw, bh),
                                       font_size=40, tint=stage_tint(i)))

    def set_unlocked(self, unlocked):
        self.unlocked = unlocked
        for i, b in enumerate(self.buttons):
            b.enabled = i < unlocked

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                return "back"
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self.sel = (self.sel + 1) % self.total
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self.sel = (self.sel - 1) % self.total
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + self.cols) % self.total
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - self.cols) % self.total
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.buttons[self.sel].enabled:
                    return ("level", self.sel)
        elif e.type == pygame.MOUSEMOTION:
            self.back.hover = self.back.rect.collidepoint(e.pos)
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(e.pos):
                    self.sel = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.back.hit(e.pos):
                return "back"
            for i, b in enumerate(self.buttons):
                if b.hit(e.pos):
                    return ("level", i)
        return None

    def draw(self, surf):
        draw_background(surf)
        C.draw_text(surf, "SELECT LEVEL", 56, (20, 20, 30), center=(W // 2 + 3, 103))
        C.draw_text(surf, "SELECT LEVEL", 56, C.RED, center=(W // 2, 100))
        for i, b in enumerate(self.buttons):
            b.hover = (i == self.sel and b.enabled)
            b.preview = self._level_thumb(i) if i == self.sel else None
            b.draw(surf)
            if not b.enabled:
                self._draw_lock(surf, b.rect.centerx, b.rect.bottom - 24)
        self.back.draw(surf)   # hover state is updated on mouse motion

    @staticmethod
    def _draw_lock(surf, cx, cy):
        body = pygame.Rect(cx - 11, cy, 22, 16)
        pygame.draw.rect(surf, C.GREY, body, border_radius=3)
        pygame.draw.arc(surf, C.GREY, (cx - 8, cy - 12, 16, 18), 0, math.pi, 3)


class SettingsMenu:
    """Adjust music and sound-effect volume (0-100% in 10% steps).

    Changes are applied live and saved immediately through the `audio` module,
    so there is nothing to persist here -- `handle_event` just returns "back".
    """

    _STEP = 0.1

    def __init__(self):
        cx = W // 2
        self.rows = [
            {"label": "MUSIC", "get": audio.get_music_volume, "set": audio.set_music_volume},
            {"label": "SOUND EFFECTS", "get": audio.get_sfx_volume, "set": audio.set_sfx_volume},
        ]
        # Selectable items: 0..len-1 = volume rows, len = FULLSCREEN,
        # len+1 = RESET, len+2 = BACK.
        self.sel = 0
        self._confirm = False                     # RESET needs a second click
        self._row_y = [250, 330]
        bw = 300                                  # bar width; -/+ flank it symmetrically
        self._bar_rect = [pygame.Rect(cx - bw // 2, y - 16, bw, 32) for y in self._row_y]
        self.minus = [Button("-", (cx - bw // 2 - 38, y), size=(46, 46), font_size=34)
                      for y in self._row_y]
        self.plus = [Button("+", (cx + bw // 2 + 38, y), size=(46, 46), font_size=34)
                     for y in self._row_y]
        self.fullscreen = audio.get_fullscreen()
        self.fs_btn = Button("FULLSCREEN", (cx, 404), size=(320, 48), font_size=26)
        self.reset_btn = Button("RESET PROGRESS", (cx, 464), size=(320, 48), font_size=26)
        self.back = Button("BACK", (cx, 528), size=(220, 52), font_size=30)

    def handle_event(self, e):
        n = len(self.rows)               # n = FULLSCREEN, n+1 = RESET, n+2 = BACK
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self._confirm:
                    self._confirm = False
                else:
                    return "back"
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % (n + 3)
                self._confirm = False
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % (n + 3)
                self._confirm = False
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                if self.sel < n:
                    self._adjust(self.sel, -1)
                elif self.sel == n:
                    return self._toggle_fullscreen()
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                if self.sel < n:
                    self._adjust(self.sel, +1)
                elif self.sel == n:
                    return self._toggle_fullscreen()
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.sel == n:
                    return self._toggle_fullscreen()
                elif self.sel == n + 1:
                    return self._activate_reset()
                elif self.sel == n + 2:
                    return "back"
        elif e.type == pygame.MOUSEMOTION:
            self._update_hover(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.fs_btn.hit(e.pos):
                self.sel = n
                return self._toggle_fullscreen()
            if self.reset_btn.hit(e.pos):
                self.sel = n + 1
                return self._activate_reset()
            self._confirm = False                 # any other click cancels confirm
            if self.back.hit(e.pos):
                return "back"
            for i in range(n):
                if self.minus[i].hit(e.pos):
                    self.sel = i
                    self._adjust(i, -1)
                    break
                if self.plus[i].hit(e.pos):
                    self.sel = i
                    self._adjust(i, +1)
                    break
                if self._bar_rect[i].collidepoint(e.pos):
                    self.sel = i
                    frac = (e.pos[0] - self._bar_rect[i].left) / self._bar_rect[i].width
                    self._set(i, frac)
                    break
        return None

    def _activate_reset(self):
        """First activation arms the confirm; the second one actually resets."""
        if self._confirm:
            self._confirm = False
            return "reset"
        self._confirm = True
        return None

    def _toggle_fullscreen(self):
        """Flip and persist the fullscreen flag; main applies the display mode."""
        self._confirm = False
        self.fullscreen = not self.fullscreen
        audio.set_fullscreen(self.fullscreen)
        return "fullscreen"

    def _adjust(self, i, direction):
        cur = round(self.rows[i]["get"]() / self._STEP) * self._STEP
        self._set(i, cur + direction * self._STEP)

    def _set(self, i, frac):
        frac = max(0.0, min(1.0, round(frac / self._STEP) * self._STEP))
        self.rows[i]["set"](frac)
        if i == 1:                               # sound-effects row: audible preview
            audio.play("coin")

    def _update_hover(self, pos):
        n = len(self.rows)
        for i in range(n):
            self.minus[i].hover = self.minus[i].rect.collidepoint(pos)
            self.plus[i].hover = self.plus[i].rect.collidepoint(pos)
            if (self.minus[i].hover or self.plus[i].hover
                    or self._bar_rect[i].collidepoint(pos)):
                self.sel = i
        if self.fs_btn.rect.collidepoint(pos):
            self.sel = n
        elif self.reset_btn.rect.collidepoint(pos):
            self.sel = n + 1
        elif self.back.rect.collidepoint(pos):
            self.sel = n + 2

    def draw(self, surf):
        draw_background(surf)
        cx = W // 2
        n = len(self.rows)
        C.draw_text(surf, "SETTINGS", 56, (20, 20, 30), center=(cx + 3, 103))
        C.draw_text(surf, "SETTINGS", 56, C.RED, center=(cx, 100))
        for i, row in enumerate(self.rows):
            sel = (self.sel == i)
            rect = self._bar_rect[i]
            txt = C.WHITE if sel else (205, 205, 225)
            # Label on the left, value on the right, both sitting just above the
            # bar (and within its width) so nothing spills outside the control.
            C.draw_text(surf, row["label"], 26, txt, midleft=(rect.left, rect.top - 22))
            C.draw_text(surf, f"{int(round(row['get']() * 100))}%", 26, txt,
                        midright=(rect.right, rect.top - 22))
            self.minus[i].draw(surf)
            self.plus[i].draw(surf)
            self._draw_bar(surf, i, row["get"](), sel)
        self._draw_fullscreen(surf, self.sel == n)
        self._draw_reset(surf, self.sel == n + 1)
        self.back.hover = (self.sel == n + 2)
        self.back.draw(surf)
        C.draw_text(surf, "Up / Down: select     Left / Right / Enter: change     Esc: back",
                    22, (35, 35, 60), center=(cx, H - 34))

    def _draw_fullscreen(self, surf, sel):
        """Toggle button reflecting the current fullscreen state (green = on)."""
        b = self.fs_btn
        on = self.fullscreen
        if sel:
            fill, edge = (C.GREEN_DARK if on else (70, 70, 110)), C.WHITE
        else:
            fill, edge = ((52, 110, 58) if on else (44, 44, 78)), (210, 210, 230)
        pygame.draw.rect(surf, (20, 20, 30), b.rect.move(0, 4), border_radius=10)
        pygame.draw.rect(surf, fill, b.rect, border_radius=10)
        pygame.draw.rect(surf, edge, b.rect, width=3, border_radius=10)
        C.draw_text(surf, "FULLSCREEN: " + ("ON" if on else "OFF"),
                    b.font_size, C.WHITE, center=b.rect.center)

    def _draw_reset(self, surf, sel):
        """Destructive 'reset all progress' button (red), with a confirm state."""
        b = self.reset_btn
        if self._confirm:
            fill, edge, label = (205, 55, 55), C.WHITE, "CONFIRM RESET?"
        elif sel:
            fill, edge, label = (175, 55, 55), C.WHITE, "RESET PROGRESS"
        else:
            fill, edge, label = (95, 42, 42), (210, 175, 175), "RESET PROGRESS"
        pygame.draw.rect(surf, (20, 20, 30), b.rect.move(0, 4), border_radius=10)
        pygame.draw.rect(surf, fill, b.rect, border_radius=10)
        pygame.draw.rect(surf, edge, b.rect, width=3, border_radius=10)
        C.draw_text(surf, label, b.font_size, C.WHITE, center=b.rect.center)

    def _draw_bar(self, surf, i, value, sel):
        rect = self._bar_rect[i]
        pygame.draw.rect(surf, (20, 20, 30), rect.move(0, 3), border_radius=6)
        pygame.draw.rect(surf, (44, 44, 78), rect, border_radius=6)
        seg = rect.width / 10.0
        filled = int(round(value * 10))
        fill_col = C.GREEN if sel else C.GREEN_DARK
        for s in range(filled):
            surf.fill(fill_col, pygame.Rect(int(rect.left + s * seg + 2), rect.top + 4,
                                            int(seg - 4), rect.height - 8))
        pygame.draw.rect(surf, C.WHITE if sel else (210, 210, 230), rect,
                         width=2, border_radius=6)
