"""Fetch NBA regular-season player totals and bios from stats.nba.com."""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = ROOT / "stats"

STATS_URL = "https://stats.nba.com/stats/leaguedashplayerstats"
BIO_URL = "https://stats.nba.com/stats/leaguedashplayerbiostats"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "DNT": "1",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "sec-ch-ua": '"Chromium";v="154", "Google Chrome";v="154", "Not_A Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

# Season labels use calendar overlap: basketball/stats/2023-24.csv is 2023-24.
# Loops still use the season end year as an integer key.
START_END_YEAR = 2007
END_END_YEAR = 2026

COUNTING_COLS = [
    "playerId",
    "playerName",
    "teamId",
    "season",
    "G",
    "MIN",
    "PTS",
    "FGM",
    "FGA",
    "FG3M",
    "FG3A",
    "FTM",
    "FTA",
    "OREB",
    "DREB",
    "AST",
    "STL",
    "BLK",
    "TOV",
]

API_TO_COL = {
    "PLAYER_ID": "playerId",
    "PLAYER_NAME": "playerName",
    "TEAM_ID": "teamId",
    "GP": "G",
    "MIN": "MIN",
    "PTS": "PTS",
    "FGM": "FGM",
    "FGA": "FGA",
    "FG3M": "FG3M",
    "FG3A": "FG3A",
    "FTM": "FTM",
    "FTA": "FTA",
    "OREB": "OREB",
    "DREB": "DREB",
    "AST": "AST",
    "STL": "STL",
    "BLK": "BLK",
    "TOV": "TOV",
}

MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3
REQUEST_SLEEP_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 60

_SESSION: requests.Session | None = None


def end_year_to_season(end_year: int) -> str:
    """Convert season end year (2024) to NBA label (2023-24)."""
    start = end_year - 1
    return f"{start}-{str(end_year)[-2:]}"


def _session() -> requests.Session:
    """Reuse a session so TCP/TLS and cookies persist across seasons."""
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    session = requests.Session()
    session.headers.update(HEADERS)
    _SESSION = session
    return session


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    session = _session()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                url, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)
    return None


def _league_dash_params(season: str, *, for_bio: bool = False) -> dict[str, str]:
    """Query params matching the nba.com stats dashboard request shape."""
    params = {
        "College": "",
        "Conference": "",
        "Country": "",
        "DateFrom": "",
        "DateTo": "",
        "Division": "",
        "DraftPick": "",
        "DraftYear": "",
        "GameScope": "",
        "GameSegment": "",
        "Height": "",
        "ISTRound": "",
        "LastNGames": "0",
        "LeagueID": "00",
        "Location": "",
        "Month": "0",
        "OpponentTeamID": "0",
        "Outcome": "",
        "PORound": "0",
        "PerMode": "Totals",
        "Period": "0",
        "PlayerExperience": "",
        "PlayerPosition": "",
        "Season": season,
        "SeasonSegment": "",
        "SeasonType": "Regular Season",
        "ShotClockRange": "",
        "StarterBench": "",
        "TeamID": "0",
        "VsConference": "",
        "VsDivision": "",
        "Weight": "",
    }
    if not for_bio:
        params.update(
            {
                "MeasureType": "Base",
                "PaceAdjust": "N",
                "PlusMinus": "N",
                "Rank": "N",
            }
        )
    return params


def _result_frame(payload: dict[str, Any]) -> pd.DataFrame:
    result_sets = payload.get("resultSets") or []
    if not result_sets:
        return pd.DataFrame()
    result = result_sets[0]
    headers = result.get("headers") or []
    rows = result.get("rowSet") or []
    return pd.DataFrame(rows, columns=headers)


def fetch_season_stats(end_year: int) -> list[dict[str, Any]]:
    season = end_year_to_season(end_year)
    params = _league_dash_params(season)

    payload = _request_json(STATS_URL, params)
    if payload is None:
        print(f"  No stats payload for {season}")
        return []

    df = _result_frame(payload)
    if df.empty:
        print(f"  Empty stats for {season}")
        return []

    records = []
    for _, row in df.iterrows():
        record: dict[str, Any] = {"season": season}
        for api_name, col in API_TO_COL.items():
            value = row.get(api_name)
            if col in ("playerId", "teamId", "G"):
                record[col] = int(value) if pd.notna(value) else 0
            elif col == "playerName":
                record[col] = str(value) if pd.notna(value) else ""
            else:
                record[col] = float(value) if pd.notna(value) else 0.0
        records.append(record)

    return records


def fetch_season_bios(end_year: int) -> list[dict[str, Any]]:
    season = end_year_to_season(end_year)
    params = _league_dash_params(season, for_bio=True)

    payload = _request_json(BIO_URL, params)
    if payload is None:
        print(f"  No bio payload for {season}")
        return []

    df = _result_frame(payload)
    if df.empty:
        print(f"  Empty bios for {season}")
        return []

    records = []
    for _, row in df.iterrows():
        player_id = row.get("PLAYER_ID")
        age = row.get("AGE")
        if pd.isna(player_id) or pd.isna(age):
            continue
        age_f = float(age)
        records.append(
            {
                "playerId": int(player_id),
                "playerName": str(row.get("PLAYER_NAME") or ""),
                "birthYear": int(round(end_year - age_f)),
            }
        )
    return records


def build_player_bio(all_bio_records: list[dict[str, Any]]) -> pd.DataFrame:
    """Collapse season bio rows to one birth year per player (mode)."""
    by_player: dict[int, dict[str, Any]] = {}
    birth_years: dict[int, list[int]] = defaultdict(list)

    for record in all_bio_records:
        player_id = record["playerId"]
        birth_years[player_id].append(record["birthYear"])
        # Prefer the most recent name seen.
        by_player[player_id] = {
            "playerId": player_id,
            "playerName": record["playerName"],
        }

    rows = []
    for player_id, meta in by_player.items():
        counts = Counter(birth_years[player_id])
        birth_year = counts.most_common(1)[0][0]
        rows.append(
            {
                "playerId": player_id,
                "playerName": meta["playerName"],
                "birthYear": birth_year,
            }
        )

    return pd.DataFrame(rows).sort_values("playerId").reset_index(drop=True)


def main() -> None:
    STATS_DIR.mkdir(parents=True, exist_ok=True)

    all_bio_records: list[dict[str, Any]] = []

    for end_year in range(START_END_YEAR, END_END_YEAR + 1):
        season = end_year_to_season(end_year)
        print(f"Fetching {season}...")

        print(f"  Player totals...")
        records = fetch_season_stats(end_year)
        if records:
            df = pd.DataFrame(records)[COUNTING_COLS]
            out_path = STATS_DIR / f"{season}.csv"
            df.to_csv(out_path, index=False)
            print(f"    Saved {len(records)} players to {out_path}")
        else:
            print(f"    No player totals for {season}")

        time.sleep(REQUEST_SLEEP_SECONDS)

        print(f"  Player bios...")
        bio_records = fetch_season_bios(end_year)
        if bio_records:
            all_bio_records.extend(bio_records)
            print(f"    Retrieved {len(bio_records)} bio rows")
        else:
            print(f"    No bios for {season}")

        time.sleep(REQUEST_SLEEP_SECONDS)

    if all_bio_records:
        bio_df = build_player_bio(all_bio_records)
        bio_path = STATS_DIR / "player_bio.csv"
        bio_df.to_csv(bio_path, index=False)
        print(f"\nSaved {len(bio_df)} player bios to {bio_path}")
    else:
        print("\nNo biographical data retrieved")

    print("NBA stats fetch complete!")


if __name__ == "__main__":
    main()
