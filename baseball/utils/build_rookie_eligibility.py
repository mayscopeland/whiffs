"""
Build per-season MLB rookie-eligibility cohorts.

A player enters season Y with rookie eligibility intact unless, in prior seasons,
he has exceeded 130 AB, 50 IP, or more than 45 days on an active MLB roster
during the Championship Season (IL time excluded via rosterType=active).

Era rules for the 45-day clock:
  - Through 2019: only days before Sept 1 count
  - 2020+: all Championship Season days count
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = ROOT / "stats"
ROOKIES_DIR = ROOT / "rookies"
ROSTER_DAYS_DIR = STATS_DIR / "roster_days"
ROSTER_CACHE_DIR = ROSTER_DAYS_DIR / "cache"

EVAL_YEARS = list(range(2010, 2027))
AB_IP_HISTORY_START = 1995
# statsapi active rosters are sparse before ~2009; AB/IP cover earlier burn cases.
ROSTER_HISTORY_START = 2009
MIN_OPENING_ROSTER_SIZE = 20
AB_THRESHOLD = 130
IP_THRESHOLD = 50.0
ROSTER_DAY_THRESHOLD = 45

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "whiffs-rookie-eligibility/1.0"})


def _convert_ip_to_decimal(ip: float) -> float:
    integer_part = int(ip)
    fractional_part = round(ip - integer_part, 1)
    if fractional_part == 0.1:
        return integer_part + (1 / 3)
    if fractional_part == 0.2:
        return integer_part + (2 / 3)
    return float(ip)


def _get_json(url: str, params: Optional[dict] = None, retries: int = 4) -> dict:
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            response = SESSION.get(url, params=params, timeout=60)
            if response.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed GET {url} params={params}: {last_err}")


def ensure_season_ab_ip(year: int) -> None:
    """Fetch batting AB / pitching IP for a season if CSVs are missing."""
    bat_path = STATS_DIR / f"{year}_bat.csv"
    pit_path = STATS_DIR / f"{year}_pit.csv"
    if bat_path.exists() and pit_path.exists():
        return

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Fetching AB/IP history for {year}...")

    if not bat_path.exists():
        data = _get_json(
            "https://statsapi.mlb.com/api/v1/stats",
            {
                "stats": "season",
                "season": year,
                "group": "hitting",
                "playerPool": "ALL",
                "limit": 5000,
            },
        )
        splits = (data.get("stats") or [{}])[0].get("splits", [])
        rows = []
        for split in splits:
            player = split.get("player") or {}
            stat = split.get("stat") or {}
            if not player.get("id"):
                continue
            rows.append(
                {
                    "playerId": player["id"],
                    "playerName": player.get("fullName", ""),
                    "season": year,
                    "AB": stat.get("atBats", 0) or 0,
                }
            )
        pd.DataFrame(rows).to_csv(bat_path, index=False)
        time.sleep(0.4)

    if not pit_path.exists():
        data = _get_json(
            "https://statsapi.mlb.com/api/v1/stats",
            {
                "stats": "season",
                "season": year,
                "group": "pitching",
                "playerPool": "ALL",
                "limit": 5000,
            },
        )
        splits = (data.get("stats") or [{}])[0].get("splits", [])
        rows = []
        for split in splits:
            player = split.get("player") or {}
            stat = split.get("stat") or {}
            if not player.get("id"):
                continue
            ip_raw = float(stat.get("inningsPitched", 0) or 0)
            rows.append(
                {
                    "playerId": player["id"],
                    "playerName": player.get("fullName", ""),
                    "season": year,
                    "IP": round(_convert_ip_to_decimal(ip_raw), 6),
                }
            )
        pd.DataFrame(rows).to_csv(pit_path, index=False)
        time.sleep(0.4)


def load_season_ab(year: int) -> Dict[int, int]:
    path = STATS_DIR / f"{year}_bat.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if "playerId" not in df.columns or "AB" not in df.columns:
        return {}
    df["playerId"] = pd.to_numeric(df["playerId"], errors="coerce")
    df["AB"] = pd.to_numeric(df["AB"], errors="coerce").fillna(0)
    df = df.dropna(subset=["playerId"])
    return {
        int(pid): int(ab)
        for pid, ab in df.groupby("playerId", sort=False)["AB"].sum().items()
    }


def load_season_ip(year: int) -> Dict[int, float]:
    path = STATS_DIR / f"{year}_pit.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if "playerId" not in df.columns or "IP" not in df.columns:
        return {}
    df["playerId"] = pd.to_numeric(df["playerId"], errors="coerce")
    df["IP"] = pd.to_numeric(df["IP"], errors="coerce").fillna(0).map(
        lambda x: _convert_ip_to_decimal(float(x))
    )
    df = df.dropna(subset=["playerId"])
    return {
        int(pid): float(ip)
        for pid, ip in df.groupby("playerId", sort=False)["IP"].sum().items()
    }


def season_date_bounds(year: int) -> Tuple[date, date]:
    data = _get_json(
        "https://statsapi.mlb.com/api/v1/seasons",
        {"sportId": 1, "season": year},
    )
    seasons = data.get("seasons") or []
    if not seasons:
        raise RuntimeError(f"No season metadata for {year}")
    info = seasons[0]
    start = datetime.strptime(info["regularSeasonStartDate"], "%Y-%m-%d").date()
    end = datetime.strptime(info["regularSeasonEndDate"], "%Y-%m-%d").date()
    if year <= 2019:
        end = min(end, date(year, 8, 31))
    return start, end


def mlb_team_ids(year: int) -> List[int]:
    data = _get_json(
        "https://statsapi.mlb.com/api/v1/teams",
        {"sportId": 1, "season": year},
    )
    teams = data.get("teams") or []
    return sorted(int(t["id"]) for t in teams if t.get("id"))


def fetch_active_roster(team_id: int, on_date: date, season: int) -> List[int]:
    data = _get_json(
        f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster",
        {
            "rosterType": "active",
            "date": on_date.isoformat(),
            "season": season,
        },
    )
    roster = data.get("roster") or []
    ids: List[int] = []
    for entry in roster:
        person = entry.get("person") or {}
        pid = person.get("id")
        if pid:
            ids.append(int(pid))
    return ids


def team_change_dates(
    team_id: int, start: date, end: date
) -> List[date]:
    data = _get_json(
        "https://statsapi.mlb.com/api/v1/transactions",
        {
            "teamId": team_id,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
        },
    )
    dates: Set[date] = set()
    for tx in data.get("transactions") or []:
        raw = tx.get("effectiveDate") or tx.get("date")
        if not raw:
            continue
        try:
            d = datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if start <= d <= end:
            dates.add(d)
    return sorted(dates)


def daterange(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def build_team_roster_timeline(
    team_id: int, year: int, start: date, end: date
) -> Dict[date, Set[int]]:
    """
    Fetch active roster at opening day and each transaction date, then fill
    intervening days with the last known roster.
    """
    change_dates = [start] + [
        d for d in team_change_dates(team_id, start, end) if d != start
    ]
    snapshots: Dict[date, Set[int]] = {}
    for d in change_dates:
        cache_path = ROSTER_CACHE_DIR / str(year) / f"{d.isoformat()}_team{team_id}.json"
        if cache_path.exists():
            ids = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            ids = fetch_active_roster(team_id, d, year)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(ids), encoding="utf-8")
            time.sleep(0.05)
        snapshots[d] = set(ids)

    timeline: Dict[date, Set[int]] = {}
    current: Set[int] = set()
    snap_iter = iter(sorted(snapshots.items()))
    next_snap = next(snap_iter, None)
    for d in daterange(start, end):
        while next_snap is not None and next_snap[0] <= d:
            current = set(next_snap[1])
            next_snap = next(snap_iter, None)
        timeline[d] = set(current)
    return timeline


def opening_roster_quality_ok(year: int, start: date, teams: List[int]) -> bool:
    """Reject seasons where statsapi returns incomplete historical active rosters."""
    sample = teams[: min(6, len(teams))]
    sizes = []
    for tid in sample:
        sizes.append(len(fetch_active_roster(tid, start, year)))
        time.sleep(0.05)
    median = sorted(sizes)[len(sizes) // 2] if sizes else 0
    ok = median >= MIN_OPENING_ROSTER_SIZE
    print(f"    Opening-roster quality sample sizes={sizes} median={median} ok={ok}")
    return ok


def build_roster_days_for_year(year: int, workers: int = 6) -> pd.DataFrame:
    out_path = ROSTER_DAYS_DIR / f"{year}.csv"
    if out_path.exists():
        print(f"  Roster days cache hit for {year}")
        return pd.read_csv(out_path)

    print(f"  Building roster-day ledger for {year}...")
    start, end = season_date_bounds(year)
    teams = mlb_team_ids(year)
    print(
        f"    Season window {start} → {end} ({(end - start).days + 1} days), "
        f"{len(teams)} teams"
    )

    if not opening_roster_quality_ok(year, start, teams):
        print(
            f"    Skipping roster API for {year} (incomplete historical data); "
            "AB/IP thresholds still apply"
        )
        df = pd.DataFrame(columns=["year", "playerId", "roster_days"])
        ROSTER_DAYS_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        return df

    day_counts: Dict[int, int] = {}
    ROSTER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _one_team(team_id: int) -> Dict[int, int]:
        timeline = build_team_roster_timeline(team_id, year, start, end)
        local: Dict[int, int] = {}
        for roster in timeline.values():
            for pid in roster:
                local[pid] = local.get(pid, 0) + 1
        return local

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one_team, tid): tid for tid in teams}
        for fut in as_completed(futures):
            tid = futures[fut]
            try:
                local = fut.result()
            except Exception as exc:
                print(f"    Warning: team {tid} roster timeline failed: {exc}")
                continue
            for pid, days in local.items():
                day_counts[pid] = day_counts.get(pid, 0) + days
            print(f"    Team {tid}: tracked {len(local)} players")

    rows = [
        {"year": year, "playerId": pid, "roster_days": days}
        for pid, days in sorted(day_counts.items())
    ]
    df = pd.DataFrame(rows)
    ROSTER_DAYS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"    Wrote {out_path} ({len(df)} players)")
    return df


def load_roster_days(year: int) -> Dict[int, int]:
    path = ROSTER_DAYS_DIR / f"{year}.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if df.empty:
        return {}
    df["playerId"] = pd.to_numeric(df["playerId"], errors="coerce")
    df["roster_days"] = pd.to_numeric(df["roster_days"], errors="coerce").fillna(0)
    df = df.dropna(subset=["playerId"])
    return {int(r.playerId): int(r.roster_days) for r in df.itertuples(index=False)}


def players_in_season_stats(year: int) -> Set[int]:
    ids: Set[int] = set()
    for suffix in ("bat", "pit"):
        path = STATS_DIR / f"{year}_{suffix}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "playerId" not in df.columns:
            continue
        for pid in pd.to_numeric(df["playerId"], errors="coerce").dropna():
            ids.add(int(pid))
    return ids


def cumulative_through(
    season_maps: Dict[int, Dict[int, float]], through_year: int
) -> Dict[int, float]:
    totals: Dict[int, float] = {}
    for year, mapping in season_maps.items():
        if year > through_year:
            continue
        for pid, val in mapping.items():
            totals[pid] = totals.get(pid, 0.0) + float(val)
    return totals


def build_rookie_csv(
    year: int,
    ab_by_year: Dict[int, Dict[int, int]],
    ip_by_year: Dict[int, Dict[int, float]],
    days_by_year: Dict[int, Dict[int, int]],
) -> pd.DataFrame:
    prior_ab = cumulative_through(ab_by_year, year - 1)
    prior_ip = cumulative_through(ip_by_year, year - 1)
    prior_days = cumulative_through(days_by_year, year - 1)

    season_ids = players_in_season_stats(year)
    rows = []
    for pid in sorted(season_ids):
        ab = int(prior_ab.get(pid, 0))
        ip = float(prior_ip.get(pid, 0.0))
        days = int(prior_days.get(pid, 0))
        if ab <= AB_THRESHOLD and ip <= IP_THRESHOLD and days <= ROSTER_DAY_THRESHOLD:
            rows.append(
                {
                    "year": year,
                    "playerId": pid,
                    "prior_ab": ab,
                    "prior_ip": round(ip, 3),
                    "prior_roster_days": days,
                }
            )
    return pd.DataFrame(rows)


def validate_known_cases(rookies_by_year: Dict[int, Set[int]]) -> None:
    """Spot-check a few public eligibility cases."""
    trout_2015 = 545361 in rookies_by_year.get(2015, set())
    print(f"  Validation: Mike Trout eligible entering 2015? {trout_2015} (expected False)")
    if trout_2015:
        print("    Warning: Trout unexpectedly marked eligible")

    adell_2021 = 666176 in rookies_by_year.get(2021, set())
    print(
        f"  Validation: Jo Adell eligible entering 2021? {adell_2021} (expected False)"
    )
    if adell_2021:
        print("    Warning: Adell unexpectedly marked eligible (roster-day rule)")

    julio_2022 = 677594 in rookies_by_year.get(2022, set())
    print(
        f"  Validation: Julio Rodriguez eligible entering 2022? {julio_2022} (expected True)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--eval-years",
        nargs="*",
        type=int,
        default=EVAL_YEARS,
        help="Seasons to write rookies/{year}.csv for",
    )
    parser.add_argument(
        "--roster-workers",
        type=int,
        default=6,
        help="Parallel team workers for roster-day builds",
    )
    parser.add_argument(
        "--skip-roster",
        action="store_true",
        help="Skip roster-day ledger (AB/IP only; not official)",
    )
    args = parser.parse_args()
    eval_years = sorted(args.eval_years)

    earliest_eval = min(eval_years)
    history_start = min(AB_IP_HISTORY_START, earliest_eval - 1)
    roster_start = min(ROSTER_HISTORY_START, earliest_eval - 1)
    history_end = max(eval_years)  # need year Y stats for cohort membership

    print("Ensuring AB/IP season files...")
    for year in range(history_start, history_end + 1):
        ensure_season_ab_ip(year)

    print("Loading AB/IP ledgers...")
    ab_by_year = {y: load_season_ab(y) for y in range(history_start, history_end + 1)}
    ip_by_year = {y: load_season_ip(y) for y in range(history_start, history_end + 1)}

    days_by_year: Dict[int, Dict[int, int]] = {}
    if not args.skip_roster:
        print("Building roster-day ledgers...")
        for year in range(roster_start, max(eval_years)):
            # Roster days in season S contribute to eligibility entering S+1 and later.
            df = build_roster_days_for_year(year, workers=args.roster_workers)
            days_by_year[year] = {
                int(r.playerId): int(r.roster_days)
                for r in df.itertuples(index=False)
            }
    else:
        print("WARNING: --skip-roster set; cohorts use AB/IP only")

    ROOKIES_DIR.mkdir(parents=True, exist_ok=True)
    rookies_by_year: Dict[int, Set[int]] = {}
    for year in eval_years:
        df = build_rookie_csv(year, ab_by_year, ip_by_year, days_by_year)
        out = ROOKIES_DIR / f"{year}.csv"
        df.to_csv(out, index=False)
        rookies_by_year[year] = set(int(x) for x in df["playerId"].tolist()) if not df.empty else set()
        print(f"Wrote {out} ({len(df)} eligible players in season stats)")

    validate_known_cases(rookies_by_year)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
