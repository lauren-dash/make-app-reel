"""Record the two shots from the real chat where TODOOM was built, as 1080x1920 30fps clips.

Only the opening request and the account approval cards are filmed. The chat goes on
to show real tasks (names, money, phone numbers) from about 4400px down, so nothing
past 2800px is ever on screen.

Run from the repo root:
  uv run --with imageio-ffmpeg python data/todoom-reel/record_chat_shots.py
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from record_shots import Clip, ease  # noqa: E402

URL = "http://127.0.0.1:8010/<build-chat-agent-id>"
SCROLLER = "document.querySelector('main.transcript-scroll')"
SAFE_BOTTOM = 2800  # the lowest pixel of the chat that may ever be visible


def open_chat(browser):
    page = browser.new_page(viewport={"width": 360, "height": 640}, device_scale_factor=3)
    page.goto(URL)
    page.wait_for_timeout(5000)
    for _ in range(30):  # older messages load in as the top is reached
        page.evaluate(f"{SCROLLER}.scrollTop = 0")
        page.wait_for_timeout(400)
    return page


def set_scroll(page, y):
    visible = page.evaluate(f"{SCROLLER}.clientHeight")
    assert y + visible <= SAFE_BOTTOM, "would show the private part of the chat"
    page.evaluate(f"{SCROLLER}.scrollTop = {y}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/opt/fortress/tilion-fortress/tilion")
        page = open_chat(browser)

        clip = Clip(page, "1a-the-request")
        set_scroll(page, 0)
        page.wait_for_timeout(500)
        clip.hold(3.0)
        clip.save()

        clip = Clip(page, "1b-connecting-accounts")
        start, end = 1940, 2200
        set_scroll(page, start)
        page.wait_for_timeout(800)
        clip.hold(1.2)
        steps = 75
        for i in range(1, steps + 1):
            set_scroll(page, start + (end - start) * ease(i / steps))
            page.wait_for_timeout(15)
            clip.frame()
        clip.hold(1.5)
        clip.save()
        browser.close()


if __name__ == "__main__":
    main()
