#!/usr/bin/env python3
"""Turn a photo into an ASCII portrait that types itself in, once.

Dev-only: needs pillow, numpy, opencv-python-headless, rembg, onnxruntime.
The committed artefact is portrait.svg -- CI never runs this.

    python3 scripts/make_portrait.py assets/profile.jpg portrait.svg
    python3 scripts/make_portrait.py in.jpg out.svg --crop 0.22,0.01,0.79,0.66 --gamma 1.55

--crop takes left,top,right,bottom as fractions of the source. Crop tight --
chin to just above the hair. ASCII draws with shadow and has 13 levels to do
it with, so a face filling 30% of the frame simply will not resolve.
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svgkit as k

# --- grid -------------------------------------------------------------------
COLS = 90                     # below ~88 the face muddies; above it the block dominates
FONT_SIZE = 12.9
CHAR_W = FONT_SIZE * k.ADVANCE          # 7.74
ASPECT = 0.48                           # monospace cells are ~2x taller than wide
LINE_H = CHAR_W / ASPECT                # 16.125

# light -> dark. The leading space clears the cut-out background to nothing.
RAMP = " .`:-=+*cs#%@"

# --- animation --------------------------------------------------------------
STAGGER = 0.09                # seconds between one row starting and the next
WIPE = 0.85                   # how long a single row takes to fill in
GAMMA = 1.7                   # the darkening curve: without it the face washes out
CLIP = 3.0                    # CLAHE clip limit: local contrast, per tile
TILES = 8                     # CLAHE tile grid

# chosen for assets/profile.jpg: hair line to just under the chin, ears in.
# Anything looser and the shirt fills half the grid with mid-tone noise that
# competes with the face for attention.
CROP = (0.23, 0.02, 0.76, 0.63)


def to_ascii(path: Path, crop=None, gamma=GAMMA, clip=CLIP, tiles=TILES) -> list[str]:
    from rembg import new_session, remove

    src = Image.open(path).convert("RGBA")
    if crop:
        w, h = src.size
        l, t, r, b = crop
        src = src.crop((round(l * w), round(t * h), round(r * w), round(b * h)))
    # u2net_human_seg: ~176 MB, trained on people, and far smaller than the
    # 1 GB model rembg now defaults to. Downloaded once, then cached.
    cut = remove(src, session=new_session("u2net_human_seg"))
    rgba = np.array(cut)
    alpha = rgba[:, :, 3]

    # composite on white so anything outside the subject lands on the blank
    # end of the ramp instead of filling with '@'
    rgb = rgba[:, :, :3].astype(np.float32)
    a = (alpha.astype(np.float32) / 255.0)[:, :, None]
    flat = (rgb * a + 255.0 * (1 - a)).astype(np.uint8)

    g = cv2.cvtColor(flat, cv2.COLOR_RGB2GRAY)
    g = cv2.bilateralFilter(g, 9, 75, 75)              # smooth skin, keep edges
    g = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tiles, tiles)).apply(g)
    g = (np.power(g / 255.0, gamma) * 255.0).astype(np.uint8)

    h, w = g.shape
    rows = max(1, round(COLS * (h / w) * ASPECT))
    small = cv2.resize(g, (COLS, rows), interpolation=cv2.INTER_AREA)
    mask = cv2.resize(alpha, (COLS, rows), interpolation=cv2.INTER_AREA)
    small = np.where(mask < 40, 255, small)            # hard-clear the background

    idx = np.clip(((255 - small.astype(np.int32)) * (len(RAMP) - 1)) // 255,
                  0, len(RAMP) - 1)
    return ["".join(RAMP[i] for i in row) for row in idx]


def build_svg(lines: list[str]) -> str:
    cols = max(len(l) for l in lines)
    lines = [l.ljust(cols) for l in lines]
    w = round(cols * CHAR_W, 2)
    h = round(len(lines) * LINE_H, 2)

    style = (
        k.face("ramp.woff2")
        + f"text{{{k.stack()}font-size:{FONT_SIZE}px;fill:{k.INK};"
          "white-space:pre;font-kerning:none;}"
        + f".cur{{fill:{k.INK};}}"
    )

    parts, clips = [], []
    for i, line in enumerate(lines):
        y = round(i * LINE_H, 3)
        begin = round(i * STAGGER, 3)
        clips.append(
            f'<clipPath id="w{i}"><rect x="0" y="{y}" width="0" height="{LINE_H}">'
            f'<animate attributeName="width" from="0" to="{w}" dur="{WIPE}s" '
            f'begin="{begin}s" fill="freeze"/></rect></clipPath>'
        )
        # baseline sits at 0.78 of the cell so descenders stay inside the row
        parts.append(
            f'<text x="0" y="{round(y + LINE_H * 0.78, 3)}" xml:space="preserve" '
            f'textLength="{w}" lengthAdjust="spacing" clip-path="url(#w{i})">'
            f"{k.esc(line)}</text>"
        )
        # A block riding the wipe edge. It starts invisible -- otherwise every
        # row's cursor sits parked at x=0 as a column of dashes until its turn.
        parts.append(
            f'<rect class="cur" x="0" y="{round(y + LINE_H * 0.12, 3)}" '
            f'width="{round(CHAR_W, 2)}" height="{round(LINE_H * 0.76, 2)}" opacity="0">'
            f'<animate attributeName="x" from="0" to="{round(w - CHAR_W, 2)}" '
            f'dur="{WIPE}s" begin="{begin}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.5" begin="{begin}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0" begin="{round(begin + WIPE, 3)}s" '
            f'fill="freeze"/></rect>'
        )

    body = f"<defs>{''.join(clips)}</defs>{''.join(parts)}"
    return k.svg(w, h, body, style, "ASCII portrait of Ayush, typed in one row at a time")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default="assets/profile.jpg")
    ap.add_argument("dst", nargs="?", default="portrait.svg")
    ap.add_argument("--crop", default=",".join(str(c) for c in CROP),
                    help="left,top,right,bottom as fractions of the source")
    ap.add_argument("--gamma", type=float, default=GAMMA)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    src, dst = Path(a.src), Path(a.dst)
    crop = tuple(float(x) for x in a.crop.split(",")) if a.crop else None
    print(f"crop {crop}  gamma {a.gamma}  clahe clip {CLIP} tiles {TILES}")
    lines = to_ascii(src, crop, a.gamma)
    k.write(dst, build_svg(lines))
    total = (len(lines) - 1) * STAGGER + WIPE
    print(f"{COLS} cols x {len(lines)} rows, types out in {total:.1f}s")
    if not a.quiet:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
