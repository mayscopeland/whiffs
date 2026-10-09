"""Fetch ESPN fantasy season projections.

ESPN keeps a full-season projection (stat source 1, split 0) separate from
actuals for end years 2018 through the current season. Those lines include
games, minutes, and the box score, including total rebounds. The offensive
and defensive rebound split is absent. ``nba_id`` comes from
https://github.com/mayscopeland/fbkb_ids.

Writes basketball/projections/espn_YYYY-YY.csv.
"""

from __future__ import annotations

import argparse
import json
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
PROJECTIONS_DIR = ROOT / "projections"

# ESPN's season id is the NBA end year: 2024 is 2023-24. 2017 and earlier 404.
FIRST_END_YEAR = 2018
LAST_END_YEAR = 2027

PLAYERS_URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/"
    "{season}/segments/0/leaguedefaults/1"
)
ID_MAP_URL = (
    "https://raw.githubusercontent.com/mayscopeland/fbkb_ids/main/player_ids.csv"
)

HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
}

# ESPN stat id -> Bricks counting column. OREB (4) and DREB (5) are absent
# from projections. Total rebounds are stat id 6.
STAT_IDS = {
    "42": "G",
    "40": "MIN",
    "0": "PTS",
    "13": "FGM",
    "14": "FGA",
    "17": "FG3M",
    "18": "FG3A",
    "15": "FTM",
    "16": "FTA",
    "6": "REB",
    "3": "AST",
    "2": "STL",
    "1": "BLK",
    "11": "TOV",
}

COUNTING_COLS = list(STAT_IDS.values())

TEAM_ABBR = {
    0: "FA",
    1: "ATL",
    2: "BOS",
    3: "NOP",
    4: "CHI",
    5: "CLE",
    6: "DAL",
    7: "DEN",
    8: "DET",
    9: "GSW",
    10: "HOU",
    11: "IND",
    12: "LAC",
    13: "LAL",
    14: "MIA",
    15: "MIL",
    16: "MIN",
    17: "BKN",
    18: "NYK",
    19: "ORL",
    20: "PHL",
    21: "PHO",
    22: "POR",
    23: "SAC",
    24: "SAS",
    25: "OKC",
    26: "UTA",
    27: "WAS",
    28: "TOR",
    29: "MEM",
    30: "CHA",
}

PAGE_SIZE = 500
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3
REQUEST_SLEEP_SECONDS = 0.4
REQUEST_TIMEOUT_SECONDS = 90


def end_year_to_season(end_year: int) -> str:
    """Convert season end year (2024) to NBA label (2023-24)."""
    start = end_year - 1
    return f"{start}-{str(end_year)[-2:]}"


def _safe_div(numer: pd.Series, denom: pd.Series) -> pd.Series:
    result = numer.div(denom)
    return result.replace([float("inf"), float("-inf")], pd.NA).fillna(0)


def add_available_rates(frame: pd.DataFrame) -> pd.DataFrame:
    """Rates ESPN can fill without the offensive/defensive rebound split."""
    out = frame.copy()
    out["PTS/MIN"] = _safe_div(out["PTS"], out["MIN"])
    out["REB/MIN"] = _safe_div(out["REB"], out["MIN"])
    out["STL/MIN"] = _safe_div(out["STL"], out["MIN"])
    out["AST/MIN"] = _safe_div(out["AST"], out["MIN"])
    out["BLK/MIN"] = _safe_div(out["BLK"], out["MIN"])
    out["FTA/MIN"] = _safe_div(out["FTA"], out["MIN"])
    out["FGA/MIN"] = _safe_div(out["FGA"], out["MIN"])
    out["FG3A/MIN"] = _safe_div(out["FG3A"], out["MIN"])
    out["TOV/MIN"] = _safe_div(out["TOV"], out["MIN"])
    out["FTM/FTA"] = _safe_div(out["FTM"], out["FTA"])
    out["FGM/FGA"] = _safe_div(out["FGM"], out["FGA"])
    out["FG3M/FG3A"] = _safe_div(out["FG3M"], out["FG3A"])
    out["FG3A/FGA"] = _safe_div(out["FG3A"], out["FGA"])
    out["MIN/G"] = _safe_div(out["MIN"], out["G"])
    return out


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


def load_nba_ids(session: requests.Session) -> pd.Series:
    """espn_id -> nba_id from mayscopeland/fbkb_ids."""
    response = _request_json(session, ID_MAP_URL)
    if response is None:
        raise SystemExit(f"Could not download {ID_MAP_URL}")
    frame = pd.read_csv(StringIO(response.text), dtype=str)
    if "espn_id" not in frame.columns or "nba_id" not in frame.columns:
        raise SystemExit("fbkb_ids player_ids.csv is missing espn_id or nba_id.")
    frame["espn_id"] = pd.to_numeric(frame["espn_id"], errors="coerce").astype("Int64")
    frame["nba_id"] = pd.to_numeric(frame["nba_id"], errors="coerce").astype("Int64")
    frame = frame.dropna(subset=["espn_id"])
    frame["_has_nba"] = frame["nba_id"].notna()
    frame = frame.sort_values("_has_nba", ascending=False)
    nba_counts = (
        frame.dropna(subset=["nba_id"]).groupby("espn_id")["nba_id"].nunique()
    )
    conflicts = int((nba_counts > 1).sum())
    if conflicts:
        print(f"    {conflicts} espn ids map to more than one nba id; keeping the first.")
    frame = frame.drop_duplicates("espn_id", keep="first")
    return frame.set_index("espn_id")["nba_id"]


def _season_projection(player: dict, end_year: int) -> dict | None:
    for split in player.get("stats") or []:
        if (
            split.get("statSourceId") == 1
            and split.get("statSplitTypeId") == 0
            and split.get("scoringPeriodId") == 0
            and split.get("seasonId") == end_year
        ):
            stats = split.get("stats") or {}
            return stats or None
    return None


def _player_row(entry: dict, end_year: int) -> dict | None:
    player = entry.get("player") or {}
    stats = _season_projection(player, end_year)
    if not stats:
        return None
    espn_id = player.get("id")
    if espn_id is None:
        return None
    row = {
        "espn_id": int(espn_id),
        "player_name": player.get("fullName") or "",
        "team": TEAM_ABBR.get(player.get("proTeamId"), ""),
    }
    for stat_id, column in STAT_IDS.items():
        value = stats.get(stat_id)
        row[column] = None if value is None else float(value)
    return row


def fetch_season(session: requests.Session, end_year: int) -> pd.DataFrame | None:
    url = PLAYERS_URL.format(season=end_year)
    rows: list[dict] = []
    seen: set[int] = set()
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
            row = _player_row(entry, end_year)
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


def season_frame(players: pd.DataFrame, nba_ids: pd.Series) -> pd.DataFrame:
    frame = players.copy()
    frame["espn_id"] = frame["espn_id"].astype("Int64")
    frame["nba_id"] = frame["espn_id"].map(nba_ids)
    for column in COUNTING_COLS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").round(1)
    frame = add_available_rates(frame)
    rate_cols = [
        "PTS/MIN",
        "REB/MIN",
        "STL/MIN",
        "AST/MIN",
        "BLK/MIN",
        "FTA/MIN",
        "FGA/MIN",
        "FG3A/MIN",
        "TOV/MIN",
        "FTM/FTA",
        "FGM/FGA",
        "FG3M/FG3A",
        "FG3A/FGA",
        "MIN/G",
    ]
    for column in rate_cols:
        frame[column] = frame[column].round(6)
    ordered = ["espn_id", "nba_id", "player_name", "team"] + COUNTING_COLS + rate_cols
    frame = frame[ordered]
    frame = frame.sort_values(
        ["MIN", "player_name"], ascending=[False, True], kind="mergesort"
    )
    return frame.reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch ESPN fantasy season projections.")
    parser.add_argument(
        "--start",
        type=int,
        default=FIRST_END_YEAR,
        help=f"First season end year (default: {FIRST_END_YEAR}).",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=LAST_END_YEAR,
        help=f"Last season end year (default: {LAST_END_YEAR}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start > args.end:
        raise SystemExit(f"--start {args.start} is after --end {args.end}.")
    PROJECTIONS_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    print("Downloading NBA id map...")
    nba_ids = load_nba_ids(session)
    print(f"    {int(nba_ids.notna().sum())} espn ids have an nba id.")

    years = list(range(args.start, args.end + 1))
    print(
        f"Fetching {len(years)} seasons "
        f"({end_year_to_season(years[0])} through {end_year_to_season(years[-1])})..."
    )
    for index, end_year in enumerate(years):
        label = end_year_to_season(end_year)
        print(f"Fetching {label}...")
        if index:
            time.sleep(REQUEST_SLEEP_SECONDS)
        players = fetch_season(session, end_year)
        if players is None:
            print(f"    Skipped {label}")
            continue
        if players.empty:
            print(f"    No projections for {label}")
            continue
        frame = season_frame(players, nba_ids)
        matched = int(frame["nba_id"].notna().sum())
        out_path = PROJECTIONS_DIR / f"espn_{label}.csv"
        frame.to_csv(out_path, index=False)
        print(
            f"    Saved {len(frame)} players ({matched} with nba_id) to {out_path}"
        )

    print("ESPN fetch complete!")


if __name__ == "__main__":
    main()
