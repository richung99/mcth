#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# make_holiday_promo.sh
# Usage: make_holiday_promo.sh [out.mp4] [board.png] [promo.png]
# Builds the holiday promo: the menu board, the gift-wrap ribbon stinger, the
# holiday picture, the stinger again, and back to the board.
# Depends on: ffmpeg (with libvpx for the alpha stinger),
#   assets/holiday/gift-wrap-stinger.webm, a board PNG (default
#   img/TV-menu-drink.png) and a promo PNG (default img/winter-promo.png).
# Does NOT handle: putting it into the TV loop (build_drink_video.py does that).
# -----------------------------------------------------------------------------
# Why this stinger: the snowball stinger lagged on the TV. The ribbon is a few
# large smooth shapes, about as light to play as the THIRTEEN boba stinger.
#
# Timing (30 fps frames). The ribbon fully covers the screen from 20 to 42
# frames after it starts; the picture underneath is swapped 31 frames in.
#   0-28    board               stinger #1 starts at 29, swap at 60
#   60-284  holiday picture     stinger #2 starts at 254, swap at 285
#   285-334 board               (335 frames = 11.17 s)
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-img/winter-promo-menu.mp4}
BOARD=${2:-img/TV-menu-drink.png}
PROMO=${3:-img/winter-promo.png}
ST=assets/holiday/gift-wrap-stinger.webm
ffmpeg -loglevel error -y \
  -loop 1 -framerate 30 -i "$BOARD" -loop 1 -framerate 30 -i "$PROMO" \
  -c:v libvpx -i "$ST" -c:v libvpx -i "$ST" \
  -filter_complex "
    [0:v]scale=1920:1080,format=yuv420p,setsar=1,split=2[ba][bb];
    [ba]trim=end_frame=60,setpts=PTS-STARTPTS[b1];
    [1:v]scale=1920:1080,format=yuv420p,setsar=1,trim=end_frame=225,setpts=PTS-STARTPTS[w];
    [bb]trim=end_frame=50,setpts=PTS-STARTPTS[b2];
    [b1][w][b2]concat=n=3:v=1:a=0[base];
    [2:v]fps=30,format=yuva420p,setpts=PTS-STARTPTS+29/30/TB[s1];
    [3:v]fps=30,format=yuva420p,setpts=PTS-STARTPTS+254/30/TB[s2];
    [base][s1]overlay=eof_action=pass:format=auto[o1];
    [o1][s2]overlay=eof_action=pass:format=auto,format=yuv420p[out]" \
  -map "[out]" -r 30 -frames:v 335 -c:v libx264 -preset slow -crf 17 -an -movflags +faststart "$OUT"
