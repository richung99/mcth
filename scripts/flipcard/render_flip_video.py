#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# render_flip_video.py
# Builds img/instagram-menu.mp4: the drink menu board (img/TV-menu-drink.png)
# with the logo card flipping over to the website/Instagram card and back.
# Depends on: Python playwright + Chromium, ffmpeg.
# Does NOT handle: the combined TV loop (scripts/build_drink_video.py does that)
#   or any change to the board itself (edit img/TV-menu-drink.png instead).
# -----------------------------------------------------------------------------
# Usage: python3 scripts/flipcard/render_flip_video.py <out.mp4> [--frames 5,230,...  --png-dir DIR]
#   With --frames, only those frames are written as PNGs (for previewing).
import argparse, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BOARD = HERE.parent.parent / "img" / "TV-menu-drink.png"
TOTAL_FRAMES = 492  # 16.4 s at 30 fps, same length as the original video


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--frames", help="comma-separated frame numbers to export as PNG previews")
    ap.add_argument("--png-dir", default=".")
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp())
    for item in ("card.html", "fonts"):
        src = HERE / item
        (shutil.copytree if src.is_dir() else shutil.copy)(src, work / item)
    shutil.copy(BOARD, work / "TV-menu-drink.png")

    wanted = [int(x) for x in args.frames.split(",")] if args.frames else list(range(TOTAL_FRAMES))
    frames_dir = Path(args.png_dir) if args.frames else work / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.goto((work / "card.html").as_uri())
        page.evaluate("document.fonts.ready")
        for i, n in enumerate(wanted):
            page.evaluate(f"setFrame({n})")
            page.screenshot(path=str(frames_dir / (f"f{n:04d}.png" if args.frames else f"f{i:04d}.png")))
        b.close()

    if not args.frames:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", str(frames_dir / "f%04d.png"),
                        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-an",
                        "-movflags", "+faststart", args.out], check=True)
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
