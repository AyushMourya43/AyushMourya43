"""
make_ascii_svg.py — convert two prepped grayscale photos into a single
self-typing, auto-cycling monochrome ASCII-art SVG.

Frame 1 types itself in row-by-row on load, holds for ~9.5s, then
crossfades into Frame 2 (which was pre-rendered off-screen), holds,
and crossfades back — looping forever, switching photo every 10s.

Usage:
    python scripts/make_ascii_svg.py <prepped_main.png> <prepped_alt.png> <out.svg>
"""

import sys
from PIL import Image

RAMP = " .`:-=+*cs#%@"   # bright (sparse) -> dark (dense), leading space = blank
COLS = 92
ROWS = 52
FONT_SIZE = 8.6
LINE_HEIGHT = FONT_SIZE * 1.0
CHAR_WIDTH = FONT_SIZE * 0.6
PAD = 14
FILL_COLOR = "#c9d1d9"   # monochrome light-gray, GitHub-dark-friendly


def image_to_rows(path: str, cols: int, rows: int) -> list[str]:
    im = Image.open(path).convert("L").resize((cols, rows))
    px = im.load()
    lines = []
    for y in range(rows):
        row_chars = []
        for x in range(cols):
            brightness = px[x, y] / 255.0
            idx = int((1 - brightness) * (len(RAMP) - 1))
            row_chars.append(RAMP[idx])
        lines.append("".join(row_chars).rstrip() or " ")
    return lines


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_frame_rows_svg(rows: list[str], group_id: str, animate_typing: bool) -> str:
    """One <g> with one <text> per row. Optionally wipes in row by row."""
    out = [f'<g id="{group_id}" font-family="Fira Code, Consolas, monospace" '
           f'font-size="{FONT_SIZE}" fill="{FILL_COLOR}">']
    for i, row in enumerate(rows):
        y = PAD + (i + 1) * LINE_HEIGHT
        row_w = len(row) * CHAR_WIDTH
        clip_id = f"{group_id}-clip-{i}"
        if animate_typing:
            begin = 0.35 + i * 0.024
            out.append(
                f'<clipPath id="{clip_id}"><rect x="{PAD}" y="{y - LINE_HEIGHT}" '
                f'width="0" height="{LINE_HEIGHT + 2}">'
                f'<animate attributeName="width" from="0" to="{row_w + 4}" '
                f'begin="{begin:.2f}s" dur="0.35s" fill="freeze" '
                f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
                f'</rect></clipPath>'
            )
            out.append(
                f'<text x="{PAD}" y="{y}" clip-path="url(#{clip_id})" '
                f'xml:space="preserve">{esc(row)}</text>'
            )
        else:
            out.append(
                f'<text x="{PAD}" y="{y}" xml:space="preserve">{esc(row)}</text>'
            )
    out.append("</g>")
    return "\n".join(out)


def build_svg(rows_main: list[str], rows_alt: list[str]) -> str:
    width = PAD * 2 + COLS * CHAR_WIDTH
    height = PAD * 2 + ROWS * LINE_HEIGHT

    frame1 = build_frame_rows_svg(rows_main, "frame1", animate_typing=True)
    frame2 = build_frame_rows_svg(rows_alt, "frame2", animate_typing=False)

    # crossfade loop: frame1 visible 0-9.5s, frame2 visible 10-19.5s, dur 20s, infinite
    svg = f'''<svg viewBox="0 0 {width:.0f} {height:.0f}" xmlns="http://www.w3.org/2000/svg">
<style>
  text {{ white-space: pre; }}
</style>
<rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="none"/>
<g id="frame1-wrap" opacity="1">
{frame1}
<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.475;0.5;0.975;1"
         dur="20s" begin="2s" repeatCount="indefinite"/>
</g>
<g id="frame2-wrap" opacity="0">
{frame2}
<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.475;0.5;0.975;1"
         dur="20s" begin="2s" repeatCount="indefinite"/>
</g>
</svg>'''
    return svg


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: python make_ascii_svg.py <main.png> <alt.png> <out.svg>")
        sys.exit(1)
    main_png, alt_png, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    rows_main = image_to_rows(main_png, COLS, ROWS)
    rows_alt = image_to_rows(alt_png, COLS, ROWS)
    svg = build_svg(rows_main, rows_alt)
    with open(out_path, "w") as f:
        f.write(svg)
    print(f"wrote {out_path}")
