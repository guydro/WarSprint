"""Runtime for a single level: layout, entities, collision, drawing and HUD."""

import math

import pygame

import audio
import config as C
from config import TILE, TOP_BAR_H, SCREEN_WIDTH, SCREEN_HEIGHT
from sprites import Player, Enemy, Coin
from menu import draw_background
print(f"{SCREEN_WIDTH=}, {SCREEN_HEIGHT=}")

def _draw_gear(surf, cx, cy, r, color):
    """Draw a small gear/cog icon (used as the in-level settings button)."""
    for k in range(8):
        a = math.pi * k / 4.0
        ca, sa = math.cos(a), math.sin(a)
        pygame.draw.line(surf, color, (cx + ca * (r - 1), cy + sa * (r - 1)),
                         (cx + ca * (r + 4), cy + sa * (r + 4)), 4)
    pygame.draw.circle(surf, color, (int(cx), int(cy)), r)
    pygame.draw.circle(surf, C.BLACK, (int(cx), int(cy)), max(2, r // 2))


# Level.update return values.
PLAYING = "playing"
WON = "won"

WALKABLE = ".SE"
RESPAWN_GRACE = 0.5   # seconds of collision immunity after (re)spawning


class Level:
    def __init__(self, level_data, index, total):
        self.data = level_data
        self.index = index            # 0-based
        self.total = total
        self.name = level_data["name"]
        self.theme = C.theme_for(index)
        self.grid = level_data["map"]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.deaths = 0

        # Center the grid inside the play area (below the top bar).
        gw = self.cols * TILE
        gh = self.rows * TILE
        self.ox = (SCREEN_WIDTH - gw) // 2
        self.oy = TOP_BAR_H + (SCREEN_HEIGHT - TOP_BAR_H - gh) // 2

        # End-zone cell rects, used for the win check.
        self.end_rects = [self._cell_rect(c, r)
                          for r in range(self.rows) for c in range(self.cols)
                          if self.grid[r][c] == "E"]

        # Green (start + exit) cell rects: enemies are kept out of these.
        self.green_rects = [self._cell_rect(c, r)
                            for r in range(self.rows) for c in range(self.cols)
                            if self.grid[r][c] in "SE"]

        # Spawn = centroid of the start cells.
        s_cells = [(c, r) for r in range(self.rows) for c in range(self.cols)
                   if self.grid[r][c] == "S"]
        avg_c = sum(c for c, _ in s_cells) / len(s_cells)
        avg_r = sum(r for _, r in s_cells) / len(s_cells)
        self.spawn = (self._px(avg_c), self._py(avg_r))

        self._build_entities()

        self.player = Player(*self.spawn)
        self.checkpoint_pos = self.spawn       # active respawn point
        self.coin_snapshot = set()             # collected coins at last checkpoint
        self.respawn_grace = RESPAWN_GRACE
        self.goal_msg = 0.0                    # "collect coins" hint timer
        self.menu_rect = None                  # set each frame by _draw_hud
        self.settings_rect = None              # in-level settings (gear) button

        # The arena (floor, walls, borders, checkpoint outlines) never changes,
        # so render it once here and just blit it each frame.
        self.bg_surface = self._render_static()

    # --- coordinate helpers -------------------------------------------------
    def _px(self, tx):
        return self.ox + (tx + 0.5) * TILE

    def _py(self, ty):
        return self.oy + (ty + 0.5) * TILE

    def _cell_rect(self, col, row):
        return pygame.Rect(self.ox + col * TILE, self.oy + row * TILE, TILE, TILE)

    # --- setup --------------------------------------------------------------
    def _build_entities(self):
        self.enemies = []
        scale = C.ENEMY_SPEED_SCALE
        for e in self.data.get("enemies", []):
            kind = e["type"]
            if kind == "linear":
                if e["axis"] == "h":
                    fixed = self._py(e["y"])
                    pmin, pmax = self._px(e["x"]), self._px(e["x"] + e["range"])
                else:
                    fixed = self._px(e["x"])
                    pmin, pmax = self._py(e["y"]), self._py(e["y"] + e["range"])
                self.enemies.append(Enemy(
                    "linear", C.ENEMY_RADIUS, axis=e["axis"], fixed=fixed,
                    pmin=pmin, pmax=pmax, speed=e["speed"] * TILE * scale, phase=e["phase"]))
            elif kind == "circle":
                self.enemies.append(Enemy(
                    "circle", C.ENEMY_RADIUS, cx=self._px(e["cx"]), cy=self._py(e["cy"]),
                    orbit_r=e["r"] * TILE, speed=e["speed"] * scale, phase=e["phase"]))
            elif kind == "diag":
                self.enemies.append(Enemy(
                    "diag", C.ENEMY_RADIUS,
                    p0=(self._px(e["x0"]), self._py(e["y0"])),
                    p1=(self._px(e["x1"]), self._py(e["y1"])),
                    speed=e["speed"] * TILE * scale, phase=e["phase"]))
            elif kind == "patrol":
                pts = [(self._px(x), self._py(y)) for x, y in e["pts"]]
                self.enemies.append(Enemy(
                    "patrol", C.ENEMY_RADIUS, points=pts,
                    speed=e["speed"] * TILE * scale, phase=e["phase"]))
            else:  # "chase"
                self.enemies.append(Enemy(
                    "chase", C.ENEMY_RADIUS, cx=self._px(e["x"]), cy=self._py(e["y"]),
                    speed=e["speed"] * TILE * scale))

        self.coins = [Coin(self._px(x), self._py(y))
                      for x, y in self.data.get("coins", [])]
        self.total_coins = len(self.coins)

        # Checkpoints: (cell_rect, center_pos, activated?)
        self.checkpoints = []
        for x, y in self.data.get("checkpoints", []):
            self.checkpoints.append({
                "rect": self._cell_rect(int(round(x)), int(round(y))),
                "pos": (self._px(x), self._py(y)),
                "active": False,
            })

    # --- collision queries --------------------------------------------------
    def rect_walkable(self, rect):
        c0 = (rect.left - self.ox) // TILE
        c1 = (rect.right - 1 - self.ox) // TILE
        r0 = (rect.top - self.oy) // TILE
        r1 = (rect.bottom - 1 - self.oy) // TILE
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if not (0 <= r < self.rows and 0 <= c < self.cols):
                    return False
                if self.grid[r][c] not in WALKABLE:
                    return False
        return True

    @property
    def coins_left(self):
        return sum(1 for c in self.coins if not c.collected)

    # --- per-frame update ---------------------------------------------------
    def respawn(self, count_death=True):
        if count_death:
            self.deaths += 1
            audio.play("death")        # only on a real death, not a manual restart
        self.player.set_center(*self.checkpoint_pos)
        for i, coin in enumerate(self.coins):
            coin.collected = i in self.coin_snapshot
        for e in self.enemies:
            e.reset()
        self.respawn_grace = RESPAWN_GRACE

    def restart(self):
        """Start the level over from scratch: forget checkpoints and coins and
        send the player back to the original start (used by the R key)."""
        self.checkpoint_pos = self.spawn
        self.coin_snapshot = set()
        for cp in self.checkpoints:
            cp["active"] = False
        self.respawn(count_death=False)

    def update(self, dt, keys):
        if self.respawn_grace > 0:
            self.respawn_grace -= dt

        self.player.update(dt, keys, self)
        for e in self.enemies:
            if e.kind == "chase":
                # Homing chasers may not enter the green safe zones: revert any
                # step that would put them on a start/exit cell.
                prev = pygame.Vector2(e.pos)
                e.update(dt, self.player.rect.center)
                if any(e.hits(r) for r in self.green_rects):
                    e.pos.update(prev)
            else:
                e.update(dt, self.player.rect.center)

        # Collect coins.
        for coin in self.coins:
            if not coin.collected and coin.hits(self.player.rect):
                coin.collected = True
                audio.play("coin")

        # Activate checkpoints (snapshot collected coins when reached).
        for cp in self.checkpoints:
            if not cp["active"] and self.player.rect.colliderect(cp["rect"]):
                cp["active"] = True
                self.checkpoint_pos = cp["pos"]
                self.coin_snapshot = {i for i, c in enumerate(self.coins) if c.collected}
                audio.play("checkpoint")

        # Death from enemies. The post-respawn grace only covers an enemy sitting
        # on the respawn point: it ends the moment the player is clear of every
        # enemy, so it can't be used to dash through them.
        touching = any(e.hits(self.player.rect) for e in self.enemies)
        if self.respawn_grace > 0:
            if not touching:
                self.respawn_grace = 0.0
        elif touching:
            self.respawn()
            return PLAYING

        # Win: stand on the end zone with every coin collected.
        if any(self.player.rect.colliderect(r) for r in self.end_rects):
            if self.coins_left == 0:
                return WON
            self.goal_msg = 1.0
        if self.goal_msg > 0:
            self.goal_msg -= dt

        return PLAYING

    # --- drawing ------------------------------------------------------------
    def draw(self, surf):
        draw_background(surf, self.theme["bg"])    # animated drifting void (menu-style)
        surf.blit(self.bg_surface, (0, 0))         # static arena over the void
        # Filled checkpoint discs are the only arena element that changes; draw
        # them over the pre-rendered background once they have been reached.
        for cp in self.checkpoints:
            if cp["active"]:
                pygame.draw.circle(surf, C.CHECKPOINT, cp["rect"].center, TILE // 3)
        for coin in self.coins:
            coin.draw(surf)
        self.player.draw(surf)
        for e in self.enemies:
            e.draw(surf)
        if self.goal_msg > 0:
            C.draw_text(surf, "Collect all the coins first!", 26, C.RED_DARK,
                        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 26))
        self._draw_hud(surf)

    def _render_static(self):
        """Render the unchanging arena once (floor, walls, checkpoint outlines and
        the black border) onto a TRANSPARENT surface. The void is left clear so
        the animated themed background shows through; blitted over it each frame."""
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for r in range(self.rows):
            for c in range(self.cols):
                ch = self.grid[r][c]
                if ch == " ":
                    continue
                rect = self._cell_rect(c, r)
                if ch in "SE":
                    surf.fill(C.GREEN, rect)
                elif ch == "#":
                    surf.fill(self.theme["wall"], rect)
                else:  # floor checker
                    color = self.theme["floor_a"] if (r + c) % 2 == 0 else self.theme["floor_b"]
                    surf.fill(color, rect)

        # Checkpoint outline rings (the filled disc is drawn live once active).
        for cp in self.checkpoints:
            pygame.draw.circle(surf, C.CHECKPOINT, cp["rect"].center, TILE // 3, 3)

        # Black outline wherever a walkable cell meets a non-walkable one.
        t = 3
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] not in WALKABLE:
                    continue
                rect = self._cell_rect(c, r)
                if not self._walk(r - 1, c):
                    surf.fill(C.BORDER, (rect.left, rect.top, TILE, t))
                if not self._walk(r + 1, c):
                    surf.fill(C.BORDER, (rect.left, rect.bottom - t, TILE, t))
                if not self._walk(r, c - 1):
                    surf.fill(C.BORDER, (rect.left, rect.top, t, TILE))
                if not self._walk(r, c + 1):
                    surf.fill(C.BORDER, (rect.right - t, rect.top, t, TILE))
        return surf.convert_alpha()

    def _walk(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols and self.grid[r][c] in WALKABLE

    def _draw_hud(self, surf):
        surf.fill(C.BLACK, (0, 0, SCREEN_WIDTH, TOP_BAR_H))
        mid = TOP_BAR_H // 2
        self.menu_rect = C.draw_text(surf, "MENU", 28, C.WHITE, midleft=(16, mid))
        # Small gear button: opens Settings without leaving the level.
        gx = self.menu_rect.right + 26
        _draw_gear(surf, gx, mid, 11, C.WHITE)
        self.settings_rect = pygame.Rect(gx - 16, mid - 16, 32, 32)
        C.draw_text(surf, f"{self.theme['name'].upper()}   {self.index + 1}/{self.total}",
                    26, C.WHITE, center=(SCREEN_WIDTH // 2, mid))
        C.draw_text(surf, f"DEATHS: {self.deaths}", 28, C.WHITE,
                    midright=(SCREEN_WIDTH - 16, mid))
        if self.total_coins:
            collected = self.total_coins - self.coins_left
            C.draw_text(surf, f"COINS: {collected}/{self.total_coins}", 24, C.YELLOW,
                        midleft=(gx + 28, mid))
