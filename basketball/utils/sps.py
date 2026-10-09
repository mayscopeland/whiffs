"""Basketball-Reference Simple Projection System, plus games and minutes.

Published SPS projects per-36 rates only. The last three seasons are weighted
6/3/1, each rate is regressed with 1,000 minutes of league-average production
at the player's own minute mix, and age adjusts around 28. Missed shots,
turnovers, and fouls take the opposite age adjustment. Attempts are made plus
missed, and points are computed from the makes.

Games and minutes are not on the Basketball-Reference page. This version
projects minutes with a Marcel split: half of last year's minutes, a tenth of
the minutes from two seasons ago, and a 600-minute prior, then an age curve
around 27. Minutes per game come from the SPS weights plus 1,000 minutes of
league-average games, and games are projected minutes divided by that rate.

A player is projected only if he played at least one game the previous season.
"""

from __future__ import annotations

import argparse
import math
import re
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd

from rates import STAT_COLS, add_rate_stats, end_year_to_season

ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = ROOT / "stats"
PROJECTIONS_DIR = ROOT / "projections"
BIRTH_DATES_PATH = STATS_DIR / "player_birth_dates.csv"
ROSTER_URL = (
    "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
    "nba_stats_rosters/rosters_{year}.csv"
)
ROSTER_YEARS = range(2006, 2027)

# Projection seasons by end year: 2010 -> sps_2009-10.csv.
FIRST_PROJ_END_YEAR = 2010
LAST_PROJ_END_YEAR = 2027

YEAR_WEIGHTS = {1: 6, 2: 3, 3: 1}  # seasons ago -> weight
REGRESSION_MINUTES = 1000
RATE_PEAK_AGE = 28
YOUNG_RATE_SLOPE = 0.004
OLD_RATE_SLOPE = 0.002

# Marcel minutes: half of last year, a tenth of two years ago, then this prior.
MINUTES_PRIOR = 600
PEAK_AGE = 27
YOUNG_AGE_SLOPE = 0.006
OLD_AGE_SLOPE = -0.003

# Counting pieces inside the per-36 formula. True means the age adjustment
# is reversed (misses and turnovers).
COMPONENTS: list[tuple[str, bool]] = [
    ("FGM", False),
    ("FG_MISS", True),
    ("FG3M", False),
    ("FG3_MISS", True),
    ("FTM", False),
    ("FT_MISS", True),
    ("OREB", False),
    ("DREB", False),
    ("AST", False),
    ("STL", False),
    ("BLK", False),
    ("TOV", True),
]

BR_URL = "https://www.basketball-reference.com/friv/projections.cgi?year={year}"
BR_COLUMNS = {
    "fg_per_mp": "FGM",
    "fga_per_mp": "FGA",
    "fg3_per_mp": "FG3M",
    "fg3a_per_mp": "FG3A",
    "ft_per_mp": "FTM",
    "fta_per_mp": "FTA",
    "orb_per_mp": "OREB",
    "trb_per_mp": "REB",
    "ast_per_mp": "AST",
    "stl_per_mp": "STL",
    "blk_per_mp": "BLK",
    "tov_per_mp": "TOV",
    "pts_per_mp": "PTS",
    "fg_pct": "FGM/FGA",
    "fg3_pct": "FG3M/FG3A",
    "ft_pct": "FTM/FTA",
}


def _round_half_up(value: float, places: int) -> float:
    factor = 10**places
    return math.floor(value * factor + 0.5) / factor


def _integer_minutes(minutes: pd.Series) -> pd.Series:
    """Basketball-Reference uses whole minutes in the worked example."""
    return minutes.map(lambda value: _round_half_up(float(value), 0))


def _prepare_season(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in ("G", "MIN", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB", "AST", "STL", "BLK", "TOV"):
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    out["MIN_BR"] = _integer_minutes(out["MIN"])
    out["FG_MISS"] = (out["FGA"] - out["FGM"]).clip(lower=0)
    out["FG3_MISS"] = (out["FG3A"] - out["FG3M"]).clip(lower=0)
    out["FT_MISS"] = (out["FTA"] - out["FTM"]).clip(lower=0)
    return out


def ensure_birth_dates() -> pd.DataFrame:
    """NBA id to birth date, from seasonal rosters. February 1 age needs the day."""
    if BIRTH_DATES_PATH.exists():
        frame = pd.read_csv(BIRTH_DATES_PATH)
        frame["playerId"] = frame["playerId"].astype(int)
        frame["birthDate"] = pd.to_datetime(frame["birthDate"])
        return frame

    frames = []
    for year in ROSTER_YEARS:
        request = urllib.request.Request(
            ROSTER_URL.format(year=year),
            headers={"User-Agent": "Mozilla/5.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                roster = pd.read_csv(response)
        except Exception as exc:
            print(f"    Skipping roster {year}: {exc}")
            continue
        if "player_id" not in roster.columns or "birth_date" not in roster.columns:
            continue
        frames.append(roster[["player_id", "birth_date"]])
    if not frames:
        return pd.DataFrame(columns=["playerId", "birthDate"])

    dates = pd.concat(frames, ignore_index=True)
    dates["playerId"] = pd.to_numeric(dates["player_id"], errors="coerce")
    dates["birthDate"] = pd.to_datetime(
        dates["birth_date"].astype(str).str.title(),
        format="%b %d, %Y",
        errors="coerce",
    )
    dates = dates.dropna(subset=["playerId", "birthDate"])
    dates["playerId"] = dates["playerId"].astype(int)
    dates = dates.drop_duplicates("playerId")[["playerId", "birthDate"]]
    BIRTH_DATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    dates.to_csv(BIRTH_DATES_PATH, index=False)
    print(f"    Saved {len(dates)} birth dates to {BIRTH_DATES_PATH}")
    return dates


def _february_first_age(birth_date: pd.Series, end_year: int, fallback: pd.Series) -> pd.Series:
    """Age on February 1 of the season's ending year, matching Basketball-Reference."""
    month = birth_date.dt.month
    day = birth_date.dt.day
    age = end_year - birth_date.dt.year
    after_feb1 = (month > 2) | ((month == 2) & (day > 1))
    age = age.where(~after_feb1, age - 1)
    return age.where(birth_date.notna(), fallback)


def _rate_age_delta(age: pd.Series) -> pd.Series:
    delta = pd.Series(0.0, index=age.index)
    younger = age < RATE_PEAK_AGE
    older = age > RATE_PEAK_AGE
    delta.loc[younger] = (RATE_PEAK_AGE - age.loc[younger]) * YOUNG_RATE_SLOPE
    delta.loc[older] = (RATE_PEAK_AGE - age.loc[older]) * OLD_RATE_SLOPE
    return delta


def _minutes_age_factor(age: pd.Series) -> pd.Series:
    factor = pd.Series(1.0, index=age.index)
    older = age > PEAK_AGE
    younger = age < PEAK_AGE
    factor.loc[older] = 1.0 + (age.loc[older] - PEAK_AGE) * OLD_AGE_SLOPE
    factor.loc[younger] = 1.0 + (PEAK_AGE - age.loc[younger]) * YOUNG_AGE_SLOPE
    return factor


def _load_window(target_end_year: int) -> tuple[pd.DataFrame, dict[int, dict[str, float]]] | None:
    year_weights = {
        target_end_year - ago: weight for ago, weight in YEAR_WEIGHTS.items()
    }
    frames = []
    league_rates: dict[int, dict[str, float]] = {}
    for end_year, weight in year_weights.items():
        path = STATS_DIR / f"{end_year_to_season(end_year)}.csv"
        if not path.exists():
            continue
        season = _prepare_season(pd.read_csv(path))
        season["end_year"] = end_year
        season["weight"] = weight
        minutes = float(season["MIN_BR"].sum())
        rates = {}
        for col, _reversed in COMPONENTS:
            rates[col] = float(season[col].sum()) / minutes if minutes else 0.0
        # Games per minute, for the minutes-per-game regression.
        rates["G"] = float(season["G"].sum()) / minutes if minutes else 0.0
        league_rates[end_year] = rates
        frames.append(season)
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True), league_rates


def build_sps_frame(
    target_end_year: int,
    player_bio: pd.DataFrame,
    birth_dates: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Per-36 rates plus projected games and minutes for one season."""
    loaded = _load_window(target_end_year)
    if loaded is None:
        return pd.DataFrame()
    all_stats, league_rates = loaded

    last_year = target_end_year - 1
    last = all_stats[all_stats["end_year"] == last_year]
    last = last[last["G"] >= 1]
    if last.empty:
        return pd.DataFrame()
    all_stats = all_stats[all_stats["playerId"].isin(last["playerId"])].copy()

    all_stats["w_min"] = all_stats["MIN_BR"] * all_stats["weight"]
    all_stats["w_min_raw"] = all_stats["MIN"] * all_stats["weight"]
    all_stats["w_g"] = all_stats["G"] * all_stats["weight"]
    for col, _reversed in COMPONENTS:
        all_stats[f"w_{col}"] = all_stats[col] * all_stats["weight"]
        rate_map = {year: rates[col] for year, rates in league_rates.items()}
        all_stats[f"lg_{col}"] = all_stats["w_min"] * all_stats["end_year"].map(rate_map)
    g_rate_map = {year: rates["G"] for year, rates in league_rates.items()}
    all_stats["lg_g"] = all_stats["w_min"] * all_stats["end_year"].map(g_rate_map)

    sum_cols = ["w_min", "w_min_raw", "w_g", "lg_g"] + [
        f"w_{col}" for col, _reversed in COMPONENTS
    ] + [f"lg_{col}" for col, _reversed in COMPONENTS]
    grouped = all_stats.groupby("playerId")[sum_cols].sum()
    grouped = grouped[grouped["w_min"] > 0]
    if grouped.empty:
        return pd.DataFrame()

    per36 = pd.DataFrame(index=grouped.index)
    for col, reversed_age in COMPONENTS:
        blended = REGRESSION_MINUTES * (grouped[f"lg_{col}"] / grouped["w_min"])
        per36[col] = (grouped[f"w_{col}"] + blended) / (grouped["w_min"] + REGRESSION_MINUTES) * 36

    per36 = per36.merge(
        player_bio[["playerId", "playerName", "birthYear"]],
        left_index=True,
        right_on="playerId",
        how="inner",
    )
    if birth_dates is not None and not birth_dates.empty:
        per36 = per36.merge(birth_dates, on="playerId", how="left")
    else:
        per36["birthDate"] = pd.NaT
    fallback_age = target_end_year - per36["birthYear"]
    per36["age"] = _february_first_age(per36["birthDate"], target_end_year, fallback_age)
    age_delta = _rate_age_delta(per36["age"])
    for col, reversed_age in COMPONENTS:
        factor = 1.0 - age_delta if reversed_age else 1.0 + age_delta
        per36[col] = per36[col] * factor.to_numpy()

    per36["FGA"] = per36["FGM"] + per36["FG_MISS"]
    per36["FG3A"] = per36["FG3M"] + per36["FG3_MISS"]
    per36["FTA"] = per36["FTM"] + per36["FT_MISS"]
    per36["PTS"] = 2 * per36["FGM"] + per36["FG3M"] + per36["FTM"]
    per36["REB"] = per36["OREB"] + per36["DREB"]

    min_last = last.set_index("playerId")["MIN"]
    two_years = all_stats[all_stats["end_year"] == target_end_year - 2].drop_duplicates(
        "playerId"
    )
    min_two = two_years.set_index("playerId")["MIN"]
    per36["projected_min"] = (
        0.5 * per36["playerId"].map(min_last).fillna(0)
        + 0.1 * per36["playerId"].map(min_two).fillna(0)
        + MINUTES_PRIOR
    )
    per36["projected_min"] *= _minutes_age_factor(per36["age"]).to_numpy()

    regressed_games = grouped["w_g"] + REGRESSION_MINUTES * (
        grouped["lg_g"] / grouped["w_min"]
    )
    regressed_minutes = grouped["w_min"] + REGRESSION_MINUTES
    mpg = (regressed_minutes / regressed_games).replace([float("inf")], pd.NA)
    per36["projected_g"] = per36["projected_min"] / per36["playerId"].map(mpg)
    return per36


def build_sps_projections(
    target_end_year: int,
    player_bio: pd.DataFrame,
    birth_dates: pd.DataFrame | None = None,
) -> list[dict]:
    per36 = build_sps_frame(target_end_year, player_bio, birth_dates)
    if per36.empty:
        return []

    projections = per36.copy()
    scale = projections["projected_min"] / 36
    for col in STAT_COLS:
        if col == "MIN":
            projections[col] = projections["projected_min"]
        elif col == "G":
            projections[col] = projections["projected_g"]
        else:
            projections[col] = projections[col] * scale

    for col in STAT_COLS:
        if col == "MIN":
            projections[col] = projections[col].round(1)
        else:
            projections[col] = projections[col].round()

    projections = add_rate_stats(projections)
    projections = projections.rename(columns={"playerId": "player_id"})
    output_cols = ["player_id"] + STAT_COLS
    rate_cols = [col for col in projections.columns if "/" in col]
    return projections[output_cols + rate_cols].to_dict("records")


def _norm_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(text.split())


def fetch_br_projections(end_year: int) -> pd.DataFrame:
    """Published per-36 projections for the season ending in ``end_year``."""
    request = urllib.request.Request(
        BR_URL.format(year=end_year),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode("utf-8", "replace")
    # Older season tables are wrapped in comments for Basketball-Reference's JS.
    html = html.replace("<!--", "").replace("-->", "")

    rows = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S):
        if "Projected" not in row_html:
            continue
        name_match = re.search(
            r'data-stat="player"[^>]*>(?:<a[^>]*>)?([^<]+)',
            row_html,
        )
        if name_match is None:
            continue
        stats = {
            stat: value
            for stat, value in re.findall(
                r'data-stat="([^"]+)"\s*>\s*([0-9.]+)',
                row_html,
            )
        }
        if "fg_per_mp" not in stats:
            continue
        record = {"player_name": name_match.group(1).strip()}
        for source, dest in BR_COLUMNS.items():
            if source in stats:
                record[dest] = float(stats[source])
        rows.append(record)
    if not rows:
        raise SystemExit(f"No projected rows parsed from Basketball-Reference for {end_year}.")
    return pd.DataFrame(rows)


def compare_to_basketball_reference(
    end_year: int,
    player_bio: pd.DataFrame,
    birth_dates: pd.DataFrame | None = None,
) -> None:
    """Print how our per-36 rates differ from the published SPS page."""
    ours = build_sps_frame(end_year, player_bio, birth_dates)
    if ours.empty:
        raise SystemExit(f"No SPS projections for {end_year_to_season(end_year)}.")
    published = fetch_br_projections(end_year)
    ours["name_key"] = ours["playerName"].map(_norm_name)
    published["name_key"] = published["player_name"].map(_norm_name)
    ours = ours.drop_duplicates("name_key")
    published = published.drop_duplicates("name_key")
    merged = published.merge(ours, on="name_key", suffixes=("_br", "_ours"))
    print(
        f"{end_year_to_season(end_year)}: published {len(published)}, "
        f"ours {len(ours)}, matched {len(merged)}"
    )

    counting = ["FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "REB", "AST", "STL", "BLK", "TOV", "PTS"]
    exact_cells = 0
    total_cells = 0
    for col in counting:
        br_col = f"{col}_br"
        ours_col = f"{col}_ours"
        ours_rounded = merged[ours_col].map(lambda value: _round_half_up(float(value), 1))
        diff = (ours_rounded - merged[br_col]).abs()
        exact = int((diff < 0.001).sum())
        exact_cells += exact
        total_cells += len(merged)
        print(
            f"  {col}: exact {exact}/{len(merged)} "
            f"mean |d| {diff.mean():.4f} max {diff.max():.1f}"
        )

    for col in ("FGM/FGA", "FG3M/FG3A", "FTM/FTA"):
        numer, denom = col.split("/")
        ratio = merged[f"{numer}_ours"] / merged[f"{denom}_ours"].replace(0, pd.NA)
        ours_rounded = ratio.map(
            lambda value: _round_half_up(float(value), 3) if pd.notna(value) else pd.NA
        )
        published_col = f"{col}_br" if f"{col}_br" in merged.columns else col
        published_vals = merged[published_col]
        comparable = ours_rounded.notna() & published_vals.notna()
        diff = (ours_rounded[comparable] - published_vals[comparable]).abs()
        exact = int((diff < 0.0005).sum())
        print(
            f"  {col}: exact {exact}/{int(comparable.sum())} "
            f"mean |d| {diff.mean():.5f} max {diff.max():.3f}"
        )
    print(f"  counting cells exact at 1 decimal: {exact_cells}/{total_cells}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SPS projections.")
    parser.add_argument(
        "--check",
        type=int,
        action="append",
        default=[],
        help="Season end year to compare against Basketball-Reference, e.g. 2025.",
    )
    args = parser.parse_args()

    bio_path = STATS_DIR / "player_bio.csv"
    if not bio_path.exists():
        raise SystemExit(f"Missing {bio_path}. Run: npm run basketball:stats")
    player_bio = pd.read_csv(bio_path)
    birth_dates = ensure_birth_dates()

    if args.check:
        for end_year in args.check:
            compare_to_basketball_reference(end_year, player_bio, birth_dates)
        return

    PROJECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    for end_year in range(FIRST_PROJ_END_YEAR, LAST_PROJ_END_YEAR + 1):
        season = end_year_to_season(end_year)
        print(f"Generating SPS projections for {season}...")
        try:
            records = build_sps_projections(end_year, player_bio, birth_dates)
            if records:
                out_path = PROJECTIONS_DIR / f"sps_{season}.csv"
                pd.DataFrame(records).to_csv(out_path, index=False)
                print(f"    Saved {len(records)} projections to {out_path}")
            else:
                print(f"    No projections generated for {season}")
        except Exception as exc:
            print(f"    Error generating projections for {season}: {exc}")
            import traceback

            traceback.print_exc()

    print("SPS projection generation complete!")


if __name__ == "__main__":
    main()
