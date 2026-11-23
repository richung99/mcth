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

The food page works the same way: `food/playlist.json` lists the food board (`img/TV-menu-food.png`, a still image is fine) and the promo (`img/promotion-menu-food.mp4`, the THIRTEEN promo with the boba stinger over the food board). GitHub builds `img/food_menu_loop.mp4`. Changing `TV-menu-food.png` rebuilds it automatically. Hand build: `python3 scripts/build_drink_video.py food`.

### Winter promo (snowball transition)

`img/winter-promo-menu.mp4` is the drink board, a snowball transition, the winter promo picture (`img/winter-promo.png`), and back. It alternates with the THIRTEEN promo on the drink menu, and `img/winter-promo-food-menu.mp4` does the same on the food menu (made with `scripts/make_winter_promo.sh img/winter-promo-food-menu.mp4 img/TV-menu-food.png`). To change the picture, replace `img/winter-promo.png` and run `scripts/make_winter_promo.sh` (needs ffmpeg), then push. The snowball transition clip is in `assets/winter/`.

### THIRTEEN promo

`img/promotion-menu.mp4` is the drink board, the boba stinger, the THIRTEEN screen and back. It's made by `scripts/make_thirteen_promo.sh` from `assets/thirteen/` and `img/TV-menu-drink.png`. If the board changes, rerun that script (and `scripts/make_winter_promo.sh`) so the promos show the current board.

**Note (Nov 22):** the food page is a still image (`img/TV-menu-food.png`). The drink page loops `img/drink_menu_loop.mp4`.
