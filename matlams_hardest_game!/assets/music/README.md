# Background music

By default the game generates its own upbeat background loop in code, so this
folder can stay empty.

To use your **own** track instead, drop a single audio file here and it will
loop forever in the background (taking priority over the generated loop).
Supported formats: `.ogg` (recommended), `.mp3`, `.wav`. If you put more than one
file here, the first one alphabetically is used.

Example: copy your track to `assets/music/background.ogg`.

Music loudness is adjustable in-game on the Settings screen (saved to
`settings.json`); the starting default is `DEFAULT_MUSIC_VOLUME` in `audio.py`.
