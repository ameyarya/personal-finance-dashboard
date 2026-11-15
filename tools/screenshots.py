"""Regenerate the README screenshots from the built-in example data (never from the real data folder).

Usage: .venv/bin/python tools/screenshots.py
Sizes are real device viewports: MacBook Air 13" (1470 x 956) and iPhone 18 Pro (402 x 874)."""
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
PORT = 8799
SHOTS = [("mac", {"width": 1470, "height": 956}, 2, False, ["overview", "payments", "insights"]),
         ("phone", {"width": 402, "height": 874}, 2, True, ["overview", "payments", "insights"])]


def main():
    with tempfile.TemporaryDirectory() as data:
        env = dict(os.environ, FINANCES_TODAY="2026-11-12")
        proc = subprocess.Popen([sys.executable, str(ROOT / "server.py"), "--port", str(PORT), "--bind", "127.0.0.1", "--name", "", "--data", data, "--quiet"], env=env)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen("http://127.0.0.1:%d/api/data" % PORT, timeout=1).read()
                    break
                except OSError:
                    time.sleep(0.1)
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                for name, size, dpr, mobile, views in SHOTS:
                    ctx = browser.new_context(viewport=size, device_scale_factor=dpr, is_mobile=mobile, has_touch=mobile, reduced_motion="reduce")
                    page = ctx.new_page()
                    page.clock.set_fixed_time("2026-11-12T10:00:00")
                    page.goto("http://127.0.0.1:%d/" % PORT)
                    page.wait_for_selector("#view .card")
                    for view in views:
                        page.evaluate("v => { location.hash = v }", view)
                        page.wait_for_timeout(600)
                        page.screenshot(path=str(OUT / ("%s-%s.png" % (name, view))))
                    ctx.close()
                browser.close()
        finally:
            proc.terminate()


if __name__ == "__main__":
    main()
