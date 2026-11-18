"""Record the TODOOM screen shots for the reel as 1080x1920 (9:16) 30fps clips.

Frames are captured one at a time (not in real time) so motion is smooth and sharp,
then joined into MP4s. Needs the made-up-data copy of the app running on port 18791.

Run from the repo root:
  uv run --with imageio-ffmpeg python data/todoom-reel/record_shots.py
"""
import json
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:18791/"
OUT = Path("data/todoom-reel/shots")
FRAMES = Path("/var/tmp/todoom-frames")
FPS = 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ALL = json.loads(Path("data/todoom-reel/demo-data/tasks.json").read_text())


class Clip:
    def __init__(self, page, name):
        self.page, self.name, self.n = page, name, 0
        self.dir = FRAMES / name
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir.mkdir(parents=True)

    def frame(self, repeat=1):
        path = self.dir / f"{self.n:05d}.png"
        self.page.screenshot(path=path)
        self.n += 1
        for _ in range(repeat - 1):
            shutil.copy(path, self.dir / f"{self.n:05d}.png")
            self.n += 1

    def hold(self, seconds):
        self.frame(int(seconds * FPS))

    def save(self):
        OUT.mkdir(parents=True, exist_ok=True)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(self.dir / "%05d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", str(OUT / f"{self.name}.mp4")], check=True)
        print(f"{self.name}.mp4  {self.n / FPS:.1f}s")


def new_page(browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, device_scale_factor=3)
    page = ctx.new_page()
    page.goto(URL)
    page.wait_for_timeout(1500)
    return page


def ease(t):
    return t * t * (3 - 2 * t)


def scroll(clip, page, distance, seconds):
    start = page.evaluate("document.getElementById('list').scrollTop")
    steps = int(seconds * FPS)
    for i in range(1, steps + 1):
        page.evaluate(f"document.getElementById('list').scrollTop = {start + distance * ease(i / steps)}")
        clip.frame()


def count_climb(browser):
    """The list fills up: tasks arrive in growing batches and the tab counts climb."""
    page = new_page(browser)
    shown = {"n": 0}

    def serve(route):
        data = {**ALL, "tasks": ALL["tasks"][: shown["n"]]}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(data))

    page.route("**/api/tasks", serve)
    page.get_by_text("Overdue").first.click()
    clip = Clip(page, "2-list-fills-up")
    total = len(ALL["tasks"])
    for i in range(0, 61):
        shown["n"] = min(total, round(total * ease(i / 60)))
        page.evaluate("load()")
        page.wait_for_timeout(30)
        clip.frame(2)
    clip.hold(0.7)
    clip.save()


def styling(browser):
    """Making it pretty: flip between dark and light a few times."""
    page = new_page(browser)
    page.get_by_text("Personal").first.click()
    clip = Clip(page, "3-making-it-pretty")
    clip.hold(0.6)
    for _ in range(4):
        page.click("#theme")
        page.wait_for_timeout(600)  # let the text colour fade finish
        clip.hold(0.5)
    page.evaluate("localStorage.removeItem('theme')")
    clip.save()


def final_list(browser):
    """The final list: Overdue, slow scroll through the doom."""
    page = new_page(browser)
    page.get_by_text("Overdue").first.click()
    page.wait_for_timeout(300)
    clip = Clip(page, "4-final-list")
    clip.hold(1.0)
    height = page.evaluate("(l => l.scrollHeight - l.clientHeight)(document.getElementById('list'))")
    scroll(clip, page, min(height, 3200), 4.0)
    clip.hold(0.6)
    clip.save()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/opt/fortress/tilion-fortress/tilion")
        count_climb(browser)
        styling(browser)
        final_list(browser)
        browser.close()


if __name__ == "__main__":
    main()
