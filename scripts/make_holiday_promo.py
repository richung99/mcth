#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# make_holiday_promo.py
# Builds img/winter-promo-menu.mp4: the menu board, a snowball-splat transition,
# the holiday promo picture, the same transition again, and back to the board.
# Depends on: Python 3 with numpy + Pillow, ffmpeg on PATH.
# Does NOT handle: putting it into the TV loop (build_drink_video.py does that).
# -----------------------------------------------------------------------------
# The transition: one snowball flies in toward the camera, splats across the
# whole screen (snow white), then the snow melts away from the middle out, with
# a very soft edge, to show what's underneath.
#
# Why home-made: the bought snowball stinger lagged on the TV. Its splat broke
# into hundreds of small blobs flying over a detailed picture, which is very
# expensive for a TV to decode. Here the ball and the splat are flat white, and
# the reveal is one soft-edged opening, so each frame only changes a ring of the
# picture. (A true see-through fade of the whole screen was tried too: it
# changes every pixel on every frame and was as heavy as the old stinger.)
#
# Usage: python3 scripts/make_holiday_promo.py [out.mp4] [board.png] [promo.png]
#
# Timing (30 fps frames). Each transition starts at S:
#   S .. S+15   snowball flies in, growing as it comes closer
#   S+16..S+23  splat spreads across the screen (fully white at S+24)
#   S+24..S+26  white (the picture underneath is swapped at S+24)
#   S+27..S+56  snow melts away
# S = 36 and 261, so the swaps land at frames 60 and 285 (same as before);
# 335 frames = 11.17 s in total.

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

W, H, FPS, TOTAL = 1920, 1080, 30, 335
STARTS = (36, 261)
FLY, SPLAT, HOLD, FADE = 16, 8, 3, 30
FEATHER = 120  # softness of the melting edge, px (softer looks more like fading)
SWAP_AT = FLY + SPLAT                      # frames after S when the screen is fully white
SNOW = np.array([255, 255, 255], np.float32)
SHADE = np.array([206, 222, 240], np.float32)  # pale blue shading on the flying ball

ROOT = Path(__file__).resolve().parent.parent
XS = np.arange(W, dtype=np.float32)[None, :]
YS = np.arange(H, dtype=np.float32)[:, None]
CX, CY = W / 2, H / 2 + 20                 # where the ball hits


def smooth(t):
    """Gentle start and stop, for a 0..1 progress value."""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lumpy_disc(cx, cy, radius, lumps, spin, soft=1.0):
    """
    Coverage (0..1) of a lumpy round shape, with smooth edges.

    Args:
        cx, cy (float): centre in pixels.
        radius (float): average radius in pixels.
        lumps (list): (count, size) pairs; each adds that many bumps of that
                      relative size around the edge.
        spin (float): rotation of the bumps, in radians.
        soft (float): edge softness in pixels.

    Returns:
        np.ndarray: HxW float coverage.
    """
    dx, dy = XS - cx, YS - cy
    dist = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx) + spin
    edge = np.full_like(ang, radius)
    for i, (count, size) in enumerate(lumps):
        edge = edge + radius * size * np.sin(count * ang + 1.7 * i)
    return np.clip((edge - dist) / soft + 0.5, 0, 1)


def snow_layer(frame):
    """
    How much snow covers the screen on one frame.

    Args:
        frame (int): 0-based frame number.

    Returns:
        tuple: (coverage, shade), each an HxW array (or a single number for a
               uniform fade) in 0..1, or (None, None) when no transition is on
               screen. shade = the pale-blue part of the snow.
    """
    for s in STARTS:
        k = frame - s
        if 0 <= k < SWAP_AT + HOLD + FADE:
            break
    else:
        return None, None

    if k < FLY:
        # Flying in: from small and far (upper right) to big at the centre, spinning
        t = k / (FLY - 1)
        r = 16 * (260 / 16) ** (t ** 1.5)                     # grows faster as it nears
        x = CX + (1 - t) * 520 - 80 * np.sin(np.pi * t)       # slight arc
        y = CY - (1 - t) * 300 - 120 * np.sin(np.pi * t)
        lumps = [(5, 0.06), (8, 0.035)]
        ball = lumpy_disc(x, y, r, lumps, spin=t * 2.2, soft=1.2)
        lit = lumpy_disc(x - r * 0.2, y - r * 0.2, r * 0.9, lumps, spin=t * 2.2, soft=r * 0.15 + 1)
        return ball, ball * (1 - lit)
    if k < SWAP_AT:
        # Splat: bursts out with big lobes until it covers the whole screen
        t = ((k - FLY + 1) / SPLAT) ** 1.3
        r = 260 + t * (2300 - 260)
        return lumpy_disc(CX, CY, r, [(7, 0.22), (12, 0.12), (19, 0.06)], spin=0.3, soft=6.0), 0.0
    if k < SWAP_AT + HOLD:
        return 1.0, 0.0
    # Fade away
    # Melt away: a soft-edged opening grows from the middle until the snow is gone
    t = smooth((k - SWAP_AT - HOLD + 1) / FADE)
    r = -150 + t * (1500 + 150)
    hole = lumpy_disc(CX, CY, r, [(6, 0.12), (11, 0.06)], spin=1.1, soft=FEATHER)
    return 1.0 - hole, 0.0


def load(path):
    """Read an image as a 1920x1080 float RGB array."""
    return np.asarray(Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS), np.float32)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "img/winter-promo-menu.mp4"
    board = load(sys.argv[2] if len(sys.argv) > 2 else ROOT / "img/TV-menu-drink.png")
    promo = load(sys.argv[3] if len(sys.argv) > 3 else ROOT / "img/winter-promo.png")
    swap_in, swap_out = STARTS[0] + SWAP_AT, STARTS[1] + SWAP_AT

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
            cov = np.asarray(cov, np.float32)
            shade = np.asarray(shade, np.float32)
            if cov.ndim:
                cov = cov[..., None]
            if shade.ndim:
                shade = shade[..., None]
            snow = SNOW * (1 - shade) + SHADE * shade
            frame = base * (1 - cov) + snow * cov
        enc.stdin.write(np.clip(frame + 0.5, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
