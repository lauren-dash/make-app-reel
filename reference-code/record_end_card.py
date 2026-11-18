"""Record the end card (end-card/end-card.html) as a 1080x1920 30fps clip: it builds in, then holds.

Run from the repo root:
  uv run --with imageio-ffmpeg python data/todoom-reel/record_end_card.py
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from record_shots import FPS, Clip  # noqa: E402

CARD = Path(__file__).parent.resolve() / "end-card" / "end-card.html"
SECONDS = 4.0


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/opt/fortress/tilion-fortress/tilion")
        page = browser.new_page(viewport={"width": 360, "height": 640}, device_scale_factor=3)
        page.goto(CARD.as_uri())
        page.wait_for_timeout(800)
        clip = Clip(page, "5-end-card")
        for i in range(int(SECONDS * FPS)):
            page.evaluate(f"render({i / FPS})")
            clip.frame()
        clip.save()
        browser.close()


if __name__ == "__main__":
    main()
