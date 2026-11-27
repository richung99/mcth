#!/usr/bin/env python3
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# -----------------------------------------------------------------------------
# build_drink_video.py
# Compiles the whole TV show for a page (drink or food) from <page>/playlist.json
# into ONE video file, img/<page>_menu_loop.mp4: the menu repeated, with each
# promo baked in at its turn. The page just loops that file. Also writes
# <page>/segments.json, a readable list of what's where (the page ignores it).
# Depends on: ffmpeg + ffprobe on PATH, Python 3.8+ standard library only.
# Does NOT handle: playback (index.html + drink/player.js) or committing the
#   output (the GitHub workflow does that).
# -----------------------------------------------------------------------------

# Why one file: TV browsers blank the screen for a moment whenever a <video>
# switches to a different file. One file played with the browser's own "loop"
# never blinks.

REPO_ROOT = Path(__file__).resolve().parent.parent
# Which TV page to build: "drink" (default) or "food". Usage: build_drink_video.py [drink|food]
PAGE = sys.argv[1] if len(sys.argv) > 1 else "drink"
if PAGE not in ("drink", "food"):
    sys.exit('Usage: build_drink_video.py [drink|food]')
PLAYLIST_PATH = REPO_ROOT / PAGE / "playlist.json"
SEGMENTS_PATH = REPO_ROOT / PAGE / "segments.json"
OUTPUT_VIDEO = f"img/{PAGE}_menu_loop.mp4"  # relative to the repo root
STILL_SECONDS = 16.4  # how long a still image (.png/.jpg) listed in "menu" plays per loop

# Output format: 1080p, 30 fps, H.264 High profile level 4.0, no audio.
# Level 4.0 / 1080p30 plays on practically every TV and streaming stick,
# unlike 1440p60 (level 5.1), which many older TVs can't decode.
WIDTH, HEIGHT, FPS = 1920, 1080, 30
BACKGROUND = "0xf5efe8"  # menu's cream color, used if a clip needs letterboxing


def load_playlist(path):
    """
    Read and validate <page>/playlist.json (page = drink or food).

    Args:
        path (Path): Location of playlist.json.

    Returns:
        dict: {"menu": [Path, ...], "promos": [Path, ...], "promoEveryMinutes": float}

    Raises:
        SystemExit: If the file is malformed or a listed video doesn't exist.
            (Exits with a readable message so the GitHub run log explains it.)
    """
    # Parse JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"Could not read {path}: {e}")

    # Validate menu list
    menu = data.get("menu")
    if not isinstance(menu, list) or not menu:
        sys.exit('playlist.json needs a "menu" list with at least one video.')

    # Validate optional promos (a "promos" list, or the older single "promo")
    promos = data.get("promos")
    if promos is None:
        promos = [data["promo"]] if data.get("promo") else []
    if not isinstance(promos, list):
        sys.exit('"promos" must be a list of video paths (or leave it out for no promos).')
    every = data.get("promoEveryMinutes", 3)
    if not isinstance(every, (int, float)) or every <= 0:
        sys.exit('"promoEveryMinutes" must be a positive number.')

    # Check every listed file exists
    paths = [REPO_ROOT / m for m in menu] + [REPO_ROOT / pr for pr in promos]
    missing = [str(p.relative_to(REPO_ROOT)) for p in paths if not p.is_file()]
    if missing:
        sys.exit("These videos are listed in playlist.json but not in the repo: " + ", ".join(missing))

    # Optional banner: {"image": "img/....png", "height": 86}. Every video is
    # shrunk to fit below a band of that height, and the image (a full
    # 1920x1080 frame with the banner at the top) fills the rest.
    banner = data.get("banner")
    if banner is not None:
        if not isinstance(banner, dict) or not isinstance(banner.get("height"), int) \
                or not (0 < banner["height"] < HEIGHT // 3) or not (REPO_ROOT / str(banner.get("image", ""))).is_file():
            sys.exit('"banner" must be {"image": "<existing png>", "height": <pixels, under 360>}.')
        banner = {"image": REPO_ROOT / banner["image"], "height": banner["height"]}

    return {
        "menu": [REPO_ROOT / m for m in menu],
        "promos": [REPO_ROOT / pr for pr in promos],
        "promoEveryMinutes": every,
        "banner": banner,
    }


def run(cmd):
    """Run a command, exiting with its error output if it fails."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{result.stderr[-2000:]}")
    return result.stdout


def normalize_clip(src, dst, banner=None):
    """
    Re-encode one clip to the shared output format.

    Args:
        src (Path): Original video.
        dst (Path): Where to write the normalized .mp4.

    Notes:
        Every clip gets byte-for-byte identical encoder settings so the clips
        can be joined afterwards without re-encoding (ffmpeg's concat with
        "-c copy" requires that). Each clip therefore also starts on a
        keyframe, which makes the page's jumps to a section start instant.
        B-frames are turned off (-bf 0) so frame timestamps stay simple and
        section start times are exact.
        Keyframes are otherwise spaced up to 20s apart (-g): the menu board is
        a detailed still image, and every extra keyframe stores the whole board
        again (a 2s spacing made the file ~4x bigger). The page only ever jumps
        to section starts, which always get their own keyframe anyway.
    """
    full = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color={BACKGROUND},"
        f"fps={FPS},setsar=1"
    )
    # A still image in the playlist becomes a short video of that image
    is_still = src.suffix.lower() in (".png", ".jpg", ".jpeg")
    inputs = ["-loop", "1", "-framerate", str(FPS), "-t", str(STILL_SECONDS), "-i", str(src)] if is_still else ["-i", str(src)]
    if banner:
        # Shrink the whole frame (keeping its shape) to fit under the banner,
        # centred left-right, and lay it on the banner image. Everything in the
        # clip, animations included, is scaled the same way, so nothing moves
        # relative to anything else.
        ch = HEIGHT - banner["height"]
        cw = round(WIDTH * ch / HEIGHT / 2) * 2
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(banner["image"])]
        filt = ["-filter_complex",
                f"[0:v]{full},scale={cw}:{ch}:flags=lanczos[c];"
                f"[1:v]scale={WIDTH}:{HEIGHT},fps={FPS},setsar=1[b];"
                f"[b][c]overlay=x={(WIDTH - cw) // 2}:y={banner['height']}:shortest=1,format=yuv420p[v]",
                "-map", "[v]"]
    else:
        filt = ["-vf", full + ",format=yuv420p"]
    run([
        "ffmpeg", "-v", "error", "-y", *inputs,
        *filt, "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-profile:v", "high", "-level", "4.0",
        "-bf", "0", "-g", str(FPS * 20),
        str(dst),
    ])


def count_frames(path):
    """Return the exact number of video frames in a file."""
    out = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
        "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path),
    ])
    return int(out.strip())


def concat_clips(parts, out_path, workdir):
    """Join normalized clips end to end without re-encoding."""
    # ffmpeg's concat demuxer reads a text file listing the parts in order
    list_file = workdir / "parts.txt"
    list_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    run([
        "ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", "-movflags", "+faststart", str(out_path),
    ])


def short_hash(path):
    """Return the first 12 hex characters of a file's SHA-256."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def main():
    """
    Build img/<page>_menu_loop.mp4 (and <page>/segments.json) from playlist.json.

    Notes:
        The output is the WHOLE show in one file, which the page simply loops:
            [menu x N][promo 1][menu x N][promo 2]...
        N is how many menu loops fit in promoEveryMinutes, so each promo comes
        round about that often. Every promo starts and ends on the menu board,
        so the joins (and the wrap-around from the end back to the start) are
        seamless. No promos -> the file is just the menu once.
        segments.json is informational only (the page doesn't read it).
    """
    playlist = load_playlist(PLAYLIST_PATH)
    menu, promo_list = playlist["menu"], playlist["promos"]

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)

        # Normalize each distinct clip once and record its exact length in frames
        part_of, frames_of = {}, {}
        for i, src in enumerate(dict.fromkeys(menu + promo_list)):
            dst = workdir / f"part{i:02d}.mp4"
            print(f"Encoding {src.relative_to(REPO_ROOT)} ...", flush=True)
            normalize_clip(src, dst, playlist["banner"])
            part_of[src], frames_of[src] = dst, count_frames(dst)

        # Lay out the whole show: N menu loops before each promo
        menu_frames = sum(frames_of[c] for c in menu)
        n_menu = max(1, round(playlist["promoEveryMinutes"] * 60 * FPS / menu_frames)) if promo_list else 1
        sequence = []
        for promo in promo_list or [None]:
            sequence += menu * n_menu
            if promo:
                sequence.append(promo)

        joined = workdir / "joined.mp4"
        concat_clips([part_of[c] for c in sequence], joined, workdir)

        # Sanity check: no frames lost or added by the join
        total = count_frames(joined)
        expected = sum(frames_of[c] for c in sequence)
        if total != expected:
            sys.exit(f"Joined video has {total} frames, expected {expected}.")

        out_path = REPO_ROOT / OUTPUT_VIDEO
        shutil.move(str(joined), out_path)

    # Record what's where (seconds), for people reading it; the page doesn't use it
    entries, start = [], 0
    for c in sequence:
        entries.append({"source": c.relative_to(REPO_ROOT).as_posix(),
                        "start": round(start / FPS, 4), "end": round((start + frames_of[c]) / FPS, 4)})
        start += frames_of[c]
    segments = {
        "video": OUTPUT_VIDEO,
        "version": short_hash(out_path),
        "fps": FPS,
        "duration": round(total / FPS, 4),
        "menuLoopsBetweenPromos": n_menu,
        "sequence": entries,
    }
    SEGMENTS_PATH.write_text(json.dumps(segments, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUTPUT_VIDEO} ({total} frames, {total / FPS:.1f}s, menu x{n_menu} between promos) and {PAGE}/segments.json")


if __name__ == "__main__":
    main()
