"""Fetch Sleeper season projections.

Sleeper's season projection (no week) is a full-season line attributed to
RotoWire, for 2018 through the current season. 2017 and earlier come back
empty. Counting stats match the nflverse actuals. Targets are published only
in 2019 and 2020; other seasons omit ``TGT`` rather than storing a zero.
``nfl_slug`` comes from the mayscopeland/ffb_ids crosswalk, joined on
``sleeper_id``. A missing Sleeper id is matched by name when that name has
one slug.

Writes football/projections/sleeper_{season}.csv. The default range is every
completed season from 2018. The season in progress is left out.
"""

from __future__ import annotations

import argparse
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

# 2017 and earlier return a player shell with no counting stats.
FIRST_SEASON = 2018

PROJECTIONS_URL = "https://api.sleeper.app/projections/nfl/{season}"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
}

POSITIONS = ("QB", "RB", "WR", "TE", "FB")

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


def _request_json(session: requests.Session, url: str, params: list | None = None) -> requests.Response | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code == 404:
                return response
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException, ValueError) as exc:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)
    return None


def _number(stats: dict, *keys: str) -> float:
    for key in keys:
        value = stats.get(key)
        if value is None or value == "":
            continue
        return float(value)
    return 0.0


def _player_name(player: dict) -> str:
    full = player.get("full_name") or ""
    if full:
        return str(full).strip()
    return f"{player.get('first_name') or ''} {player.get('last_name') or ''}".strip()


def fetch_season(session: requests.Session, season: int) -> pd.DataFrame | None:
    params: list[tuple[str, str]] = [("season_type", "regular")]
    params.extend(("position[]", position) for position in POSITIONS)
    response = _request_json(session, PROJECTIONS_URL.format(season=season), params=params)
    if response is None or response.status_code == 404:
        return None
    payload = response.json()
    if not isinstance(payload, list):
        print(f"    Unexpected response for {season}")
        return None

    targets_published = any("rec_tgt" in (entry.get("stats") or {}) for entry in payload)
    best: dict[str, dict] = {}
    for entry in payload:
        stats = entry.get("stats") or {}
        player = entry.get("player") or {}
        sleeper_id = clean_id(entry.get("player_id") or player.get("player_id"))
        if not sleeper_id:
            continue
        row = {
            "sleeper_id": sleeper_id,
            "player_name": _player_name(player),
            "ATT": _number(stats, "pass_att"),
            "CMP": _number(stats, "pass_cmp"),
            "PASS_YDS": _number(stats, "pass_yd"),
            "PASS_TD": _number(stats, "pass_td"),
            "INT": _number(stats, "pass_int", "int"),
            "CAR": _number(stats, "rush_att"),
            "RUSH_YDS": _number(stats, "rush_yd"),
            "RUSH_TD": _number(stats, "rush_td"),
            "REC": _number(stats, "rec"),
            "REC_YDS": _number(stats, "rec_yd"),
            "REC_TD": _number(stats, "rec_td"),
        }
        if targets_published:
            row["TGT"] = _number(stats, "rec_tgt")
        volume = sum(row[column] for column in COUNTING_COLS if column in row)
        current = best.get(sleeper_id)
        current_volume = 0.0
        if current is not None:
            current_volume = sum(current[column] for column in COUNTING_COLS if column in current)
        if current is None or volume > current_volume:
            best[sleeper_id] = row

    frame = pd.DataFrame(list(best.values()))
    frame.attrs["targets_published"] = targets_published
    return frame


def season_frame(players: pd.DataFrame, ids: PlayerIds) -> pd.DataFrame:
    frame = players.copy()
    if frame.empty:
        return frame
    targets_published = "TGT" in frame.columns
    frame["nfl_slug"] = [
        ids.nfl_slug("sleeper", sleeper_id, name)
        for sleeper_id, name in zip(frame["sleeper_id"], frame["player_name"])
    ]
    for column in COUNTING_COLS:
        if column == "TGT" and not targets_published:
            continue
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).round(1)
    frame = frame[frame["nfl_slug"] != ""]
    volume_cols = [column for column in COUNTING_COLS if column in frame.columns]
    frame = frame[frame[volume_cols].sum(axis=1) > 0]
    ordered = ["nfl_slug", "player_name", "sleeper_id", *volume_cols]
    frame = frame[ordered]
    frame = frame.sort_values("nfl_slug", kind="mergesort")
    frame = frame.groupby("nfl_slug", as_index=False).agg(
        {column: "max" if column in volume_cols else "first" for column in ordered if column != "nfl_slug"}
    )
    frame = frame[ordered]
    frame = frame.sort_values(
        ["player_name", "nfl_slug"], ascending=[True, True], kind="mergesort"
    )
    return frame.reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Sleeper season projections.")
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
        value_cols = [column for column in COUNTING_COLS if column in players.columns]
        projected = players[players[value_cols].fillna(0).sum(axis=1) > 0]
        matched = season_frame(projected, ids)
        dropped = projected["sleeper_id"].nunique() - matched["sleeper_id"].nunique()
        out_path = PROJECTIONS_DIR / f"sleeper_{season}.csv"
        matched.to_csv(out_path, index=False)
        targets = "published" if "TGT" in matched.columns else "not published"
        print(
            f"    Saved {len(matched)} players ({dropped} without an nfl_slug) to {out_path.name}"
        )
        print(
            f"    Max attempts {matched['ATT'].max():.0f}, "
            f"carries {matched['CAR'].max():.0f}, "
            f"receptions {matched['REC'].max():.0f}; targets {targets}"
        )

    print("Sleeper fetch complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
