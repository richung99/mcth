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
# Joins the drink menu videos listed in drink/playlist.json into ONE video file
# (img/drink_menu_loop.mp4) and writes drink/segments.json, which tells the
# drink page where the promo and menu sections start and end inside that file.
# Depends on: ffmpeg + ffprobe on PATH, Python 3.8+ standard library only.
# Does NOT handle: playback or promo timing (drink/index.html does that), or
#   committing the output (the GitHub workflow does that).
# -----------------------------------------------------------------------------

# Why one file: TV browsers blank the screen for a moment whenever a <video>
# switches to a different file. Inside one file the page can jump around with
# no blink at all.

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAYLIST_PATH = REPO_ROOT / "drink" / "playlist.json"
SEGMENTS_PATH = REPO_ROOT / "drink" / "segments.json"
OUTPUT_VIDEO = "img/drink_menu_loop.mp4"  # relative to the repo root

# Output format: 1080p, 30 fps, H.264 High profile level 4.0, no audio.
# Level 4.0 / 1080p30 plays on practically every TV and streaming stick,
# unlike 1440p60 (level 5.1), which many older TVs can't decode.
WIDTH, HEIGHT, FPS = 1920, 1080, 30
BACKGROUND = "0xf5efe8"  # menu's cream color, used if a clip needs letterboxing


def load_playlist(path):
    """
    Read and validate drink/playlist.json.

    Args:
        path (Path): Location of playlist.json.

    Returns:
        dict: {"menu": [Path, ...], "promo": Path or None, "promoEveryMinutes": float}

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

    # Validate optional promo and interval
    promo = data.get("promo") or None
    every = data.get("promoEveryMinutes", 3)
    if not isinstance(every, (int, float)) or every <= 0:
        sys.exit('"promoEveryMinutes" must be a positive number.')

    # Check every listed file exists
    paths = [REPO_ROOT / m for m in menu] + ([REPO_ROOT / promo] if promo else [])
    missing = [str(p.relative_to(REPO_ROOT)) for p in paths if not p.is_file()]
    if missing:
        sys.exit("These videos are listed in playlist.json but not in the repo: " + ", ".join(missing))

    return {
        "menu": [REPO_ROOT / m for m in menu],
        "promo": REPO_ROOT / promo if promo else None,
        "promoEveryMinutes": every,
    }


def run(cmd):
    """Run a command, exiting with its error output if it fails."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{result.stderr[-2000:]}")
    return result.stdout


def normalize_clip(src, dst):
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
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color={BACKGROUND},"
        f"fps={FPS},format=yuv420p,setsar=1"
    )
    run([
        "ffmpeg", "-v", "error", "-y", "-i", str(src),
        "-vf", vf, "-an",
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
    Build img/drink_menu_loop.mp4 and drink/segments.json from playlist.json.

    Notes:
        Layout of the output file is [promo][menu 1][menu 2]...
        The promo goes FIRST so that when it finishes it flows straight into
        the menu without a jump, and the menu section ends at the end of the
        file, where the browser's "ended" event fires at exactly the right
        moment for the page to decide what plays next.
    """
    playlist = load_playlist(PLAYLIST_PATH)
    clips = ([playlist["promo"]] if playlist["promo"] else []) + playlist["menu"]

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)

        # Normalize each clip and record its exact length in frames
        parts, frames = [], []
        for i, src in enumerate(clips):
            dst = workdir / f"part{i:02d}.mp4"
            print(f"Encoding {src.relative_to(REPO_ROOT)} ...", flush=True)
            normalize_clip(src, dst)
            parts.append(dst)
            frames.append(count_frames(dst))

        # Join the clips into one file
        joined = workdir / "joined.mp4"
        concat_clips(parts, joined, workdir)

        # Sanity check: no frames lost or added by the join
        total = count_frames(joined)
        if total != sum(frames):
            sys.exit(f"Joined video has {total} frames, expected {sum(frames)}.")

        out_path = REPO_ROOT / OUTPUT_VIDEO
        shutil.move(str(joined), out_path)

    # Work out section boundaries in seconds (frame counts / fps are exact)
    promo_frames = frames[0] if playlist["promo"] else 0
    segments = {
        "video": OUTPUT_VIDEO,
        "version": short_hash(out_path),
        "fps": FPS,
        "duration": round(total / FPS, 4),
        "promo": {"start": 0, "end": round(promo_frames / FPS, 4)} if playlist["promo"] else None,
        "menu": {"start": round(promo_frames / FPS, 4), "end": round(total / FPS, 4)},
        "promoEveryMinutes": playlist["promoEveryMinutes"],
        "sources": [str(c.relative_to(REPO_ROOT).as_posix()) for c in clips],
    }
    SEGMENTS_PATH.write_text(json.dumps(segments, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUTPUT_VIDEO} ({total} frames, {total / FPS:.1f}s) and drink/segments.json")
    print(json.dumps(segments, indent=2))


if __name__ == "__main__":
    main()
