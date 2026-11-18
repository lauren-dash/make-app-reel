# Technique: problems already solved

How to build a reel in a Studio workspace. This is about *how*, never *what*: the script,
shots, music and look come fresh from each app (see SKILL.md).

## Tools

- **Playwright** with the workspace's Fortress Chromium
  (`executable_path="/opt/fortress/tilion-fortress/tilion"`) to film app pages and the build chat.
- **ffmpeg** from `imageio-ffmpeg` (`uv run --with imageio-ffmpeg ...`); this build has
  zscale, tonemap, libass (captions) and loudnorm.
- **faster-whisper** for word-timed transcripts.
- **numpy** to synthesise music and sound (royalty-free by construction), **Pillow** for stills.

## Filming screens frame by frame

- Viewport 360x640 CSS px with device scale factor 3 gives a sharp 1080x1920 frame.
- Don't screen-record in real time. Set the page state for frame N, take a screenshot,
  repeat, then join the PNGs at 30 fps. Motion is perfectly smooth and text stays sharp.
- Drive motion with an easing function (ease-in-out) rather than linear moves.
- To show a list "filling up", intercept the app's data request (`page.route`) and serve a
  growing subset of the made-up records.
- Wait out CSS transitions (theme toggles, fades) before capturing.
- Scroll the element that actually scrolls (often a list container, not the window).
- An end card is easiest as an HTML page with a `render(t)` function, captured per frame.

## Never show real data

- Write made-up records in the app's own data format and run a private copy of the app on
  them (most workspace apps take a data-directory and port setting through environment
  variables; check the app's code).
- Past chats are served by the chat app; find the build chat's id with the workspace's
  transcript search. Measure the pixel offset where real data begins and assert the
  recording never scrolls past it.

## Memory

The workspace may be shared with other chats, and a process that grows past about 1.5 GB can
be killed by the out-of-memory guard (exit 137/143; the shed ledger in
`data/.state/oom_priority/events/shed.jsonl` confirms it). So:

- Build the picture in short pieces, one ffmpeg at a time, and join them with the concat
  demuxer (`-c copy`). Never feed many clips into one filter graph.
- Do the voice in its own audio-only pass, then mux picture and sound at the end.
- Use `-threads 2 -filter_threads 1`.
- Transcribe with `base.en`, or `small.en` on chunks under about 15 s.

## Phone video

iPhone footage is usually HLG HDR. A naive conversion blows out skin. Working chain:

```
zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p
```

## Cutting without clipping words

- Get word timings from the transcript, but don't trust them to the millisecond: they often
  run 0.1-0.3 s early. Find speech by loudness too, and only cut where *both* agree there's
  a gap.
- Keep air either side of every kept stretch (at least ~0.1 s before, ~0.15 s after).
- Match caption words to kept stretches by overlap, not by start time, or first words drop.
- Re-transcribe the finished audio and diff it against the original transcript, word by
  word. Any difference is a clipped or dropped word until proven otherwise.
- Check the level on both sides of every cut: it should be room-tone, not mid-word.

## Captions

- ASS subtitles burned in with libass. libass can't read `.woff2`; convert to `.otf` with
  fontTools first.
- One style, one fixed position, for the whole reel.
- A box that reads over any background: a dark box with a slightly larger light box drawn
  underneath (two layers), so it shows on dark and light screens alike.
- Fix mishearings by hand in a small corrections table (product names especially).

## Sound

- Voice: `loudnorm=I=-14:TP=-1.5:LRA=11`. Music about 16 dB under the voice; limiter on the
  mix.
- Compose the music fresh for each reel: choose a key, a slow progression, a tempo and a
  timbre that fit this app's mood. Soft attacks, gentle filtering, a little room. Seed any
  randomness so rebuilds are identical.
- Duck or pause music only gently; no hard stops or stings unless the creator asks.
- You can't hear. Measure levels per section, draw a spectrogram, and tell the creator to
  listen with sound on.

## Checking the picture

Pull a frame every second or so into a contact sheet and look at all of it: crops, caption
position, anything cut off, any real data, the first frame.

## The Studio icon

Studio's own icon is in the Studio app's artwork, at `apps/minds/electron/assets/icon.png`
in the Studio source (look in the uv cache if it isn't checked out).
