# Sound effects

The game synthesizes all of these in code, so it has sound out of the box and
this folder can stay empty.

To use your **own** sound instead, drop a file here with the matching name and
the game will load it automatically (a `.wav` is tried first, then `.ogg`):

| File name (put here)   | Plays when...            |
|------------------------|--------------------------|
| `coin.wav`             | you grab a coin          |
| `checkpoint.wav`       | you reach a checkpoint   |
| `death.wav`            | you die                  |
| `level_complete.wav`   | you finish a level       |
| `stage_complete.wav`   | you clear a 5-level stage / beat the game |

Overall sound-effect loudness is adjustable in-game on the Settings screen
(saved to `settings.json`); the starting default is `DEFAULT_SFX_VOLUME` in
`audio.py`.
