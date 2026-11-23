#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# make_holiday_promo.py
# Builds img/winter-promo-menu.mp4: the menu board, a "snowfall" transition, the
# holiday promo picture, the snowfall transition again, and back to the board.
# Depends on: Python 3 with numpy + Pillow, ffmpeg on PATH.
# Does NOT handle: putting it into the TV loop (build_drink_video.py does that).
# -----------------------------------------------------------------------------
# Why a home-made transition: the bought snowball stinger lagged on the TV.
# Hundreds of small moving shapes over a detailed picture are expensive for a
# TV to decode. This one is a single sheet of snow with a wavy edge and a few
# big snowballs, in flat colours, sweeping down the screen, so each frame only
# changes a narrow band of the picture.
#
# Usage: python3 scripts/make_holiday_promo.py [out.mp4] [board.png] [promo.png]
#
# Timing (30 fps frames), same slots as before:
#   0-29     board
#   30-59    snow sheet falls from the top and covers the screen at 60
#   60-81    sheet keeps falling and uncovers the promo picture
#   82-254   promo picture
#   255-306  same transition back to the board (covered at 285)
#   307-334  board                                   (335 frames = 11.17 s)

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

W, H, FPS, TOTAL = 1920, 1080, 30, 335
COVER_FRAMES, UNCOVER_FRAMES = 30, 22
STINGERS = (30, 255)          # frame each transition starts; swap at start + COVER_FRAMES
SNOW = np.array([255, 255, 255], np.float32)
SHADE = np.array([214, 228, 242], np.float32)   # pale blue rim on snowballs and edge
EDGE_SHADE_PX = 10

ROOT = Path(__file__).resolve().parent.parent
XS = np.arange(W, dtype=np.float32)
YS = np.arange(H, dtype=np.float32)[:, None]

# Snowballs riding the leading (bottom) edge and the trailing (top) edge:
# (x position, radius, how far it hangs past the edge)
LEAD_BALLS = [(120, 70, 40), (420, 95, 55), (760, 60, 30), (1010, 85, 50),
              (1330, 70, 35), (1600, 100, 60), (1850, 65, 30)]
TRAIL_BALLS = [(250, 80, 45), (640, 65, 35), (980, 95, 55), (1420, 75, 40), (1760, 85, 50)]


def ease(t):
    """Smooth start and stop for a 0..1 progress value."""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def wave(x, phase):
    """Wavy offset of a snow edge, in pixels."""
    return 28 * np.sin(2 * np.pi * x / 520 + phase) + 14 * np.sin(2 * np.pi * x / 230 + 2 * phase)


def snow_layer(frame):
    """
    Work out where the snow covers the screen on one frame.

    Args:
        frame (int): 0-based frame number.

    Returns:
        tuple: (coverage, shade) as HxW float arrays in 0..1, or (None, None)
               when no transition is on screen. coverage = snow on top of the
               picture; shade = the pale-blue part of that snow.
    """
    for start in STINGERS:
        k = frame - start
        if 0 <= k < COVER_FRAMES + UNCOVER_FRAMES:
            break
    else:
        return None, None

    margin = 220  # keeps the edges and balls fully off screen at the ends
    lead_y = -margin + (H + 2 * margin) * ease(k / COVER_FRAMES)
    trail_y = -margin + (H + 2 * margin) * ease((k - COVER_FRAMES) / UNCOVER_FRAMES) if k >= COVER_FRAMES else -1e9

    lead = lead_y + wave(XS, 0.8)
    trail = trail_y + wave(XS, 2.1)
    # Snow sheet between the two edges (with 1px soft edges for smoothness)
    cov = np.clip(lead - YS + 0.5, 0, 1) * np.clip(YS - trail + 0.5, 0, 1)
    shade = np.clip(lead - YS + 0.5, 0, 1) * np.clip(YS - (lead - EDGE_SHADE_PX) + 0.5, 0, 1) * cov

    def add_ball(cx, cy, r):
        nonlocal cov, shade
        x0, x1 = int(max(cx - r - 2, 0)), int(min(cx + r + 2, W))
        y0, y1 = int(max(cy - r - 2, 0)), int(min(cy + r + 2, H))
        if x0 >= x1 or y0 >= y1:
            return
        d = np.hypot(XS[x0:x1][None, :] - cx, YS[y0:y1] - cy)
        ball = np.clip(r - d + 0.5, 0, 1)
        # pale-blue crescent on the lower right: makes it read as a round snowball
        d_lit = np.hypot(XS[x0:x1][None, :] - (cx - r * 0.22), YS[y0:y1] - (cy - r * 0.22))
        rim = ball * (1 - np.clip(r * 0.92 - d_lit + 0.5, 0, 1))
        cov[y0:y1, x0:x1] = np.maximum(cov[y0:y1, x0:x1], ball)
        # the ball sits on top of the sheet: its own rim, sheet shading hidden under it
        shade[y0:y1, x0:x1] = shade[y0:y1, x0:x1] * (1 - ball) + rim

    for x, r, hang in LEAD_BALLS:
        add_ball(x, lead_y + wave(np.float32(x), 0.8) + hang - r * 0.4, r)
    if k >= COVER_FRAMES:
        for x, r, hang in TRAIL_BALLS:
            add_ball(x, trail_y + wave(np.float32(x), 2.1) - hang + r * 0.4, r)
    return cov, np.clip(shade, 0, 1)


def load(path):
    """Read an image as a 1920x1080 float RGB array."""
    return np.asarray(Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS), np.float32)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "img/winter-promo-menu.mp4"
    board = load(sys.argv[2] if len(sys.argv) > 2 else ROOT / "img/TV-menu-drink.png")
    promo = load(sys.argv[3] if len(sys.argv) > 3 else ROOT / "img/winter-promo.png")
    swap_in, swap_out = STINGERS[0] + COVER_FRAMES, STINGERS[1] + COVER_FRAMES

    enc = subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        "-an", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    for f in range(TOTAL):
        base = promo if swap_in <= f < swap_out else board
        cov, shade = snow_layer(f)
        if cov is None:
            frame = base
        else:
            snow = SNOW * (1 - shade[..., None]) + SHADE * shade[..., None]
            frame = base * (1 - cov[..., None]) + snow * cov[..., None]
        enc.stdin.write(np.clip(frame + 0.5, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
