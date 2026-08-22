#!/usr/bin/env python3
"""Render the four stat cards from synthetic data, to check layout offline.

Dev-only. Never run in CI -- generate_stats.py is the real thing.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_stats as g

CREATED = date(2023, 8, 17)


def fake():
    days, d = {}, CREATED
    while d <= g.TODAY:
        seed = (d.toordinal() * 2654435761) % 1000
        recent = d >= g.TODAY - timedelta(days=200)
        n = 0
        if seed > (300 if recent else 620):
            n = 1 + seed % (17 if recent else 6)
        if d.weekday() == 6 and seed % 7 == 0:
            n = 0
        days[d.isoformat()] = n
        d += timedelta(days=1)
    window = {k: v for k, v in days.items() if date.fromisoformat(k) >= g.FROM}
    langs = [("Python", 812_000, 11), ("TypeScript", 431_000, 7), ("JavaScript", 220_000, 6),
             ("SQL", 96_000, 4), ("HTML", 61_000, 5), ("CSS", 44_000, 4), ("Shell", 9_000, 2)]
    repos = [{"name": f"repo{i}", "stargazerCount": 0, "forkCount": 0, "isArchived": False,
              "languages": {"edges": []}} for i in range(23)]
    for i, (name, size, count) in enumerate(langs):
        for j in range(count):
            repos[j]["languages"]["edges"].append({"size": size // count,
                                                   "node": {"name": name}})
    return {
        "profile": {"login": "AyushMourya43", "name": "Ayush", "followers": {"totalCount": 12}},
        "created": CREATED,
        "year": {"totalCommitContributions": sum(window.values()) - 90,
                 "totalPullRequestContributions": 41,
                 "totalIssueContributions": 18,
                 "totalPullRequestReviewContributions": 9,
                 "contributionCalendar": {"totalContributions": sum(window.values()),
                                          "weeks": []}},
        "days": window,
        "history": days,
        "repos": repos,
    }


if __name__ == "__main__":
    g.render(fake())
