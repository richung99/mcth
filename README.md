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
- **promos**: take turns in the order listed, one about every `promoEveryMinutes`. The build compiles the whole show into ONE video (menu repeated, then promo 1, menu repeated, then promo 2, ...) and the TV just loops it. Use `[]` for no promos. To add another promo, add its file name to the list.

### Changing a video

1. Upload the new video to `img/`. If it has the same name as the old one, you're done.
2. If it has a different name, edit `drink/playlist.json` so it lists the new name.
3. Wait about 2 minutes. GitHub rebuilds `img/drink_menu_loop.mp4` automatically (see the **Actions** tab). Then reload the page on the TV (or turn it off and on) to pick it up. The TV never reloads by itself, so it never blinks.

Don't edit `img/drink_menu_loop.mp4` or `drink/segments.json` by hand. They're generated, and the next rebuild overwrites them.

**Why one combined file?** TV browsers blank the screen for a moment whenever a video switches files or jumps. The page plays one pre-compiled file with the browser's own looping, so it never blinks.

**Tips for new videos:** make them 1920×1080, and start and end them on the full menu board (like the current ones) so they blend into each other. Any size or frame rate works, since the build converts everything to 1080p at 30 fps.

### Checking the TV

Open `drink/?debug` (for example `https://richung99.github.io/mcth/drink/?debug`) to show a status box: playback time, whether it's waiting for data, and any reloads.

### Rebuilding by hand

Needs Python 3 and ffmpeg: `python3 scripts/build_drink_video.py`

### Regenerating the menu video (flipping logo card)

`img/instagram-menu.mp4` is generated from `img/TV-menu-drink.png`: the logo card flips to the website/Instagram card and back. To change the board, edit the PNG; to change the card text, edit `scripts/flipcard/card.html`. Then run `python3 scripts/flipcard/render_flip_video.py img/instagram-menu.mp4` (needs Python `playwright` with Chromium, and ffmpeg) and push; the Action rebuilds the TV loop.

### Food menu

The food TV page is a still image: `img/TV-menu-food.png`. To update it, upload a new image with the same name. No video or promos.

### Holiday promo (gift-wrap transition)

`img/winter-promo-menu.mp4` is the drink board, the gift-wrap ribbon stinger, the holiday picture (`img/winter-promo.png`), the stinger again, and back to the board. It's made by `scripts/make_holiday_promo.sh` from `assets/holiday/gift-wrap-stinger.webm`. The snowball stinger lagged on the TV; the ribbon is about as light to play as the THIRTEEN boba stinger. To change the picture or board, replace the PNG, rerun the script, and push.

### THIRTEEN promo

`img/promotion-menu.mp4` is the drink board, the boba stinger, the THIRTEEN screen and back. It's made by `scripts/make_thirteen_promo.sh` from `assets/thirteen/` and `img/TV-menu-drink.png`. If the board changes, rerun that script (and `scripts/make_holiday_promo.sh`) so the promos show the current board.


### Sale banner on the drink menu

`drink/playlist.json` has an optional `"banner"`: `{"image": "img/banner-black-friday.png", "height": 72, "cropTop": 20, "cropBottom": 14}`. With it, the build trims the empty strips above and below each video (cropTop/cropBottom), shrinks it slightly to fit (keeping its shape, so the card flip and transitions are unchanged) and shows the banner across the top. To remove it, delete the `"banner"` entry and push. To change the text, run `python3 scripts/make_banner.py img/banner-black-friday.png "BLACK FRIDAY SALE" "5% OFF"` (default text: "BLACK FRIDAY · FOLLOW @MCTEAHOUSETW", "5% OFF") and push.

### Loop length and the poster

Some TVs fade to black for a moment each time a video starts over. `"repeatCycles": 3` in `drink/playlist.json` repeats the whole show three times inside the file (about 13 minutes), so that happens rarely. The page's poster image, which shows while the video restarts, is the video's own first frame (`img/drink_menu_poster.jpg`, made by the build), so it looks the same as the video, banner included.
On top of that, `drink/player.js` lays a still copy of that first frame (`<img class="menu-cover">`) over the video just before the file ends and whenever the video stops moving (restart, waiting for data), and removes it once the video is moving again (5s into the file after a restart, where the board is still static). The TV's black fade happens underneath it, so it can't be seen. Open `drink/?debug` to see "cover up/down" in the log.
