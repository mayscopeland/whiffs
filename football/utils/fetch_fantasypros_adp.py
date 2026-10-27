"""Fetch FantasyPros half-PPR preseason ADP.

The board is the consensus at ``/nfl/adp/half-point-ppr-overall.php``. Yahoo's
ADP is one of the sources on that page. Kickers and defenses are dropped, then
the remaining offensive players are ranked from 1.

``nfl_slug`` comes from the mayscopeland/ffb_ids crosswalk, joined on
``fantasypros_id``. A missing FantasyPros id is matched by name when that
name has one slug.

The session cookie is read from ``FANTASYPROS_COOKIE``. It is not stored in
this file. Without a logged-in session the page returns a five-player list.

Writes football/adp/fantasypros_{season}.csv. The year menu goes back to 2015.
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "utils"))
from player_ids import PlayerIds, clean_id  # noqa: E402

ADP_DIR = ROOT / "adp"
FIRST_SEASON = 2015
REQUEST_SLEEP_SECONDS = 1.0

PAGE_URL = "https://www.fantasypros.com/nfl/adp/half-point-ppr-overall.php?year={season}"

# Team defenses and kickers are not in the passing, rushing, or receiving pools.
EXCLUDED_POSITIONS = {"K", "DST", "DEF"}

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
    "Referer": "https://www.fantasypros.com/nfl/discover/more/",
    "Sec-CH-UA": '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/155.0.0.0 Safari/537.36"
    ),
}

# A logged-out response is a five-row teaser. A real board is hundreds of names.
MIN_ROWS = 50

_POSITION = re.compile(r"^([A-Z]+)")
_BYE = re.compile(r"\s*\(\d+\)\s*$")
_SLUG = re.compile(r"/players/([^/]+)\.php")


def last_published_season() -> int:
    """Latest season the ADP year menu can point at, including a season underway."""
    return date.today().year


def _report_config(html: str) -> dict:
    marker = "window.FP.reportConfig = "
    start = html.find(marker)
    if start < 0:
        raise ValueError("no ADP reportConfig")
    payload, _ = json.JSONDecoder().raw_decode(html[start + len(marker) :])
    if not isinstance(payload, dict):
        raise ValueError("ADP reportConfig was not an object")
    return payload


def _position(value: object) -> str:
    match = _POSITION.match(str(value or "").strip())
    return match.group(1) if match else ""


def _team(value: object) -> str:
    return _BYE.sub("", str(value or "")).strip()


def _slug(url: object) -> str:
    match = _SLUG.search(str(url or ""))
    return match.group(1) if match else ""


def _source_columns(fields: list) -> list[tuple[str, str]]:
    columns: list[tuple[str, str]] = []
    used: set[str] = set()
    for field in fields:
        key = str(field.get("key") or "")
        if not key.startswith("src_"):
            continue
        label = re.sub(r"[^a-z0-9]+", "", str(field.get("label") or "").lower()) or key
        name = label
        suffix = 2
        while name in used:
            name = f"{label}{suffix}"
            suffix += 1
        used.add(name)
        columns.append((key, name))
    return columns


def _page_year(config: dict) -> int | None:
    for item in config.get("filters") or []:
        if item.get("id") != "year":
            continue
        selected = str(item.get("selected") or "").lstrip("_")
        if selected.isdigit():
            return int(selected)
    match = re.search(r"(20\d{2})", str(config.get("title") or ""))
    return int(match.group(1)) if match else None


def parse_adp(html: str, season: int) -> pd.DataFrame:
    if "isLoggedIn = true" not in html:
        raise ValueError(f"{season}: session is not logged in")
    config = _report_config(html)
    page_year = _page_year(config)
    if page_year != season:
        raise ValueError(f"{season}: page is for {page_year}")
    table = config.get("table") or {}
    rows = table.get("rows") or []
    if len(rows) < MIN_ROWS:
        raise ValueError(f"{season}: ADP table has only {len(rows)} rows")

    sources = _source_columns(table.get("fields") or [])
    records = []
    for row in rows:
        player = row.get("player") or {}
        position = _position(row.get("pos"))
        if not position or position in EXCLUDED_POSITIONS:
            continue
        fantasypros_id = clean_id(row.get("id") if row.get("id") is not None else player.get("id"))
        name = str(player.get("name") or "").strip()
        if not fantasypros_id or not name:
            continue
        record = {
            "year": season,
            "overall_rank": row.get("rank"),
            "fantasypros_id": fantasypros_id,
            "player_name": name,
            "slug": _slug(player.get("url")),
            "team": _team(player.get("team")),
            "position": position,
            "avg": row.get("avg"),
        }
        for key, name_key in sources:
            record[name_key] = row.get(key)
        records.append(record)

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        raise ValueError(f"{season}: no offensive players")
    frame["overall_rank"] = pd.to_numeric(frame["overall_rank"], errors="coerce")
    frame = frame.dropna(subset=["overall_rank"]).sort_values(
        ["overall_rank", "fantasypros_id"], kind="mergesort"
    )
    frame = frame.drop_duplicates(subset=["fantasypros_id"], keep="first")
    frame.insert(1, "rank", range(1, len(frame) + 1))
    return frame.reset_index(drop=True)


def add_nfl_slugs(frame: pd.DataFrame, ids: PlayerIds) -> pd.DataFrame:
    out = frame.copy()
    out["nfl_slug"] = [
        ids.nfl_slug("fantasypros", fantasypros_id, name)
        for fantasypros_id, name in zip(out["fantasypros_id"], out["player_name"])
    ]
    ordered = [
        "year",
        "rank",
        "overall_rank",
        "fantasypros_id",
        "nfl_slug",
        "player_name",
        "slug",
        "team",
        "position",
        "avg",
    ]
    source_cols = [column for column in out.columns if column not in set(ordered)]
    # avg stays last, after the site columns, matching the page.
    ordered = [column for column in ordered if column != "avg"] + source_cols + ["avg"]
    return out[ordered]


def fetch_season(session: requests.Session, season: int) -> pd.DataFrame:
    response = session.get(PAGE_URL.format(season=season), timeout=60)
    response.raise_for_status()
    return parse_adp(response.text, season)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch FantasyPros half-PPR preseason ADP.")
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
        help="Last NFL season (default: this calendar year).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    end = last_published_season() if args.end is None else args.end
    if args.start > end:
        raise SystemExit(f"--start {args.start} is after --end {end}.")
    years = list(range(args.start, end + 1))
    ADP_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading ffb_ids...")
    ids = PlayerIds.load()
    print(f"    {len(ids.frame)} players from {ids.url}")

    cookie = os.environ.get("FANTASYPROS_COOKIE", "").strip()
    if not cookie:
        raise SystemExit(
            "Set FANTASYPROS_COOKIE to a FantasyPros session cookie. "
            "The ADP board is only a short public list without it."
        )

    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Cookie"] = cookie
    print(f"Fetching {len(years)} seasons ({years[0]} through {years[-1]})...")
    for index, season in enumerate(years):
        print(f"Fetching {season}...")
        if index:
            time.sleep(REQUEST_SLEEP_SECONDS)
        try:
            parsed = fetch_season(session, season)
        except (requests.RequestException, ValueError) as exc:
            print(f"    Skipped {season}: {exc}")
            continue
        matched = add_nfl_slugs(parsed, ids)
        out_path = ADP_DIR / f"fantasypros_{season}.csv"
        matched.to_csv(out_path, index=False)
        missing = matched["nfl_slug"].astype(str).str.strip().eq("").sum()
        counts = matched["position"].value_counts().to_dict()
        print(f"    Saved {len(matched)} offensive players ({missing} without an nfl_slug) to {out_path.name}")
        print(f"    Positions: {counts}")

    print("FantasyPros ADP fetch complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
