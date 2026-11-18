"""Cut the full TODOOM reel: the creator's one take, the app clips cut in over the creator's voice,
captions in TODOOM's pixel font, the makeover's ta-da, and the end card.

Every time below is in seconds of the ORIGINAL take (IMG_1017.MOV); the take is trimmed
to TAKE_IN..TAKE_OUT and everything is shifted to match.

Run from the repo root:
  uv run --with imageio-ffmpeg python data/todoom-reel/cut_reel.py
Output: data/todoom-reel/final/todoom-reel.mp4
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg

ROOT = Path("data/todoom-reel")
TAKE = Path("data/uploads/4c5eef7d3e99471f93e15bc1ea9ea991/IMG_1017.MOV")
SHOTS = ROOT / "shots"
FINAL = ROOT / "final"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30

TAKE_IN, TAKE_OUT = 1.0, 65.6   # drop the second of silence before speaking and the tail after
# Stretches of the take left out of the reel: (start, end) in take time.
REMOVE = [
    (52.4, 58.0),  # "So then I spent like an hour making it really pretty. And it just works."
]
END_CARD = 4.0

# App clips cut in over the creator's voice: (clip, start, end) in take time. A clip shorter than
# its slot holds its last frame.
CUTAWAYS = [
    ("1a-the-request.mp4", 10.2, 15.0),           # "I said, find everything anyone's asked of me..."
    ("1b-connecting-accounts.mp4", 16.75, 22.8),  # "It prompted me to click a few buttons..."
    ("2-list-fills-up.mp4", 29.0, 34.0),          # "Then it dredged up my entire digital life..."
    ("4-final-list.mp4", 42.05, 47.65),           # "Or every time someone asked me to do something..."
]
# A clip whose own sound plays under the creator's voice: (clip, start in take time, volume), or None.
# The makeover reveal went with "making it pretty"; to bring it back, add
# ("3-making-it-pretty-makeover.mp4", 53.8, 58.8) to CUTAWAYS, set this to
# ("3-making-it-pretty-makeover.mp4", 53.8, 0.3), and drop the REMOVE entry.
CLIP_SOUND = None

# Captions: (start, end, text) in take time, from word timings of the take.
CAPTIONS = [
    (1.32, 4.0, "So I asked Studio to find everything"),
    (4.06, 5.15, "I've been avoiding,"),
    (5.2, 7.45, "and unfortunately, it did."),
    (7.54, 10.2, "I wrote one prompt. A couple sentences."),
    (10.28, 13.2, "I said, find everything anyone's asked of me."),
    (13.26, 16.7, "Everything I said I'd do. Find it everywhere."),
    (16.78, 19.55, "It prompted me to click a few buttons,"),
    (19.62, 22.8, "give access to some accounts."),
    (22.88, 24.1, "I didn't really read them."),
    (24.16, 26.55, "Does anybody read those?"),
    (26.62, 29.0, "Luckily, I trust Studio with all my data."),
    (29.04, 32.65, "Then it dredged up my entire digital life."),
    (32.7, 35.7, "Email. Slack. Texts. Notion."),
    (35.78, 38.3, "Google Docs. WhatsApp."),
    (38.38, 40.55, "Every single time I wrote"),
    (40.62, 42.0, "\"totally, I'll send that over.\""),
    (42.06, 44.3, "Or every time someone asked me"),
    (44.32, 48.95, "to do something for them for the past month."),
    (49.06, 52.8, "And it just worked on the first try."),
    (58.18, 59.0, "It's called TODOOM."),
    (59.04, 61.95, "It's all your doom in one place."),
    (62.02, 63.22, "So, nothing is done,"),
    (63.28, 65.4, "but at least it's all organized."),
]

# HDR (HLG) phone video to normal colour, without blowing out skin tones.
TONEMAP = ("zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,"
           "zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def keep_spans():
    """The stretches of the take that stay in the reel, in take time."""
    spans, at = [], TAKE_IN
    for a, b in sorted(REMOVE):
        spans.append((at, a))
        at = b
    spans.append((at, TAKE_OUT))
    return spans


def reel_time(t):
    """Where a moment of the take lands in the reel, once the removed stretches are gone."""
    return t - TAKE_IN - sum(min(b, max(t, a)) - a for a, b in REMOVE)


def ass_time(s):
    s = max(0.0, s)
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def write_captions(path):
    # Pixel font, white on a solid TODOOM-black box with a thin white frame (HQ's outlined
    # box), so it reads over the take, the white chat screens and the black app alike.
    # The frame is a second, slightly bigger white box drawn underneath. Sits at chest
    # height: clear of Instagram's caption area at the bottom and of the makeover stickers.
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Frame,Departure Mono,58,&H00F2F2F2,&H00F2F2F2,&H00F2F2F2,&H00F2F2F2,0,0,0,0,100,100,1,0,3,19,0,2,110,110,780,1
Style: Cap,Departure Mono,58,&H00F2F2F2,&H00F2F2F2,&H00141414,&H00141414,0,0,0,0,100,100,1,0,3,15,0,2,110,110,780,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f"Dialogue: {layer},{ass_time(reel_time(a))},{ass_time(reel_time(b))},{style},,0,0,0,,{text}"
             for a, b, text in CAPTIONS for layer, style in ((0, "Frame"), (1, "Cap"))]
    path.write_text(head + "\n".join(lines) + "\n")


def main():
    FINAL.mkdir(parents=True, exist_ok=True)
    subs = FINAL / "captions.ass"
    write_captions(subs)
    length = reel_time(TAKE_OUT)
    take_length = TAKE_OUT - TAKE_IN

    # Pass 1: the take alone, trimmed and converted to normal colour. Doing this separately
    # keeps memory low; the HDR conversion is the heavy part.
    base = FINAL / "take-sdr.mp4"
    if not base.exists() or base.stat().st_mtime < TAKE.stat().st_mtime:
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-nostdin", "-ss", str(TAKE_IN), "-t", str(take_length),
                        "-i", str(TAKE), "-map", "0:v:0", "-map", "0:a:0", "-vf", f"{TONEMAP},fps=30,scale=1080:1920,setsar=1",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-c:a", "aac", "-b:a", "256k",
                        "-threads", "2", "-filter_threads", "1", str(base)], check=True)

    # Pass 2: the picture, one short piece at a time (memory stays low): stretches of the
    # take between the app clips, each app clip held to fill its slot, then the end card.
    # Every piece is a whole number of frames so the joins stay in sync with the sound.
    def frames(sec):
        return round(sec * FPS)

    parts_dir = FINAL / "parts"
    parts_dir.mkdir(exist_ok=True)
    enc = ["-an", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p",
           "-r", str(FPS), "-threads", "2", "-filter_threads", "1"]
    pieces = []
    for ka, kb in keep_spans():
        cursor = ka
        for clip, a, b in CUTAWAYS:
            if not ka <= a < kb:
                continue
            if a > cursor:
                pieces.append((["-ss", f"{cursor - TAKE_IN:.4f}", "-i", str(base)], "setsar=1",
                               frames(reel_time(a)) - frames(reel_time(cursor))))
            count = frames(reel_time(b)) - frames(reel_time(a))
            pieces.append((["-i", str(SHOTS / clip)], f"setsar=1,tpad=stop_mode=clone:stop_duration={count / FPS}", count))
            cursor = b
        pieces.append((["-ss", f"{cursor - TAKE_IN:.4f}", "-i", str(base)], "setsar=1",
                       frames(reel_time(kb)) - frames(reel_time(cursor))))
    pieces.append((["-i", str(SHOTS / "5-end-card.mp4")], "setsar=1", frames(END_CARD)))
    listing = []
    for n, (src, vf, count) in enumerate(pieces):
        part = parts_dir / f"{n:02d}.mp4"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-nostdin", *src, "-vf", vf,
                        "-frames:v", str(count), *enc, str(part)], check=True)
        listing.append(f"file '{part.resolve()}'")
    (parts_dir / "list.txt").write_text("\n".join(listing) + "\n")
    picture = FINAL / "picture.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-nostdin", "-f", "concat", "-safe", "0",
                    "-i", str(parts_dir / "list.txt"), "-c", "copy", str(picture)], check=True)

    # Pass 3: captions on the picture; the creator's voice (with the same stretches removed), any
    # clip sound under it, then silence under the end card.
    fontsdir = (FINAL / "fonts").resolve()
    spans = keep_spans()
    f = [f"[0:v]subtitles={subs.resolve()}:fontsdir={fontsdir},format=yuv420p[v]",
         f"[1:a]asplit={len(spans)}" + "".join(f"[s{i}]" for i in range(len(spans)))]
    for i, (a, b) in enumerate(spans):
        f.append(f"[s{i}]atrim={a - TAKE_IN}:{b - TAKE_IN},asetpts=PTS-STARTPTS[k{i}]")
    # the phone recorded quietly: bring the creator's voice up to normal Instagram loudness
    f.append("".join(f"[k{i}]" for i in range(len(spans))) + f"concat=n={len(spans)}:v=0:a=1,"
             "aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[voice]")
    inputs = ["-i", str(picture), "-i", str(base)]
    if CLIP_SOUND:
        clip, s_at, s_vol = CLIP_SOUND
        delay = int(reel_time(s_at) * 1000)
        inputs += ["-i", str(SHOTS / clip)]
        f.append(f"[2:a]volume={s_vol},adelay={delay}|{delay}[fx]")
        f.append("[voice][fx]amix=inputs=2:duration=first:normalize=0[mixed]")
    else:
        f.append("[voice]anull[mixed]")
    f.append(f"[mixed]alimiter=limit=0.89,apad=whole_dur={length + END_CARD}[a]")
    out = FINAL / "todoom-reel.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-nostdin", *inputs, "-filter_complex", ";".join(f),
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-x264-params", "rc-lookahead=20", "-pix_fmt", "yuv420p",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-threads", "2",
                    "-filter_threads", "1", "-t", f"{length + END_CARD}", str(out)], check=True)
    print(f"wrote {out}  ({length + END_CARD:.1f}s)")


if __name__ == "__main__":
    main()
