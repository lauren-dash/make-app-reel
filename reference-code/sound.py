"""Music and sound effects for the TODOOM reel, made from scratch (nothing licensed).

- music(): a dry, slightly melancholy lo-fi loop (A minor, 84 BPM): soft kick, rim, swung
  hats, an electric-piano chord loop, sub bass and a little vinyl crackle.
- whoosh(), record_scratch(), ding(), typing(), thud(): the cut and punchline effects.

Everything is mono float arrays at RATE; the editor places and mixes them.
"""
import numpy as np

RATE = 48000
BPM = 84
BEAT = 60 / BPM


def _t(dur):
    return np.arange(int(dur * RATE)) / RATE


def _env(dur, attack, release):
    t = _t(dur)
    return np.clip(t / max(attack, 1e-4), 0, 1) * np.exp(-t / release)


def _place(track, sound, at):
    i = int(at * RATE)
    if i >= len(track) or i + len(sound) <= 0:
        return
    s = sound[max(0, -i):]
    i = max(0, i)
    j = min(len(track), i + len(s))
    track[i:j] += s[: j - i]


def _lowpass(x, cutoff):
    """One-pole low-pass, enough to soften noise and keys."""
    a = np.exp(-2 * np.pi * cutoff / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # small buffers only (effects), fine in pure numpy loop
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def _lowpass_fast(x, cutoff):
    """The same filter for long buffers, via an FFT brick-wall with a soft edge."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    spec *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(spec, len(x))


def _midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def _epiano(freq, dur):
    """A soft Rhodes-like note: a sine with a short bell overtone and gentle tremolo."""
    t = _t(dur)
    bell = np.sin(2 * np.pi * freq * 3.5 * t) * np.exp(-t * 9) * 0.25
    body = np.sin(2 * np.pi * freq * t + 0.6 * np.sin(2 * np.pi * freq * t) * np.exp(-t * 3))
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.2 * t)
    return (body + bell) * trem * _env(dur, 0.006, 1.6) * np.clip((dur - t) / 0.15, 0, 1)


def music(duration, seed=3):
    """The loop for `duration` seconds, starting on a downbeat."""
    rng = np.random.default_rng(seed)
    n = int(duration * RATE)
    keys, drums, bass = np.zeros(n), np.zeros(n), np.zeros(n)
    # Am9 - Fmaj7 - Cmaj7 - G6, one chord per bar, voiced low and close
    chords = [[57, 60, 64, 67, 71], [53, 57, 60, 64], [48, 55, 59, 64], [55, 59, 62, 64]]
    roots = [45, 41, 48, 43]
    bar = BEAT * 4
    kick = np.sin(2 * np.pi * np.cumsum(45 + 75 * np.exp(-_t(0.35) * 30)) / RATE) * _env(0.35, 0.002, 0.11)
    rim = _lowpass(rng.standard_normal(int(0.08 * RATE)), 3500) * _env(0.08, 0.001, 0.018) * 3
    hat = rng.standard_normal(int(0.05 * RATE))
    hat = (hat - _lowpass(hat, 7000)) * _env(0.05, 0.001, 0.012)
    b = 0
    while b * bar < duration:
        start = b * bar
        ch = b % 4
        for k, note in enumerate(chords[ch]):  # a lazy strum
            _place(keys, _epiano(_midi(note), bar * 0.95) * 0.16, start + 0.012 * k)
        _place(bass, np.sin(2 * np.pi * _midi(roots[ch] - 12) * _t(bar * 0.9)) * _env(bar * 0.9, 0.01, 1.2) * 0.32, start)
        for beat in range(4):
            at = start + beat * BEAT
            if beat in (0, 2) or (beat == 3 and b % 2):
                _place(drums, kick * 0.55, at if beat != 3 else at + BEAT / 2)
            if beat in (1, 3):
                _place(drums, rim * 0.22, at)
            for half in (0, 1):  # swung eighth-note hats
                _place(drums, hat * (0.07 if half else 0.1), at + half * BEAT * 0.58)
        b += 1
    crackle = np.zeros(n)
    pops = rng.integers(0, n, int(duration * 9))
    crackle[pops] = rng.uniform(-0.3, 0.3, len(pops))
    crackle = _lowpass_fast(crackle, 5000) * 0.25 + _lowpass_fast(rng.standard_normal(n), 900) * 0.004
    mix = _lowpass_fast(keys, 2600) + drums + bass + crackle
    return mix / (np.max(np.abs(mix)) + 1e-9)


def whoosh(dur=0.45, seed=1):
    """Air sweeping past: filtered noise rising then falling."""
    rng = np.random.default_rng(seed)
    t = _t(dur)
    noise = rng.standard_normal(len(t))
    # sweep a band through the noise by mixing two low-passes with a moving weight
    lo, hi = _lowpass(noise, 600), _lowpass(noise, 4500)
    sweep = np.sin(np.pi * t / dur) ** 2
    out = lo * (1 - sweep) + (hi - lo * 0.5) * sweep
    return out * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5 * 0.9


def record_scratch(seed=2):
    """A quick back-and-forth scratch, then nothing."""
    rng = np.random.default_rng(seed)
    dur = 0.42
    t = _t(dur)
    # the "pitch" of the scratched sound follows the hand: fast forward, back, forward
    speed = np.interp(t, [0, 0.08, 0.16, 0.26, 0.42], [0.2, 2.2, -1.6, 1.9, 0.0])
    phase = np.cumsum(np.abs(speed)) / RATE
    tone = np.sin(2 * np.pi * 180 * phase * 6) * 0.5 + np.sign(np.sin(2 * np.pi * 95 * phase * 6)) * 0.25
    grit = _lowpass(rng.standard_normal(len(t)), 2500) * 0.5
    out = (tone + grit) * np.abs(speed) / 2.2
    return out * np.clip((dur - t) / 0.03, 0, 1)


def ding(step=0):
    """A small bright notification ding; each step goes up a note (a rising counter)."""
    scale = [76, 79, 81, 83, 84, 86, 88, 91, 93, 95, 96]
    f = _midi(scale[min(step, len(scale) - 1)])
    t = _t(0.5)
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 14)
    return tone * _env(0.5, 0.002, 0.16) * 0.55


def typing(dur, seed=4):
    """Laptop keys: short clicky ticks at a quick, uneven typing rhythm."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(dur * RATE))
    at = 0.0
    while at < dur - 0.05:
        click = rng.standard_normal(int(0.03 * RATE))
        click = (click - _lowpass(click, 1800)) * _env(0.03, 0.0005, 0.006 + rng.uniform(0, 0.004))
        _place(out, click * rng.uniform(0.35, 0.7), at)
        at += rng.choice([0.06, 0.08, 0.1, 0.13, 0.2], p=[0.25, 0.3, 0.25, 0.15, 0.05])
    return out


def thud():
    """A soft low hit under a punch-in zoom."""
    t = _t(0.4)
    return np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t * 25)) / RATE) * _env(0.4, 0.002, 0.12) * 0.9
