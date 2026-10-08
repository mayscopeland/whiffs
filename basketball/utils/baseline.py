"""Marcel-like NBA projections (Baseline).

Weights the last three seasons 5/4/3, regresses counting stats toward league
average by a fixed minutes amount, projects minutes with a prior plus aging,
then scales everything (including G) to projected minutes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = ROOT / "stats"
PROJECTIONS_DIR = ROOT / "projections"

# Tunable Marcel-style knobs (retune after evaluation).
REGRESSION_MINUTES = 2000
MINUTES_PRIOR = 600
PEAK_AGE = 27
YOUNG_AGE_SLOPE = 0.006
OLD_AGE_SLOPE = -0.003

YEAR_WEIGHTS = {1: 5, 2: 4, 3: 3}  # seasons ago -> weight

# Projection seasons by end year: 2010 -> baseline_2009-10.csv (from 2008-09..2006-07).
FIRST_PROJ_END_YEAR = 2010
LAST_PROJ_END_YEAR = 2027

STAT_COLS = [
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

RATE_COLS = [
    "PTS/MIN",
    "OREB/MIN",
    "DREB/MIN",
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


def end_year_to_season(end_year: int) -> str:
    """Convert season end year (2024) to NBA label (2023-24)."""
    start = end_year - 1
    return f"{start}-{str(end_year)[-2:]}"


def _safe_div(numer: pd.Series, denom: pd.Series) -> pd.Series:
    result = numer.div(denom)
    return result.replace([float("inf"), float("-inf")], pd.NA).fillna(0)


def add_rate_stats(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["PTS/MIN"] = _safe_div(out["PTS"], out["MIN"])
    out["OREB/MIN"] = _safe_div(out["OREB"], out["MIN"])
    out["DREB/MIN"] = _safe_div(out["DREB"], out["MIN"])
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


def load_season_stats(end_years: list[int]) -> list[pd.DataFrame]:
    frames = []
    for end_year in end_years:
        path = STATS_DIR / f"{end_year_to_season(end_year)}.csv"
        if path.exists():
            df = pd.read_csv(path)
            df["end_year"] = end_year
            frames.append(df)
    return frames


def build_baseline_projections(target_end_year: int, player_bio: pd.DataFrame) -> list[dict]:
    year_weights = {
        target_end_year - ago: weight for ago, weight in YEAR_WEIGHTS.items()
    }
    all_stats_dfs = load_season_stats(list(year_weights.keys()))
    if not all_stats_dfs:
        return []

    total_league_stats = {col: 0.0 for col in STAT_COLS}
    for end_year, weight in year_weights.items():
        year_df = next(
            (df for df in all_stats_dfs if int(df["end_year"].iloc[0]) == end_year),
            None,
        )
        if year_df is None:
            continue
        league_year_stats = year_df[STAT_COLS].sum()
        if league_year_stats.get("MIN", 0) > 0:
            for field in STAT_COLS:
                total_league_stats[field] += float(league_year_stats[field]) * weight

    league_avg = {}
    if total_league_stats["MIN"] > 0:
        ratio = REGRESSION_MINUTES / total_league_stats["MIN"]
        for field in total_league_stats:
            league_avg[field] = total_league_stats[field] * ratio

    all_stats = pd.concat(all_stats_dfs, ignore_index=True)

    min_last_year = (
        all_stats[all_stats["end_year"] == target_end_year - 1]
        .set_index("playerId")["MIN"]
    )
    min_two_years_ago = (
        all_stats[all_stats["end_year"] == target_end_year - 2]
        .set_index("playerId")["MIN"]
    )

    all_stats["weight"] = all_stats["end_year"].map(year_weights)
    for col in STAT_COLS:
        all_stats[f"w_{col}"] = all_stats[col].fillna(0) * all_stats["weight"]

    weighted_totals = all_stats.groupby("playerId")[
        [f"w_{col}" for col in STAT_COLS]
    ].sum()
    weighted_totals.columns = [c.replace("w_", "") for c in weighted_totals.columns]

    projections = weighted_totals.copy()
    for col in STAT_COLS:
        projections[col] = projections[col] + league_avg.get(col, 0)

    projections["min_last_year"] = projections.index.map(min_last_year).fillna(0)
    projections["min_two_years_ago"] = projections.index.map(min_two_years_ago).fillna(0)
    projections["projected_min"] = (
        0.5 * projections["min_last_year"]
        + 0.1 * projections["min_two_years_ago"]
        + MINUTES_PRIOR
    )

    projections = projections.merge(
        player_bio[["playerId", "birthYear"]],
        left_index=True,
        right_on="playerId",
        how="inner",
    )
    projections["age"] = target_end_year - projections["birthYear"]

    age_adj = pd.Series(1.0, index=projections.index)
    older = projections["age"] > PEAK_AGE
    younger = projections["age"] < PEAK_AGE
    age_adj.loc[older] = 1.0 + (
        (projections.loc[older, "age"] - PEAK_AGE) * OLD_AGE_SLOPE
    )
    age_adj.loc[younger] = 1.0 + (
        (PEAK_AGE - projections.loc[younger, "age"]) * YOUNG_AGE_SLOPE
    )
    projections["projected_min"] *= age_adj.values

    min_ratio = (projections["projected_min"] / projections["MIN"]).fillna(0)
    for col in STAT_COLS:
        if col == "MIN":
            projections[col] = projections["projected_min"]
        else:
            projections[col] = projections[col] * min_ratio

    # Round counting stats; keep MIN to one decimal like innings-style playing time.
    for col in STAT_COLS:
        if col == "MIN":
            projections[col] = projections[col].round(1)
        else:
            projections[col] = projections[col].round()

    projections = add_rate_stats(projections)
    for col in RATE_COLS:
        projections[col] = projections[col].round(6)
    projections = projections.rename(columns={"playerId": "player_id"})

    output_cols = ["player_id"] + STAT_COLS + RATE_COLS
    return projections[output_cols].to_dict("records")


def main() -> None:
    PROJECTIONS_DIR.mkdir(parents=True, exist_ok=True)

    bio_path = STATS_DIR / "player_bio.csv"
    if not bio_path.exists():
        raise SystemExit(
            f"Missing {bio_path}. Run: npm run basketball:stats"
        )

    player_bio = pd.read_csv(bio_path)

    for end_year in range(FIRST_PROJ_END_YEAR, LAST_PROJ_END_YEAR + 1):
        season = end_year_to_season(end_year)
        print(f"Generating Baseline projections for {season}...")
        try:
            records = build_baseline_projections(end_year, player_bio)
            if records:
                out_path = PROJECTIONS_DIR / f"baseline_{season}.csv"
                pd.DataFrame(records).to_csv(out_path, index=False)
                print(f"    Saved {len(records)} projections to {out_path}")
            else:
                print(f"    No projections generated for {season}")
        except Exception as exc:
            print(f"    Error generating projections for {season}: {exc}")
            import traceback

            traceback.print_exc()

    print("Baseline projection generation complete!")


if __name__ == "__main__":
    main()
