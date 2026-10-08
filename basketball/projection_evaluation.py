"""Evaluate NBA projection accuracy (Bricks) and write site cache."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
STATS_DIR = ROOT / "stats"
PROJECTIONS_DIR = ROOT / "projections"
REPORTS_DIR = ROOT / "reports"

sys.path.insert(0, str(ROOT / "utils"))
from baseline import (  # noqa: E402
    RATE_COLS,
    STAT_COLS,
    add_rate_stats,
    end_year_to_season,
)

PROJECTION_SYSTEMS: List[str] = ["Baseline"]
PROJECTION_SYSTEM_FILES: Dict[str, str] = {"Baseline": "baseline"}
PLAYER_TYPE = "player"
PLAYER_TYPES: List[str] = [PLAYER_TYPE]

VOLUME_STATS: List[str] = ["MIN", "G"]
RATE_STATS: List[str] = list(RATE_COLS)
PLAYING_TIME_COL = "MIN"
MISSING_PLAYING_TIME = 500

# Evaluate seasons where both actuals and Baseline projections exist.
def discover_years() -> List[int]:
    years: List[int] = []
    for path in sorted(PROJECTIONS_DIR.glob("baseline_????-??.csv")):
        # baseline_2023-24.csv -> end year 2024
        label = path.stem.replace("baseline_", "", 1)
        try:
            end_year = int(label.split("-")[0]) + 1
        except (ValueError, IndexError):
            continue
        if (STATS_DIR / f"{label}.csv").exists():
            years.append(end_year)
    return years


YEARS: List[int] = discover_years()


@dataclass
class ProjectionResult:
    year: int
    system: str
    player_type: str
    stat: str
    rmse: float
    mae: float
    bias: float
    r_squared: float
    la_rmse: float
    la_mae: float
    la_bias: float
    la_r_squared: float
    wla_rmse: float
    wla_mae: float
    wla_bias: float
    wla_r_squared: float
    n_players: int
    biggest_misses: List[Dict]
    unique_misses: List[Dict] = field(default_factory=list)
    all_misses: List[Dict] = field(default_factory=list, repr=False)


def calculate_metrics(
    actual: np.ndarray, projected: np.ndarray, weights: Optional[np.ndarray] = None
) -> Dict[str, float]:
    if len(actual) == 0 or len(projected) == 0:
        return {"rmse": np.nan, "mae": np.nan, "bias": np.nan, "r_squared": np.nan}

    errors = projected - actual
    mae = np.average(np.abs(errors), weights=weights)
    rmse = np.sqrt(np.average(errors**2, weights=weights))
    bias = np.average(errors, weights=weights)

    if weights is not None:
        ss_res = np.sum(weights * (errors**2))
        weighted_actual_mean = np.average(actual, weights=weights)
        ss_tot = np.sum(weights * ((actual - weighted_actual_mean) ** 2))
    else:
        ss_res = np.sum(errors**2)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)

    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    return {"rmse": rmse, "mae": mae, "bias": bias, "r_squared": max(0, r_squared)}


def collect_player_misses(
    df: pd.DataFrame,
    actual_col: str,
    proj_col: str,
    error_col: Optional[str] = None,
) -> List[Dict]:
    if actual_col not in df.columns or proj_col not in df.columns:
        return []

    errors = df[error_col] if error_col and error_col in df.columns else np.abs(
        df[proj_col] - df[actual_col]
    )

    misses = []
    for idx in df.index:
        err = errors.loc[idx]
        if pd.isna(err):
            continue
        misses.append(
            {
                "player_name": df.loc[idx, "playerName"],
                "actual": float(df.loc[idx, actual_col]),
                "projected": float(df.loc[idx, proj_col]),
                "error": float(err),
                "player_id": df.loc[idx, "playerId"],
            }
        )
    return misses


def find_biggest_misses(
    df: pd.DataFrame,
    actual_col: str,
    proj_col: str,
    n_misses: int = 20,
    error_col: Optional[str] = None,
    player_misses: Optional[List[Dict]] = None,
) -> List[Dict]:
    misses = player_misses
    if misses is None:
        misses = collect_player_misses(df, actual_col, proj_col, error_col=error_col)
    if not misses:
        return []
    ranked = sorted(misses, key=lambda m: m["error"], reverse=True)
    return ranked[: min(n_misses, len(ranked))]


def clear_all_misses(results: List[ProjectionResult]) -> None:
    for result in results:
        result.all_misses = []


def calculate_summary_stats(results: List[ProjectionResult]) -> Dict:
    summary: Dict[str, Any] = {}
    for system in PROJECTION_SYSTEMS:
        summary[system] = {}
        system_results = [r for r in results if r.system == system]
        if not system_results:
            continue
        summary[system][PLAYER_TYPE] = {
            "avg_rmse": float(np.nanmean([r.rmse for r in system_results])),
            "avg_mae": float(np.nanmean([r.mae for r in system_results])),
            "avg_r2": float(np.nanmean([r.r_squared for r in system_results])),
            "avg_la_rmse": float(np.nanmean([r.la_rmse for r in system_results])),
            "avg_la_mae": float(np.nanmean([r.la_mae for r in system_results])),
            "avg_la_r2": float(np.nanmean([r.la_r_squared for r in system_results])),
            "avg_wla_rmse": float(np.nanmean([r.wla_rmse for r in system_results])),
            "avg_wla_mae": float(np.nanmean([r.wla_mae for r in system_results])),
            "avg_wla_r2": float(np.nanmean([r.wla_r_squared for r in system_results])),
            "n_evaluations": len(system_results),
        }
    return summary


def load_actual_stats(end_year: int) -> pd.DataFrame:
    path = STATS_DIR / f"{end_year_to_season(end_year)}.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df = add_rate_stats(df)
    return df


def load_projections(end_year: int, system: str) -> pd.DataFrame:
    prefix = PROJECTION_SYSTEM_FILES.get(
        system, system.replace(" ", "").lower()
    )
    path = PROJECTIONS_DIR / f"{prefix}_{end_year_to_season(end_year)}.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "player_id" in df.columns and "playerId" not in df.columns:
        df = df.rename(columns={"player_id": "xPlayerId"})
    elif "playerId" in df.columns:
        df = df.rename(columns={"playerId": "xPlayerId"})
    # Ensure rates exist even if a future system ships counting stats only.
    missing_rates = [c for c in RATE_STATS if c not in df.columns]
    if missing_rates and all(c in df.columns for c in STAT_COLS):
        df = add_rate_stats(df)
    return df


def process_year_system(
    year: int, system: str
) -> tuple[List[ProjectionResult], Optional[pd.DataFrame]]:
    print(f"Processing {system} {end_year_to_season(year)}...")

    actual_df = load_actual_stats(year)
    proj_df = load_projections(year, system)
    if actual_df.empty or proj_df.empty:
        print("  Skipping - missing data")
        return [], None

    actual_df["playerId"] = actual_df["playerId"].astype(str)
    proj_df["xPlayerId"] = proj_df["xPlayerId"].astype(str)

    actual_league_avgs = {}
    for stat in RATE_STATS:
        if stat in actual_df.columns and PLAYING_TIME_COL in actual_df.columns:
            weights = actual_df[PLAYING_TIME_COL]
            if weights.sum() > 0:
                actual_league_avgs[stat] = float(np.average(actual_df[stat], weights=weights))

    merged_df = actual_df.merge(
        proj_df, left_on="playerId", right_on="xPlayerId", how="left", suffixes=("_x", "_y")
    )

    for stat in RATE_STATS:
        proj_col = f"{stat}_y"
        if proj_col in merged_df.columns and stat in actual_league_avgs:
            merged_df[proj_col] = merged_df[proj_col].fillna(actual_league_avgs[stat])

    for stat in VOLUME_STATS:
        proj_col = f"{stat}_y"
        if proj_col in merged_df.columns:
            fill = MISSING_PLAYING_TIME if stat == PLAYING_TIME_COL else 0
            merged_df[proj_col] = merged_df[proj_col].fillna(fill)

    playing_time_col_x = f"{PLAYING_TIME_COL}_x"
    proj_league_avgs = {}
    for stat in RATE_STATS:
        proj_col = f"{stat}_y"
        if proj_col in merged_df.columns and playing_time_col_x in merged_df.columns:
            weights = merged_df[playing_time_col_x]
            if weights.sum() > 0:
                proj_league_avgs[stat] = float(np.average(merged_df[proj_col], weights=weights))

    for stat in RATE_STATS:
        actual_col = f"{stat}_x"
        proj_col = f"{stat}_y"
        if (
            actual_col in merged_df.columns
            and proj_col in merged_df.columns
            and stat in actual_league_avgs
            and stat in proj_league_avgs
        ):
            merged_df[f"{stat}_actual_la"] = merged_df[actual_col] - actual_league_avgs[stat]
            merged_df[f"{stat}_proj_la"] = merged_df[proj_col] - proj_league_avgs[stat]

    print(f"  Found {len(merged_df)} players")
    results: List[ProjectionResult] = []
    all_stats = RATE_STATS + VOLUME_STATS

    for stat in all_stats:
        actual_col = f"{stat}_x"
        proj_col = f"{stat}_y"
        if actual_col not in merged_df.columns or proj_col not in merged_df.columns:
            continue

        actual_vals = merged_df[actual_col]
        proj_vals = merged_df[proj_col]
        mask = ~(actual_vals.isna() | proj_vals.isna())
        actual_clean = actual_vals[mask].values
        proj_clean = proj_vals[mask].values
        if len(actual_clean) == 0:
            continue

        if playing_time_col_x in merged_df.columns:
            weights = merged_df[playing_time_col_x][mask].values
        else:
            weights = np.ones(len(actual_clean))

        if stat in RATE_STATS:
            actual_la = actual_clean - actual_league_avgs[stat]
            proj_la = proj_clean - proj_league_avgs[stat]
            raw_metrics = calculate_metrics(actual_clean, proj_clean)
            la_metrics = calculate_metrics(actual_la, proj_la)
            wla_metrics = calculate_metrics(actual_la, proj_la, weights=weights)
            miss_errors = np.abs(actual_la - proj_la) * weights
        else:
            raw_metrics = calculate_metrics(actual_clean, proj_clean)
            la_metrics = raw_metrics
            wla_metrics = raw_metrics
            miss_errors = np.abs(actual_clean - proj_clean)

        temp_df = merged_df[mask].copy()
        temp_df["miss_error"] = miss_errors
        temp_df["actual_for_misses"] = actual_clean
        temp_df["proj_for_misses"] = proj_clean
        all_misses = collect_player_misses(
            temp_df, "actual_for_misses", "proj_for_misses", error_col="miss_error"
        )
        biggest_misses = find_biggest_misses(
            temp_df,
            "actual_for_misses",
            "proj_for_misses",
            error_col="miss_error",
            player_misses=all_misses,
        )

        results.append(
            ProjectionResult(
                year=year,
                system=system,
                player_type=PLAYER_TYPE,
                stat=stat,
                rmse=raw_metrics["rmse"],
                mae=raw_metrics["mae"],
                bias=raw_metrics["bias"],
                r_squared=raw_metrics["r_squared"],
                la_rmse=la_metrics["rmse"],
                la_mae=la_metrics["mae"],
                la_bias=la_metrics["bias"],
                la_r_squared=la_metrics["r_squared"],
                wla_rmse=wla_metrics["rmse"],
                wla_mae=wla_metrics["mae"],
                wla_bias=wla_metrics["bias"],
                wla_r_squared=wla_metrics["r_squared"],
                n_players=len(actual_clean),
                biggest_misses=biggest_misses,
                all_misses=all_misses,
            )
        )
        print(
            f"    {stat}: RMSE={raw_metrics['rmse']:.4f}, "
            f"LA-RMSE={la_metrics['rmse']:.4f}, WLA-RMSE={wla_metrics['rmse']:.4f}"
        )

    return results, merged_df


def generate_players_data_from_merged(merged_dataframes: Dict) -> List[Dict[str, Any]]:
    print("Generating player data from merged dataframes...")
    players_dict: Dict[Any, Dict[str, Any]] = {}

    for (year, system), merged_df in merged_dataframes.items():
        for _, row in merged_df.iterrows():
            player_id = row["playerId"]
            if player_id not in players_dict:
                players_dict[player_id] = {
                    "id": player_id,
                    "name": row.get("playerName", "Unknown"),
                    "years": {},
                    "primary_type": PLAYER_TYPE,
                }

    counting_and_rates = list(dict.fromkeys(STAT_COLS + RATE_STATS))

    for player_id, player_info in players_dict.items():
        for year in YEARS:
            type_data: Dict[str, Any] = {}
            actual_stats = None

            for system in PROJECTION_SYSTEMS:
                merged_df = merged_dataframes.get((year, system))
                if merged_df is None or player_id not in merged_df["playerId"].values:
                    continue
                player_row = merged_df[merged_df["playerId"] == player_id].iloc[0]

                if actual_stats is None:
                    actual_stats = {}
                    for stat in counting_and_rates:
                        actual_col = f"{stat}_x" if f"{stat}_x" in player_row.index else stat
                        if actual_col in player_row.index:
                            val = player_row[actual_col]
                            actual_stats[stat] = None if pd.isna(val) else val
                    for stat in RATE_STATS:
                        la_col = f"{stat}_actual_la"
                        if la_col in player_row.index:
                            val = player_row[la_col]
                            actual_stats[f"{stat}_la"] = None if pd.isna(val) else val
                    type_data["Actual"] = actual_stats

                proj_stats: Dict[str, Any] = {}
                for stat in counting_and_rates:
                    proj_col = f"{stat}_y"
                    if proj_col in player_row.index:
                        val = player_row[proj_col]
                        proj_stats[stat] = None if pd.isna(val) else val
                for stat in RATE_STATS:
                    la_col = f"{stat}_proj_la"
                    if la_col in player_row.index:
                        val = player_row[la_col]
                        proj_stats[f"{stat}_la"] = None if pd.isna(val) else val
                type_data[system] = proj_stats

            if type_data:
                player_info["years"][str(year)] = {PLAYER_TYPE: type_data}

    players_list = [p for p in players_dict.values() if p["years"]]
    players_list.sort(key=lambda x: str(x["id"]))
    print(f"  Prepared {len(players_list)} players for site pages")
    return players_list


def generate_summary_spreadsheet(results: List[ProjectionResult], output_dir: Path) -> None:
    rows = []
    for r in results:
        rows.append(
            {
                "Year": r.year,
                "Season": end_year_to_season(r.year),
                "System": r.system,
                "Stat": r.stat,
                "RMSE": r.rmse,
                "MAE": r.mae,
                "Bias": r.bias,
                "R2": r.r_squared,
                "LA_RMSE": r.la_rmse,
                "LA_MAE": r.la_mae,
                "WLA_RMSE": r.wla_rmse,
                "WLA_MAE": r.wla_mae,
                "N": r.n_players,
            }
        )
    df = pd.DataFrame(rows).sort_values(["Year", "Stat", "System"])
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "projection_summary.csv"
    df.to_csv(out_path, index=False)
    print(f"  Saved summary spreadsheet to {out_path}")


def result_to_dict(result: ProjectionResult) -> Dict[str, Any]:
    return {
        "system": result.system,
        "player_type": result.player_type,
        "stat": result.stat,
        "rmse": result.rmse,
        "mae": result.mae,
        "bias": result.bias,
        "r_squared": result.r_squared,
        "la_rmse": result.la_rmse,
        "la_mae": result.la_mae,
        "la_bias": result.la_bias,
        "la_r_squared": result.la_r_squared,
        "wla_rmse": result.wla_rmse,
        "wla_mae": result.wla_mae,
        "wla_bias": result.wla_bias,
        "wla_r_squared": result.wla_r_squared,
        "n_players": result.n_players,
        "biggest_misses": result.biggest_misses,
        "unique_misses": result.unique_misses,
    }


def run_evaluation() -> None:
    print("Starting basketball projection evaluation...")
    if not YEARS:
        raise SystemExit(
            "No overlapping seasons found under basketball/stats and "
            "basketball/projections. Run basketball:stats and basketball:baseline first."
        )

    print(f"Seasons: {', '.join(end_year_to_season(y) for y in YEARS)}")

    all_results: List[ProjectionResult] = []
    merged_dataframes: Dict = {}
    total = len(YEARS) * len(PROJECTION_SYSTEMS)
    current = 0

    for year in YEARS:
        for system in PROJECTION_SYSTEMS:
            current += 1
            print(f"\nProgress: {current}/{total}")
            results, merged_df = process_year_system(year, system)
            all_results.extend(results)
            if merged_df is not None:
                merged_dataframes[(year, system)] = merged_df

    print(f"\nCompleted evaluation. Total results: {len(all_results)}")
    clear_all_misses(all_results)

    years = sorted(set(r.year for r in all_results))
    summary = calculate_summary_stats(all_results)
    site_data = {
        "meta": {
            "years": years,
            "seasons": [end_year_to_season(y) for y in years],
            "projection_systems": PROJECTION_SYSTEMS,
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
        "years": years,
        "seasons": {str(y): end_year_to_season(y) for y in years},
        "summary": summary,
    }

    years_data: Dict[str, Any] = {}
    for year in YEARS:
        year_results = [r for r in all_results if r.year == year]
        if not year_results:
            continue
        years_data[str(year)] = {
            PLAYER_TYPE: [result_to_dict(r) for r in year_results],
        }

    misses_data: Dict[str, Any] = {}
    for year_str, data in years_data.items():
        player_misses: Dict[str, List] = {}
        for item in data.get(PLAYER_TYPE, []):
            if "biggest_misses" in item or "unique_misses" in item:
                stat = item["stat"]
                player_misses.setdefault(stat, []).append(
                    {
                        "system": item["system"],
                        "biggest_misses": item.pop("biggest_misses", []),
                        "unique_misses": item.pop("unique_misses", []),
                    }
                )
        misses_data[year_str] = {
            "player_misses": player_misses,
            "everybody_missed_player": {},
        }

    print("\nGenerating player pages data...")
    players_list = generate_players_data_from_merged(merged_dataframes)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generate_summary_spreadsheet(all_results, REPORTS_DIR)

    from site_builder import sanitize, save_site_cache

    print("\nCaching site data for HTML builds...")
    save_site_cache(
        sanitize(site_data),
        sanitize(years_data),
        sanitize(misses_data),
        sanitize(players_list),
    )

    print("\nEvaluation complete!")
    print(f"  Years: {len(site_data['years'])}")
    print(f"  Players: {len(players_list)}")
    print(f"  Summary CSV: {REPORTS_DIR / 'projection_summary.csv'}")
    print("  Site cache ready — run `npm run basketball:site` to render HTML")


if __name__ == "__main__":
    run_evaluation()
