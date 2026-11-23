#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# make_thirteen_promo.sh
# Usage: make_thirteen_promo.sh [out.mp4] [board.png]
# Builds the THIRTEEN promo: the menu board, the boba stinger transition, the
# THIRTEEN screen, the stinger again, and back to the board.
# Depends on: ffmpeg (with libvpx for the alpha stinger), assets/thirteen/
#   boba-stinger.webm and thirteen-screen.png, and a board PNG
#   (default img/TV-menu-drink.png).
# Does NOT handle: putting it into the TV loop (build_drink_video.py does that).
# -----------------------------------------------------------------------------
# Timing (30 fps frames), same as the original THIRTEEN promo video:
#   0-199   board            stinger #1 starts at 147; it fully covers the screen
#                            around frames 186-214, and the swap happens at 200
#   200-443 THIRTEEN screen  stinger #2 starts at 391, swap at 444
#   444-510 board            (17.0 s total)
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-img/promotion-menu.mp4}
BOARD=${2:-img/TV-menu-drink.png}
ffmpeg -loglevel error -y \
  -loop 1 -framerate 30 -i "$BOARD" -loop 1 -framerate 30 -i assets/thirteen/thirteen-screen.png \
  -c:v libvpx -i assets/thirteen/boba-stinger.webm -c:v libvpx -i assets/thirteen/boba-stinger.webm \
  -filter_complex "
    [0:v]scale=1920:1080,format=yuv420p,setsar=1,split=2[ba][bb];
    [ba]trim=end_frame=200,setpts=PTS-STARTPTS[b1];
    [1:v]scale=1920:1080,format=yuv420p,setsar=1,trim=end_frame=244,setpts=PTS-STARTPTS[t];
    [bb]trim=end_frame=67,setpts=PTS-STARTPTS[b2];
    [b1][t][b2]concat=n=3:v=1:a=0[base];
    [2:v]format=yuva420p,setpts=PTS+147/30/TB[s1];
    [3:v]format=yuva420p,setpts=PTS+391/30/TB[s2];
    [base][s1]overlay=eof_action=pass:format=auto[o1];
    [o1][s2]overlay=eof_action=pass:format=auto,format=yuv420p[out]" \
  -map "[out]" -r 30 -frames:v 511 -c:v libx264 -preset slow -crf 17 -an -movflags +faststart "$OUT"
