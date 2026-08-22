#!/usr/bin/env python3
"""Section headings as SVG -- the only way to put your own typeface on one.

The trade is real and worth stating: an image heading has no anchor link, so
GitHub's README outline goes empty. The alt text carries the word instead.

Standard library only. Output is static; regenerate after editing SECTIONS.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svgkit as k

ROOT = Path(__file__).resolve().parent.parent
W, H = 860, 30
SIZE = 15
TRACK = 0.16          # letter-spacing, in em

SECTIONS = ["whoami", "activity", "languages", "stack", "work",
            "experience", "elsewhere"]


def heading(word: str) -> str:
    style = (k.face("head.woff2", 500)
             + f"text{{{k.stack()}font-size:{SIZE}px;font-weight:500;"
               f"fill:{k.INK};letter-spacing:{TRACK}em;}}")
    # advance + tracking, so the rule always starts clear of the last glyph
    text_w = len(word) * SIZE * (k.ADVANCE + TRACK)
    body = (f'<text x="0" y="21">{k.esc(word)}</text>'
            f'<line x1="{round(text_w + 14, 1)}" y1="16" x2="{W}" y2="16" '
            f'stroke="{k.MUTED}" stroke-opacity="0.32" stroke-width="1"/>')
    return k.svg(W, H, body, style, word)


def main():
    for word in SECTIONS:
        k.write(ROOT / f"hd-{word.replace(' ', '-')}.svg", heading(word))


if __name__ == "__main__":
    main()
