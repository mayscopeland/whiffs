"""Fetch FFToday preseason projections.

FFToday keeps a regular-season projection board for quarterbacks, running
backs, wide receivers, and tight ends. The pages checked here run from 2014
through the last completed season, stamped at the start of that season.
Counting stats are passing, rushing, and receptions. FFToday does not publish
targets, so ``TGT`` is omitted rather than stored as zero. ``nfl_slug`` comes
from the mayscopeland/ffb_ids crosswalk, joined on ``fftoday_id``. A missing
FFToday id is matched by name when that name has one slug.

Writes football/projections/fftoday_{season}.csv. The season in progress is
left out.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "utils"))
from player_ids import PlayerIds  # noqa: E402
from rates import COUNTING_COLS  # noqa: E402

PROJECTIONS_DIR = ROOT / "projections"

# 2014 is the earliest board that still renders a full preseason line.
FIRST_SEASON = 2014

PAGE_URL = "https://www.fftoday.com/rankings/playerproj.php"

HEADERS = {
    "Accept": "text/html",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
}

# PosID values from the projection-page position links.
POSITIONS = (("QB", 10), ("RB", 20), ("WR", 30), ("TE", 40))

GROUP_STATS = {
    ("PASSING", "CMP"): "CMP",
    ("PASSING", "ATT"): "ATT",
    ("PASSING", "YDS"): "PASS_YDS",
    ("PASSING", "TD"): "PASS_TD",
    ("PASSING", "INT"): "INT",
    ("RUSHING", "ATT"): "CAR",
    ("RUSHING", "YDS"): "RUSH_YDS",
    ("RUSHING", "TD"): "RUSH_TD",
    ("RECEIVING", "REC"): "REC",
    ("RECEIVING", "YDS"): "REC_YDS",
    ("RECEIVING", "TD"): "REC_TD",
}

PLAYER_ID_RE = re.compile(r"/stats/players/(\d+)/")
MAX_PAGES = 15
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 8
REQUEST_SLEEP_SECONDS = 1.5
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


def _request(session: requests.Session, params: dict) -> requests.Response | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(PAGE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code in {403, 429}:
                raise requests.exceptions.HTTPError(f"{response.status_code} from FFToday")
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException, ValueError) as exc:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)
    return None


def _direct_rows(table) -> list:
    rows = table.find_all("tr", recursive=False)
    if rows:
        return rows
    body = table.find("tbody", recursive=False)
    if body is None:
        return []
    return body.find_all("tr", recursive=False)


def _stat_rows(soup: BeautifulSoup) -> list:
    for table in soup.find_all("table"):
        rows = _direct_rows(table)
        for row in rows:
            cells = row.find_all(["td", "th"], recursive=False)
            if cells and cells[0].get_text(strip=True) == "Chg":
                return rows
    return []


def _column_index(rows: list) -> dict[int, str]:
    header_at = None
    for index, row in enumerate(rows):
        cells = row.find_all(["td", "th"], recursive=False)
        if cells and cells[0].get_text(strip=True) == "Chg":
            header_at = index
            break
    if header_at is None or header_at == 0:
        return {}
    groups: list[str] = []
    for cell in rows[header_at - 1].find_all(["td", "th"], recursive=False):
        label = cell.get_text(strip=True).upper()
        span = int(cell.get("colspan") or 1)
        groups.extend([label] * span)
    headers = [
        cell.get_text(" ", strip=True).upper()
        for cell in rows[header_at].find_all(["td", "th"], recursive=False)
    ]
    mapping: dict[int, str] = {}
    for index, header in enumerate(headers):
        group = groups[index] if index < len(groups) else ""
        column = GROUP_STATS.get((group, header))
        if column:
            mapping[index] = column
    return mapping


def _parse_number(text: str) -> float:
    cleaned = text.replace(",", "").strip()
    if cleaned in {"", "-"}:
        return 0.0
    return float(cleaned)


def _last_page(soup: BeautifulSoup) -> int:
    last = 0
    for anchor in soup.find_all("a"):
        if anchor.get_text(strip=True) not in {"Next Page", "Last Page"}:
            continue
        href = anchor.get("href") or ""
        query = parse_qs(href.split("?", 1)[-1])
        if "cur_page" in query:
            last = max(last, int(query["cur_page"][0]))
    return last


def parse_page(html: str) -> tuple[list[dict], int]:
    soup = BeautifulSoup(html, "lxml")
    rows = _stat_rows(soup)
    columns = _column_index(rows)
    parsed: list[dict] = []
    if not columns:
        return parsed, _last_page(soup)
    for row in rows:
        cells = row.find_all(["td", "th"], recursive=False)
        link = row.find("a", href=PLAYER_ID_RE)
        if link is None:
            continue
        match = PLAYER_ID_RE.search(link.get("href") or "")
        if match is None:
            continue
        record = {column: 0.0 for column in COUNTING_COLS if column != "TGT"}
        record["fftoday_id"] = match.group(1)
        record["player_name"] = link.get_text(" ", strip=True)
        for index, column in columns.items():
            if index >= len(cells):
                continue
            record[column] = _parse_number(cells[index].get_text(" ", strip=True))
        parsed.append(record)
    return parsed, _last_page(soup)


def fetch_position(session: requests.Session, season: int, pos_id: int) -> list[dict] | None:
    rows: list[dict] = []
    seen: set[str] = set()
    page = 0
    while page < MAX_PAGES:
        params = {"Season": season, "PosID": pos_id, "LeagueID": 1}
        if page:
            params["cur_page"] = page
        response = _request(session, params)
        if response is None:
            return None
        page_rows, last_page = parse_page(response.text)
        added = 0
        for row in page_rows:
            if row["fftoday_id"] in seen:
                continue
            seen.add(row["fftoday_id"])
            rows.append(row)
            added += 1
        if added == 0 or page >= last_page:
            break
        page += 1
        time.sleep(REQUEST_SLEEP_SECONDS)
    return rows


def _merge_rows(rows: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    value_cols = [column for column in COUNTING_COLS if column != "TGT"]
    for row in rows:
        current = merged.get(row["fftoday_id"])
        if current is None:
            merged[row["fftoday_id"]] = row
            continue
        for column in value_cols:
            current[column] = max(current[column], row[column])
    return list(merged.values())


def fetch_season(session: requests.Session, season: int) -> pd.DataFrame | None:
    rows: list[dict] = []
    for index, (name, pos_id) in enumerate(POSITIONS):
        if index:
            time.sleep(REQUEST_SLEEP_SECONDS)
        position_rows = fetch_position(session, season, pos_id)
        if position_rows is None:
            return None
        print(f"    {name}: {len(position_rows)} players")
        rows.extend(position_rows)
    return pd.DataFrame(_merge_rows(rows))


def season_frame(players: pd.DataFrame, ids: PlayerIds) -> pd.DataFrame:
    frame = players.copy()
    if frame.empty:
        return frame
    frame["nfl_slug"] = [
        ids.nfl_slug("fftoday", fftoday_id, name)
        for fftoday_id, name in zip(frame["fftoday_id"], frame["player_name"])
    ]
    value_cols = [column for column in COUNTING_COLS if column != "TGT" and column in frame.columns]
    for column in value_cols:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).round(1)
    frame = frame[frame["nfl_slug"] != ""]
    frame = frame[frame[value_cols].sum(axis=1) > 0]
    ordered = ["nfl_slug", "player_name", "fftoday_id", *value_cols]
    frame = frame[ordered]
    frame = frame.sort_values("nfl_slug", kind="mergesort")
    frame = frame.groupby("nfl_slug", as_index=False).agg(
        {column: "max" if column in value_cols else "first" for column in ordered if column != "nfl_slug"}
    )
    frame = frame[ordered]
    frame = frame.sort_values(
        ["player_name", "nfl_slug"], ascending=[True, True], kind="mergesort"
    )
    return frame.reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch FFToday season projections.")
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
    PROJECTIONS_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    print("Loading ffb_ids...")
    ids = PlayerIds.load()
    print(f"    {len(ids.frame)} players from {ids.url}")

    years = list(range(args.start, end + 1))
    print(f"Fetching {len(years)} seasons ({years[0]} through {years[-1]})...")
    for index, season in enumerate(years):
        print(f"Fetching {season}...")
        if index:
            time.sleep(REQUEST_SLEEP_SECONDS)
        players = fetch_season(session, season)
        if players is None:
            print(f"    Skipped {season}")
            continue
        if players.empty:
            print(f"    No projections for {season}")
            continue
        matched = season_frame(players, ids)
        dropped = players["fftoday_id"].nunique() - matched["fftoday_id"].nunique()
        out_path = PROJECTIONS_DIR / f"fftoday_{season}.csv"
        matched.to_csv(out_path, index=False)
        print(
            f"    Saved {len(matched)} players ({dropped} without an nfl_slug) to {out_path.name}"
        )
        print(
            f"    Max attempts {matched['ATT'].max():.0f}, "
            f"carries {matched['CAR'].max():.0f}, receptions {matched['REC'].max():.0f}"
        )

    print("FFToday fetch complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
