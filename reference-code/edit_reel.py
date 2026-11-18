"""Edit the TODOOM reel (v2): tight jump cuts, zooms, a Studio-icon hook, app close-ups with
the creator's face in a corner, word-by-word captions, music and sound effects, a short end card.

Inputs: final/take-sdr.mp4 (the take in normal colour, starting at take second TAKE_IN; made
by cut_reel.py's first pass), final/keep.json (from pacing.py), the app clips in shots/,
/var/tmp/take/words.json (word timings of the take).

Every time written below is in seconds of the ORIGINAL take; reel_time() maps it to the reel.

Run from the repo root:
  uv run --with imageio-ffmpeg --with numpy python data/todoom-reel/edit_reel.py
Output: data/todoom-reel/final/todoom-reel-v2.mp4
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import sound  # noqa: E402

ROOT = Path("data/todoom-reel")
FINAL = ROOT / "final"
SHOTS = ROOT / "shots"
WORK = Path("/var/tmp/todoom-v2")  # pieces and scratch audio (rebuildable, kept off the backup)
BASE = FINAL / "take-sdr.mp4"
TAKE_IN = 1.0
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
W, H = 1080, 1920

# Where the creator's face sits in the take (pixels): zooms and the corner picture centre on it.
FACE_X, FACE_Y = 540, 700
ZOOMS = [1.0, 1.14]          # jump cuts alternate between these
PUNCH = 1.32                 # punch-in on the jokes, held on the creator's face
PUNCHLINES = [24.16, 26.93, 58.18, 62.02]  # "Does anybody read those?", "Luckily, I trust Studio...",
                                           # "It's called TODOOM.", "So no, nothing is done..."
MAX_SHOT = 2.8               # a talking-head shot longer than this gets a zoom change mid-way

# The opening: the creator's face with the Studio app icon popping in above them and the hook written
# across. TODOOM itself is not shown until later (the reveal).
HOOK = (TAKE_IN, 5.15)
STUDIO_ICON = ROOT / "studio-icon" / "icon.png"  # the Studio app's own icon
ICON_SIZE, ICON_Y = 330, 235  # size and centre height of the icon, in reel pixels
HOOK_TEXT = "STUDIO FOUND EVERYTHING\\NI'VE BEEN AVOIDING"
# App close-ups with the creator's face in the corner: (clip, take start, take end, crop) where crop is
# (width, height, x at start, y at start, x at end, y at end) in the clip's 1080x1920 pixels.
CUTAWAYS = [
    ("1a-the-request.mp4", 10.2, 16.15, (788, 1400, 272, 0, 272, 80)),
    ("1b-connecting-accounts.mp4", 16.8, 21.0, (864, 1536, 0, 0, 120, 0)),
    ("2-list-fills-up.mp4", 29.6, 35.4, (720, 1280, 30, 0, 30, 60)),
    ("4-final-list.mp4", 42.0, 48.95, (864, 1536, 0, 0, 0, 0)),
]
END_CARD = 1.6  # the card's build-in, played at double speed

# Caption fixes where the transcription misheard: (take second of the word, right word).
WORD_FIXES = {2.42: "Studio", 5.74: "it", 6.58: "did.", 6.72: None, 14.28: "I'd", 14.54: "do.",
              40.62: "\"totally,", 41.6: "over.\""}
CAPTION_GAP = 0.6  # a pause longer than this starts a new caption


def run(*args):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-nostdin", *map(str, args)], check=True)


# ---- timeline --------------------------------------------------------------------------

def load_spans():
    """Kept stretches of the take, each a whole number of frames long."""
    spans = []
    for a, b in json.loads((FINAL / "keep.json").read_text()):
        spans.append((a, a + round((b - a) * FPS) / FPS))
    return spans


SPANS = load_spans()


def reel_time(t):
    """Where take second t lands in the reel (a moment inside a cut lands where the cut is)."""
    out = 0.0
    for a, b in SPANS:
        if t <= a:
            return out
        if t < b:
            return out + (t - a)
        out += b - a
    return out


REEL_LEN = reel_time(SPANS[-1][1])


def shots():
    """The talking-head shots: (take start, take end, zoom). Cut at every kept stretch, at the
    edges of the hook and app close-ups, at punchlines, and mid-way through long stretches."""
    marks = set(PUNCHLINES) | {HOOK[1]} | {c[1] for c in CUTAWAYS} | {c[2] for c in CUTAWAYS}
    words = [w[0] for w in json.loads(Path("/var/tmp/take/words.json").read_text())]
    out = []
    for a, b in SPANS:
        cuts = [a] + sorted(m for m in marks if a + 0.4 < m < b - 0.4) + [b]
        pieces = list(zip(cuts, cuts[1:]))
        for pa, pb in pieces:  # split long shots at word starts
            while pb - pa > MAX_SHOT:
                options = [w for w in words if pa + 1.6 < w < min(pb - 1.0, pa + MAX_SHOT)]
                if not options:
                    break
                out.append((pa, options[-1]))
                pa = options[-1]
            out.append((pa, pb))
    planned, flip = [], 0
    for pa, pb in out:
        if any(pa - 0.3 <= p < pb - 0.2 for p in PUNCHLINES):
            planned.append((pa, pb, PUNCH))
        else:
            planned.append((pa, pb, ZOOMS[flip % 2]))
            flip += 1
    return planned


def in_window(t):
    windows = [HOOK] + [(c[1], c[2]) for c in CUTAWAYS]
    return any(a - 0.01 <= t < b - 0.01 for a, b in windows)


# ---- picture ---------------------------------------------------------------------------

def zoom_filter(z):
    w, h = round(W / z / 2) * 2, round(H / z / 2) * 2
    x = min(max(FACE_X - w // 2, 0), W - w)
    y = min(max(FACE_Y - int(h * 0.36), 0), H - h)
    return f"crop={w}:{h}:{x}:{y},scale={W}:{H},setsar=1"


def build_talking_head():
    """Pass A: the take, cut to the kept stretches, each shot at its zoom, as one track."""
    parts = []
    for n, (a, b, z) in enumerate(shots()):
        frames = round(reel_time(b) * FPS) - round(reel_time(a) * FPS)
        if frames <= 0:
            continue
        if in_window(a):
            z = 1.0  # under the hook and the close-ups the face sits in a fixed frame
        part = WORK / f"th{n:03d}.mp4"
        run("-ss", f"{a - TAKE_IN:.4f}", "-i", BASE, "-an", "-vf", zoom_filter(z), "-frames:v", frames,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", 14, "-pix_fmt", "yuv420p", "-r", FPS,
            "-threads", 2, part)
        parts.append(part)
    return concat(parts, WORK / "talking-head.mp4")


def concat(parts, out):
    listing = WORK / f"{out.stem}.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    run("-f", "concat", "-safe", 0, "-i", listing, "-c", "copy", out)
    return out


def framed_face(label, size):
    """The creator's face cut from the talking-head track, with a thin white HQ frame."""
    w, h = size
    cw, ch = 680, 850
    return (f"[{label}]crop={cw}:{ch}:{FACE_X - cw // 2}:{FACE_Y - int(ch * 0.4)},scale={w - 8}:{h - 8},"
            f"pad={w}:{h}:4:4:color=0xF2F2F2")


def icon_box():
    return int(ICON_SIZE * 1.5)  # room for the overshoot and the shadow


def render_icon_pop(frames):
    """The Studio icon's frames for the opening: pops in with a little overshoot, holds,
    and shrinks away just before the hook ends. Transparent PNGs, one per frame."""
    from PIL import Image, ImageFilter

    out = WORK / "icon"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    icon = Image.open(STUDIO_ICON).convert("RGBA")
    icon = icon.crop(icon.getbbox())  # the tile itself, without the file's empty margin
    box = icon_box()

    def back_out(x):
        x = min(max(x, 0.0), 1.0)
        c = 1.9
        return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

    for i in range(frames):
        t = i / FPS
        end = frames / FPS
        scale = back_out((t + 0.1) / 0.4) * (1 - max(0.0, min(1.0, (t - (end - 0.22)) / 0.2)) ** 2)
        canvas = Image.new("RGBA", (box, box), (0, 0, 0, 0))
        size = int(ICON_SIZE * scale)
        if size > 2:
            tile = icon.resize((size, size), Image.LANCZOS)
            shadow = Image.new("RGBA", (box, box), (0, 0, 0, 0))
            alpha = Image.new("L", (box, box), 0)
            alpha.paste(tile.getchannel("A").point(lambda a: a * 0.45), ((box - size) // 2, (box - size) // 2 + size // 14))
            shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(size // 14)))
            canvas = Image.alpha_composite(canvas, shadow)
            canvas.alpha_composite(tile, ((box - size) // 2, (box - size) // 2))
        canvas.save(out / f"{i + 1:04d}.png")
    return out


def build_pieces(th):
    """Pass B: the reel picture, piece by piece: plain talking head, the Studio-icon hook,
    and each app close-up with the creator's face in the corner."""
    windows = [("hook", None, *HOOK, None)] + [("app", *c[:3], c[3]) for c in CUTAWAYS]
    windows.sort(key=lambda w: w[2])
    parts, cursor = [], 0.0
    enc = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", 14, "-pix_fmt", "yuv420p", "-r", FPS,
           "-threads", 2]

    def plain(r0, r1):
        if r1 - r0 < 1 / FPS:
            return
        part = WORK / f"p{len(parts):03d}.mp4"
        run("-ss", f"{r0:.4f}", "-i", th, "-frames:v", round((r1 - r0) * FPS), *enc, part)
        parts.append(part)

    for kind, clip, ta, tb, crop in windows:
        r0, r1 = reel_time(ta), reel_time(tb)
        plain(cursor, r0)
        frames = round(r1 * FPS) - round(r0 * FPS)
        dur = frames / FPS
        part = WORK / f"p{len(parts):03d}.mp4"
        if kind == "hook":
            # the creator's face, with the Studio icon popping in above their head
            icon_frames = render_icon_pop(frames)
            box = icon_box()
            graph = (f"[1:v]format=rgba[icon];[0:v][icon]overlay={(W - box) // 2}:{ICON_Y - box // 2}:"
                     f"eof_action=pass,setsar=1[v]")
            run("-ss", f"{r0:.4f}", "-i", th, "-framerate", FPS, "-i", icon_frames / "%04d.png",
                "-filter_complex", graph, "-map", "[v]", "-frames:v", frames, *enc, part)
        else:
            cw, ch, x0, y0, x1, y1 = crop
            pan = f"(t/{dur:.3f})"
            pw, ph = 360, 450
            graph = (f"[1:v]tpad=stop_mode=clone:stop_duration={dur},trim=duration={dur},setpts=PTS-STARTPTS,"
                     f"crop={cw}:{ch}:'{x0}+({x1 - x0})*{pan}':'{y0}+({y1 - y0})*{pan}',"
                     f"scale={W}:{H},setsar=1[app];"
                     f"{framed_face('0:v', (pw, ph))}[face];"
                     f"[app][face]overlay={W - pw - 40}:{H - ph - 230}[v]")
            run("-ss", f"{r0:.4f}", "-i", th, "-i", SHOTS / clip, "-filter_complex", graph,
                "-map", "[v]", "-frames:v", frames, *enc, part)
        parts.append(part)
        cursor = round(r1 * FPS) / FPS
    plain(cursor, REEL_LEN)
    card = WORK / "card.mp4"  # the end card's build-in at double speed, then its last frame
    run("-i", SHOTS / "5-end-card.mp4", "-vf", "setpts=0.5*PTS,setsar=1", "-frames:v", round(END_CARD * FPS),
        *enc, card)
    parts.append(card)
    return concat(parts, WORK / "picture.mp4")


# ---- captions --------------------------------------------------------------------------

def ass_time(s):
    s = max(0.0, s)
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def caption_words():
    out = []
    for a, b, text in json.loads(Path("/var/tmp/take/words.json").read_text()):
        key = next((k for k in WORD_FIXES if abs(k - a) < 0.02), None)
        if key is not None:
            if WORD_FIXES[key] is None:
                continue
            text = WORD_FIXES[key]
        text = text.strip()
        # the transcriber's word timings run a little early, so a word counts as kept when it
        # overlaps a kept stretch, and starts no earlier than that stretch
        span = next(((sa, sb) for sa, sb in SPANS if a < sb - 0.05 and b > sa + 0.05), None)
        if span is None:
            continue  # this word was cut
        if a < HOOK[1] - 0.1:
            continue  # the hook card says it
        out.append([reel_time(max(a, span[0])), reel_time(min(max(b, span[0] + 0.1), span[1])), text])
    return out


def chunks(words):
    """Two to four words a caption, breaking after punctuation and at pauses."""
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        # at four words, take a fifth rather than leave one word stranded before a full stop
        full = len(cur) >= 5 or (len(cur) == 4 and not (nxt and nxt[2][-1] in ".?!"))
        end = (w[2][-1] in ".,?!" and len(cur) >= 2) or full or nxt is None \
            or (nxt and nxt[0] - w[1] > CAPTION_GAP) or (w[2][-1] in ".?!")
        if end:
            groups.append(cur)
            cur = []
    return groups


def write_captions(path):
    amber = "&H1AC6FF&"  # TODOOM's amber (hsl 45 100% 55%), in the caption format's blue-green-red order
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Frame,Departure Mono,74,&H00F2F2F2,&H00F2F2F2,&H00F2F2F2,&H00F2F2F2,0,0,0,0,100,100,1,0,3,21,0,2,90,90,760,1
Style: Cap,Departure Mono,74,&H00F2F2F2,&H00F2F2F2,&H00141414,&H00141414,0,0,0,0,100,100,1,0,3,17,0,2,90,90,760,1
Style: HookFrame,Departure Mono,70,&H00F2F2F2,&H00F2F2F2,&H00F2F2F2,&H00F2F2F2,0,0,0,0,100,100,2,0,3,24,0,5,60,60,0,1
Style: Hook,Departure Mono,70,&H00F2F2F2,&H00F2F2F2,&H00141414,&H00141414,0,0,0,0,100,100,2,0,3,20,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    hook_end = reel_time(HOOK[1])
    for layer, style in ((0, "HookFrame"), (1, "Hook")):
        lines.append(f"Dialogue: {layer},{ass_time(0)},{ass_time(hook_end)},{style},,0,0,0,,{{\\pos({W // 2},{H - 830})}}{HOOK_TEXT}")
    groups = chunks(caption_words())
    for gi, g in enumerate(groups):
        g_end = min(g[-1][1] + 0.25, groups[gi + 1][0][0] if gi + 1 < len(groups) else REEL_LEN)
        for wi, w in enumerate(g):
            start = w[0] if wi else max(w[0] - 0.05, 0)
            end = g[wi + 1][0] if wi + 1 < len(g) else g_end
            if end <= start:
                continue
            text = " ".join((f"{{\\c{amber}}}{x[2]}{{\\c&HF2F2F2&}}" if k == wi else x[2]) for k, x in enumerate(g))
            plain = " ".join(x[2] for x in g)
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Frame,,0,0,0,,{plain}")
            lines.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,{text}")
    path.write_text(head + "\n".join(lines) + "\n")


# ---- sound -----------------------------------------------------------------------------

def norm(x):
    return x / (np.max(np.abs(x)) + 1e-9)


def build_bed(path):
    """Music and effects on the reel's timeline (the creator's voice is mixed in later)."""
    total = REEL_LEN + END_CARD
    n = int(total * sound.RATE)
    bed = np.zeros(n)
    place = sound._place
    # music: from the top, stops dead on the record scratch before "Luckily, I trust Studio",
    # comes back in fresh on "Then it dredged up..."
    scratch_at = reel_time(26.93) - 0.38
    back_at = reel_time(29.66)
    m1 = sound.music(scratch_at + 0.02)
    m1[-int(0.015 * sound.RATE):] *= np.linspace(1, 0, int(0.015 * sound.RATE))
    place(bed, m1 * 0.13, 0)
    m2 = sound.music(total - back_at)
    fade = int(1.2 * sound.RATE)
    m2[-fade:] *= np.linspace(1, 0, fade)
    place(bed, m2 * 0.13, back_at)
    place(bed, norm(sound.record_scratch()) * 0.5, scratch_at)
    place(bed, norm(sound.ding(6)) * 0.16, 0.0)  # the Studio icon popping in
    # a whoosh into every app close-up and back out
    for _, ta, tb, _ in CUTAWAYS:
        place(bed, norm(sound.whoosh()) * 0.32, reel_time(ta) - 0.22)
        place(bed, norm(sound.whoosh(0.35, seed=5)) * 0.2, reel_time(tb) - 0.15)
    # typing under the request close-up
    place(bed, norm(sound.typing(1.6)) * 0.22, reel_time(10.2) + 0.1)
    # dings as the counts climb (the clip's count rises over its first ~4 seconds, eased)
    list_at = reel_time(29.6)
    for k in range(9):
        x = (k + 0.5) / 9
        t = 4.0 * (np.arccos(1 - 2 * x) / np.pi)  # when the eased counter passes x of the way
        place(bed, norm(sound.ding(k)) * 0.18, list_at + t)
    # a soft thud under each punch-in
    for a, _, z in shots():
        if z == PUNCH and not in_window(a):
            place(bed, norm(sound.thud()) * 0.35, reel_time(a))
    pcm = (np.stack([bed, bed], axis=1).clip(-1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sound.RATE)
        w.writeframes(pcm.tobytes())
    return path


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    th = build_talking_head()
    picture = build_pieces(th)
    subs = WORK / "captions.ass"
    write_captions(subs)
    bed = build_bed(WORK / "bed.wav")

    # the creator's voice: the same kept stretches, brought up to normal loudness (its own light pass)
    f = [f"[0:a]asplit={len(SPANS)}" + "".join(f"[s{i}]" for i in range(len(SPANS)))]
    for i, (a, b) in enumerate(SPANS):
        f.append(f"[s{i}]atrim={a - TAKE_IN:.4f}:{b - TAKE_IN:.4f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:d=0.012,afade=t=out:st={b - a - 0.012:.4f}:d=0.012[k{i}]")
    f.append("".join(f"[k{i}]" for i in range(len(SPANS))) + f"concat=n={len(SPANS)}:v=0:a=1,"
             "aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    voice = WORK / "voice.wav"
    run("-vn", "-i", BASE, "-filter_complex", ";".join(f), "-map", "[a]", voice)

    # last pass: captions on the picture; the creator's voice with the music and effects under it
    f = [f"[0:v]subtitles={subs.resolve()}:fontsdir={(FINAL / 'fonts').resolve()},format=yuv420p[v]",
         "[1:a][2:a]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.89[a]"]
    out = FINAL / "todoom-reel-v2.mp4"
    run("-i", picture, "-i", voice, "-i", bed, "-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", 18, "-x264-params", "rc-lookahead=10", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-threads", 2, "-filter_threads", 1,
        "-t", f"{REEL_LEN + END_CARD:.3f}", out)
    print(f"wrote {out}  ({REEL_LEN + END_CARD:.1f}s)")


if __name__ == "__main__":
    main()
