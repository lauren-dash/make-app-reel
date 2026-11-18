"""Find the pauses in the creator's take and decide which stretches to keep (a jump cut at every pause).

Speech is found from loudness: anything quieter than SILENCE_DB for at least MIN_PAUSE
seconds is a pause. Each kept stretch keeps a little air either side (LEAD_IN / TAIL), so
words are never clipped and the rhythm stays natural, just faster.

Run from the repo root:  uv run --with numpy python data/todoom-reel/pacing.py
Reads /var/tmp/take/audio.wav (the take's sound, 16 kHz mono; re-make it with
  ffmpeg -i <take> -map 0:1 -ac 1 -ar 16000 /var/tmp/take/audio.wav)
Writes data/todoom-reel/final/keep.json: [[start, end], ...] in take seconds.
"""
import json
import wave
from pathlib import Path

import numpy as np

AUDIO = Path("/var/tmp/take/audio.wav")
OUT = Path("data/todoom-reel/final/keep.json")
TAKE_IN, TAKE_OUT = 1.0, 65.6
# Lines left out entirely: (start, end) in take seconds.
REMOVE = [
    (25.45, 26.6),  # an "um" before "Luckily, I trust Studio"
    (52.4, 58.0),   # "So then I spent like an hour making it really pretty. And it just works."
]
SILENCE_DB = -44.0   # the room sits around -50 dB; the quietest words are above -40
MIN_PAUSE = 0.30     # shorter gaps are part of speech and stay
LEAD_IN, TAIL = 0.07, 0.13


def speech_spans(samples, rate):
    hop, win = rate // 100, rate // 50
    level = np.array([np.sqrt(np.mean(samples[i:i + win] ** 2)) for i in range(0, len(samples) - win, hop)])
    loud = 20 * np.log10(level + 1e-9) > SILENCE_DB
    spans, start = [], None
    for i, on in enumerate(loud):
        t = i * hop / rate
        if on and start is None:
            start = t
        elif not on and start is not None:
            spans.append([start, t])
            start = None
    if start is not None:
        spans.append([start, len(samples) / rate])
    merged = []  # join speech separated by less than a real pause
    for s in spans:
        if merged and s[0] - merged[-1][1] < MIN_PAUSE:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [s for s in merged if s[1] - s[0] > 0.08]  # drop clicks and breaths


def main():
    w = wave.open(str(AUDIO))
    rate = w.getframerate()
    samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16) / 32768
    keep = []
    for a, b in speech_spans(samples, rate):
        a, b = max(TAKE_IN, a - LEAD_IN), min(TAKE_OUT, b + TAIL)
        for ra, rb in REMOVE:  # trim anything inside a removed line
            if a < rb and b > ra:
                if a < ra:
                    keep.append([a, ra])
                a = max(a, rb)
        if b - a > 0.1:
            if keep and a <= keep[-1][1]:
                keep[-1][1] = max(keep[-1][1], b)
            else:
                keep.append([round(a, 3), round(b, 3)])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(keep))
    total = sum(b - a for a, b in keep)
    print(f"{len(keep)} stretches kept, {total:.1f}s of {TAKE_OUT - TAKE_IN:.1f}s")


if __name__ == "__main__":
    main()
