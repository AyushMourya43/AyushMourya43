"""
fetch_contributions.py — pull the real contribution calendar for a
GitHub user with no token and no GraphQL API. GitHub serves the
calendar as public HTML at /users/<username>/contributions (the same
fragment the profile page itself loads).

Usage:
    python scripts/fetch_contributions.py [username]

Writes data/contributions.json with:
  - raw per-day counts/levels
  - derived stats: current streak, longest streak, best day, total
"""

import sys
import json
import os
from datetime import datetime, date, timezone
import requests
from bs4 import BeautifulSoup

DEFAULT_USERNAME = "AyushMourya43"
URL_TMPL = "https://github.com/users/{username}/contributions"


def fetch_days(username: str) -> list[dict]:
    resp = requests.get(
        URL_TMPL.format(username=username),
        headers={"User-Agent": "Mozilla/5.0 (profile-readme-bot)"},
        timeout=20,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cells = soup.select("table.ContributionCalendar-grid td.ContributionCalendar-day")
    if not cells:
        # GitHub markup fallback: newer markup uses <td> with data-date directly
        cells = soup.select("td[data-date]")

    days = []
    for cell in cells:
        d = cell.get("data-date")
        if not d:
            continue
        level = cell.get("data-level")
        count_attr = cell.get("data-count")
        if count_attr is not None:
            count = int(count_attr)
        else:
            tooltip_id = cell.get("id")
            count = 0
            if tooltip_id:
                tt = soup.find("tool-tip", attrs={"for": tooltip_id})
                if tt and tt.text:
                    first_word = tt.text.strip().split()[0]
                    count = 0 if first_word.lower() == "no" else int(first_word)
        days.append({
            "date": d,
            "count": count,
            "level": int(level) if level is not None else (0 if count == 0 else 1),
        })

    days.sort(key=lambda x: x["date"])
    return days


def derive_stats(days: list[dict]) -> dict:
    total = sum(d["count"] for d in days)

    # streaks (consecutive days with count > 0)
    longest = current = 0
    running = 0
    today_str = date.today().isoformat()
    for d in days:
        if d["count"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    # current streak: walk backwards from the most recent day
    for d in reversed(days):
        if d["date"] > today_str:
            continue
        if d["count"] > 0:
            current += 1
        else:
            break

    best_day = max(days, key=lambda d: d["count"], default=None)

    by_month: dict[str, int] = {}
    for d in days:
        month = d["date"][:7]
        by_month[month] = by_month.get(month, 0) + d["count"]

    return {
        "total": total,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best_day,
        "by_month": by_month,
    }


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USERNAME
    days = fetch_days(username)
    stats = derive_stats(days)

    os.makedirs("data", exist_ok=True)
    payload = {
        "username": username,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "stats": stats,
    }
    with open("data/contributions.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"wrote data/contributions.json — {stats['total']} contributions, "
          f"streak {stats['current_streak']} (longest {stats['longest_streak']})")
