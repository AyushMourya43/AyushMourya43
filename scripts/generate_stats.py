#!/usr/bin/env python3
"""Draw stats.svg, streak.svg, langs.svg and year.svg from the GraphQL API.

Standard library only -- nothing to install in CI, nothing to break.
Needs GITHUB_TOKEN (the workflow's built-in one is enough) and GH_LOGIN.
"""
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svgkit as k

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com/graphql"
RAMP = " .`:-=+*cs#%@"          # the portrait's ramp, reused one character per day
WINDOW = 365

# --- the window ------------------------------------------------------------
# Pinned to whole UTC days. Left to its own devices contributionsCollection
# measures "the past year" from the instant of the request, so two runs minutes
# apart bucket days into different weeks and the sparkline shifts by a fraction
# of a pixel -- enough to produce a commit every night that means nothing.
TODAY = datetime.now(timezone.utc).date()
FROM = TODAY - timedelta(days=WINDOW - 1)


def day_start(d: date) -> str:
    return f"{d.isoformat()}T00:00:00Z"


def day_end(d: date) -> str:
    return f"{d.isoformat()}T23:59:59Z"


# --- api -------------------------------------------------------------------
CALENDAR_Q = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount } }
      }
    }
  }
}"""

PROFILE_Q = """
query($login:String!){
  user(login:$login){ login name createdAt followers{ totalCount } }
}"""

# privacy:PUBLIC matters. A personal token sees private repositories and the
# workflow's token does not, so without it the language split depends on who ran it.
REPOS_Q = """
query($login:String!,$cursor:String){
  user(login:$login){
    repositories(first:100, after:$cursor, isFork:false, privacy:PUBLIC,
                 ownerAffiliations:OWNER, orderBy:{field:STARGAZERS,direction:DESC}){
      totalCount
      pageInfo{ hasNextPage endCursor }
      nodes{
        name stargazerCount forkCount isArchived
        languages(first:12, orderBy:{field:SIZE,direction:DESC}){
          edges{ size node{ name } }
        }
      }
    }
  }
}"""


def gql(query: str, variables: dict, token: str) -> dict:
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"GraphQL HTTP {e.code}: {e.read().decode()[:400]}")
    if payload.get("errors"):
        raise SystemExit("GraphQL: " + json.dumps(payload["errors"])[:400])
    return payload["data"]


def calendar(login: str, token: str, start: date, end: date) -> dict:
    return gql(CALENDAR_Q, {"login": login, "from": day_start(start),
                            "to": day_end(end)}, token)["user"]["contributionsCollection"]


def collect(login: str, token: str) -> dict:
    profile = gql(PROFILE_Q, {"login": login}, token)["user"]
    created = datetime.fromisoformat(profile["createdAt"].replace("Z", "+00:00")).date()

    year = calendar(login, token, FROM, TODAY)
    days = {}
    for week in year["contributionCalendar"]["weeks"]:
        for d in week["contributionDays"]:
            days[d["date"]] = d["contributionCount"]

    # contributionsCollection covers at most one year per call, so walk the
    # account's whole life in year-long slices to get an honest longest streak
    history = dict(days)
    cursor = created
    while cursor < FROM:
        end = min(cursor + timedelta(days=WINDOW - 1), FROM - timedelta(days=1))
        for week in calendar(login, token, cursor, end)["contributionCalendar"]["weeks"]:
            for d in week["contributionDays"]:
                history.setdefault(d["date"], d["contributionCount"])
        cursor = end + timedelta(days=1)

    repos, cursor = [], None
    while True:
        page = gql(REPOS_Q, {"login": login, "cursor": cursor}, token)["user"]["repositories"]
        repos.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    return {"profile": profile, "created": created, "year": year,
            "days": days, "history": history, "repos": repos}


# --- derived numbers -------------------------------------------------------
def streaks(history: dict) -> dict:
    ordered = sorted(history)
    best = {"length": 0, "start": None, "end": None}
    run, run_start = 0, None
    for d in ordered:
        if history[d] > 0:
            run += 1
            run_start = run_start or d
            if run > best["length"]:
                best = {"length": run, "start": run_start, "end": d}
        else:
            run, run_start = 0, None

    # a day with nothing on it yet is not a broken streak, it is an unfinished one
    cur, day = 0, TODAY
    if history.get(TODAY.isoformat(), 0) == 0:
        day -= timedelta(days=1)
    end = day
    while history.get(day.isoformat(), 0) > 0:
        cur += 1
        day -= timedelta(days=1)
    current = {"length": cur, "start": day + timedelta(days=1) if cur else None,
               "end": end if cur else None}
    return {"current": current, "longest": best}


def weekly(days: dict) -> list:
    """52 buckets of seven whole days, oldest first, ending today."""
    out = []
    for w in range(52):
        end = TODAY - timedelta(days=7 * (51 - w))
        out.append(sum(days.get((end - timedelta(days=i)).isoformat(), 0) for i in range(7)))
    return out


def languages(repos: list) -> list:
    by_bytes, by_repo = {}, {}
    for r in repos:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            by_bytes[name] = by_bytes.get(name, 0) + e["size"]
            by_repo[name] = by_repo.get(name, 0) + 1
    total = sum(by_bytes.values()) or 1
    ranked = sorted(by_bytes, key=lambda n: -by_bytes[n])
    return [{"name": n, "bytes": by_bytes[n], "share": by_bytes[n] / total,
             "repos": by_repo[n]} for n in ranked]


# --- drawing helpers -------------------------------------------------------
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]


def text(x, y, s, size=13, fill=None, weight=400, anchor="start",
         opacity=None, spacing=None):
    a = [f'x="{x}"', f'y="{y}"', f'font-size="{size}"',
         f'fill="{fill or k.INK}"', f'font-weight="{weight}"']
    if anchor != "start":
        a.append(f'text-anchor="{anchor}"')
    if opacity is not None:
        a.append(f'fill-opacity="{opacity}"')
    if spacing:
        a.append(f'letter-spacing="{spacing}"')
    return f"<text {' '.join(a)}>{k.esc(s)}</text>"


def label(x, y, s):
    return text(x, y, s, size=11, fill=k.MUTED, spacing="0.09em")


def rule(x1, y1, x2, y2, colour=None, opacity=0.28, width=1):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{colour or k.MUTED}" stroke-opacity="{opacity}" '
            f'stroke-width="{width}"/>')


CARD_STYLE = (k.face("mono-regular.woff2", 400) + k.face("mono-bold.woff2", 700)
              + f"text{{{k.stack()}}}")


def fmt(n: int) -> str:
    return f"{n:,}"


def pretty(d) -> str:
    if not d:
        return "--"
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return f"{d.day} {MONTHS[d.month - 1]} {str(d.year)[2:]}"


# --- stats.svg -------------------------------------------------------------
def draw_stats(data: dict) -> str:
    W, H = 700, 300
    c = data["year"]
    cal = c["contributionCalendar"]
    series = weekly(data["days"])
    peak = max(series) or 1

    x0, x1 = 24, 676
    top, base = 176, 262
    step = (x1 - x0) / (len(series) - 1)
    pts = [(round(x0 + i * step, 2),
            round(base - (v / peak) * (base - top), 2)) for i, v in enumerate(series)]
    line = " ".join(f"{x},{y}" for x, y in pts)
    area = f"{x0},{base} {line} {x1},{base}"

    peak_i = series.index(peak)
    px, py = pts[peak_i]

    body = [
        label(x0, 34, "contributions · last 365 days"),
        text(x0, 100, fmt(cal["totalContributions"]), size=58,
             fill=k.STRONG, weight=700),
        rule(x0, 122, x1, 122),
    ]

    cells = [("commits", c["totalCommitContributions"]),
             ("pull requests", c["totalPullRequestContributions"]),
             ("issues", c["totalIssueContributions"]),
             ("reviews", c["totalPullRequestReviewContributions"])]
    for i, (name, value) in enumerate(cells):
        cx = x0 + i * 163
        body.append(text(cx, 148, fmt(value), size=20, fill=k.INK, weight=700))
        body.append(label(cx, 166, name))

    body += [
        label(x0, 200, f"by week · peak {peak}"),
        f'<polygon points="{area}" fill="{k.BLUE}" fill-opacity="0.16"/>',
        f'<polyline points="{line}" fill="none" stroke="{k.BLUE}" '
        f'stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>',
        rule(x0, base, x1, base, opacity=0.35),
        f'<circle cx="{px}" cy="{py}" r="2.6" fill="{k.BLUE}"/>',
        text(x0, 282, pretty(FROM), size=10.5, fill=k.MUTED),
        text(x1, 282, pretty(TODAY), size=10.5, fill=k.MUTED, anchor="end"),
    ]
    return k.svg(W, H, "".join(body), CARD_STYLE,
                 f"{cal['totalContributions']} contributions in the last 365 days, "
                 f"weekly sparkline peaking at {peak}")


# --- streak.svg ------------------------------------------------------------
def draw_streak(data: dict) -> str:
    W, H = 700, 220
    s = streaks(data["history"])
    active = sum(1 for v in data["days"].values() if v > 0)
    pct = round(100 * active / WINDOW)

    def plural(n):
        return "day" if n == 1 else "days"

    cols = [
        ("current streak", s["current"]["length"], plural(s["current"]["length"]),
         f"{pretty(s['current']['start'])} → {pretty(s['current']['end'])}"
         if s["current"]["length"] else "no run in progress"),
        ("longest streak", s["longest"]["length"], plural(s["longest"]["length"]),
         f"{pretty(s['longest']['start'])} → {pretty(s['longest']['end'])}"
         if s["longest"]["length"] else "--"),
        ("days with a commit", active, f"of {WINDOW}", f"{pct}% of the year"),
    ]

    body = [label(24, 34, "streaks · since " + pretty(data["created"]))]
    for i, (name, value, unit, sub) in enumerate(cols):
        x = 24 + i * 226
        if i:
            body.append(rule(x - 26, 56, x - 26, 190, opacity=0.22))
        body.append(label(x, 76, name))
        body.append(text(x, 132, fmt(value), size=46, fill=k.STRONG, weight=700))
        body.append(text(x + 11 + len(fmt(value)) * 46 * k.ADVANCE, 132, unit,
                         size=12, fill=k.MUTED))
        body.append(text(x, 162, sub, size=11.5, fill=k.MUTED))
    return k.svg(W, H, "".join(body), CARD_STYLE,
                 f"current streak {s['current']['length']} days, "
                 f"longest {s['longest']['length']} days, "
                 f"{active} active days of {WINDOW}")


# --- langs.svg -------------------------------------------------------------
FILLS = [(k.BLUE, 1.0), (k.GREEN, 1.0), (k.VIOLET, 1.0),
         (k.BLUE, 0.55), (k.GREEN, 0.55), (k.VIOLET, 0.55)]


def draw_langs(data: dict) -> str:
    W, H = 700, 300
    ranked = languages(data["repos"])
    shown = ranked[:6]
    rest = sum(l["share"] for l in ranked[6:])
    x0, x1 = 24, 676

    body = [label(x0, 34, f"languages · {len(data['repos'])} public repos")]

    # one stacked bar for the whole byte split, then the same order as rows
    x = x0
    for (colour, op), lang in zip(FILLS, shown):
        w = (x1 - x0) * lang["share"]
        body.append(f'<rect x="{round(x, 2)}" y="52" width="{round(w, 2)}" height="10" '
                    f'fill="{colour}" fill-opacity="{op}"/>')
        x += w
    if rest > 0.001:
        body.append(f'<rect x="{round(x, 2)}" y="52" width="{round(x1 - x, 2)}" '
                    f'height="10" fill="{k.MUTED}" fill-opacity="0.3"/>')

    widest = shown[0]["share"] if shown else 1
    for i, lang in enumerate(shown):
        (colour, op) = FILLS[i]
        y = 100 + i * 30
        bar = 300 * (lang["share"] / widest)
        body += [
            f'<rect x="{x0}" y="{y - 9}" width="9" height="9" fill="{colour}" '
            f'fill-opacity="{op}"/>',
            text(x0 + 18, y, lang["name"], size=13, fill=k.INK),
            text(200, y, f"{lang['repos']} repo" + ("s" if lang["repos"] != 1 else ""),
                 size=11.5, fill=k.MUTED),
            f'<rect x="290" y="{y - 8}" width="{round(bar, 2)}" height="8" '
            f'fill="{colour}" fill-opacity="{op * 0.75}"/>',
            text(x1, y, f"{lang['share'] * 100:.1f}%", size=13,
                 fill=k.STRONG, weight=700, anchor="end"),
        ]

    tail = f"{len(ranked) - len(shown)} more" if len(ranked) > len(shown) else "everything"
    body.append(text(x0, 282, f"measured by bytes of source · {tail} below the cut",
                     size=10.5, fill=k.MUTED))
    return k.svg(W, H, "".join(body), CARD_STYLE,
                 "top languages by share of bytes: "
                 + ", ".join(f"{l['name']} {l['share'] * 100:.0f}%" for l in shown))


# --- year.svg --------------------------------------------------------------
FS = 12.9
CH = FS * k.ADVANCE
LH = CH / 0.48


def levels(days: dict) -> dict:
    """Quantile buckets, so a quiet year still uses the whole ramp."""
    counts = sorted(v for v in days.values() if v > 0)
    if not counts:
        return {}
    edges = [counts[min(len(counts) - 1, int(len(counts) * i / (len(RAMP) - 1)))]
             for i in range(1, len(RAMP) - 1)]
    out = {}
    for d, v in days.items():
        if v <= 0:
            out[d] = 0
            continue
        level = 1
        for e in edges:
            if v > e:
                level += 1
        out[d] = min(level, len(RAMP) - 1)
    return out


def draw_year(data: dict) -> str:
    lv = levels(data["days"])
    start = FROM - timedelta(days=(FROM.weekday() + 1) % 7)   # back to a Sunday
    weeks = (TODAY - start).days // 7 + 1
    gut, pad_top = 34, 30
    W = round(gut + weeks * CH + 12, 2)
    H = round(pad_top + 7 * LH + 34, 2)

    rows = [[" "] * weeks for _ in range(7)]
    for w in range(weeks):
        for r in range(7):
            d = start + timedelta(days=w * 7 + r)
            if FROM <= d <= TODAY:
                rows[r][w] = RAMP[lv.get(d.isoformat(), 0)]

    style = (k.face("mono-regular.woff2", 400)
             + f"text{{{k.stack()}font-size:{FS}px;fill:{k.INK};"
               "white-space:pre;font-kerning:none;}"
             # a <style> rule beats a presentation attribute, so every size
             # that is not FS has to be a class, not a font-size=" " on the tag
             + f".m{{font-size:10.5px;fill:{k.MUTED};}}"
             + ".lg{font-size:11.5px;letter-spacing:0.06em;}")

    body = []
    seen = None
    for w in range(weeks):
        d = start + timedelta(days=w * 7)
        # label a month only where it actually starts, so a part-month at
        # either end does not collide with its neighbour
        if d.month != seen and d.day <= 7 and d >= FROM and w < weeks - 2:
            body.append(f'<text class="m" x="{round(gut + w * CH, 2)}" y="16">'
                        f"{MONTHS[d.month - 1]}</text>")
            seen = d.month

    for r, row in enumerate(rows):
        y = round(pad_top + r * LH + LH * 0.78, 2)
        if r in (1, 3, 5):
            body.append(f'<text class="m" x="0" y="{y}">'
                        f'{["sun", "mon", "tue", "wed", "thu", "fri", "sat"][r]}</text>')
        body.append(f'<text x="{gut}" y="{y}" xml:space="preserve" '
                    f'textLength="{round(weeks * CH, 2)}" lengthAdjust="spacing">'
                    f"{k.esc(''.join(row))}</text>")

    legend_y = round(pad_top + 7 * LH + 22, 2)
    ramp_x = round(gut + len("quiet") * 10.5 * k.ADVANCE + 12, 2)
    ramp_w = len(RAMP.strip()) * 11.5 * (k.ADVANCE + 0.06)
    body += [
        f'<text class="m" x="{gut}" y="{legend_y}">quiet</text>',
        f'<text class="lg" x="{ramp_x}" y="{legend_y}" xml:space="preserve">'
        f"{k.esc(RAMP.strip())}</text>",
        f'<text class="m" x="{round(ramp_x + ramp_w * 1.06 + 12, 2)}" '
        f'y="{legend_y}">busy</text>',
    ]
    total = sum(data["days"].values())
    return k.svg(W, H, "".join(body), style,
                 f"one character per day for the last 365 days, {total} contributions")


# --- entry point -----------------------------------------------------------
def render(data: dict) -> None:
    k.write(ROOT / "stats.svg", draw_stats(data))
    k.write(ROOT / "streak.svg", draw_streak(data))
    k.write(ROOT / "langs.svg", draw_langs(data))
    k.write(ROOT / "year.svg", draw_year(data))


def main():
    token = os.environ.get("GITHUB_TOKEN")
    login = os.environ.get("GH_LOGIN")
    if not token or not login:
        raise SystemExit("set GITHUB_TOKEN and GH_LOGIN")
    render(collect(login, token))


if __name__ == "__main__":
    main()
