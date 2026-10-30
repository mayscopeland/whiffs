"""Evaluate NFL projection accuracy (Drops) and write the site cache.

Each pool scores counting stats per game (attempts, yards, touchdowns, and so
on). A player can land in more than one pool. Projections without games played
are treated as a full season. With no projection files, this still writes an
empty cache so the site can render.
"""

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
ADP_DIR = ROOT / "adp"

# Offensive players on the FantasyPros half-PPR preseason board. Kickers and
# defenses are already absent from football/adp/.
FAN_ADP_TOP_N = 150

sys.path.insert(0, str(ROOT / "utils"))
from rates import (  # noqa: E402
    PLAYER_TYPES,
    POOLS,
    add_rate_stats,
    ensure_projection_games,
    scored_rate_stats,
)

PROJECTION_SYSTEMS: List[str] = [
    "ESPN",
    "Sleeper",
    "FFToday",
    "FantasyPros",
]
# Display name -> CSV file prefix when they differ (default: spaces removed, lowercased)
PROJECTION_SYSTEM_FILES: Dict[str, str] = {
    "ESPN": "espn",
    "Sleeper": "sleeper",
    "FFToday": "fftoday",
    "FantasyPros": "fantasypros",
}


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


def as_player_id(series: pd.Series) -> pd.Series:
    """Player ids as strings. Slugs stay as-is, and 382.0 joins 382."""

    def one(value: object) -> object:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return pd.NA
        text = str(value).strip()
        if text.lower() in {"", "nan", "none", "<na>"}:
            return pd.NA
        if text.endswith(".0"):
            text = text[:-2]
        return text

    return series.map(one)


def discover_years() -> List[int]:
    """Seasons with actuals and at least one known projection file."""
    years: set[int] = set()
    for prefix in PROJECTION_SYSTEM_FILES.values():
        for path in sorted(PROJECTIONS_DIR.glob(f"{prefix}_????.csv")):
            year_text = path.stem.rsplit("_", 1)[-1]
            try:
                year = int(year_text)
            except ValueError:
                continue
            if (STATS_DIR / f"{year}.csv").exists():
                years.add(year)
    return sorted(years)


YEARS: List[int] = discover_years()


def load_actual_stats(year: int) -> pd.DataFrame:
    path = STATS_DIR / f"{year}.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if "nfl_slug" not in frame.columns:
        return pd.DataFrame()
    frame["player_id"] = as_player_id(frame["nfl_slug"])
    frame = frame.drop(columns=["nfl_slug"])
    frame = frame[frame["player_id"].notna()]
    if "G" not in frame.columns:
        print(f"Warning: {path.name} has no G column; re-run npm run football:stats")
        return pd.DataFrame()
    frame["G"] = pd.to_numeric(frame["G"], errors="coerce")
    return add_rate_stats(frame)


def load_projections(year: int, system: str) -> pd.DataFrame:
    file_prefix = PROJECTION_SYSTEM_FILES.get(system, system.replace(" ", "").lower())
    path = PROJECTIONS_DIR / f"{file_prefix}_{year}.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    id_column = next(
        (col for col in ("nfl_slug", "player_id", "playerId", "nfl_id") if col in frame.columns),
        None,
    )
    if id_column is None:
        return pd.DataFrame()
    frame = frame.rename(columns={id_column: "xPlayerId"})
    frame["xPlayerId"] = as_player_id(frame["xPlayerId"])
    frame = frame[frame["xPlayerId"].notna()]
    frame = ensure_projection_games(frame, year)
    return add_rate_stats(frame)


def merged_column(frame: pd.DataFrame, stat: str, suffix: str) -> Optional[str]:
    """Stat column renamed before the merge so each side keeps its own values."""
    column = f"{stat}{suffix}"
    if column in frame.columns:
        return column
    return None


def weighted_mean(values: pd.Series, weights: pd.Series) -> Optional[float]:
    mask = values.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        return None
    return float(np.average(values[mask], weights=weights[mask]))


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


def find_biggest_misses(player_misses: List[Dict], n_misses: int = 20) -> List[Dict]:
    ranked = sorted(player_misses, key=lambda miss: miss["error"], reverse=True)
    return ranked[: min(n_misses, len(ranked))]


def clear_all_misses(results: List[ProjectionResult]) -> None:
    for result in results:
        result.all_misses = []


def load_fantasy_adp_ids(year: int, top_n: int = FAN_ADP_TOP_N) -> List[str]:
    """Return nfl_slugs for the top offensive players in a season's preseason ADP."""
    path = ADP_DIR / f"fantasypros_{year}.csv"
    if not path.exists():
        return []

    adp = pd.read_csv(path)
    if "rank" not in adp.columns or "nfl_slug" not in adp.columns:
        print(f"Warning: {path} missing rank/nfl_slug columns")
        return []

    adp["rank"] = pd.to_numeric(adp["rank"], errors="coerce")
    adp["nfl_slug"] = as_player_id(adp["nfl_slug"])
    top = adp.dropna(subset=["rank"]).sort_values(["rank"], kind="mergesort")
    if "position" in top.columns:
        position = top["position"].astype(str).str.upper()
        top = top.loc[~position.isin(["K", "DST", "DEF"])]
    window = top.head(top_n)
    missing = int(window["nfl_slug"].isna().sum())
    if missing:
        print(f"Warning: {missing} of the top-{top_n} ADP players in {year} have no nfl_slug")
    ids = (
        window.dropna(subset=["nfl_slug"])
        .drop_duplicates(subset=["nfl_slug"], keep="first")["nfl_slug"]
        .astype(str)
        .tolist()
    )
    return ids


def restrict_pool(frame: pd.DataFrame, volume: str, minimum: float, *, at_least: bool) -> pd.DataFrame:
    if volume not in frame.columns:
        return frame.iloc[0:0].copy()
    values = pd.to_numeric(frame[volume], errors="coerce").fillna(0)
    mask = values >= minimum if at_least else values > minimum
    return frame.loc[mask].copy()


def evaluate_pool(
    year: int,
    system: str,
    player_type: str,
    *,
    fantasy: bool,
) -> tuple[List[ProjectionResult], Optional[pd.DataFrame]]:
    pool = POOLS[player_type]
    label = f"fan_{player_type}" if fantasy else player_type
    print(f"Processing {system} {year} {label}...")

    actual_df = load_actual_stats(year)
    proj_df = load_projections(year, system)
    if actual_df.empty or proj_df.empty:
        print("  Skipping - missing data")
        return [], None

    membership = pool.get("membership", pool["volume"])
    weight_col = pool.get("weight", pool["volume"])
    rate_stats = scored_rate_stats(pool)
    if fantasy:
        adp_ids = load_fantasy_adp_ids(year, FAN_ADP_TOP_N)
        if not adp_ids:
            print(f"  Skipping - no FantasyPros top-{FAN_ADP_TOP_N} ADP for {year}")
            return [], None
        actual_df = actual_df[actual_df["player_id"].isin(adp_ids)]
    actual_df = restrict_pool(actual_df, membership, 0, at_least=False)
    actual_df = restrict_pool(actual_df, weight_col, 0, at_least=False)
    if actual_df.empty:
        print("  Skipping - no players in this pool")
        return [], None
    if fantasy:
        print(f"  Using {len(actual_df)} {player_type} players from top-{FAN_ADP_TOP_N} ADP")

    # Only score per-game stats this projection can derive (counting numerators
    # present after rates are added). Missing targets still skips TGT/G.
    stat_names = [stat for stat in rate_stats if stat in proj_df.columns]
    if not stat_names:
        print("  Skipping - projection has no stats for this pool")
        return [], None

    actual_league_avgs = {
        stat: weighted_mean(actual_df[stat], actual_df[weight_col])
        for stat in rate_stats
        if stat in actual_df.columns
    }
    actual_league_avgs = {stat: avg for stat, avg in actual_league_avgs.items() if avg is not None}

    actual_df = actual_df.rename(columns={"player_id": "playerId", "player_name": "playerName"})
    proj_df = proj_df.rename(columns={"xPlayerId": "xPlayerId"})
    if "player_name" in proj_df.columns:
        proj_df = proj_df.rename(columns={"player_name": "projName"})
    actual_df = actual_df.rename(
        columns={col: f"{col}_x" for col in actual_df.columns if col not in {"playerId", "playerName"}}
    )
    proj_df = proj_df.rename(
        columns={col: f"{col}_y" for col in proj_df.columns if col not in {"xPlayerId", "projName"}}
    )

    merged = actual_df.merge(proj_df, left_on="playerId", right_on="xPlayerId", how="left")
    if "playerName_x" in merged.columns:
        merged["playerName"] = merged["playerName_x"]

    for stat in rate_stats:
        proj_col = merged_column(merged, stat, "_y")
        if proj_col is not None and stat in actual_league_avgs:
            merged[proj_col] = merged[proj_col].fillna(actual_league_avgs[stat])

    actual_weight = merged_column(merged, weight_col, "_x")
    proj_league_avgs = {}
    for stat in rate_stats:
        proj_col = merged_column(merged, stat, "_y")
        if proj_col is not None and actual_weight is not None:
            avg = weighted_mean(merged[proj_col], merged[actual_weight])
            if avg is not None:
                proj_league_avgs[stat] = avg

    for stat in rate_stats:
        actual_col = merged_column(merged, stat, "_x")
        proj_col = merged_column(merged, stat, "_y")
        if (
            actual_col is not None
            and proj_col is not None
            and stat in actual_league_avgs
            and stat in proj_league_avgs
        ):
            merged[f"{stat}_actual_la"] = merged[actual_col] - actual_league_avgs[stat]
            merged[f"{stat}_proj_la"] = merged[proj_col] - proj_league_avgs[stat]

    print(f"  Found {len(merged)} players")
    results: List[ProjectionResult] = []
    for stat in stat_names:
        actual_col = merged_column(merged, stat, "_x")
        proj_col = merged_column(merged, stat, "_y")
        if actual_col is None or proj_col is None or actual_weight is None:
            continue
        mask = merged[[actual_col, proj_col, actual_weight]].notna().all(axis=1)
        clean = merged.loc[mask]
        if clean.empty:
            continue

        actual_vals = clean[actual_col].to_numpy(dtype=float)
        proj_vals = clean[proj_col].to_numpy(dtype=float)
        weights = clean[actual_weight].to_numpy(dtype=float)

        if stat not in actual_league_avgs or stat not in proj_league_avgs:
            continue
        actual_la = actual_vals - actual_league_avgs[stat]
        proj_la = proj_vals - proj_league_avgs[stat]
        raw_metrics = calculate_metrics(actual_vals, proj_vals)
        la_metrics = calculate_metrics(actual_la, proj_la)
        wla_metrics = calculate_metrics(actual_la, proj_la, weights=weights)
        miss_errors = np.abs(actual_la - proj_la) * weights

        temp = clean.copy()
        temp["miss_error"] = miss_errors
        all_misses = collect_player_misses(temp, actual_col, proj_col, error_col="miss_error")
        stored_stat = f"fan_{stat}" if fantasy else stat
        results.append(
            ProjectionResult(
                year=year,
                system=system,
                player_type=player_type,
                stat=stored_stat,
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
                n_players=len(clean),
                biggest_misses=find_biggest_misses(all_misses),
                all_misses=all_misses,
            )
        )
        print(
            f"    {stored_stat}: RMSE={raw_metrics['rmse']:.4f}, "
            f"LA-RMSE={la_metrics['rmse']:.4f}, WLA-RMSE={wla_metrics['rmse']:.4f}"
        )

    return results, None if fantasy else merged


def identify_everybody_missed(results: List[ProjectionResult]) -> Dict[tuple, List[Dict]]:
    everybody_missed: Dict[tuple, List[Dict]] = {}
    years = sorted({r.year for r in results})
    stats = sorted({r.stat for r in results})

    for year in years:
        for player_type in PLAYER_TYPES:
            for stat in stats:
                stat_results = [
                    r
                    for r in results
                    if r.year == year and r.player_type == player_type and r.stat == stat
                ]
                if len(stat_results) < 2:
                    continue
                miss_sets = [{miss["player_id"] for miss in r.biggest_misses} for r in stat_results]
                unanimous_ids = set.intersection(*miss_sets) if miss_sets else set()
                if not unanimous_ids:
                    continue
                details = []
                for player_id in unanimous_ids:
                    player_details: Dict[str, Any] = {
                        "player_id": player_id,
                        "player_name": None,
                        "actual": None,
                        "projections": {},
                    }
                    for result in stat_results:
                        miss_data = next(
                            (miss for miss in result.biggest_misses if miss["player_id"] == player_id),
                            None,
                        )
                        if not miss_data:
                            continue
                        player_details["player_name"] = player_details["player_name"] or miss_data["player_name"]
                        player_details["actual"] = player_details["actual"] or miss_data["actual"]
                        player_details["projections"][result.system] = {
                            "projected": miss_data["projected"],
                            "error": miss_data["error"],
                        }
                    details.append(player_details)
                if details:
                    everybody_missed[(year, player_type, stat)] = details
                for result in stat_results:
                    result.biggest_misses = [
                        miss for miss in result.biggest_misses if miss["player_id"] not in unanimous_ids
                    ]
    return everybody_missed


def calculate_summary_stats(results: List[ProjectionResult], systems: List[str]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for system in systems:
        summary[system] = {}
        for player_type in PLAYER_TYPES:
            system_results = [
                r
                for r in results
                if r.system == system
                and r.player_type == player_type
                and not r.stat.startswith("fan_")
            ]
            if not system_results:
                continue
            summary[system][player_type] = {
                "avg_rmse": float(np.nanmean([r.rmse for r in system_results])),
                "avg_mae": float(np.nanmean([r.mae for r in system_results])),
                "avg_wla_rmse": float(np.nanmean([r.wla_rmse for r in system_results])),
                "avg_wla_mae": float(np.nanmean([r.wla_mae for r in system_results])),
                "n_evaluations": len(system_results),
            }
    return summary


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


def _stat_value(row: pd.Series, stat: str) -> Any:
    column = f"{stat}_x" if f"{stat}_x" in row.index else stat
    if column not in row.index:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    return value


def generate_players_data(merged_dataframes: Dict) -> List[Dict[str, Any]]:
    players: Dict[str, Dict[str, Any]] = {}
    for (year, system, player_type), merged in merged_dataframes.items():
        pool = POOLS[player_type]
        rate_stats = scored_rate_stats(pool)
        keep_stats = list(dict.fromkeys([*pool["counting"], *rate_stats]))
        for _, row in merged.iterrows():
            player_id = str(row["playerId"])
            info = players.setdefault(
                player_id,
                {"id": player_id, "name": row.get("playerName", "Unknown"), "years": {}},
            )
            if not info["name"] and row.get("playerName"):
                info["name"] = row["playerName"]
            year_key = str(year)
            year_data = info["years"].setdefault(year_key, {})
            type_data = year_data.setdefault(player_type, {})
            if "Actual" not in type_data:
                actual_stats: Dict[str, Any] = {}
                for stat in keep_stats:
                    actual_stats[stat] = _stat_value(row, stat)
                for stat in rate_stats:
                    la_col = f"{stat}_actual_la"
                    if la_col in row.index and not pd.isna(row[la_col]):
                        actual_stats[f"{stat}_la"] = row[la_col]
                    else:
                        actual_stats[f"{stat}_la"] = None
                type_data["Actual"] = actual_stats
            proj_stats: Dict[str, Any] = {}
            for stat in keep_stats:
                proj_col = f"{stat}_y"
                if proj_col in row.index and not pd.isna(row[proj_col]):
                    proj_stats[stat] = row[proj_col]
                else:
                    proj_stats[stat] = None
            for stat in rate_stats:
                la_col = f"{stat}_proj_la"
                if la_col in row.index and not pd.isna(row[la_col]):
                    proj_stats[f"{stat}_la"] = row[la_col]
                else:
                    proj_stats[f"{stat}_la"] = None
            type_data[system] = proj_stats

    players_list = [player for player in players.values() if player["years"]]
    for player in players_list:
        totals = {player_type: 0.0 for player_type in PLAYER_TYPES}
        present = []
        for year_data in player["years"].values():
            for player_type in PLAYER_TYPES:
                typed = year_data.get(player_type)
                if not typed:
                    continue
                if player_type not in present:
                    present.append(player_type)
                actual = typed.get("Actual") or {}
                membership = actual.get(POOLS[player_type].get("membership", POOLS[player_type]["volume"]))
                if isinstance(membership, (int, float)) and not pd.isna(membership):
                    totals[player_type] += float(membership)
        player["types"] = present
        ranked = [player_type for player_type in present if totals[player_type] > 0]
        if ranked:
            player["primary_type"] = max(ranked, key=lambda key: totals[key])
        elif present:
            player["primary_type"] = present[0]
        else:
            player["primary_type"] = "passing"
    players_list.sort(key=lambda player: str(player["id"]))
    return players_list


def generate_summary_spreadsheet(results: List[ProjectionResult], output_dir: Path) -> None:
    rows = [
        {
            "Year": result.year,
            "System": result.system,
            "PlayerType": result.player_type,
            "Stat": result.stat,
            "RMSE": result.rmse,
            "MAE": result.mae,
            "Bias": result.bias,
            "R2": result.r_squared,
            "LA_RMSE": result.la_rmse,
            "LA_MAE": result.la_mae,
            "WLA_RMSE": result.wla_rmse,
            "WLA_MAE": result.wla_mae,
            "N": result.n_players,
        }
        for result in results
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "projection_summary.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"  Saved summary spreadsheet to {out_path}")


def write_cache(
    systems: List[str],
    years: List[int],
    results: List[ProjectionResult],
    merged_dataframes: Dict,
) -> None:
    from site_builder import sanitize, save_site_cache

    everybody_missed = identify_everybody_missed(results)
    clear_all_misses(results)
    scored_years = sorted({result.year for result in results})
    site_data = {
        "meta": {
            "years": scored_years,
            "seasons": [str(year) for year in scored_years],
            "projection_systems": systems,
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
        "years": scored_years,
        "seasons": {str(year): str(year) for year in scored_years},
        "summary": calculate_summary_stats(results, systems),
    }

    years_data: Dict[str, Any] = {}
    for year in years:
        year_results = [result for result in results if result.year == year]
        if not year_results:
            continue
        payload: Dict[str, Any] = {}
        for player_type in PLAYER_TYPES:
            payload[player_type] = [
                result_to_dict(result)
                for result in year_results
                if result.player_type == player_type
            ]
        years_data[str(year)] = payload

    misses_data: Dict[str, Any] = {}
    for year_str, data in years_data.items():
        year_misses: Dict[str, Any] = {}
        for player_type in PLAYER_TYPES:
            player_misses: Dict[str, List] = {}
            for item in data.get(player_type, []):
                stat = item["stat"]
                player_misses.setdefault(stat, []).append(
                    {
                        "system": item["system"],
                        "biggest_misses": item.pop("biggest_misses", []),
                        "unique_misses": item.pop("unique_misses", []),
                    }
                )
            year_misses[player_type] = {
                "player_misses": player_misses,
                "everybody_missed": {
                    stat: misses
                    for (miss_year, miss_type, stat), misses in everybody_missed.items()
                    if str(miss_year) == year_str and miss_type == player_type
                },
            }
        misses_data[year_str] = year_misses

    players_list = generate_players_data(merged_dataframes)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if results:
        generate_summary_spreadsheet(results, REPORTS_DIR)
    save_site_cache(
        sanitize(site_data),
        sanitize(years_data),
        sanitize(misses_data),
        sanitize(players_list),
    )
    print(f"  Years: {len(scored_years)}")
    print(f"  Players: {len(players_list)}")


def run_evaluation() -> None:
    print("Starting football projection evaluation...")
    if not YEARS:
        print("No projection files overlap football/stats. Writing an empty site cache.")
        write_cache(PROJECTION_SYSTEMS, [], [], {})
        return

    print(f"Seasons: {', '.join(str(year) for year in YEARS)}")
    print(f"Systems: {', '.join(PROJECTION_SYSTEMS)}")
    all_results: List[ProjectionResult] = []
    merged_dataframes: Dict = {}
    total = len(YEARS) * len(PROJECTION_SYSTEMS) * len(PLAYER_TYPES)
    current = 0
    for year in YEARS:
        for system in PROJECTION_SYSTEMS:
            for player_type in PLAYER_TYPES:
                current += 1
                print(f"\nProgress: {current}/{total}")
                results, merged = evaluate_pool(year, system, player_type, fantasy=False)
                all_results.extend(results)
                if merged is not None:
                    merged_dataframes[(year, system, player_type)] = merged
                fantasy_results, _ = evaluate_pool(year, system, player_type, fantasy=True)
                all_results.extend(fantasy_results)

    print(f"\nCompleted evaluation. Total results: {len(all_results)}")
    write_cache(PROJECTION_SYSTEMS, YEARS, all_results, merged_dataframes)
    print("\nEvaluation complete!")
    print("  Site cache ready — run `npm run football:site` to render HTML")


if __name__ == "__main__":
    run_evaluation()
