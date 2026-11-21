#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# make_winter_promo.sh
# Usage: make_winter_promo.sh [out.mp4] [board.png]
# Builds img/winter-promo-menu.mp4 (or food): the menu board, a snowball transition, the
# winter promo picture (img/winter-promo.png) (no snow overlay; removed to keep it light),
# another snowball transition, and back to the drink board.
# Depends on: ffmpeg (with libvpx-vp9 for the alpha snowball .webm in assets/winter/),
#   a board PNG (default img/TV-menu-drink.png), img/winter-promo.png.
# Does NOT handle: adding it to the TV rotation (drink/playlist.json) or joining
#   it into the loop (build_drink_video.py).
# -----------------------------------------------------------------------------
# Timing (30 fps frames). The snowball stinger fully covers the screen exactly 1.0s
# (30 frames) after it starts, so the board <-> promo swap happens at that frame.
#   0-29    board            stinger #1 starts at 30, swap at 60
#   60-284  winter promo picture (7.5s)
#   285-334 board            stinger #2 starts at 255, swap at 285, clears by ~320
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-img/winter-promo-menu.mp4}
BOARD=${2:-img/TV-menu-drink.png}   # use img/TV-menu-food.png for the food menu
ffmpeg -loglevel error -y \
  -loop 1 -framerate 30 -i "$BOARD" \
  -loop 1 -framerate 30 -i img/winter-promo.png \
  -c:v libvpx-vp9 -i assets/winter/snowball-transition.webm \
  -c:v libvpx-vp9 -i assets/winter/snowball-transition.webm \
  -filter_complex "
    [0:v]scale=1920:1080,format=yuv420p,setsar=1,split=2[ba][bb];
    [ba]trim=end_frame=60,setpts=PTS-STARTPTS[b1];
    [1:v]scale=1920:1080,format=yuv420p,setsar=1,trim=end_frame=225,setpts=PTS-STARTPTS[w];
    [bb]trim=end_frame=50,setpts=PTS-STARTPTS[b2];
    [b1][w][b2]concat=n=3:v=1:a=0[base];
    [2:v]fps=30,format=yuva420p,setpts=PTS-STARTPTS+30/30/TB[s1];
    [3:v]fps=30,format=yuva420p,setpts=PTS-STARTPTS+255/30/TB[s2];
    [base][s1]overlay=eof_action=pass:format=auto[o1];
    [o1][s2]overlay=eof_action=pass:format=auto,format=yuv420p[out]" \
  -map "[out]" -r 30 -frames:v 335 -c:v libx264 -preset slow -crf 17 -an -movflags +faststart "$OUT"
