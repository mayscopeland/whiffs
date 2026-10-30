"""Download regular-season player stats from nflverse into football/stats.

Season totals (including games played) come from nflverse
``stats_player_reg_{season}.csv``. Each row is joined to ``nfl_slug`` through
``gsis_id`` on the mayscopeland/ffb_ids crosswalk.
"""

from __future__ import annotations

import argparse
import io
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = ROOT / "stats"
NFLVERSE_REG = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_player/stats_player_reg_{season}.csv"
)
FFB_IDS_URL = "https://raw.githubusercontent.com/mayscopeland/ffb_ids/main/player_ids.csv"

# nflverse column -> Drops counting column.
NFLVERSE_COLS = {
    "games": "G",
    "attempts": "ATT",
    "completions": "CMP",
    "passing_yards": "PASS_YDS",
    "passing_tds": "PASS_TD",
    "passing_interceptions": "INT",
    "carries": "CAR",
    "rushing_yards": "RUSH_YDS",
    "rushing_tds": "RUSH_TD",
    "targets": "TGT",
    "receptions": "REC",
    "receiving_yards": "REC_YDS",
    "receiving_tds": "REC_TD",
}

COUNTING_COLS = [
    "G",
    "ATT",
    "CMP",
    "PASS_YDS",
    "PASS_TD",
    "INT",
    "CAR",
    "RUSH_YDS",
    "RUSH_TD",
    "TGT",
    "REC",
    "REC_YDS",
    "REC_TD",
]

# Align with projection coverage; earlier nflverse seasons exist but are unused.
FIRST_SEASON = 2018


def _read_csv_url(url: str) -> pd.DataFrame:
    request = urllib.request.Request(url, headers={"User-Agent": "whiffs"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return pd.read_csv(io.StringIO(response.read().decode("utf-8")))


def _url_exists(url: str) -> bool:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "whiffs"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return 200 <= getattr(response, "status", 200) < 300
    except urllib.error.HTTPError as exc:
        if exc.code in {404, 403}:
            return False
        # Some hosts reject HEAD; fall through to a tiny GET.
    except urllib.error.URLError:
        pass
    try:
        frame = _read_csv_url(url)
    except (urllib.error.URLError, urllib.error.HTTPError, pd.errors.EmptyDataError):
        return False
    return not frame.empty


def load_ffb_gsis_slugs() -> pd.DataFrame:
    ids = _read_csv_url(FFB_IDS_URL)
    if "gsis_id" not in ids.columns or "nfl_slug" not in ids.columns:
        raise SystemExit("ffb_ids is missing gsis_id or nfl_slug")
    keep = ["gsis_id", "nfl_slug"]
    if "gsis_name" in ids.columns:
        keep.append("gsis_name")
    frame = ids[keep].copy()
    frame["gsis_id"] = frame["gsis_id"].astype(str).str.strip()
    frame["nfl_slug"] = frame["nfl_slug"].astype(str).str.strip()
    frame = frame.loc[
        frame["gsis_id"].ne("")
        & frame["gsis_id"].str.lower().ne("nan")
        & frame["nfl_slug"].ne("")
        & frame["nfl_slug"].str.lower().ne("nan")
    ]
    return frame.drop_duplicates(subset=["gsis_id"], keep="first")


def load_nflverse_season(season: int) -> pd.DataFrame:
    url = NFLVERSE_REG.format(season=season)
    try:
        reg = _read_csv_url(url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return pd.DataFrame()
        raise
    if "season_type" in reg.columns:
        reg = reg.loc[reg["season_type"].astype(str).str.upper().eq("REG")].copy()
    if reg.empty:
        return pd.DataFrame()

    out = pd.DataFrame(
        {
            "gsis_id": reg["player_id"].astype(str).str.strip(),
            "player_name": reg.get(
                "player_display_name",
                reg.get("player_name", pd.Series(index=reg.index, dtype=str)),
            ),
        }
    )
    for source, dest in NFLVERSE_COLS.items():
        if source in reg.columns:
            out[dest] = pd.to_numeric(reg[source], errors="coerce").fillna(0)
        else:
            out[dest] = 0.0

    volume = out[["ATT", "CAR", "TGT"]].sum(axis=1)
    out = out.loc[volume > 0].copy()
    return out


def scrape_season(season: int, ids: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build one season file: nflverse totals joined to nfl_slug on gsis_id."""
    if ids is None:
        ids = load_ffb_gsis_slugs()
    frame = load_nflverse_season(season)
    if frame.empty:
        return pd.DataFrame()

    before = len(frame)
    merged = frame.merge(ids[["gsis_id", "nfl_slug"]], on="gsis_id", how="left")
    matched = merged["nfl_slug"].notna().sum()
    dropped = before - int(matched)
    print(f"  {season}: {matched} players ({dropped} without an nfl_slug)")
    merged = merged.loc[merged["nfl_slug"].notna()].copy()
    if merged.empty:
        return pd.DataFrame()

    if "gsis_name" in ids.columns:
        names = ids.drop_duplicates("gsis_id").set_index("gsis_id")["gsis_name"]
        named = merged["gsis_id"].map(names)
        use_name = named.notna() & named.astype(str).str.strip().ne("")
        merged.loc[use_name, "player_name"] = named.loc[use_name].astype(str).str.strip()

    for column in COUNTING_COLS:
        if column not in merged.columns:
            merged[column] = 0.0
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0)

    merged.insert(0, "season", season)
    return merged[["season", "nfl_slug", "player_name", *COUNTING_COLS]].sort_values(
        ["player_name", "nfl_slug"]
    )


def latest_season() -> int:
    year = date.today().year + 1
    while year >= FIRST_SEASON:
        if _url_exists(NFLVERSE_REG.format(season=year)):
            return year
        year -= 1
    raise SystemExit("nflverse returned no regular-season player stats.")


def seasons_to_fetch(args: argparse.Namespace) -> list[int]:
    if args.season:
        return sorted(set(args.season))
    start = args.last if args.last is not None else latest_season()
    stop = args.first if args.first is not None else FIRST_SEASON
    seasons = []
    year = start
    while year >= stop:
        if _url_exists(NFLVERSE_REG.format(season=year)):
            seasons.append(year)
        elif args.first is None:
            break
        year -= 1
    return seasons


def main() -> int:
    parser = argparse.ArgumentParser(description="Download nflverse player season stats")
    parser.add_argument("--season", type=int, action="append", help="Fetch this season only. Repeatable.")
    parser.add_argument("--first", type=int, help="Oldest season to include when walking backward.")
    parser.add_argument("--last", type=int, help="Newest season to include when walking backward.")
    parser.add_argument("--refresh", action="store_true", help="Rewrite seasons that already have a CSV.")
    args = parser.parse_args()

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    ids = load_ffb_gsis_slugs()
    print(f"Loaded {len(ids)} gsis_id -> nfl_slug rows from ffb_ids")

    for season in seasons_to_fetch(args):
        path = STATS_DIR / f"{season}.csv"
        if path.exists() and not args.refresh and not args.season:
            print(f"Skipping {season}; {path.name} exists")
            continue
        print(f"Fetching {season}...")
        frame = scrape_season(season, ids=ids)
        if frame.empty:
            print(f"  No players for {season}")
            continue
        frame.to_csv(path, index=False)
        print(f"  Wrote {path.name} ({len(frame)} players)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
