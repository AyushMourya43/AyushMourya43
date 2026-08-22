#!/usr/bin/env python3
"""Shared SVG plumbing. Standard library only, so CI needs no dependencies.

Two things live here that every generated file needs: the base64 @font-face
block (an external font URL cannot load inside an <img>-embedded SVG, so each
file carries its own subset), and a palette picked to clear 3:1 contrast on
both GitHub themes -- README images cannot see prefers-color-scheme, so one
set of colours has to work on #ffffff and on #0d1117 alike.
"""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBSET = ROOT / "assets" / "fonts" / "subset"

# contrast on white / on #0d1117
INK    = "#6e7887"   # 4.47 / 4.24  portrait glyphs, body
STRONG = "#5f6a79"   # 5.49 / 3.45  headline numerals
MUTED  = "#828c9b"   # 3.40 / 5.56  labels, axes, rules
BLUE   = "#4f8fd4"   # 3.38 / 5.60
GREEN  = "#3f9e78"   # 3.29 / 5.74
VIOLET = "#a371f7"   # 3.35 / 5.64

FAMILY = "JBMono"
# JetBrains Mono is 600/1000 units: exactly the 0.600 em the character grid assumes.
ADVANCE = 0.600
FALLBACK = ("'Liberation Mono','DejaVu Sans Mono','Noto Sans Mono',"
            "'Menlo','Consolas',monospace")


def _b64(name: str) -> str:
    return base64.b64encode((SUBSET / name).read_bytes()).decode("ascii")


def face(subset: str, weight: int = 400) -> str:
    """One @font-face rule with the subset inlined as a data URI."""
    return (f"@font-face{{font-family:'{FAMILY}';font-style:normal;"
            f"font-weight:{weight};src:url(data:font/woff2;base64,{_b64(subset)}) "
            f"format('woff2');}}")


def stack(extra: str = "") -> str:
    return f"font-family:'{FAMILY}',{FALLBACK};{extra}"


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def svg(width, height, body: str, style: str, title: str) -> str:
    """A complete standalone SVG document."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title>"
        f"<defs><style>{style}</style></defs>"
        f"{body}</svg>"
    )


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"{path.name:16} {len(text.encode('utf-8'))/1024:6.1f} KB")
