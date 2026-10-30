# Code Map — Drink menu playlist with periodic promo
Generated: 2026-10-21
Spec summary: Keep menu/promo videos as separate files, show the promos (taking turns) at a fixed interval, and never blink on the TV.

## How it fits together

```
You upload videos ──► drink/playlist.json (what plays, how often)
                              │
        GitHub Action (.github/workflows/build-drink-video.yml)
                              │ runs
                              ▼
               scripts/build_drink_video.py
                │                         │
                ▼                         ▼
   img/drink_menu_loop.mp4        drink/segments.json
   [promo 1][promo 2][menu 1][menu 2]        where each section starts/ends
                │                         │
                └──────────┬──────────────┘
                           ▼
          drink/index.html + drink/player.js (on the TV)
          loop menu section, jump to promo when due
```

## Files

### drink/playlist.json
Responsibility: The only file a person edits. Lists menu videos (in order), the `promos` list (they take turns; `[]` for none), and `promoEveryMinutes`. The older single `"promo": "file.mp4"` form still works.

### scripts/build_drink_video.py
Responsibility: Turns the playlist into one video file plus a section map.

| Function | What it does | Returns |
|---|---|---|
| load_playlist() | Reads and validates playlist.json; exits with a clear message if a video is missing | dict of Paths + interval |
| run() | Runs a command, exits with its error output on failure | stdout |
| normalize_clip() | Re-encodes one clip to 1080p30 H.264 L4.0, no audio, no B-frames | — |
| count_frames() | Exact frame count of a file (used for exact section times) | int |
| concat_clips() | Joins normalized clips without re-encoding | — |
| short_hash() | First 12 hex chars of SHA-256 (the build "version") | str |
| main() | Orchestrates the above, writes segments.json | — |

Key design decisions:
- **Promos first in the file, in playlist order.** The last promo flows straight into the menu with no jump; any earlier one is cut to the menu by player.js the moment it ends. The menu ends at the end of the file, where the browser's `ended` event fires at exactly the right moment.
- **Each clip encoded separately, then joined with `-c copy`.** Every section starts on a keyframe, so jumps are instant, and section boundaries are exact frame counts instead of estimates.
- **Keyframes up to 20s apart.** The menu board is a detailed still, so every keyframe stores the whole board again. 2s spacing made the file about 4× bigger.

### drink/segments.json (generated)
Responsibility: Tells the player the file name, build `version`, fps, and the start/end times in seconds of each entry in `promos` and of `menu`.

### drink/player.js
Responsibility: All playback decisions on the TV.

| Function | What it does | Returns |
|---|---|---|
| note() | Adds a line to the ?debug log | — |
| play() | play() that logs instead of throwing | — |
| fetchSegments() | Loads segments.json, bypassing caches | object or null |
| jumpTo(name, seg) | Seeks to a segment's start (+½ frame) and plays | — |
| onEnded() | End of the menu loop: reload if there's a new build, else the next promo in the rotation if one is due, else menu | — |
| promoEnded() | Every 50ms while a promo plays: when it finishes, jump to the menu (unless it's the last promo, which flows into it) | — |
| checkForUpdate() | Every 5 min: if the build version changed, flag a reload | — |
| renderDebug() | Draws the ?debug overlay | — |
| watchdog() | Every 1s: resume if paused, handle a missed `ended`, reload the video if frozen 15s | — |
| start() | Loads segments.json, sets the video URL (with ?v=version), wires events and timers | — |

Key design decisions:
- **Never changes `video.src` during normal playback.** Changing it is what makes TVs blink. Only seeking happens.
- **Promo only at a loop boundary.** Jumping mid-loop would make the animated card under Lemonades visibly snap.
- **New builds load at the next loop end**, which is the least noticeable moment for the one reload.

### drink/index.html
Responsibility: Page markup (one `<video>` with no `loop` attribute), loads player.js. Holds the optional full-screen button code.

### .github/workflows/build-drink-video.yml
Responsibility: On pushes to main that touch `img/`, the playlist, the script or itself, installs ffmpeg, runs the build and commits the output.

## Dependencies between files
player.js → segments.json, img/drink_menu_loop.mp4 (fetched at runtime)
build_drink_video.py → playlist.json, the videos it lists, ffmpeg/ffprobe
build-drink-video.yml → build_drink_video.py
