"""Fetch FantasyPros preseason consensus projections.

The draft board is the season-long consensus at
``/nfl/projections/{position}.php?week=draft&year={season}`` for quarterbacks,
running backs, wide receivers, and tight ends. Counting stats match the
nflverse actuals except targets, which FantasyPros does not publish, so ``TGT``
is omitted. Receptions are the ``rec_att`` column. ``nfl_slug`` comes from the
mayscopeland/ffb_ids crosswalk, joined on ``fantasypros_id``. A missing
FantasyPros id is matched by name when that name has one slug.

The session cookie is read from ``FANTASYPROS_COOKIE``. It is not stored in
this file. Without a logged-in session the page returns a short public list,
so a live season is skipped unless the response is logged in.

Seasons 2018–2022 are taken from Wayback Machine captures of the preseason
draft board. The live ``year=`` pages omit players who later left the league.
A position with no preseason capture keeps whatever is already in the saved
file. Players listed in both places keep the saved row.

Writes football/projections/fantasypros_{season}.csv. The default range starts
at 2018, the first season with actuals in this project. Earlier draft pages
are only a handful of players. The season in progress is left out.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "utils"))
from player_ids import PlayerIds, clean_id  # noqa: E402
from rates import COUNTING_COLS  # noqa: E402

PROJECTIONS_DIR = ROOT / "projections"

# 2018 is the first season with nflverse actuals here. Earlier FantasyPros
# draft pages only list a handful of players.
FIRST_SEASON = 2018

PAGE_URL = "https://www.fantasypros.com/nfl/projections/{position}.php"

HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "DNT": "1",
    "Priority": "u=0, i",
    "Sec-CH-UA": '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/155.0.0.0 Safari/537.36"
    ),
}

POSITIONS = ("qb", "rb", "wr", "te")

# FantasyPros field -> Drops counting column. rec_att is receptions.
STAT_FIELDS = {
    "pass_att": "ATT",
    "pass_cmp": "CMP",
    "pass_yds": "PASS_YDS",
    "pass_tds": "PASS_TD",
    "pass_ints": "INT",
    "rush_att": "CAR",
    "rush_yds": "RUSH_YDS",
    "rush_tds": "RUSH_TD",
    "rec_att": "REC",
    "rec_yds": "REC_YDS",
    "rec_tds": "REC_TD",
}

VALUE_COLS = [column for column in COUNTING_COLS if column != "TGT"]

# Group header + column label on the old projection table.
ARCHIVE_FIELDS = {
    ("PASSING", "ATT"): "ATT",
    ("PASSING", "CMP"): "CMP",
    ("PASSING", "YDS"): "PASS_YDS",
    ("PASSING", "TDS"): "PASS_TD",
    ("PASSING", "INTS"): "INT",
    ("RUSHING", "ATT"): "CAR",
    ("RUSHING", "YDS"): "RUSH_YDS",
    ("RUSHING", "TDS"): "RUSH_TD",
    ("RECEIVING", "REC"): "REC",
    ("RECEIVING", "YDS"): "REC_YDS",
    ("RECEIVING", "TDS"): "REC_TD",
}

# timestamp, original URL. These are season-long draft boards. Some positions
# were only crawled before projections had settled, or after the season had
# started; the weekly board is a different page and is not used here.
# 2018 has no archived RB or TE board.
ARCHIVE_CAPTURES: dict[int, dict[str, tuple[str, str]]] = {
    2018: {
        "qb": ("20180901025239", "https://www.fantasypros.com/nfl/projections/qb.php?week=draft"),
        "wr": ("20180808115212", "https://www.fantasypros.com/nfl/projections/wr.php?week=draft"),
    },
    2019: {
        "qb": ("20190902051150", "https://www.fantasypros.com/nfl/projections/qb.php?week=draft"),
        "rb": ("20190719152359", "https://www.fantasypros.com/nfl/projections/rb.php?week=draft"),
        "wr": ("20190719153515", "https://www.fantasypros.com/nfl/projections/wr.php?week=draft"),
        "te": ("20190717194456", "https://www.fantasypros.com/nfl/projections/te.php?week=draft"),
    },
    2020: {
        "qb": ("20200818160645", "https://www.fantasypros.com/nfl/projections/qb.php?week=draft"),
        "rb": ("20200811013535", "https://www.fantasypros.com/nfl/projections/rb.php?week=draft"),
        "wr": ("20201111181923", "https://www.fantasypros.com/nfl/projections/wr.php?week=draft"),
        "te": ("20200811022718", "https://www.fantasypros.com/nfl/projections/te.php?week=draft"),
    },
    2021: {
        "qb": ("20210831064359", "https://www.fantasypros.com/nfl/projections/qb.php"),
        "rb": ("20210919170754", "https://www.fantasypros.com/nfl/projections/rb.php?week=draft"),
        "wr": ("20210728120136", "https://www.fantasypros.com/nfl/projections/wr.php?week=draft"),
        "te": ("20211022105359", "https://www.fantasypros.com/nfl/projections/te.php?week=draft"),
    },
    2022: {
        "qb": ("20220905222011", "https://www.fantasypros.com/nfl/projections/qb.php"),
        "rb": ("20220526044551", "https://www.fantasypros.com/nfl/projections/rb.php?week=draft"),
        "wr": ("20220825210324", "https://www.fantasypros.com/nfl/projections/wr.php?week=draft"),
        "te": ("20220529061711", "https://www.fantasypros.com/nfl/projections/te.php?week=draft"),
    },
}

MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 5
REQUEST_SLEEP_SECONDS = 0.8
REQUEST_TIMEOUT_SECONDS = 60


def last_completed_season(today: date | None = None) -> int:
    """NFL season year that most recently finished.

    The season labeled Y runs from September Y through February Y+1.
    """
    today = today or date.today()
    if today.month >= 9:
        return today.year - 1
    if today.month <= 2:
        return today.year - 2
    return today.year - 1


def _request(session: requests.Session, position: str, season: int) -> requests.Response | None:
    url = PAGE_URL.format(position=position)
    params = {"week": "draft", "year": season}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code in {403, 429}:
                raise requests.exceptions.HTTPError(f"{response.status_code} from FantasyPros")
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException, ValueError) as exc:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)
    return None


def _report_config(html: str) -> dict | None:
    marker = "window.FP.reportConfig = "
    start = html.find(marker)
    if start < 0:
        return None
    try:
        config, _ = json.JSONDecoder().raw_decode(html, start + len(marker))
    except json.JSONDecodeError:
        return None
    if not isinstance(config, dict):
        return None
    return config


def _number(value: object) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def parse_page(html: str) -> list[dict] | None:
    """Projection rows, or None when the session is not logged in."""
    if "isLoggedIn = true" not in html:
        return None
    config = _report_config(html)
    if config is None:
        return []
    table = config.get("table") or {}
    parsed: list[dict] = []
    for row in table.get("rows") or []:
        player = row.get("player") or {}
        fantasypros_id = clean_id(row.get("id") if row.get("id") is not None else player.get("id"))
        if not fantasypros_id:
            continue
        record = {column: 0.0 for column in VALUE_COLS}
        record["fantasypros_id"] = fantasypros_id
        record["player_name"] = str(player.get("name") or "").strip()
        for field, column in STAT_FIELDS.items():
            if field in row and row[field] is not None:
                record[column] = _number(row[field])
        parsed.append(record)
    return parsed


def _merge_rows(rows: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for row in rows:
        current = merged.get(row["fantasypros_id"])
        if current is None:
            merged[row["fantasypros_id"]] = row
            continue
        for column in VALUE_COLS:
            current[column] = max(current[column], row[column])
        if not current["player_name"] and row["player_name"]:
            current["player_name"] = row["player_name"]
    return list(merged.values())


def _header_fields(table) -> list[str | None]:
    rows = table.select("tr")
    if len(rows) < 2:
        raise ValueError("projection table has no header")
    groups: list[str] = []
    for cell in rows[0].find_all(["th", "td"]):
        span = int(cell.get("colspan") or 1)
        groups.extend([cell.get_text(" ", strip=True).upper()] * span)
    labels = [cell.get_text(" ", strip=True).upper() for cell in rows[1].find_all(["th", "td"])]
    if not labels or labels[0] != "PLAYER":
        raise ValueError(f"unexpected projection header: {labels}")
    fields: list[str | None] = []
    for index, label in enumerate(labels):
        group = groups[index] if index < len(groups) else ""
        fields.append(ARCHIVE_FIELDS.get((group, label)))
    return fields


def _fantasypros_id(link) -> str:
    for class_name in link.get("class") or []:
        if class_name.startswith("fp-id-"):
            return clean_id(class_name.removeprefix("fp-id-"))
    return ""


def _cell_number(text: str) -> float:
    cleaned = text.replace(",", "").strip()
    if not cleaned:
        return 0.0
    return float(cleaned)


def parse_archive_html(html: str, season: int, source: str) -> list[dict]:
    """Season-long rows from an archived FantasyPros projection table."""
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if re.match(r"Week \d+", title):
        raise ValueError(f"{source} is a weekly board: {title}")
    if str(season) not in title:
        raise ValueError(f"{source} title is not the {season} board: {title}")
    table = soup.select_one("#data")
    if table is None:
        raise ValueError(f"{source} has no projection table")
    fields = _header_fields(table)
    parsed: list[dict] = []
    for tr in table.select("tr")[2:]:
        link = tr.select_one("a.fp-player-link")
        if link is None:
            continue
        fantasypros_id = _fantasypros_id(link)
        name = str(link.get("fp-player-name") or "").strip()
        if not fantasypros_id or not name:
            continue
        record = {column: 0.0 for column in VALUE_COLS}
        record["fantasypros_id"] = fantasypros_id
        record["player_name"] = name
        for field, cell in zip(fields, tr.find_all("td")):
            if field is None:
                continue
            record[field] = _cell_number(cell.get_text(" ", strip=True))
        parsed.append(record)
    if not parsed:
        raise ValueError(f"{source} parsed no players")
    return parsed


def _archive_html(session: requests.Session, timestamp: str, url: str) -> str:
    archived = f"https://web.archive.org/web/{timestamp}id_/{url}"
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(archived, timeout=90)
            if response.status_code in {403, 429, 503}:
                raise requests.exceptions.HTTPError(f"{response.status_code} from the Internet Archive")
            response.raise_for_status()
            return response.text
        except (requests.exceptions.RequestException, ValueError) as exc:
            last_error = exc
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)
    raise RuntimeError(f"could not download {archived}: {last_error}")


def _existing_rows(season: int) -> list[dict]:
    path = PROJECTIONS_DIR / f"fantasypros_{season}.csv"
    if not path.exists():
        return []
    frame = pd.read_csv(path)
    rows: list[dict] = []
    for record in frame.to_dict("records"):
        fantasypros_id = clean_id(record.get("fantasypros_id"))
        if not fantasypros_id:
            continue
        row = {column: 0.0 for column in VALUE_COLS}
        row["fantasypros_id"] = fantasypros_id
        row["player_name"] = str(record.get("player_name") or "").strip()
        for column in VALUE_COLS:
            row[column] = _number(record.get(column))
        rows.append(row)
    return rows


def fetch_archive_season(season: int) -> pd.DataFrame:
    """Archived draft board, with saved rows kept where the archive has no one."""
    session = requests.Session()
    session.headers["User-Agent"] = HEADERS["User-Agent"]
    rows_by_id: dict[str, dict] = {}
    for index, (position, (timestamp, url)) in enumerate(ARCHIVE_CAPTURES[season].items()):
        if index:
            time.sleep(REQUEST_SLEEP_SECONDS)
        html = _archive_html(session, timestamp, url)
        parsed = parse_archive_html(html, season, f"{season} {position}")
        print(f"    {position.upper()} archive {timestamp}: {len(parsed)} players")
        for row in parsed:
            rows_by_id[row["fantasypros_id"]] = row
    archive_ids = set(rows_by_id)
    replaced = 0
    kept = 0
    for row in _existing_rows(season):
        if row["fantasypros_id"] in archive_ids:
            replaced += 1
        else:
            kept += 1
        rows_by_id[row["fantasypros_id"]] = row
    print(f"    Saved file kept {kept} players the archive did not list and {replaced} overlapping rows")
    return pd.DataFrame(rows_by_id.values())


def fetch_season(session: requests.Session, season: int) -> pd.DataFrame | None:
    rows: list[dict] = []
    for index, position in enumerate(POSITIONS):
        if index:
            time.sleep(REQUEST_SLEEP_SECONDS)
        response = _request(session, position, season)
        if response is None:
            return None
        page_rows = parse_page(response.text)
        if page_rows is None:
            print(f"    {position.upper()}: session is not logged in")
            return None
        print(f"    {position.upper()}: {len(page_rows)} players")
        rows.extend(page_rows)
    return pd.DataFrame(_merge_rows(rows))


def season_frame(players: pd.DataFrame, ids: PlayerIds) -> pd.DataFrame:
    frame = players.copy()
    if frame.empty:
        return frame
    frame["nfl_slug"] = [
        ids.nfl_slug("fantasypros", fantasypros_id, name)
        for fantasypros_id, name in zip(frame["fantasypros_id"], frame["player_name"])
    ]
    for column in VALUE_COLS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).round(1)
    frame = frame[frame["nfl_slug"] != ""]
    frame = frame[frame[VALUE_COLS].sum(axis=1) > 0]
    ordered = ["nfl_slug", "player_name", "fantasypros_id", *VALUE_COLS]
    frame = frame[ordered]
    frame = frame.sort_values("nfl_slug", kind="mergesort")
    frame = frame.groupby("nfl_slug", as_index=False).agg(
        {column: "max" if column in VALUE_COLS else "first" for column in ordered if column != "nfl_slug"}
    )
    frame = frame[ordered]
    frame = frame.sort_values(
        ["player_name", "nfl_slug"], ascending=[True, True], kind="mergesort"
    )
    return frame.reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch FantasyPros season projections.")
    parser.add_argument(
        "--start",
        type=int,
        default=FIRST_SEASON,
        help=f"First NFL season (default: {FIRST_SEASON}).",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="Last NFL season (default: the last completed season).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    end = last_completed_season() if args.end is None else args.end
    if args.start > end:
        raise SystemExit(f"--start {args.start} is after --end {end}.")
    years = list(range(args.start, end + 1))
    needs_live = any(season not in ARCHIVE_CAPTURES for season in years)
    cookie = os.environ.get("FANTASYPROS_COOKIE", "").strip()
    if needs_live and not cookie:
        raise SystemExit(
            "Set FANTASYPROS_COOKIE to a FantasyPros session cookie. "
            "The draft board is only a short public list without it."
        )
    PROJECTIONS_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)
    if cookie:
        session.headers["Cookie"] = cookie

    print("Loading ffb_ids...")
    ids = PlayerIds.load()
    print(f"    {len(ids.frame)} players from {ids.url}")

    print(f"Fetching {len(years)} seasons ({years[0]} through {years[-1]})...")
    for index, season in enumerate(years):
        print(f"Fetching {season}...")
        if index:
            time.sleep(REQUEST_SLEEP_SECONDS)
        if season in ARCHIVE_CAPTURES:
            players = fetch_archive_season(season)
        else:
            players = fetch_season(session, season)
        if players is None:
            print(f"    Skipped {season}")
            continue
        if players.empty:
            print(f"    No projections for {season}")
            continue
        projected = players[players[VALUE_COLS].fillna(0).sum(axis=1) > 0]
        matched = season_frame(projected, ids)
        dropped_ids = set(projected["fantasypros_id"]) - set(matched["fantasypros_id"])
        out_path = PROJECTIONS_DIR / f"fantasypros_{season}.csv"
        matched.to_csv(out_path, index=False)
        print(
            f"    Saved {len(matched)} players ({len(dropped_ids)} without an nfl_slug) to {out_path.name}"
        )
        if dropped_ids:
            names = list(dict.fromkeys(projected.loc[projected["fantasypros_id"].isin(dropped_ids), "player_name"].astype(str)))
            shown = ", ".join(names[:12])
            if len(names) > 12:
                shown = f"{shown} (+{len(names) - 12} more)"
            print(f"    Unmatched: {shown}")
        print(
            f"    Max attempts {matched['ATT'].max():.0f}, "
            f"carries {matched['CAR'].max():.0f}, receptions {matched['REC'].max():.0f}"
        )

    print("FantasyPros fetch complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
