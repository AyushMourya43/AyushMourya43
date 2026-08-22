#!/usr/bin/env python3
"""Subset JetBrains Mono into the smallest woff2 files each SVG needs.

Dev-only (needs fonttools + brotli). The .woff2 output is committed; the
generators just base64 it in at render time, so CI needs nothing but stdlib.
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "fonts"
OUT = SRC / "subset"

# the 13 glyphs the portrait ramp draws with, nothing else
RAMP = " .`:-=+*cs#%@"
# every character that appears in a section heading
HEADINGS = "abcdefghijklmnopqrstuvwxyz ./"
# the data graphics: digits, both cases, punctuation they format with
LATIN = ("abcdefghijklmnopqrstuvwxyz"
         "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
         "0123456789"
         " .,:;%+-/()·—→'\"#")

JOBS = [
    ("JetBrainsMono-Regular.ttf", RAMP,     "ramp.woff2"),
    ("JetBrainsMono-Medium.ttf",  HEADINGS, "head.woff2"),
    ("JetBrainsMono-Regular.ttf", LATIN,    "mono-regular.woff2"),
    ("JetBrainsMono-Bold.ttf",    LATIN,    "mono-bold.woff2"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for src, text, name in JOBS:
        dst = OUT / name
        subprocess.run([
            sys.executable, "-m", "fontTools.subset", str(SRC / src),
            f"--text={text}",
            "--flavor=woff2",
            "--layout-features=",
            "--no-hinting",
            "--desubroutinize",
            f"--output-file={dst}",
        ], check=True)
        print(f"{name:22} {dst.stat().st_size/1024:6.1f} KB  ({len(set(text))} glyphs)")


if __name__ == "__main__":
    main()
