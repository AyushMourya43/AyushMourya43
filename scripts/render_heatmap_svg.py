"""
render_heatmap_svg.py — draw the real 53-week x 7-day contribution
calendar as an animated SVG: rounded boxes that slide in diagonally,
line after line, then freeze. Includes a Less->More legend and a
stats footer (current + longest streak, total contributions).

Usage:
    python scripts/render_heatmap_svg.py
"""

import json
from datetime import datetime

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
DIM = "#8b949e"
TEXT = "#c9d1d9"
ACCENT = "#6366f1"

CELL = 11
GAP = 3
LEFT_PAD = 30
TOP_PAD = 34
LEGEND_H = 18
FOOTER_H = 30

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_ROW_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}


def load_data(path: str = "data/contributions.json") -> dict:
    with open(path) as f:
        return json.load(f)


def weeks_from_days(days: list[dict]) -> list[list[dict | None]]:
    """Bucket flat day list into GitHub-style weeks (columns), each 7 rows (Sun-Sat)."""
    if not days:
        return []
    first_date = datetime.strptime(days[0]["date"], "%Y-%m-%d")
    lead_empty = (first_date.weekday() + 1) % 7  # convert Mon=0 -> Sun=0 offset

    cells: list[dict | None] = [None] * lead_empty + days
    weeks = [cells[i:i + 7] for i in range(0, len(cells), 7)]
    if weeks and len(weeks[-1]) < 7:
        weeks[-1] += [None] * (7 - len(weeks[-1]))
    return weeks


def month_ticks(weeks: list[list[dict | None]]) -> list[tuple[int, str]]:
    ticks = []
    last_month = None
    for wi, week in enumerate(weeks):
        for day in week:
            if day is None:
                continue
            m = int(day["date"][5:7])
            if m != last_month:
                ticks.append((wi, MONTH_LABELS[m - 1]))
                last_month = m
            break
    return ticks


def build_svg(data: dict) -> str:
    days = data["days"]
    stats = data["stats"]
    username = data["username"]
    weeks = weeks_from_days(days)
    n_weeks = len(weeks)

    grid_w = n_weeks * (CELL + GAP)
    width = LEFT_PAD + grid_w + 20
    height = TOP_PAD + 7 * (CELL + GAP) + LEGEND_H + FOOTER_H + 10

    parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
    parts.append(
        f'<style>.cell{{animation: cellIn .4s ease forwards; opacity:0;}}'
        f'@keyframes cellIn{{from{{opacity:0;transform:translate(-4px,-4px);}}'
        f'to{{opacity:1;transform:translate(0,0);}}}}</style>'
    )

    # month labels
    for wi, label in month_ticks(weeks):
        x = LEFT_PAD + wi * (CELL + GAP)
        parts.append(
            f'<text x="{x}" y="{TOP_PAD - 8}" font-family="Fira Code, Consolas, monospace" '
            f'font-size="10" fill="{DIM}">{label}</text>'
        )

    # day-of-week labels
    for row, label in DAY_ROW_LABELS.items():
        y = TOP_PAD + row * (CELL + GAP) + CELL - 1
        parts.append(
            f'<text x="0" y="{y}" font-family="Fira Code, Consolas, monospace" '
            f'font-size="9" fill="{DIM}">{label}</text>'
        )

    # cells — diagonal stagger: delay increases with (week + row)
    for wi, week in enumerate(weeks):
        x = LEFT_PAD + wi * (CELL + GAP)
        for row, day in enumerate(week):
            y = TOP_PAD + row * (CELL + GAP)
            if day is None:
                continue
            level = min(day["level"], len(PALETTE) - 1)
            color = PALETTE[level]
            delay = 0.15 + (wi + row) * 0.012
            title = f'{day["count"]} contributions on {day["date"]}'
            parts.append(
                f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2.5" fill="{color}" style="animation-delay:{delay:.2f}s">'
                f'<title>{title}</title></rect>'
            )

    legend_y = TOP_PAD + 7 * (CELL + GAP) + 14
    parts.append(
        f'<text x="{LEFT_PAD}" y="{legend_y+8}" font-family="Fira Code, Consolas, monospace" '
        f'font-size="10" fill="{DIM}">Less</text>'
    )
    lx = LEFT_PAD + 34
    for i, c in enumerate(PALETTE):
        parts.append(f'<rect x="{lx + i*15}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{c}"/>')
    parts.append(
        f'<text x="{lx + len(PALETTE)*15 + 6}" y="{legend_y+8}" '
        f'font-family="Fira Code, Consolas, monospace" font-size="10" fill="{DIM}">More</text>'
    )

    footer_y = legend_y + 34
    footer_text = (
        f'{stats["total"]} contributions in the last year  //  '
        f'current streak {stats["current_streak"]}d  //  longest {stats["longest_streak"]}d'
    )
    parts.append(
        f'<text x="{LEFT_PAD}" y="{footer_y}" font-family="Fira Code, Consolas, monospace" '
        f'font-size="11.5" fill="{ACCENT}" font-weight="700">{footer_text}</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    data = load_data()
    svg = build_svg(data)
    with open("contrib-heatmap.svg", "w") as f:
        f.write(svg)
    print("wrote contrib-heatmap.svg")
