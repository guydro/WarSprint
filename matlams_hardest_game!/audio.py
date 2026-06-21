"""Sound effects and background music.

Self-contained and fail-safe: if there is no audio device (or anything else
goes wrong) the whole module silently disables itself and every function below
becomes a harmless no-op, so the game always keeps running.

Sound effects are synthesized in code with a warm, mellow tone, and the
background music is generated too (a short upbeat loop) -- so the game has full
audio out of the box. You can still override things with your own files:
  * any SFX -> drop  assets/sounds/<name>.wav  (or .ogg)
  * music   -> drop a track in  assets/music/  (used instead of the generated loop)

Per-music / per-SFX volume is adjustable at runtime (see the Settings screen)
and persisted to settings.json next to this file.
"""

import array
import json
import math
import os

import pygame

# ---------------------------------------------------------------------------
# Default volumes (0.0 = silent .. 1.0 = full). These are just the starting
# values; the Settings screen overrides them and saves to settings.json.
DEFAULT_MUSIC_VOLUME = 0.5
DEFAULT_SFX_VOLUME = 0.7
# ---------------------------------------------------------------------------

_SAMPLE_RATE = 44100

# Warm additive timbre: fundamental + a couple of quieter harmonics (no harsh
# square edges). Individual effects can override this with their own list.
_WARM = (1.0, 0.45, 0.2)

# Note frequencies (Hz) used by the effects below, for readability.
C4, E4, F4, A4 = 261.63, 329.63, 349.23, 440.00
C5, E5, G5, A5, B5, C6 = 523.25, 659.25, 783.99, 880.00, 987.77, 1046.50
E6 = 1318.51

# Recipe for each synthesized sound effect (used when no override file exists).
#   vol       : per-effect loudness 0..1 (on top of the global SFX volume)
#   harmonics : optional timbre override
#   notes     : (frequency_hz, duration_ms) segments played back to back
SOUND_SPECS = {
    "coin":           {"vol": 0.50, "notes": [(A5, 70), (E6, 110)]},
    "checkpoint":     {"vol": 0.50, "notes": [(E5, 90), (B5, 200)]},
    "death":          {"vol": 0.50, "harmonics": (1.0, 0.5, 0.28, 0.14),
                       "notes": [(A4, 110), (F4, 110), (C4, 260)]},
    "level_complete": {"vol": 0.50, "notes": [(C5, 100), (E5, 100), (G5, 240)]},
    "stage_complete": {"vol": 0.55, "notes": [(C5, 110), (E5, 110), (G5, 110), (C6, 360)]},
}

# Folders for user-supplied overrides / music (relative to this file).
_HERE = os.path.dirname(os.path.abspath(__file__))
_SFX_DIR = os.path.join(_HERE, "assets", "sounds")
_MUSIC_DIR = os.path.join(_HERE, "assets", "music")
_MUSIC_EXTS = (".ogg", ".mp3", ".wav")
_SETTINGS_FILE = os.path.join(_HERE, "settings.json")

ENABLED = False
_sounds = {}

_music_volume = DEFAULT_MUSIC_VOLUME
_sfx_volume = DEFAULT_SFX_VOLUME
_fullscreen = False         # display preference, persisted alongside the volumes
_music_mode = None          # "file" (streamed track) | "gen" (looping Sound) | None
_music_channel = None       # Channel the generated loop plays on
_music_sound = None         # cached generated loop


# --- lifecycle --------------------------------------------------------------
def init():
    """Load saved settings, start the mixer, and build every sound effect."""
    global ENABLED
    _load_settings()                        # also loads the fullscreen flag (audio-independent)
    try:
        pygame.mixer.quit()
        pygame.mixer.pre_init(_SAMPLE_RATE, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)   # keep room for the looping music + SFX
    except pygame.error:
        ENABLED = False
        return
    ENABLED = True
    _load_sounds()


def play(name):
    """Play a one-shot sound effect by name. No-op if audio is unavailable."""
    if not ENABLED:
        return
    snd = _sounds.get(name)
    if snd is None:
        return
    try:
        snd.play()
    except pygame.error:
        pass


def start_music():
    """Begin looping background music: a track from assets/music/ if present,
    otherwise the generated loop. No-op if audio is unavailable."""
    global _music_mode, _music_channel, _music_sound
    if not ENABLED:
        return
    path = _find_music()
    if path:
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(_music_volume)
            pygame.mixer.music.play(-1)
            _music_mode = "file"
            return
        except pygame.error:
            pass
    if _music_sound is None:
        _music_sound = _generate_music()
    if _music_sound is not None:
        try:
            _music_channel = _music_sound.play(loops=-1)
            if _music_channel is not None:
                _music_channel.set_volume(_music_volume)
                _music_mode = "gen"
        except pygame.error:
            pass


# --- volume control ---------------------------------------------------------
def get_music_volume():
    return _music_volume


def get_sfx_volume():
    return _sfx_volume


def get_fullscreen():
    return _fullscreen


def set_fullscreen(on):
    """Persist the fullscreen preference (the display itself is set by main)."""
    global _fullscreen
    _fullscreen = bool(on)
    _save_settings()


def set_music_volume(v):
    """Set music volume (0..1), apply it live, and persist it."""
    global _music_volume
    _music_volume = _clamp(v)
    if ENABLED:
        try:
            if _music_mode == "file":
                pygame.mixer.music.set_volume(_music_volume)
            elif _music_mode == "gen" and _music_channel is not None:
                _music_channel.set_volume(_music_volume)
        except pygame.error:
            pass
    _save_settings()


def set_sfx_volume(v):
    """Set sound-effect volume (0..1), apply it to all effects, and persist it."""
    global _sfx_volume
    _sfx_volume = _clamp(v)
    for snd in _sounds.values():
        try:
            snd.set_volume(_sfx_volume)
        except pygame.error:
            pass
    _save_settings()


# --- internals --------------------------------------------------------------
def _clamp(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))


def _load_settings():
    global _music_volume, _sfx_volume, _fullscreen
    try:
        with open(_SETTINGS_FILE) as f:
            d = json.load(f)
        _music_volume = _clamp(d.get("music_volume", _music_volume))
        _sfx_volume = _clamp(d.get("sfx_volume", _sfx_volume))
        _fullscreen = bool(d.get("fullscreen", _fullscreen))
    except (OSError, ValueError, TypeError):
        pass


def _save_settings():
    try:
        with open(_SETTINGS_FILE, "w") as f:
            json.dump({"music_volume": _music_volume, "sfx_volume": _sfx_volume,
                       "fullscreen": _fullscreen}, f)
    except OSError:
        pass


def _load_sounds():
    for name, spec in SOUND_SPECS.items():
        snd = _load_override(name) or _synth(spec)
        if snd is not None:
            try:
                snd.set_volume(_sfx_volume)
            except pygame.error:
                pass
            _sounds[name] = snd


def _load_override(name):
    """Return a Sound from assets/sounds/<name>.(wav|ogg) if one exists."""
    for ext in (".wav", ".ogg"):
        path = os.path.join(_SFX_DIR, name + ext)
        if os.path.isfile(path):
            try:
                return pygame.mixer.Sound(path)
            except pygame.error:
                return None
    return None


def _synth(spec):
    """Render a Sound from a spec as warm 16-bit stereo PCM.

    Each note is additive (fundamental + a few decaying harmonics) with a quick
    attack and a smooth exponential decay, which reads as mellow/retro rather
    than the harsh buzz of a raw square wave.
    """
    harmonics = spec.get("harmonics", _WARM)
    hsum = sum(abs(h) for h in harmonics) or 1.0
    amp = 32767 * spec.get("vol", 0.5)
    attack = max(1, int(_SAMPLE_RATE * 0.008))      # 8 ms
    samples = array.array("h")                       # signed 16-bit
    for freq, ms in spec["notes"]:
        n = max(1, int(_SAMPLE_RATE * ms / 1000))
        for i in range(n):
            t = i / _SAMPLE_RATE
            s = 0.0
            for k, h in enumerate(harmonics, start=1):
                s += h * math.sin(2.0 * math.pi * freq * k * t)
            s /= hsum
            if i < attack:                          # fade in
                env = i / attack
            else:                                   # exponential decay
                env = math.exp(-3.0 * (i - attack) / n)
            tail = n - i                            # clean fade out (no click)
            if tail < attack:
                env *= tail / attack
            v = int(amp * s * env)
            v = 32767 if v > 32767 else -32768 if v < -32768 else v
            samples.append(v)                       # left
            samples.append(v)                       # right
    try:
        return pygame.mixer.Sound(buffer=samples.tobytes())
    except pygame.error:
        return None


def _generate_music():
    """Generate an upbeat, looping background tune as a stereo Sound.

    A 16-bar progression (two phrases) with a different melody pattern each bar,
    so the loop runs ~30s and doesn't feel as repetitive. Uses numpy for speed;
    returns None (so the game stays quiet) if numpy is missing or anything fails.
    To use your own track instead, drop a file in assets/music/ -- start_music()
    prefers that over this.
    """
    try:
        import numpy as np
    except Exception:
        return None
    try:
        sr = _SAMPLE_RATE
        bpm = 128.0
        beat = 60.0 / bpm
        bar = 4 * beat
        # Chords in C major as (root_midi, tone offsets).
        c, g, am, f, dm = ((60, (0, 4, 7)), (67, (0, 4, 7)), (69, (0, 3, 7)),
                           (65, (0, 4, 7)), (62, (0, 3, 7)))
        # 16 bars: phrase A then a varied phrase B, ending on V to lead back in.
        prog = [c, g, am, f,  c, g, f, g,
                am, f, c, g,  dm, g, c, g]
        n = int(sr * len(prog) * bar)
        track = np.zeros(n, dtype=np.float64)

        def midi_freq(m):
            return 440.0 * 2.0 ** ((m - 69) / 12.0)

        def add_note(start_t, dur, freq, vol, harmonics=(1.0, 0.4, 0.2)):
            i0 = int(start_t * sr)
            ln = min(int(dur * sr), n - i0)
            if i0 < 0 or ln <= 0:
                return
            t = np.arange(ln) / sr
            wave = np.zeros(ln)
            for k, h in enumerate(harmonics, start=1):
                wave += h * np.sin(2.0 * np.pi * freq * k * t)
            wave /= sum(harmonics)
            env = np.exp(-4.0 * t / dur)                 # plucky decay
            atk = max(1, int(sr * 0.005))
            env[:atk] *= np.linspace(0.0, 1.0, atk)
            track[i0:i0 + ln] += wave * env * vol

        # 8th-note melody patterns (indices into `pool` below, None = rest).
        # Cycling a different one per bar keeps the tune from looping on itself.
        melodies = [
            (0, 1, 2, 3, 2, 1, 0, 1),
            (3, 2, 1, 0, 1, 2, 3, 2),
            (0, None, 1, None, 2, None, 3, 2),
            (2, 3, 2, 1, 0, 1, 2, None),
            (0, 1, 2, 3, 2, 3, 1, 0),
            (3, None, 2, 1, 2, 3, None, 0),
            (0, 2, 1, 3, 2, 0, 1, 2),
            (1, 2, 3, 2, 1, 0, 1, None),
        ]

        for bar_i, (root, tones) in enumerate(prog):
            bt = bar_i * bar
            pool = (tones[0], tones[1], tones[2], 12)    # chord tones + root octave
            # Bass: root two octaves down, with an octave bounce on beat 3.
            for b in range(4):
                bass = root - 24 + (12 if b == 2 else 0)
                add_note(bt + b * beat, beat * 0.9, midi_freq(bass),
                         0.55, harmonics=(1.0, 0.3))
            # Melody: a different bouncy pattern each bar (always chord tones).
            for s, idx in enumerate(melodies[bar_i % len(melodies)]):
                if idx is None:
                    continue
                add_note(bt + s * (beat / 2), (beat / 2) * 0.9,
                         midi_freq(root + 12 + pool[idx]), 0.32)
            # Pad: soft sustained triad for body.
            for off in tones:
                add_note(bt, bar * 0.98, midi_freq(root + off), 0.10,
                         harmonics=(1.0, 0.5, 0.25))

        peak = float(np.max(np.abs(track))) or 1.0
        track = (track / peak) * 0.85
        fade = int(sr * 0.01)                             # avoid a click at the seam
        track[:fade] *= np.linspace(0.0, 1.0, fade)
        track[-fade:] *= np.linspace(1.0, 0.0, fade)
        stereo = np.ascontiguousarray(
            (np.column_stack([track, track]) * 32767).astype(np.int16))
        try:
            return pygame.sndarray.make_sound(stereo)
        except Exception:
            return pygame.mixer.Sound(buffer=stereo.tobytes())
    except Exception:
        return None


def _find_music():
    if not os.path.isdir(_MUSIC_DIR):
        return None
    for fn in sorted(os.listdir(_MUSIC_DIR)):
        if fn.lower().endswith(_MUSIC_EXTS):
            return os.path.join(_MUSIC_DIR, fn)
    return None
