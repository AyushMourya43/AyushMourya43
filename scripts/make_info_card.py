"""
make_info_card.py — a neofetch-style info panel SVG that fades/slides
in line by line. Content lives here as plain data below, so you can
edit it without touching the render logic.

Env var STATIC=1 -> emit a frozen (non-animated) frame, useful for
Quick Look / static previews.

Usage:
    python scripts/make_info_card.py            # writes info-card.svg
    STATIC=1 python scripts/make_info_card.py    # frozen frame
"""

import os

WIDTH, HEIGHT = 490, 300
PAD_X, PAD_Y = 26, 34
LINE_H = 25
FONT = "Fira Code, Consolas, monospace"

BG = "#0d1117"
BORDER = "#30363d"
TITLE_BAR = "#161b22"
DOT_RED, DOT_YEL, DOT_GRN = "#ff5f56", "#ffbd2e", "#27c93f"
KEY_COLOR = "#6366f1"
VAL_COLOR = "#c9d1d9"
DIM = "#8b949e"

USER = "ayush@github"

# ---- content: edit freely ----
ROWS = [
    ("OS", "GD Goenka University :: CSE '27"),
    ("Now", "Aspiring Data Engineer (Python, SQL, ETL)"),
    ("Prev", "Full-Stack Developer (MERN)"),
    ("Stack", "Python, SQL, Pandas, React, Node.js"),
    ("Highlights", "3rd @ Syntax Sprint '25  //  100+ DSA solved"),
    ("Uptime", "Building, breaking, shipping since 2022"),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(static: bool) -> str:
    parts = [
        f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect x="1" y="1" width="{WIDTH-2}" height="{HEIGHT-2}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}"/>',
        f'<rect x="1" y="1" width="{WIDTH-2}" height="30" rx="10" fill="{TITLE_BAR}"/>',
        f'<rect x="1" y="21" width="{WIDTH-2}" height="10" fill="{TITLE_BAR}"/>',
        f'<circle cx="22" cy="16" r="6" fill="{DOT_RED}"/>',
        f'<circle cx="42" cy="16" r="6" fill="{DOT_YEL}"/>',
        f'<circle cx="62" cy="16" r="6" fill="{DOT_GRN}"/>',
        f'<text x="{WIDTH/2}" y="20" text-anchor="middle" font-family="{FONT}" '
        f'font-size="12" fill="{DIM}">{USER}: neofetch</text>',
    ]

    header_y = PAD_Y + 6
    header = f"{USER}"
    parts.append(
        f'<text x="{PAD_X}" y="{header_y}" font-family="{FONT}" font-size="14.5" '
        f'font-weight="700" fill="{KEY_COLOR}">{esc(header)}</text>'
    )
    parts.append(
        f'<line x1="{PAD_X}" y1="{header_y+8}" x2="{WIDTH-PAD_X}" y2="{header_y+8}" '
        f'stroke="{BORDER}"/>'
    )

    for i, (key, val) in enumerate(ROWS):
        y = header_y + 34 + i * LINE_H
        group_attrs = ""
        anim = ""
        if not static:
            begin = 0.4 + i * 0.18
            group_attrs = f' opacity="0" transform="translate(-14,0)"'
            anim = (
                f'<animate attributeName="opacity" from="0" to="1" '
                f'begin="{begin:.2f}s" dur="0.35s" fill="freeze"/>'
                f'<animateTransform attributeName="transform" type="translate" '
                f'from="-14 0" to="0 0" begin="{begin:.2f}s" dur="0.35s" '
                f'fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
            )
        parts.append(f'<g{group_attrs}>')
        parts.append(
            f'<text x="{PAD_X}" y="{y}" font-family="{FONT}" font-size="13" '
            f'font-weight="700" fill="{KEY_COLOR}">{esc(key)}</text>'
        )
        parts.append(
            f'<text x="{PAD_X + 108}" y="{y}" font-family="{FONT}" font-size="12.5" '
            f'fill="{VAL_COLOR}">{esc(val)}</text>'
        )
        parts.append(anim)
        parts.append('</g>')

    # color swatch strip at the bottom, classic neofetch touch
    swatch_y = HEIGHT - 28
    colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353",
              "#6366f1", "#8b5cf6", "#ec4899"]
    for i, c in enumerate(colors):
        x = PAD_X + i * 24
        if not static:
            begin = 0.4 + len(ROWS) * 0.18 + 0.1
            parts.append(
                f'<rect x="{x}" y="{swatch_y}" width="18" height="18" rx="3" '
                f'fill="{c}" opacity="0">'
                f'<animate attributeName="opacity" from="0" to="1" '
                f'begin="{begin:.2f}s" dur="0.5s" fill="freeze"/></rect>'
            )
        else:
            parts.append(
                f'<rect x="{x}" y="{swatch_y}" width="18" height="18" rx="3" fill="{c}"/>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    static = os.environ.get("STATIC") == "1"
    svg = build_svg(static)
    with open("info-card.svg", "w") as f:
        f.write(svg)
    print("wrote info-card.svg")
