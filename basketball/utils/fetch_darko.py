"""Fetch historical DARKO box-score projections from darko.app.

The projections board (``/projections?asof=``) publishes minutes per game, pace,
and per-100 possession box rates. Bricks scores the per-minute rates those
fields imply. Games and season minutes are not on the board.

An offseason ``asof`` still returns the previous season. For each season this
script takes the first later date whose board is the new season and names
every franchise.

Writes basketball/projections/darko_YYYY-YY.csv for 2006-07 through 2025-26.
The 2026-27 file is the separate preseason snapshot and is left alone.
"""

from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
PROJECTIONS_DIR = ROOT / "projections"

DATA_URL = "https://www.darko.app/projections/__data.json"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Referer": "https://www.darko.app/projections",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
}

# First season with basketball/stats, through the last completed season.
DEFAULT_START = 2007
DEFAULT_END = 2026

FULL_ROSTER = 350
EXPECTED_TEAMS = 30
SCAN_DAYS = 28

MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3
REQUEST_SLEEP_SECONDS = 0.3
REQUEST_TIMEOUT_SECONDS = 90

COLUMN_ORDER = [
    "nba_id",
    "player_name",
    "team_name",
    "asof",
    "projection_date",
    "PTS/MIN",
    "OREB/MIN",
    "DREB/MIN",
    "REB/MIN",
    "STL/MIN",
    "AST/MIN",
    "BLK/MIN",
    "FTA/MIN",
    "FGA/MIN",
    "FG3A/MIN",
    "FG3M/MIN",
    "TOV/MIN",
    "FTM/FTA",
    "FGM/FGA",
    "FG3M/FG3A",
    "FG3A/FGA",
    "MIN/G",
]


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


class BoardCache:
    """Fetch each asof date once."""

    def __init__(self, session: requests.Session) -> None:
        self.session = session
        self._boards: dict[str, dict[str, Any] | None] = {}

    def get(self, day: date) -> dict[str, Any] | None:
        key = day.isoformat()
        if key in self._boards:
            return self._boards[key]
        if self._boards:
            time.sleep(REQUEST_SLEEP_SECONDS)
        board = _fetch_board(self.session, key)
        self._boards[key] = board
        return board


def _fetch_board(session: requests.Session, asof: str) -> dict[str, Any] | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                DATA_URL,
                params={"asof": asof},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            nodes = response.json().get("nodes") or []
            for node in nodes:
                if isinstance(node, dict) and node.get("type") == "data":
                    data = node.get("data")
                    if isinstance(data, list):
                        root = _resolve(data, 0)
                        if isinstance(root, dict) and isinstance(root.get("players"), list):
                            return root
            print(f"    No projection board for asof={asof}")
            return None
        except (requests.exceptions.RequestException, ValueError) as exc:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed for {asof}: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)
    return None


def _history(root: dict[str, Any] | None) -> dict[str, Any]:
    if not root:
        return {}
    history = root.get("history")
    return history if isinstance(history, dict) else {}


def _is_new_season(root: dict[str, Any] | None, end_year: int) -> bool:
    history = _history(root)
    return history.get("season") == end_year and history.get("pastRegularSeason") is False


def _players(root: dict[str, Any] | None) -> list[Any]:
    if not root:
        return []
    players = root.get("players")
    return players if isinstance(players, list) else []


def _player_count(root: dict[str, Any] | None) -> int:
    return len(_players(root))


def _team_count(root: dict[str, Any] | None) -> int:
    return len(
        {
            player.get("team_name")
            for player in _players(root)
            if isinstance(player, dict) and player.get("team_name")
        }
    )


def _first_true(cache: BoardCache, end_year: int, lo: date, hi: date) -> date | None:
    """First date in [lo, hi] whose board is the new season."""
    if not _is_new_season(cache.get(hi), end_year):
        return None
    if _is_new_season(cache.get(lo), end_year):
        return lo
    while (hi - lo).days > 1:
        mid = lo + timedelta(days=(hi - lo).days // 2)
        if _is_new_season(cache.get(mid), end_year):
            hi = mid
        else:
            lo = mid
    return hi


def find_full_board(
    cache: BoardCache, end_year: int
) -> tuple[date, dict[str, Any]] | None:
    """Earliest board after the season flip that names every franchise."""
    start_year = end_year - 1
    opened = _first_true(
        cache, end_year, date(start_year, 10, 1), date(end_year, 1, 31)
    )
    if opened is None:
        print(f"    No {end_year_to_season(end_year)} board between Oct 1 and Jan 31.")
        return None

    best: tuple[date, dict[str, Any], int] | None = None
    for offset in range(SCAN_DAYS + 1):
        day = opened + timedelta(days=offset)
        root = cache.get(day)
        if not _is_new_season(root, end_year) or root is None:
            continue
        if _player_count(root) < FULL_ROSTER:
            continue
        n_teams = _team_count(root)
        if best is None or n_teams > best[2]:
            best = (day, root, n_teams)
        if n_teams >= EXPECTED_TEAMS:
            if offset:
                print(
                    f"    All {n_teams} teams are {offset} day(s) after the season flip ({opened})."
                )
            return day, root

    if best is None:
        print(
            f"    No full roster within {SCAN_DAYS} days of {opened} "
            f"for {end_year_to_season(end_year)}."
        )
        return None

    day, root, n_teams = best
    print(
        f"    Only {n_teams} teams within {SCAN_DAYS} days of {opened} "
        f"for {end_year_to_season(end_year)}; using {day.isoformat()}."
    )
    return day, root


def _per_minute(per_100: pd.Series, pace: pd.Series) -> pd.Series:
    return pd.to_numeric(per_100, errors="coerce") * pace / 4800


def _ratio(numer: pd.Series, denom: pd.Series) -> pd.Series:
    result = pd.to_numeric(numer, errors="coerce") / pd.to_numeric(denom, errors="coerce")
    return result.replace([float("inf"), float("-inf")], pd.NA).fillna(0)


def players_to_frame(players: list[dict[str, Any]], asof: str) -> pd.DataFrame:
    frame = pd.DataFrame(players)
    pace = pd.to_numeric(frame["x_pace"], errors="coerce")
    fg3_pct = pd.to_numeric(frame["x_fg3_pct"], errors="coerce")
    fg3a = pd.to_numeric(frame["x_fg3a_100"], errors="coerce")
    out = pd.DataFrame(
        {
            "nba_id": pd.to_numeric(frame["nba_id"], errors="coerce").astype("Int64"),
            "player_name": frame["player_name"],
            "team_name": frame["team_name"],
            "asof": asof,
            "projection_date": frame["date"],
            "PTS/MIN": _per_minute(frame["x_pts_100"], pace),
            "OREB/MIN": _per_minute(frame["x_orb_100"], pace),
            "DREB/MIN": _per_minute(frame["x_drb_100"], pace),
            "STL/MIN": _per_minute(frame["x_stl_100"], pace),
            "AST/MIN": _per_minute(frame["x_ast_100"], pace),
            "BLK/MIN": _per_minute(frame["x_blk_100"], pace),
            "FTA/MIN": _per_minute(frame["x_fta_100"], pace),
            "FGA/MIN": _per_minute(frame["x_fga_100"], pace),
            "FG3A/MIN": _per_minute(fg3a, pace),
            "FG3M/MIN": _per_minute(fg3a * fg3_pct, pace),
            "TOV/MIN": _per_minute(frame["x_tov_100"], pace),
            "FTM/FTA": pd.to_numeric(frame["x_ft_pct"], errors="coerce"),
            "FGM/FGA": pd.to_numeric(frame["x_fg_pct"], errors="coerce"),
            "FG3M/FG3A": fg3_pct,
            "FG3A/FGA": _ratio(frame["x_fg3a_100"], frame["x_fga_100"]),
            "MIN/G": pd.to_numeric(frame["x_minutes"], errors="coerce"),
        }
    )
    out["REB/MIN"] = out["OREB/MIN"] + out["DREB/MIN"]
    out = out[out["nba_id"].notna()].drop_duplicates("nba_id", keep="first")
    out = out.sort_values("MIN/G", ascending=False, kind="mergesort")
    return out[COLUMN_ORDER].reset_index(drop=True)


def _already_converted(path: Path) -> bool:
    if not path.exists():
        return False
    header = path.read_text(encoding="utf-8").splitlines()[:1]
    if not header:
        return False
    columns = header[0].split(",")
    return "PTS/MIN" in columns and "asof" in columns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch historical DARKO box-score projections.")
    parser.add_argument(
        "--start",
        type=int,
        default=DEFAULT_START,
        help="First season end year (default: 2007, the 2006-07 season).",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=DEFAULT_END,
        help="Last season end year (default: 2026, the 2025-26 season).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace a season file that already has converted rates.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start > args.end:
        raise SystemExit(f"--start {args.start} is after --end {args.end}.")
    if args.end >= 2027:
        raise SystemExit("2026-27 is the preseason snapshot and is not replaced by this fetcher.")

    PROJECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)
    cache = BoardCache(session)

    seasons = list(range(args.start, args.end + 1))
    print(
        f"Fetching DARKO projections for {len(seasons)} seasons "
        f"({end_year_to_season(seasons[0])} through {end_year_to_season(seasons[-1])})..."
    )

    saved = 0
    for end_year in seasons:
        label = end_year_to_season(end_year)
        out_path = PROJECTIONS_DIR / f"darko_{label}.csv"
        if not args.force and _already_converted(out_path):
            print(f"{label}: already converted, skipping")
            continue

        print(f"Finding {label}...")
        found = find_full_board(cache, end_year)
        if found is None:
            continue
        day, root = found
        frame = players_to_frame(root["players"], day.isoformat())
        frame.to_csv(out_path, index=False)
        saved += 1
        minutes = frame["MIN/G"]
        print(
            f"    Saved {len(frame)} players, {frame['team_name'].nunique()} teams "
            f"to {out_path.name} (asof {day.isoformat()}, "
            f"mpg median {minutes.median():.1f}, max {minutes.max():.1f})"
        )

    print(f"DARKO fetch complete. Wrote {saved} season files.")


if __name__ == "__main__":
    main()
