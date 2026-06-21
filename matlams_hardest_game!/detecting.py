"""Level definitions for the game.

A level is a dict with:
    name        - display name
    map         - list of equal-length strings. Tile chars:
                    ' ' void (not walkable)   '.' floor
                    '#' wall (not walkable)   'S' start zone   'E' end zone
    enemies     - list of enemy dicts (tile coordinates, see helpers below)
    coins       - optional list of (x, y) tile coords to collect
    checkpoints - optional list of (x, y) tile coords (start is implicit)

Tile coordinate (x, y) refers to the CENTER of grid cell (col=x, row=y); the
runtime converts these to pixels and centers the grid in the play area.
"""

import math


# --- Map authoring ----------------------------------------------------------
def _grid(cols, rows):
    """A blank (all void) mutable grid."""
    return [[" "] * cols for _ in range(rows)]


def _fill(g, r0, r1, c0, c1, ch="."):
    """Fill the inclusive cell rectangle rows r0..r1, cols c0..c1 with `ch`."""
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            g[r][c] = ch


def _done(g):
    return ["".join(row) for row in g]


def _boxed(cols, rows, top, bot, left, right, stub_rows):
    """A rectangular floor box with green start/exit stubs poking out the sides.

    The start stub fills cols 1..left-1 and the exit stub cols right+1..cols-2,
    both spanning the rows in `stub_rows` (gives the classic protruding look).
    """
    g = _grid(cols, rows)
    _fill(g, top, bot, left, right, ".")
    sr0, sr1 = stub_rows
    _fill(g, sr0, sr1, 1, left - 1, "S")
    _fill(g, sr0, sr1, right + 1, cols - 2, "E")
    return _done(g)


def _carve(rows, cells, ch="#"):
    """Return a copy of `rows` (list of strings) with each (r, c) set to `ch`."""
    grid = [list(row) for row in rows]
    for r, c in cells:
        grid[r][c] = ch
    return ["".join(row) for row in grid]


# --- Enemy authoring --------------------------------------------------------
def vmover(x, top, bottom, speed, phase):
    """Vertical ping-pong mover in column x between rows top..bottom."""
    return {"type": "linear", "axis": "v", "x": x, "y": top,
            "range": bottom - top, "speed": speed, "phase": phase}


def hmover(y, left, right, speed, phase):
    """Horizontal ping-pong mover on row y between cols left..right."""
    return {"type": "linear", "axis": "h", "x": left, "y": y,
            "range": right - left, "speed": speed, "phase": phase}


def orbit(cx, cy, r, speed, phase=0.0):
    """Circular orbiter around (cx, cy). Negative speed reverses direction."""
    return {"type": "circle", "cx": cx, "cy": cy, "r": r, "speed": speed, "phase": phase}


def dmover(x0, y0, x1, y1, speed, phase=0.0):
    """Diagonal (any-angle) ping-pong between tile points (x0,y0) and (x1,y1)."""
    return {"type": "diag", "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "speed": speed, "phase": phase}


def patrol(pts, speed, phase=0.0):
    """One-directional loop around the closed list of tile waypoints `pts`."""
    return {"type": "patrol", "pts": list(pts), "speed": speed, "phase": phase}


def rect_patrol(c0, r0, c1, r1, speed, phase=0.0):
    """Patrol the four corners of the tile rectangle (c0,r0)-(c1,r1)."""
    return patrol([(c0, r0), (c1, r0), (c1, r1), (c0, r1)], speed, phase)


def chaser(x, y, speed):
    """Homing enemy that starts at tile (x, y) and tracks the player."""
    return {"type": "chase", "x": x, "y": y, "speed": speed}


def windmill(cx, cy, radii, arms, speed, phase=0.0):
    """A rigid rotating windmill: `arms` spokes of orbiters at each radius in
    `radii`, all sharing one centre and angular speed. Returns a LIST of orbit
    dicts (combine into an enemies list with `+ windmill(...)`).
    """
    return [orbit(cx, cy, r, speed, phase + arm / arms)
            for arm in range(arms) for r in radii]


def block(x, y):
    """A stationary enemy parked at tile (x, y) (a fixed, radius-0 orbiter)."""
    return orbit(x, y, 0.0, 0.0)


def _alt(i):
    """Alternating phase 0.0 / 0.5 for index i (opposite-phase neighbours)."""
    return 0.0 if i % 2 == 0 else 0.5


# --- The 20 levels, 4 stages of 5 --------------------------------------------
# Difficulty: BRUTAL. Start/exit move around the arena from level to level and
# every map has a distinct shape. New movement types are introduced one per
# level (diag=L4, patrol=L5, windmill=L6, chaser=L7) then combined. Each block
# of 5 is a themed stage (see config.THEMES): Lavender Plains, Emerald Forest,
# Amber Inferno, Cosmic Void. Coins are never placed inside a windmill.
def _build():
    levels = []

    # ====================== STAGE 1 - Lavender Plains ======================

    # 1 - First Steps: open box, a wall of vertical movers.  LEFT -> RIGHT.
    levels.append({
        "name": "First Steps",
        "map": _boxed(22, 9, 1, 7, 4, 17, (3, 5)),
        "enemies": [vmover(x, 1, 7, 4.8, _alt(i))
                    for i, x in enumerate([6, 8, 10, 12, 14])],
    })

    # 2 - Sidewinder: a tall shaft swept by horizontal lanes.  BOTTOM -> TOP.
    g = _grid(16, 13)
    _fill(g, 1, 11, 3, 12)
    _fill(g, 12, 12, 6, 9, "S")
    _fill(g, 0, 0, 6, 9, "E")
    levels.append({
        "name": "Sidewinder",
        "map": _done(g),
        "enemies": [hmover(y, 3, 12, 5.0, _alt(i))
                    for i, y in enumerate(range(1, 12))],   # one per row
        "coins": [(4, 9), (11, 3)],
    })

    # 3 - Carousel: orbiters; rest in the calm eye, dodge the columns. L -> R.
    levels.append({
        "name": "Carousel",
        "map": _boxed(24, 10, 1, 8, 4, 19, (4, 6)),
        "enemies": [orbit(7, 4, 1.9, 3.6, 0.0), orbit(12, 4, 1.9, -3.6, 0.25),
                    orbit(17, 4, 1.9, 3.6, 0.5),
                    vmover(9, 1, 8, 5.0, 0.0), vmover(15, 1, 8, 5.0, 0.5)],
        "coins": [(7, 4), (17, 4)],
    })

    # 4 - Crossfire: a plus arena slashed by diagonals (DIAG intro). TOP -> BOTTOM.
    g = _grid(17, 13)
    _fill(g, 1, 11, 6, 10)          # vertical arm
    _fill(g, 5, 7, 1, 15)           # horizontal arm
    _fill(g, 0, 0, 7, 9, "S")
    _fill(g, 12, 12, 7, 9, "E")
    levels.append({
        "name": "Crossfire",
        "map": _done(g),
        "enemies": [dmover(1, 5, 15, 7, 5.0, 0.0), dmover(15, 5, 1, 7, 5.0, 0.5),
                    dmover(6, 1, 10, 11, 5.0, 0.25), dmover(10, 1, 6, 11, 5.0, 0.75),
                    orbit(8, 6, 1.6, 3.4, 0.0)],
        "coins": [(8, 2), (8, 10), (2, 6), (14, 6)],
    })

    # 5 - Rising Tide: a vertical mover in every column. In each group of 3 the
    #     left is slow, the middle faster, the right very fast (speeds 1:2:3), all
    #     starting at the top - so they spread into a wave and surge back up to the
    #     top together every ~6-7 seconds. Coins sit up top where they converge.
    #     LEFT -> RIGHT.
    g = _grid(21, 11)
    _fill(g, 1, 9, 3, 17)            # mover field
    _fill(g, 8, 9, 1, 2, "S")       # start stub, bottom-left
    _fill(g, 8, 9, 18, 19, "E")     # exit stub, bottom-right
    _TIDE = (2.0, 4.0, 6.0)          # slow / faster / very fast  (1:2:3 -> align at top)
    levels.append({
        "name": "Rising Tide",
        "map": _done(g),
        "enemies": [vmover(c, 1, 9, _TIDE[(c - 3) % 3], 0.0) for c in range(3, 18)],
        "coins": [(5, 1), (10, 1), (15, 1), (8, 7), (13, 7)],
    })

    # ====================== STAGE 2 - Emerald Forest =======================

    # 6 - Windmill Hall (WINDMILL intro): a corridor exactly as tall as the
    #     windmills - thread THREE counter-spinning swirls. The only windmill-safe
    #     spots (cols 9 and 15) are blocked by fixed hazards, so you must slip past
    #     them high or low while grabbing the coins.  RIGHT -> LEFT.
    g = _grid(24, 7)
    _fill(g, 1, 5, 3, 20)
    _fill(g, 2, 4, 21, 22, "S")
    _fill(g, 2, 4, 1, 2, "E")
    levels.append({
        "name": "Windmill Hall",
        "map": _done(g),
        "enemies": (windmill(6, 3, [1.0, 2.0], 3, 2.8, 0.0)
                    + windmill(12, 3, [1.0, 2.0], 3, -2.8, 0.16)
                    + windmill(18, 3, [1.0, 2.0], 3, 2.8, 0.33)
                    + [block(9, 3), block(15, 3)]),   # fixed hazards in the safe gaps
        "coins": [(9, 1), (15, 5)],
    })

    # 7 - The Stalker: a homing chaser; break its line of sight on the walls
    #     (CHASE intro).  TOP-LEFT -> BOTTOM-RIGHT.
    g = _grid(24, 11)
    _fill(g, 1, 9, 3, 20)
    _fill(g, 1, 2, 3, 4, "S")
    _fill(g, 8, 9, 19, 20, "E")
    m = _carve(_done(g), [(r, 9) for r in range(1, 7)] + [(r, 15) for r in range(4, 10)])
    levels.append({
        "name": "The Stalker",
        "map": m,
        "enemies": [chaser(19, 2, 3.0),
                    vmover(6, 1, 9, 5.0, 0.0), vmover(13, 1, 9, 5.0, 0.5)],
        "checkpoints": [(11, 5)],
    })

    # 8 - Pinwheel: a four-armed windmill fills a snug octagon - the arms reach
    #     the walls, so you must thread BETWEEN them (no room to go around).
    #     Snatch the coins off the arms. Enter from the TOP, leave by the LEFT.
    g = _grid(18, 14)
    oct_r0, oct_c0, oct_sz, cut = 3, 6, 9, 2      # 9x9 square = arm reach; chamfered
    for rr in range(oct_r0, oct_r0 + oct_sz):
        for cc in range(oct_c0, oct_c0 + oct_sz):
            a, b = cc - oct_c0, rr - oct_r0
            if (a + b >= cut and (oct_sz - 1 - a) + b >= cut
                    and a + (oct_sz - 1 - b) >= cut
                    and (oct_sz - 1 - a) + (oct_sz - 1 - b) >= cut):
                g[rr][cc] = "."
    _fill(g, 1, 2, 9, 11, "S")                    # start stub poking out the top
    _fill(g, 6, 8, 3, 5, "E")                     # exit stub poking out the left
    levels.append({
        "name": "Pinwheel",
        "map": _done(g),
        "enemies": windmill(10, 7, [1, 2, 3, 4], 4, 1.8, 0.0),
        "coins": [(10, 4), (13, 7), (10, 10)],
    })

    # 9 - Hedge Maze: a walled maze of corridors. Movers sweep the lanes and the
    #     connectors, so enemies keep blocking the way - time them and use the
    #     alternate routes.  BOTTOM-LEFT -> TOP-RIGHT.
    g = _grid(23, 13)
    _fill(g, 1, 11, 1, 21, "#")                  # solid hedge block
    for r in (2, 5, 8, 11):                       # horizontal corridors
        _fill(g, r, r, 2, 20, ".")
    _fill(g, 2, 5, 4, 4, ".")                     # H1<->H2 connectors
    _fill(g, 2, 5, 18, 18, ".")
    _fill(g, 5, 8, 8, 8, ".")                     # H2<->H3 connectors
    _fill(g, 5, 8, 14, 14, ".")
    _fill(g, 8, 11, 4, 4, ".")                    # H3<->H4 connectors
    _fill(g, 8, 11, 18, 18, ".")
    _fill(g, 11, 11, 0, 1, "S")                   # start (bottom-left)
    _fill(g, 2, 2, 21, 22, "E")                   # exit (top-right)
    levels.append({
        "name": "Hedge Maze",
        "map": _done(g),
        "enemies": [hmover(2, 2, 20, 5.0, 0.0),
                    hmover(8, 2, 20, 5.0, 1 / 3),
                    hmover(11, 2, 20, 5.0, 2 / 3),
                    vmover(4, 2, 5, 4.5, 0.25),
                    vmover(8, 5, 8, 4.5, 0.0),
                    vmover(18, 8, 11, 4.5, 0.5)],
        "coins": [(4, 8), (18, 5), (11, 11)],
        "checkpoints": [(14, 6)],
    })

    # 10 - Concentric: nested rectangles of marchers, one ring inside another,
    #      from the arena edge all the way to the centre - layers covering the
    #      whole square map. Penetrate to the centre and out the top, timing each
    #      ring's gap.  BOTTOM -> TOP.
    g = _grid(20, 14)
    _fill(g, 1, 12, 4, 15)                         # 12x12 floor
    _fill(g, 13, 13, 9, 10, "S")                  # start, bottom-centre
    _fill(g, 0, 0, 9, 10, "E")                    # exit, top-centre
    rings = ([rect_patrol(4, 1, 15, 12, 4.5, k / 7) for k in range(7)]    # outer edge layer
             + [rect_patrol(5, 2, 14, 11, 4.5, k / 6) for k in range(6)]   # 2nd layer
             + [rect_patrol(7, 4, 12, 9, 4.5, k / 4) for k in range(4)]    # 3rd layer
             + [rect_patrol(9, 6, 10, 7, 3.5, k / 2) for k in range(2)])   # inner layer
    levels.append({
        "name": "Concentric",
        "map": _done(g),
        "enemies": rings,
        "coins": [(9, 6), (6, 6), (13, 6)],
        "checkpoints": [(9, 10)],
    })

    # ====================== STAGE 3 - Amber Inferno ========================

    # 11 - Labyrinth: serpentine walls, an orbiter per chamber, a chaser hunting.
    #      LEFT -> RIGHT.
    m = _boxed(24, 11, 1, 9, 4, 19, (4, 6))
    m = _carve(m, ([(r, 8) for r in range(1, 7)] +     # wall A, gap rows 7-9
                   [(r, 12) for r in range(4, 10)] +    # wall B, gap rows 1-3
                   [(r, 16) for r in range(1, 7)]))      # wall C, gap rows 7-9
    levels.append({
        "name": "Labyrinth",
        "map": m,
        "enemies": [orbit(6, 5, 1.5, 3.6, 0.0), orbit(10, 5, 1.5, -3.6, 0.3),
                    orbit(14, 5, 1.5, 3.6, 0.6), orbit(17, 5, 1.5, -3.6, 0.1),
                    chaser(18, 8, 3.2)],
        "coins": [(6, 2), (14, 8), (18, 2)],
        "checkpoints": [(10, 8), (14, 2)],
    })

    # 12 - The Gauntlet: a vertical squeeze; snake through wall gaps as lanes
    #      and diagonals grind.  TOP -> BOTTOM.
    g = _grid(13, 13)
    _fill(g, 1, 11, 2, 11)
    _fill(g, 0, 0, 5, 6, "S")
    _fill(g, 12, 12, 5, 6, "E")
    m = _carve(_done(g), [(3, c) for c in range(2, 8)] + [(7, c) for c in range(6, 12)])
    levels.append({
        "name": "The Gauntlet",
        "map": m,
        "enemies": [hmover(2, 2, 11, 6.0, 0.0), hmover(5, 2, 11, 6.0, 0.5),
                    hmover(9, 2, 11, 6.0, 0.25),
                    dmover(2, 1, 11, 11, 6.0, 0.0), dmover(11, 1, 2, 11, 6.0, 0.5)],
    })

    # 13 - Hunted: an open pillar lattice; two chasers cut straight at you.
    #      BOTTOM-LEFT -> TOP-RIGHT.
    g = _grid(24, 11)
    _fill(g, 1, 9, 3, 20)
    _fill(g, 8, 9, 3, 4, "S")
    _fill(g, 1, 2, 19, 20, "E")
    m = _carve(_done(g), [(r, c) for r in (2, 4, 6, 8) for c in (6, 9, 12, 15, 18)])
    levels.append({
        "name": "Hunted",
        "map": m,
        "enemies": [chaser(4, 2, 3.4), chaser(19, 8, 3.4),
                    hmover(3, 3, 20, 5.5, 0.0), hmover(7, 3, 20, 5.5, 0.5),
                    vmover(7, 1, 9, 5.5, 0.0), vmover(16, 1, 9, 5.5, 0.5)],
        "checkpoints": [(11, 5)],
    })

    # 14 - Clockwork: the same arena, but every 2x2 block of tiles has one enemy
    #      tracing a square loop around it - and they all move in perfect sync
    #      (identical speed and phase).  LEFT -> RIGHT.
    levels.append({
        "name": "Clockwork",
        "map": _boxed(24, 12, 1, 10, 3, 20, (5, 7)),
        "enemies": [rect_patrol(c, r, c + 1, r + 1, 2.3, 0.0)
                    for r in range(1, 10, 2) for c in range(3, 20, 2)],
        "coins": [(4, 2), (19, 2), (4, 9), (19, 9)],
    })

    # 15 - Crossroads: a busy intersection. Cross-traffic sweeps the horizontal
    #      arm, a roundabout spins at the hub and two lanes ride the side columns
    #      while a chaser prowls; grab the coins out at the arm ends.  TOP -> BOTTOM.
    g = _grid(23, 13)
    _fill(g, 1, 11, 9, 13)          # vertical arm
    _fill(g, 5, 8, 1, 21)           # horizontal arm (full width, 4 tall)
    _fill(g, 0, 0, 10, 12, "S")
    _fill(g, 12, 12, 10, 12, "E")
    levels.append({
        "name": "Crossroads",
        "map": _done(g),
        "enemies": [hmover(5, 1, 21, 6.0, 0.0), hmover(8, 1, 21, 6.0, 0.5),
                    vmover(9, 1, 11, 6.0, 0.0), vmover(13, 1, 11, 6.0, 0.5),
                    orbit(11, 6, 1.6, 3.2, 0.0),
                    chaser(2, 6, 3.4)],
        "coins": [(3, 6), (19, 6)],
        "checkpoints": [(11, 9)],
    })

    # ====================== STAGE 4 - Cosmic Void ==========================

    # 16 - Meat Grinder: an S-snake; a sweeping lane plus two windmill grinders
    #      per band, and a mover per connector.  TOP-LEFT -> BOTTOM-RIGHT.
    g = _grid(24, 13)
    _fill(g, 1, 3, 3, 20)          # top band
    _fill(g, 5, 7, 3, 20)         # middle band
    _fill(g, 9, 11, 3, 20)        # bottom band
    _fill(g, 1, 7, 17, 20)        # right connector (top -> middle)
    _fill(g, 5, 11, 3, 6)         # left connector (middle -> bottom)
    _fill(g, 0, 0, 3, 4, "S")
    _fill(g, 12, 12, 19, 20, "E")
    levels.append({
        "name": "Meat Grinder",
        "map": _done(g),
        "enemies": ([hmover(2, 3, 20, 6.0, 0.0), hmover(6, 3, 20, 6.0, 0.5),
                     hmover(10, 3, 20, 6.0, 0.25),
                     vmover(18, 1, 7, 5.5, 0.0), vmover(5, 5, 11, 5.5, 0.5)]
                    # grinder windmills: two per band (the old spinners are now
                    # windmills, plus three extra); col 11 stays clear for the coins
                    + windmill(8, 2, [1.0], 3, 3.4, 0.0)
                    + windmill(14, 2, [1.0], 3, -3.4, 0.2)
                    + windmill(8, 6, [1.0], 3, -3.4, 0.1)
                    + windmill(14, 6, [1.0], 3, 3.4, 0.3)
                    + windmill(8, 10, [1.0], 3, 3.4, 0.15)
                    + windmill(15, 10, [1.0], 3, -3.4, 0.6)),
        "coins": [(11, 2), (11, 6), (11, 10)],
        "checkpoints": [(18, 6), (5, 9)],
    })

    # 17 - The Gallery: two big windmills fill the large corner rooms; patrols
    #      still guard the other two corners. Partition walls with offset
    #      doorways make you weave through.  BOTTOM-CENTRE -> TOP-CENTRE.
    g = _grid(24, 12)
    _fill(g, 1, 10, 3, 20)
    _fill(g, 4, 4, 3, 14, "#")     # upper partition wall, doorway on the right
    _fill(g, 7, 7, 9, 20, "#")     # lower partition wall, doorway on the left
    _fill(g, 11, 11, 11, 12, "S")
    _fill(g, 0, 0, 11, 12, "E")
    levels.append({
        "name": "The Gallery",
        "map": _done(g),
        "enemies": ([rect_patrol(3, 1, 8, 3, 5.4, 0.0),       # top-left corner guard
                     rect_patrol(15, 8, 20, 10, 5.4, 0.1),    # bottom-right corner guard
                     hmover(3, 3, 20, 5.0, 0.0), hmover(5, 3, 20, 5.0, 0.5),
                     hmover(8, 3, 20, 5.0, 0.25)]
                    + windmill(17.5, 3.5, [1.3, 2.2], 4, 2.4, 0.0)    # big windmill: upper-right room
                    + windmill(5.5, 7.5, [1.3, 2.2], 4, -2.4, 0.0)),  # big windmill: lower-left room
        "coins": [(4, 2), (20, 1), (3, 10), (19, 9), (11, 5)],
        "checkpoints": [(11, 9)],
    })

    # 18 - Tempest: a field of windmills with two chasers closing in.  TOP -> BOTTOM.
    g = _grid(24, 12)
    _fill(g, 1, 10, 3, 20)
    _fill(g, 0, 0, 11, 12, "S")
    _fill(g, 11, 11, 11, 12, "E")
    levels.append({
        "name": "Tempest",
        "map": _done(g),
        "enemies": (windmill(6, 4, [1.3, 2.4], 4, 2.4, 0.0)
                    + windmill(16, 4, [1.3, 2.4], 4, -2.4, 0.12)
                    + windmill(11, 8, [1.3, 2.4], 4, 2.4, 0.25)
                    + [chaser(4, 8, 3.6), chaser(19, 8, 3.6)]),
        "coins": [(4, 9), (19, 2)],     # opposite corners, clear of the windmills
        "checkpoints": [(11, 4)],
    })

    # 19 - Apocalypse: every movement type at once, at maximum speed. Start/exit
    #      are protruding pockets so the full-arena movers stay off the green.
    #      TOP-LEFT -> BOTTOM-RIGHT.
    g = _grid(24, 13)
    _fill(g, 1, 11, 3, 20)
    _fill(g, 0, 0, 3, 4, "S")
    _fill(g, 12, 12, 19, 20, "E")
    levels.append({
        "name": "Apocalypse",
        "map": _done(g),
        "enemies": (windmill(7, 4, [1.3, 2.4], 4, 2.6, 0.0)
                    + windmill(16, 8, [1.3, 2.4], 4, -2.6, 0.12)
                    + [dmover(3, 1, 20, 11, 6.5, 0.0), dmover(20, 1, 3, 11, 6.5, 0.5),
                       vmover(11, 1, 11, 6.5, 0.0), vmover(13, 1, 11, 6.5, 0.5),
                       hmover(2, 3, 20, 6.0, 0.25), hmover(10, 3, 20, 6.0, 0.75),
                       rect_patrol(9, 4, 14, 8, 6.0, 0.0),
                       chaser(4, 6, 3.8), chaser(19, 6, 3.8)]),
        "coins": [(20, 2), (3, 10)],
        "checkpoints": [(11, 11)],
    })

    # 20 - Finale: Gridlock: an up-down mover in EVERY column and a left-right
    #      mover in EVERY row, all alternating phase, with four coins.  L -> R.
    #      (_boxed stubs sit outside the mover grid, so the green stays safe.)
    levels.append({
        "name": "Finale: Gridlock",
        "map": _boxed(20, 11, 1, 9, 4, 15, (4, 6)),
        "enemies": ([vmover(x, 1, 9, 4.2, _alt(i)) for i, x in enumerate(range(4, 16))]
                    + [hmover(y, 4, 15, 4.2, _alt(i)) for i, y in enumerate(range(1, 10))]),
        "coins": [(6, 3), (13, 3), (6, 7), (13, 7)],
    })

    return levels


LEVELS = _build()


def validate_levels():
    """Sanity-check every level. Raises AssertionError on a bad definition."""
    for idx, lv in enumerate(LEVELS, 1):
        grid = lv["map"]
        w = len(grid[0])
        rows = len(grid)
        for r, row in enumerate(grid):
            assert len(row) == w, f"L{idx} '{lv['name']}': row {r} width {len(row)} != {w}"
        joined = "".join(grid)
        assert "S" in joined, f"L{idx} '{lv['name']}': no start zone"
        assert "E" in joined, f"L{idx} '{lv['name']}': no end zone"

        def walkable(tx, ty):
            ci, ri = int(round(tx)), int(round(ty))
            if not (0 <= ri < rows and 0 <= ci < w):
                return False
            return grid[ri][ci] in ".SE"

        for c in lv.get("coins", []):
            assert walkable(*c), f"L{idx} '{lv['name']}': coin {c} not on floor"
        for cp in lv.get("checkpoints", []):
            assert walkable(*cp), f"L{idx} '{lv['name']}': checkpoint {cp} not on floor"
        for e in lv.get("enemies", []):
            kind = e["type"]
            if kind == "linear":
                if e["axis"] == "h":
                    pts = [(e["x"], e["y"]), (e["x"] + e["range"], e["y"])]
                else:
                    pts = [(e["x"], e["y"]), (e["x"], e["y"] + e["range"])]
            elif kind == "circle":
                pts = [(e["cx"], e["cy"])]
            elif kind == "diag":
                pts = [(e["x0"], e["y0"]), (e["x1"], e["y1"])]
            elif kind == "patrol":
                pts = list(e["pts"])
            else:  # "chase"
                pts = [(e["x"], e["y"])]
            for px, py in pts:
                assert walkable(px, py), \
                    f"L{idx} '{lv['name']}': enemy anchor {(px, py)} not on floor"

        # No STATIC enemy path may cross a green start/exit cell (chasers are
        # kept out at runtime instead). Sample each path and check the cells.
        def is_green(tx, ty):
            ci, ri = int(round(tx)), int(round(ty))
            return 0 <= ri < rows and 0 <= ci < w and grid[ri][ci] in "SE"

        def path_samples(e):
            kind = e["type"]
            if kind == "linear":
                n = max(1, int(round(abs(e["range"]))))
                for i in range(n + 1):
                    t = e["range"] * i / n
                    yield (e["x"] + t, e["y"]) if e["axis"] == "h" else (e["x"], e["y"] + t)
            elif kind == "diag":
                for i in range(21):
                    t = i / 20.0
                    yield (e["x0"] + (e["x1"] - e["x0"]) * t,
                           e["y0"] + (e["y1"] - e["y0"]) * t)
            elif kind == "patrol":
                pts = list(e["pts"])
                for i in range(len(pts)):
                    ax, ay = pts[i]
                    bx, by = pts[(i + 1) % len(pts)]
                    for k in range(11):
                        t = k / 10.0
                        yield (ax + (bx - ax) * t, ay + (by - ay) * t)
            elif kind == "circle":
                for k in range(24):
                    a = 2.0 * math.pi * k / 24.0
                    yield (e["cx"] + math.cos(a) * e["r"], e["cy"] + math.sin(a) * e["r"])
            # "chase" intentionally skipped (handled at runtime).

        for e in lv.get("enemies", []):
            for px, py in path_samples(e):
                assert not is_green(px, py), \
                    f"L{idx} '{lv['name']}': {e['type']} enemy path enters green at {(round(px,1), round(py,1))}"
    return True


if __name__ == "__main__":
    validate_levels()
    print(f"OK: {len(LEVELS)} levels valid.")
