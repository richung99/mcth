# Mr. Chick's Tea House
Simple TV Menu

## Drink menu videos

The drink menu TV plays the videos listed in `drink/playlist.json`:

```json
{
  "menu": ["img/instagram-menu.mp4", "img/pumpkin-specials-menu.mp4"],
  "promos": ["img/promotion-menu.mp4", "img/fall-specials-menu.mp4"],
  "promoEveryMinutes": 2
}
```

- **menu**: played in order, on repeat.
- **promos**: take turns, one every `promoEveryMinutes`, in the order listed (promo 1, promo 2, promo 1, ...). Each one plays at the end of the current menu loop, so they come a bit later than the interval (up to the length of a menu loop, about 36s). Use `[]` for no promos. To add another promo, add its file name to the list.

### Changing a video

1. Upload the new video to `img/`. If it has the same name as the old one, you're done.
2. If it has a different name, edit `drink/playlist.json` so it lists the new name.
3. Wait about 2 minutes. GitHub rebuilds `img/drink_menu_loop.mp4` automatically (see the **Actions** tab), and the TV switches to it at the end of its next menu loop. No need to touch the TV.

Don't edit `img/drink_menu_loop.mp4` or `drink/segments.json` by hand. They're generated, and the next rebuild overwrites them.

**Why one combined file?** TV browsers blank the screen for a moment whenever a video switches files. The page plays one combined file and jumps inside it, so it never blinks.

**Tips for new videos:** make them 1920×1080, and start and end them on the full menu board (like the current ones) so they blend into each other. Any size or frame rate works, since the build converts everything to 1080p at 30 fps.

### Checking the TV

Open `drink/?debug` (for example `https://richung99.github.io/mcth/drink/?debug`) to show a status box: which section is playing, when the next promo is due, and the current build.

### Rebuilding by hand

Needs Python 3 and ffmpeg: `python3 scripts/build_drink_video.py`
