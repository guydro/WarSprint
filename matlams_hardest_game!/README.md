# The Matlam's Hardest Game

A pygame clone of *The Matlam's Hardest Game*: steer the **red square** from the
green start zone to the green exit while dodging patrolling **blue circles**.
Some levels hide **yellow coins** — you must collect every one before the exit opens.

## Run

```sh
python main.py
```

Requires Python 3 and `pygame` (tested with pygame-ce 2.5.7).

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move the red square |
| `R` | Restart the level from the beginning (clears checkpoints) |
| `Esc` | Back to the main menu |
| Mouse / Enter | Use menu buttons |

## How it works

- Touching a blue circle sends you back to the **last checkpoint** you reached
  (the start zone is the first one). Coins reset to that checkpoint's state too.
- The green start/exit zones are **safe**: enemies never enter them (homing
  chasers stop at the edge), so you can always pause there.
- The exit only completes the level once **all coins** are collected.
- Orange rings mark checkpoints; they fill in once activated.
- 20 levels of escalating, *brutal* difficulty, grouped into **4 stages of 5**,
  each with its own colour theme: **Lavender Plains** (1–5), **Emerald Forest**
  (6–10), **Amber Inferno** (11–15) and **Cosmic Void** (16–20). The start and
  exit move around the arena from level to level, and every map has a distinct
  shape. Progress (unlocked levels + total deaths) is saved to `progress.json`.
- Clearing a stage (every 5th level) shows a **stage-clear message** you dismiss
  with any key before the next level loads.

## Audio

Both the sound effects (coin, checkpoint, death, level/stage complete) **and** an
upbeat background music loop are synthesized in code, so the game has full audio
with no extra files. You can override any of them by dropping audio files into
`assets/` — see [`assets/sounds/README.md`](assets/sounds/README.md) and
[`assets/music/README.md`](assets/music/README.md).

Music and sound-effect volume are adjustable in-game from the **Settings** screen
(reachable from the main menu) and saved to `settings.json`. Starting defaults
are `DEFAULT_MUSIC_VOLUME` / `DEFAULT_SFX_VOLUME` in `audio.py`. If there is no
audio device the game just runs silently.

To change the text shown after each stage, edit `STAGE_CLEAR_MESSAGES` in
`config.py` (one `(title, subtitle)` entry per stage; the last entry is the
game-complete screen).

### Enemy movement types

| Type | Behaviour |
|------|-----------|
| Vertical / horizontal | Straight ping-pong along one axis (`vmover`, `hmover`) |
| Orbit | Spins around a fixed centre (`orbit`) — the centre is a safe "eye" |
| Diagonal | Ping-pongs along any line between two points (`dmover`) |
| Patrol | Marches one-way around a rectangle's perimeter (`rect_patrol`) |
| Windmill | A rigid star of orbiters on radial spokes (`windmill`) |
| Chaser | A **purple** circle that homes in on you (`chaser`) — outrun it! |

`config.ENEMY_SPEED_SCALE` is a global multiplier on every enemy's speed — raise it
to make the game even harder.

## Code layout

| File | Role |
|------|------|
| `main.py` | Window, main loop, state machine (menu / play / complete / stage-clear), progress save |
| `config.py` | Screen size, colors, tuning constants, stage messages, font helpers |
| `levels.py` | The 20 level definitions + `validate_levels()` |
| `sprites.py` | `Player`, `Enemy`, `Coin` and circle–rect collision |
| `game.py` | Per-level runtime: layout, update, collision, drawing, HUD |
| `menu.py` | Main menu and level-select screens |
| `audio.py` | Sound-effect synthesis/loading and background music |

To add a level, append a dict to `LEVELS` in `levels.py`. Build the map with
`_boxed` (a floor box with green start/exit tabs), `_grid` + `_fill` (any custom
shape — crosses, corridors, staircases, snakes), and `_carve` (walls/pillars);
place enemies with `vmover`, `hmover`, `orbit`, `dmover`, `rect_patrol`/`patrol`,
`chaser`, and `windmill` (which returns a *list* of orbiters — combine it into an
enemies list with `+ windmill(...)`). Run `python levels.py` to validate.
