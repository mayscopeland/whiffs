"""Fetch historical DARKO season boards from darko.app.

Each ``season`` value is the NBA end year (2024 is 2023-24). The site lists
full player boards from 1997 through the current season. Those boards are the
season projection tables (for 2023-24 the numbers match opening night, not the
end-of-season rating). A dated ``asof`` snapshot is a different query and only
includes players active that day, so this script does not use it.

Writes basketball/projections/darko_YYYY-YY.csv.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
PROJECTIONS_DIR = ROOT / "projections"

DATA_URL = "https://www.darko.app/__data.json"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Referer": "https://www.darko.app/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
}

# API field -> CSV column. Unlisted fields are kept under their API name.
RENAME = {
    "nba_id": "player_id",
    "tm_id": "team_id",
    "_rank": "rank",
}

COLUMN_ORDER = [
    "player_id",
    "player_name",
    "team_id",
    "team_name",
    "position",
    "age",
    "season",
    "rookie_season",
    "career_game_num",
    "dpm",
    "o_dpm",
    "d_dpm",
    "box_dpm",
    "on_off_dpm",
    "x_minutes",
    "x_pace",
    "x_pts_100",
    "x_ast_100",
    "x_fg_pct",
    "x_fg3_pct",
    "x_ft_pct",
    "sal_market_fixed",
    "actual_salary",
    "surplus_value",
    "rank",
]

INT_COLUMNS = [
    "player_id",
    "team_id",
    "season",
    "rookie_season",
    "career_game_num",
    "rank",
]

MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3
REQUEST_SLEEP_SECONDS = 0.4
REQUEST_TIMEOUT_SECONDS = 90


def end_year_to_season(end_year: int) -> str:
    """Convert season end year (2024) to NBA label (2023-24)."""
    start = end_year - 1
    return f"{start}-{str(end_year)[-2:]}"


def _resolve(data: list[Any], idx: Any, seen: set[int] | None = None) -> Any:
    """Expand a SvelteKit devalue payload. Integers inside containers are indexes."""
    if seen is None:
        seen = set()
    if not isinstance(idx, int) or isinstance(idx, bool) or idx < 0 or idx >= len(data):
        return idx
    if idx in seen:
        return None
    value = data[idx]
    if isinstance(value, (str, int, float)) or value is None or isinstance(value, bool):
        return value
    seen = seen | {idx}
    if isinstance(value, list):
        return [_resolve(data, item, seen) for item in value]
    if isinstance(value, dict):
        return {key: _resolve(data, item, seen) for key, item in value.items()}
    return value


def _request_data(session: requests.Session, season: int | None) -> list[Any] | None:
    params: dict[str, str] = {}
    if season is not None:
        params["season"] = str(season)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                DATA_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            nodes = response.json().get("nodes") or []
            for node in nodes:
                if isinstance(node, dict) and node.get("type") == "data":
                    data = node.get("data")
                    if isinstance(data, list):
                        return data
            print(f"    No data node for season={season}")
            return None
        except (requests.exceptions.RequestException, ValueError) as exc:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)
    return None


def fetch_board(session: requests.Session, season: int | None) -> dict[str, Any] | None:
    data = _request_data(session, season)
    if data is None:
        return None
    root = _resolve(data, 0)
    if not isinstance(root, dict) or "players" not in root:
        print(f"    Unexpected payload for season={season}")
        return None
    return root


def available_seasons(root: dict[str, Any]) -> list[int]:
    seasons = root.get("seasons") or []
    years = []
    for season in seasons:
        try:
            years.append(int(season))
        except (TypeError, ValueError):
            continue
    return sorted(set(years))


def board_to_frame(root: dict[str, Any]) -> pd.DataFrame:
    players = root["players"]
    keys = [RENAME.get(key, key) for key in players["keys"]]
    columns = players["values"]
    if not columns:
        return pd.DataFrame(columns=COLUMN_ORDER)
    n = len(columns[0])
    rows = [
        {keys[col]: columns[col][row] for col in range(len(keys))}
        for row in range(n)
    ]
    frame = pd.DataFrame(rows)
    ordered = [col for col in COLUMN_ORDER if col in frame.columns]
    extras = [col for col in frame.columns if col not in ordered]
    frame = frame[ordered + extras]
    for col in INT_COLUMNS:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce").astype("Int64")
    if "rank" in frame.columns:
        frame = frame.sort_values("rank", kind="mergesort")
    return frame.reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch DARKO season boards.")
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="First season end year to fetch (default: earliest the API lists).",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="Last season end year to fetch (default: latest the API lists).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    PROJECTIONS_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    print("Fetching DARKO season list...")
    catalog = fetch_board(session, None)
    if catalog is None:
        raise SystemExit("Could not load the DARKO season list.")

    seasons = available_seasons(catalog)
    if not seasons:
        raise SystemExit("DARKO did not return a season list.")

    start = args.start if args.start is not None else seasons[0]
    end = args.end if args.end is not None else seasons[-1]
    selected = [season for season in seasons if start <= season <= end]
    if not selected:
        raise SystemExit(
            f"No DARKO seasons between {start} and {end}. "
            f"Available: {seasons[0]}-{seasons[-1]}."
        )

    print(
        f"Saving {len(selected)} seasons "
        f"({end_year_to_season(selected[0])} through {end_year_to_season(selected[-1])})..."
    )

    cached: dict[int, dict[str, Any]] = {}
    selected_season = catalog.get("selectedSeason")
    if isinstance(selected_season, int) and selected_season in selected:
        cached[selected_season] = catalog

    for index, season in enumerate(selected):
        label = end_year_to_season(season)
        print(f"Fetching {label}...")
        root = cached.get(season)
        if root is None:
            if index > 0 or cached:
                time.sleep(REQUEST_SLEEP_SECONDS)
            root = fetch_board(session, season)
        if root is None:
            print(f"    Skipped {label}")
            continue
        frame = board_to_frame(root)
        out_path = PROJECTIONS_DIR / f"darko_{label}.csv"
        frame.to_csv(out_path, index=False)
        print(f"    Saved {len(frame)} players to {out_path}")

    print("DARKO fetch complete!")


if __name__ == "__main__":
    main()
