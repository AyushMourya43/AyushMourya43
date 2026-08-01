# Setup — one time

1. Create the special profile repo (skip if it already exists):
   ```
   gh repo create AyushMourya43 --public --clone
   ```
   or just create a repo named exactly `AyushMourya43` on github.com and clone it.

2. Copy everything from this folder into that repo (README.md, the
   three .svg files, `scripts/`, `data/`, `.github/`).

3. Commit and push:
   ```
   git add .
   git commit -m "profile: animated ASCII portrait + live contribution heatmap"
   git push
   ```

4. Go to the repo's **Actions** tab → "Update profile art" → **Run workflow**
   (the manual `workflow_dispatch` trigger) once, to confirm it fetches your
   real contribution data and commits a fresh `contrib-heatmap.svg`.
   After that it runs on its own every day at ~06:17 UTC.

5. Open your GitHub profile page — done.

## Changing your photos later

The two portrait photos you sent aren't stored as raw images in the repo —
only their ASCII-converted output (`avi-ascii.svg`) is committed, so there's
nothing extra to clean up. To swap in a new photo:

```bash
cd scripts
pip install -r requirements.txt --break-system-packages   # only needed once, only for this step
python prep_photo.py your-new-photo.jpg /tmp/prepped-main.png
python prep_photo.py your-other-photo.jpg /tmp/prepped-alt.png
python make_ascii_svg.py /tmp/prepped-main.png /tmp/prepped-alt.png ../avi-ascii.svg
```
Then commit the updated `avi-ascii.svg`.

## Editing the info card text

Open `scripts/make_info_card.py` — the `ROWS` list near the top is the
Now / Prev / Stack / Highlights content. Edit it, then:
```bash
python scripts/make_info_card.py
```

## How the auto-cycling portrait works

`avi-ascii.svg` embeds **both** photos as pre-rendered ASCII text layers.
Photo 1 types itself in row-by-row on load. Every 10 seconds the two layers
crossfade — photo 1 fades out as photo 2 fades in, then back — looping
forever via native SVG `<animate>` (no JavaScript, so it survives GitHub's
README sanitizer).
