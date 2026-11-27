#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# make_banner.py
# Draws a full-screen 1920x1080 "frame" image with a sale banner across the top
# and the menu's background colour everywhere else. build_drink_video.py shrinks
# every video in the drink loop slightly and places it under this banner.
# Depends on: Pillow, the Poppins font (Google Fonts).
# Does NOT handle: the video build (build_drink_video.py does that, when
#   drink/playlist.json has a "banner" entry).
# -----------------------------------------------------------------------------
# Usage: python3 scripts/make_banner.py [out.png] [title] [deal] [height]
#   default: img/banner-black-friday.png "BLACK FRIDAY SALE" "5% OFF" 86

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
BG = (245, 240, 234)        # menu background
BAND = (17, 17, 17)         # black band
PILL = (253, 218, 175)      # menu's peach header colour
PILL_TEXT = (17, 17, 17)

out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "img/banner-black-friday.png"
title = sys.argv[2] if len(sys.argv) > 2 else "BLACK FRIDAY SALE"
deal = sys.argv[3] if len(sys.argv) > 3 else "5% OFF"
h = int(sys.argv[4]) if len(sys.argv) > 4 else 86

im = Image.new("RGB", (1920, 1080), BG)
d = ImageDraw.Draw(im)
d.rectangle((0, 0, 1920, h - 1), fill=BAND)

tf = ImageFont.truetype(FONT, 46)
pf = ImageFont.truetype(FONT, 44)
spacing = 6  # letter spacing for the title, px


def spaced_width(text, font):
    return sum(d.textlength(c, font=font) for c in text) + spacing * (len(text) - 1)


tw = spaced_width(title, tf)
pw = d.textlength(deal, font=pf) + 2 * 30
gap = 34
x = (1920 - (tw + gap + pw)) / 2
cy = h / 2
# title, letter by letter for the spacing
for c in title:
    d.text((x, cy), c, font=tf, fill="white", anchor="lm")
    x += d.textlength(c, font=tf) + spacing
x += gap - spacing
# deal in a pill
ph = 60
d.rounded_rectangle((x, cy - ph / 2, x + pw, cy + ph / 2), ph / 2, fill=PILL)
d.text((x + pw / 2, cy + 2), deal, font=pf, fill=PILL_TEXT, anchor="mm")
im.save(out)
print(f"Wrote {out} (banner height {h}px)")
