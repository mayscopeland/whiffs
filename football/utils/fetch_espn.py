"""Fetch ESPN fantasy football season projections.

ESPN keeps a full-season projection (stat source 1, split 0, period 0) for
2018 through the current season, except 2023. 2017 and earlier 404. In 2023
that season split only carries stat 210 for most players, so the counting
columns would be zeros. Weekly splits are later in-season updates, not the
preseason season line, so 2023 is left out and a leftover file is removed.
Counting stats are the same box-score columns as the nflverse actuals.
``nfl_slug`` comes from the mayscopeland/ffb_ids crosswalk, joined on
``espn_id``. A missing ESPN id is matched by name when that name has one slug.

Writes football/projections/espn_{season}.csv. The default range is every
completed season. The season in progress is left out.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "utils"))
from player_ids import PlayerIds, clean_id  # noqa: E402
from rates import COUNTING_COLS  # noqa: E402

PROJECTIONS_DIR = ROOT / "projections"

# 2017 and earlier return 404. The labeled season starts in September.
FIRST_SEASON = 2018
# 2023 season projections are empty for most players (stat 210 only).
SKIP_SEASONS = {2023}

PLAYERS_URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/"
    "{season}/segments/0/leaguedefaults/1"
)
# ESPN defaultPositionId for the offensive pools. Kickers and defenses are
# not matched by name.
OFFENSIVE_POSITIONS = {1, 2, 3, 4}

HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
}

# ESPN stat id -> Drops counting column. Confirmed against 2024 season lines:
# attempts, completions, yards, touchdowns, and interceptions for passers;
# carries, yards, and touchdowns for rushers; targets, receptions, yards,
# and touchdowns for receivers.
STAT_IDS = {
    "0": "ATT",
    "1": "CMP",
    "3": "PASS_YDS",
    "4": "PASS_TD",
    "20": "INT",
    "23": "CAR",
    "24": "RUSH_YDS",
    "25": "RUSH_TD",
    "58": "TGT",
    "53": "REC",
    "42": "REC_YDS",
    "43": "REC_TD",
}

PAGE_SIZE = 200
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3
REQUEST_SLEEP_SECONDS = 0.4
REQUEST_TIMEOUT_SECONDS = 90


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


def _request_json(
    session: requests.Session, url: str, params: dict | None = None, headers: dict | None = None
) -> requests.Response | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 404:
                return response
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException, ValueError) as exc:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)
    return None


def _season_projection(player: dict, season: int) -> dict | None:
    for split in player.get("stats") or []:
        if (
            split.get("statSourceId") == 1
            and split.get("statSplitTypeId") == 0
            and split.get("scoringPeriodId") == 0
            and split.get("seasonId") == season
        ):
            stats = split.get("stats") or {}
            return stats or None
    return None


def _player_row(entry: dict, season: int) -> dict | None:
    player = entry.get("player") or {}
    stats = _season_projection(player, season)
    if not stats:
        return None
    espn_id = player.get("id")
    if espn_id is None:
        return None
    row = {
        "espn_id": clean_id(espn_id),
        "player_name": player.get("fullName") or "",
        "position_id": player.get("defaultPositionId"),
    }
    for stat_id, column in STAT_IDS.items():
        value = stats.get(stat_id)
        row[column] = None if value is None else float(value)
    return row


def fetch_season(session: requests.Session, season: int) -> pd.DataFrame | None:
    url = PLAYERS_URL.format(season=season)
    rows: list[dict] = []
    seen: set[str] = set()
    offset = 0
    while True:
        player_filter = {
            "players": {
                "limit": PAGE_SIZE,
                "offset": offset,
                "sortPercOwned": {"sortAsc": False, "sortPriority": 1},
            }
        }
        headers = {"X-Fantasy-Filter": json.dumps(player_filter)}
        response = _request_json(
            session,
            url,
            params={"view": "kona_player_info"},
            headers=headers,
        )
        if response is None:
            return None
        if response.status_code == 404:
            return None
        players = response.json().get("players") or []
        added = 0
        for entry in players:
            row = _player_row(entry, season)
            if row is None or row["espn_id"] in seen:
                continue
            seen.add(row["espn_id"])
            rows.append(row)
            added += 1
        if len(players) < PAGE_SIZE or added == 0:
            break
        offset += PAGE_SIZE
        time.sleep(REQUEST_SLEEP_SECONDS)
    return pd.DataFrame(rows)


def _is_offensive(position: object) -> bool:
    if position is None or (isinstance(position, float) and pd.isna(position)):
        return False
    try:
        return int(position) in OFFENSIVE_POSITIONS
    except (TypeError, ValueError):
        return False


def season_frame(players: pd.DataFrame, ids: PlayerIds) -> pd.DataFrame:
    frame = players.copy()
    if frame.empty:
        return frame
    frame["nfl_slug"] = [
        ids.nfl_slug(
            "espn",
            espn_id,
            name,
            match_name=_is_offensive(position),
        )
        for espn_id, name, position in zip(
            frame["espn_id"], frame["player_name"], frame["position_id"]
        )
    ]
    for column in COUNTING_COLS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).round(1)
    frame = frame[frame["nfl_slug"] != ""]
    ordered = ["nfl_slug", "player_name", "espn_id", *COUNTING_COLS]
    frame = frame[ordered]
    frame = frame.sort_values("nfl_slug", kind="mergesort")
    frame = frame.groupby("nfl_slug", as_index=False).agg(
        {column: "max" if column in COUNTING_COLS else "first" for column in ordered if column != "nfl_slug"}
    )
    frame = frame[ordered]
    frame = frame.sort_values(
        ["player_name", "nfl_slug"], ascending=[True, True], kind="mergesort"
    )
    return frame.reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch ESPN fantasy football season projections.")
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
    for season in SKIP_SEASONS:
        stale = PROJECTIONS_DIR / f"espn_{season}.csv"
        if stale.exists():
            stale.unlink()
            print(f"Removed {stale.name}; ESPN has no usable {season} season line")

    session = requests.Session()
    session.headers.update(HEADERS)

    print("Loading ffb_ids...")
    ids = PlayerIds.load()
    print(f"    {len(ids.frame)} players from {ids.url}")

    years = [season for season in range(args.start, end + 1) if season not in SKIP_SEASONS]
    skipped = [season for season in range(args.start, end + 1) if season in SKIP_SEASONS]
    for season in skipped:
        print(f"Skipping {season}; ESPN has no usable season line")
    if not years:
        print("ESPN fetch complete!")
        return 0
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
        dropped = len(players) - len(matched)
        out_path = PROJECTIONS_DIR / f"espn_{season}.csv"
        matched.to_csv(out_path, index=False)
        print(
            f"    Saved {len(matched)} players ({dropped} without an nfl_slug) to {out_path.name}"
        )
        print(
            f"    Max attempts {matched['ATT'].max():.0f}, "
            f"carries {matched['CAR'].max():.0f}, targets {matched['TGT'].max():.0f}"
        )

    print("ESPN fetch complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
