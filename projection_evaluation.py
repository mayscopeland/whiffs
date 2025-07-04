import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, UTC

YEARS: List[int] = list(range(2010, 2025))

BATTING_VOLUME_STATS: List[str] = ["PA"]
BATTING_RATE_STATS: List[str] = [
    "wOBA",
    "SO/PA",
    "BB/PA",
    "HBP/PA",
    "HR/BIP",
    "BABIP",
    "1B/(BIP-HR)",
    "2B/(BIP-HR)",
    "3B/(BIP-HR)",
    "R/PA",
    "RBI/PA",
    "SB/TOF",
    "AVG",
    "OBP",
    "SLG",
]

PITCHING_VOLUME_STATS: List[str] = ["BF"]
PITCHING_RATE_STATS: List[str] = [
    "wOBA",
    "SO/BF",
    "BB/BF",
    "HBP/BF",
    "HR/BIP",
    "BABIP",
    "1B/(BIP-HR)",
    "2B/(BIP-HR)",
    "3B/(BIP-HR)",
    "R/BF",
    "ER/BF",
    "W/G",
    "L/G",
    "SV/G",
    "HLD/G",
    "ERA",
    "WHIP",
]

PROJECTION_SYSTEMS: List[str] = ["Marcel", "Steamer", "ZiPS"]
PLAYER_TYPES: List[str] = ["batting", "pitching"]

STATS_DIR: str = "stats"
PROJECTIONS_DIR: str = "projections"
OUTPUT_DIR: str = "src/_data"

# Load wOBA constants
WOBA_CONSTANTS = pd.read_csv(Path(STATS_DIR) / "woba.csv")
WOBA_CONSTANTS.set_index("Season", inplace=True)

def calculate_woba(df: pd.DataFrame, year: int, player_type: str = "batting") -> pd.Series:
    """Calculate wOBA for a dataframe using the constants for a given year"""
    if year not in WOBA_CONSTANTS.index:
        return pd.Series(index=df.index)

    constants = WOBA_CONSTANTS.loc[year]

    # Fill missing values with 0
    for stat in ["BB", "HBP", "1B", "2B", "3B", "HR"]:
        if stat not in df.columns:
            df[stat] = 0
        else:
            df[stat] = df[stat].fillna(0)

    # Calculate wOBA
    woba = (
        constants.wBB * df["BB"] +
        constants.wHBP * df["HBP"] +
        constants.w1B * df["1B"] +
        constants.w2B * df["2B"] +
        constants.w3B * df["3B"] +
        constants.wHR * df["HR"]
    )

    # Get plate appearances/batters faced
    if player_type == "batting":
        if "PA" in df.columns:
            denom = df["PA"]
        else:
            # Calculate PA if not available
            required_cols = ["AB", "BB", "HBP", "SF", "SH"]
            if all(col in df.columns for col in required_cols):
                denom = df["AB"] + df["BB"] + df["HBP"] + df["SF"] + df["SH"]
            else:
                return pd.Series(index=df.index)  # Can't calculate without required stats
    else:  # pitching
        if "BF" in df.columns:
            denom = df["BF"]
        elif "TBF" in df.columns:
            denom = df["TBF"]
        else:
            # Calculate BF if not available: IP*3 + H + BB + HBP
            required_cols = ["IP", "H", "BB", "HBP"]
            if all(col in df.columns for col in required_cols):
                denom = df["IP"] * 3 + df["H"] + df["BB"] + df["HBP"]
            else:
                return pd.Series(index=df.index)  # Can't calculate without required stats

    # Return wOBA, handling division by zero and infinity
    result = woba.div(denom)
    result = result.replace([np.inf, -np.inf], np.nan)
    return result.fillna(0)

def calculate_rate_stats(df: pd.DataFrame, player_type: str, year: Optional[int] = None) -> pd.DataFrame:
    """Calculate all rate stats for a dataframe"""
    # Fill missing values with 0 for required stats
    required_cols = (
        ["PA", "AB", "H", "BB", "SO", "HBP", "HR", "2B", "3B", "SF", "SH"]
        if player_type == "batting"
        else ["BF", "H", "BB", "SO", "HBP", "HR", "2B", "3B", "IP", "ER", "G"]
    )

    for col in required_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Calculate singles
    if all(col in df.columns for col in ["H", "2B", "3B", "HR"]):
        df["1B"] = df["H"] - df["2B"] - df["3B"] - df["HR"]

    if player_type == "batting":
        # Calculate PA if missing
        if "PA" not in df.columns and all(col in df.columns for col in ["AB", "BB", "HBP", "SF", "SH"]):
            df["PA"] = df["AB"] + df["BB"] + df["HBP"] + df["SF"] + df["SH"]

        if "PA" in df.columns:
            # Basic rate stats
            df["SO/PA"] = df.apply(lambda row: 0 if row["PA"] == 0 else row["SO"] / row["PA"], axis=1)
            df["BB/PA"] = df.apply(lambda row: 0 if row["PA"] == 0 else row["BB"] / row["PA"], axis=1)
            df["HBP/PA"] = df.apply(lambda row: 0 if row["PA"] == 0 else row["HBP"] / row["PA"], axis=1)

            # Calculate BIP and related stats
            df["BIP"] = df["PA"] - df["SO"] - df["BB"] - df["HBP"]
            df["HR/BIP"] = df.apply(lambda row: 0 if row["BIP"] == 0 else row["HR"] / row["BIP"], axis=1)

            # Traditional stats
            df["AVG"] = df.apply(lambda row: 0 if row["AB"] == 0 else row["H"] / row["AB"], axis=1)
            df["OBP"] = df.apply(
                lambda row: 0
                if (row["AB"] + row["BB"] + row["HBP"] + row.get("SF", 0)) == 0
                else (row["H"] + row["BB"] + row["HBP"]) / (row["AB"] + row["BB"] + row["HBP"] + row.get("SF", 0)),
                axis=1
            )
            df["SLG"] = df.apply(
                lambda row: 0
                if row["AB"] == 0
                else (row["1B"] + 2*row["2B"] + 3*row["3B"] + 4*row["HR"]) / row["AB"],
                axis=1
            )

            # Calculate wOBA if year is provided
            if year is not None:
                df["wOBA"] = calculate_woba(df, year, player_type)

            # Additional rate stats
            if "R" in df.columns:
                df["R/PA"] = df.apply(lambda row: 0 if row["PA"] == 0 else row["R"] / row["PA"], axis=1)

            if "RBI" in df.columns:
                df["RBI/PA"] = df.apply(lambda row: 0 if row["PA"] == 0 else row["RBI"] / row["PA"], axis=1)

            # Calculate BABIP and hit type rates
            if all(col in df.columns for col in ["H", "2B", "3B", "HR"]):
                df["BABIP"] = df.apply(
                    lambda row: 0 if (row["BIP"] - row["HR"]) == 0 else (row["H"] - row["HR"]) / (row["BIP"] - row["HR"]),
                    axis=1,
                )
                df["1B/(BIP-HR)"] = df.apply(
                    lambda row: 0 if (row["BIP"] - row["HR"]) == 0 else row["1B"] / (row["BIP"] - row["HR"]),
                    axis=1,
                )
                df["2B/(BIP-HR)"] = df.apply(
                    lambda row: 0 if (row["BIP"] - row["HR"]) == 0 else row["2B"] / (row["BIP"] - row["HR"]),
                    axis=1,
                )
                df["3B/(BIP-HR)"] = df.apply(
                    lambda row: 0 if (row["BIP"] - row["HR"]) == 0 else row["3B"] / (row["BIP"] - row["HR"]),
                    axis=1,
                )

            # Calculate SB/TOF if all required columns are available
            if all(col in df.columns for col in ["SB", "BB", "HBP", "H", "2B", "3B", "HR"]):
                df["SB"] = df["SB"].fillna(0)
                df["TOF"] = df["BB"] + df["HBP"] + df["H"] - df["2B"] - df["3B"] - df["HR"]
                df["SB/TOF"] = df.apply(lambda row: 0 if row["TOF"] == 0 else row["SB"] / row["TOF"], axis=1)
    else:  # pitching
        # Calculate BF when missing or empty: IP*3 + H + BB + HBP
        required_cols = ["IP", "H", "BB", "HBP"]
        should_calculate_bf = True

        # Check if BF or TBF exists and has valid data
        if "BF" in df.columns and df["BF"].sum() > 0:
            should_calculate_bf = False
        elif "TBF" in df.columns and df["TBF"].sum() > 0:
            df["BF"] = df["TBF"]
            should_calculate_bf = False

        if should_calculate_bf and all(col in df.columns for col in required_cols):
            df["BF"] = df["IP"] * 3 + df["H"] + df["BB"] + df["HBP"]

        if "BF" in df.columns:
            # Basic rate stats
            df["SO/BF"] = df.apply(lambda row: 0 if row["BF"] == 0 else row["SO"] / row["BF"], axis=1)
            df["BB/BF"] = df.apply(lambda row: 0 if row["BF"] == 0 else row["BB"] / row["BF"], axis=1)
            df["HBP/BF"] = df.apply(lambda row: 0 if row["BF"] == 0 else row["HBP"] / row["BF"], axis=1)

            # Calculate BIP and related stats
            df["BIP"] = df["BF"] - df["SO"] - df["BB"] - df["HBP"]
            df["HR/BIP"] = df.apply(lambda row: 0 if row["BIP"] == 0 else row["HR"] / row["BIP"], axis=1)

            # Traditional stats
            if "IP" in df.columns and "ER" in df.columns:
                df["ERA"] = df.apply(lambda row: 0 if row["IP"] == 0 else (row["ER"] * 9) / row["IP"], axis=1)
                df["WHIP"] = df.apply(lambda row: 0 if row["IP"] == 0 else (row["BB"] + row["H"]) / row["IP"], axis=1)

            # Calculate wOBA if year is provided
            if year is not None:
                df["wOBA"] = calculate_woba(df, year, player_type)

            # Additional rate stats
            if "R" in df.columns:
                df["R/BF"] = df.apply(lambda row: 0 if row["BF"] == 0 else row["R"] / row["BF"], axis=1)

            if "ER" in df.columns:
                df["ER/BF"] = df.apply(lambda row: 0 if row["BF"] == 0 else row["ER"] / row["BF"], axis=1)

            # Calculate BABIP and hit type rates
            if all(col in df.columns for col in ["H", "2B", "3B", "HR"]):
                df["BABIP"] = df.apply(
                    lambda row: 0 if (row["BIP"] - row["HR"]) == 0 else (row["H"] - row["HR"]) / (row["BIP"] - row["HR"]),
                    axis=1,
                )
                df["1B/(BIP-HR)"] = df.apply(
                    lambda row: 0 if (row["BIP"] - row["HR"]) == 0 else row["1B"] / (row["BIP"] - row["HR"]),
                    axis=1,
                )
                df["2B/(BIP-HR)"] = df.apply(
                    lambda row: 0 if (row["BIP"] - row["HR"]) == 0 else row["2B"] / (row["BIP"] - row["HR"]),
                    axis=1,
                )
                df["3B/(BIP-HR)"] = df.apply(
                    lambda row: 0 if (row["BIP"] - row["HR"]) == 0 else row["3B"] / (row["BIP"] - row["HR"]),
                    axis=1,
                )

            # Calculate per-game stats if G column is available
            if "G" in df.columns:
                for stat in ["W", "L", "SV", "HLD"]:
                    if stat in df.columns:
                        df[stat] = df[stat].fillna(0)
                        df[f"{stat}/G"] = df.apply(lambda row: 0 if row["G"] == 0 else row[stat] / row["G"], axis=1)

    return df

def load_actual_stats(year: int, player_type: str) -> pd.DataFrame:
    """Load actual stats for a given year and player type"""
    suffix = "bat" if player_type == "batting" else "pit"
    file_path = Path(STATS_DIR) / f"{year}_{suffix}.csv"

    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return pd.DataFrame()

    df = pd.read_csv(file_path)

    # Ensure playerId is string for consistent merging
    if "playerId" in df.columns:
        df["playerId"] = df["playerId"].astype(str)

    # Filter by position
    if "position" in df.columns:
        if player_type == "batting":
            # Remove pitchers from batting data
            df = df[df["position"] != "P"]
        else:  # pitching
            # Only keep pitchers in pitching data
            df = df[df["position"] == "P"]

    # Calculate all rate stats
    df = calculate_rate_stats(df, player_type, year)

    return df

def load_projections(year: int, system: str, player_type: str) -> pd.DataFrame:
    """Load projections for a given year, system, and player type"""
    suffix = "bat" if player_type == "batting" else "pit"
    file_path = Path(PROJECTIONS_DIR) / f"{system.lower()}_{year}_{suffix}.csv"

    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return pd.DataFrame()

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

    # Fix xMLBAMID data type issues - convert float values to int to remove .0 decimals
    if "xMLBAMID" in df.columns:
        # Convert to numeric, then to int to remove .0 decimals, then to string
        df["xMLBAMID"] = (
            pd.to_numeric(df["xMLBAMID"], errors="coerce")
            .fillna(0)
            .astype(int)
            .astype(str)
        )

    # Marcel projections use 'player_id' for the MLBAM ID
    if system.lower() == "marcel" and "player_id" in df.columns:
        df = df.rename(columns={"player_id": "xMLBAMID"})
        df["xMLBAMID"] = (
            pd.to_numeric(df["xMLBAMID"], errors="coerce")
            .fillna(0)
            .astype(int)
            .astype(str)
        )

    # Calculate all rate stats
    df = calculate_rate_stats(df, player_type, year)

    return df

@dataclass
class ProjectionResult:
    """Container for projection evaluation results"""

    year: int
    system: str
    player_type: str
    stat: str
    # Raw metrics
    rmse: float
    mae: float
    bias: float
    r_squared: float
    # League-adjusted metrics
    la_rmse: float
    la_mae: float
    la_bias: float
    la_r_squared: float
    # Weighted league-adjusted metrics
    wla_rmse: float
    wla_mae: float
    wla_bias: float
    wla_r_squared: float
    n_players: int
    biggest_misses: List[Dict]


def calculate_metrics(actual: np.ndarray, projected: np.ndarray) -> Dict[str, float]:
    """Calculate basic metrics (RMSE, MAE, bias, R²)"""
    if len(actual) == 0 or len(projected) == 0:
        return {"rmse": np.nan, "mae": np.nan, "bias": np.nan, "r_squared": np.nan}

    errors = projected - actual
    rmse = np.sqrt(np.mean(errors**2))
    mae = np.mean(np.abs(errors))
    bias = np.mean(errors)

    ss_res = np.sum(errors**2)
    ss_tot = np.sum((actual - np.mean(actual)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return {"rmse": rmse, "mae": mae, "bias": bias, "r_squared": max(0, r_squared)}


def find_biggest_misses(
    df: pd.DataFrame, stat: str, actual_col: str, proj_col: str, n_misses: int = 10
) -> List[Dict]:
    """Find the biggest projection misses for a stat"""
    if actual_col not in df.columns or proj_col not in df.columns:
        return []

    errors = np.abs(df[proj_col] - df[actual_col])
    biggest_indices = errors.nlargest(n_misses).index

    misses = []
    for idx in biggest_indices:
        miss_data = {
            "player_name": df.loc[idx, "playerName"],
            "actual": float(df.loc[idx, actual_col]),
            "projected": float(df.loc[idx, proj_col]),
            "error": float(errors.loc[idx]),
            "player_id": df.loc[idx, "playerId"],
        }
        misses.append(miss_data)
    return misses


def calculate_summary_stats(results: List[ProjectionResult]) -> Dict:
    """Calculate summary statistics across all results"""
    summary = {}
    for system in PROJECTION_SYSTEMS:
        summary[system] = {}
        for player_type in PLAYER_TYPES:
            system_results = [
                r
                for r in results
                if r.system == system and r.player_type == player_type
            ]
            if system_results:
                summary[system][player_type] = {
                    "avg_rmse": np.mean(
                        [r.rmse for r in system_results if not np.isnan(r.rmse)]
                    ),
                    "avg_mae": np.mean(
                        [r.mae for r in system_results if not np.isnan(r.mae)]
                    ),
                    "avg_r2": np.mean(
                        [
                            r.r_squared
                            for r in system_results
                            if not np.isnan(r.r_squared)
                        ]
                    ),
                    "avg_la_rmse": np.mean(
                        [r.la_rmse for r in system_results if not np.isnan(r.la_rmse)]
                    ),
                    "avg_la_mae": np.mean(
                        [r.la_mae for r in system_results if not np.isnan(r.la_mae)]
                    ),
                    "avg_la_r2": np.mean(
                        [
                            r.la_r_squared
                            for r in system_results
                            if not np.isnan(r.la_r_squared)
                        ]
                    ),
                    "avg_wla_rmse": np.mean(
                        [r.wla_rmse for r in system_results if not np.isnan(r.wla_rmse)]
                    ),
                    "avg_wla_mae": np.mean(
                        [r.wla_mae for r in system_results if not np.isnan(r.wla_mae)]
                    ),
                    "avg_wla_r2": np.mean(
                        [
                            r.wla_r_squared
                            for r in system_results
                            if not np.isnan(r.wla_r_squared)
                        ]
                    ),
                    "n_evaluations": len(system_results),
                }
    return summary


def generate_players_data_from_merged(merged_dataframes: Dict) -> List[Dict[str, Any]]:
    """Generate player data using already-processed merged dataframes"""
    print("Generating player data from merged dataframes...")

    # Collect unique players
    players_dict = {}
    for (year, system, player_type), merged_df in merged_dataframes.items():
        for _, row in merged_df.iterrows():
            player_id = row["playerId"]
            player_name = row.get("playerName", "Unknown")
            if player_id not in players_dict:
                players_dict[player_id] = {
                    "id": player_id,
                    "name": player_name,
                    "years": {},
                }

    # Process each player using the merged dataframes
    for player_id, player_info in players_dict.items():
        for year in YEARS:
            year_data = {}

            for player_type in PLAYER_TYPES:
                type_data = {}
                actual_stats = None

                for system in PROJECTION_SYSTEMS:
                    merged_df = merged_dataframes.get((year, system, player_type))
                    if (
                        merged_df is not None
                        and player_id in merged_df["playerId"].values
                    ):
                        player_row = merged_df[merged_df["playerId"] == player_id].iloc[
                            0
                        ]

                        # Set actual stats once per player_type/year
                        if actual_stats is None:
                            actual_stats = {}
                            all_cols = (
                                [
                                    "PA",
                                    "AB",
                                    "H",
                                    "1B",
                                    "2B",
                                    "3B",
                                    "HR",
                                    "BB",
                                    "SO",
                                    "HBP",
                                    "R",
                                    "RBI",
                                    "SB",
                                    "BIP",
                                    "TOF",
                                ]
                                if player_type == "batting"
                                else [
                                    "BF",
                                    "IP",
                                    "H",
                                    "1B",
                                    "2B",
                                    "3B",
                                    "HR",
                                    "BB",
                                    "SO",
                                    "HBP",
                                    "ER",
                                    "R",
                                    "W",
                                    "L",
                                    "SV",
                                    "HLD",
                                    "G",
                                    "BIP",
                                ]
                            )
                            rate_stats = (
                                BATTING_RATE_STATS
                                if player_type == "batting"
                                else PITCHING_RATE_STATS
                            )
                            all_stats = list(set(all_cols + rate_stats))

                            # Raw actual stats
                            for stat in all_stats:
                                actual_col = (
                                    f"{stat}_x" if f"{stat}_x" in player_row else stat
                                )
                                if actual_col in player_row:
                                    val = player_row[actual_col]
                                    actual_stats[stat] = None if pd.isna(val) else val

                            # League-adjusted and weighted league-adjusted actual stats
                            for stat in rate_stats:
                                la_col = f"{stat}_actual_la"
                                wla_col = f"{stat}_actual_wla"
                                if la_col in player_row:
                                    val = player_row[la_col]
                                    actual_stats[f"{stat}_la"] = (
                                        None if pd.isna(val) else val
                                    )
                                if wla_col in player_row:
                                    val = player_row[wla_col]
                                    actual_stats[f"{stat}_wla"] = (
                                        None if pd.isna(val) else val
                                    )

                            type_data["Actual"] = actual_stats

                        # Projection stats for this system
                        proj_stats = {}
                        all_cols = (
                            [
                                "PA",
                                "AB",
                                "H",
                                "1B",
                                "2B",
                                "3B",
                                "HR",
                                "BB",
                                "SO",
                                "HBP",
                                "R",
                                "RBI",
                                "SB",
                                "BIP",
                                "TOF",
                            ]
                            if player_type == "batting"
                            else [
                                "BF",
                                "IP",
                                "H",
                                "1B",
                                "2B",
                                "3B",
                                "HR",
                                "BB",
                                "SO",
                                "HBP",
                                "ER",
                                "R",
                                "W",
                                "L",
                                "SV",
                                "HLD",
                                "G",
                                "BIP",
                            ]
                        )
                        rate_stats = (
                            BATTING_RATE_STATS
                            if player_type == "batting"
                            else PITCHING_RATE_STATS
                        )
                        all_stats = list(set(all_cols + rate_stats))

                        # Raw projected stats
                        for stat in all_stats:
                            proj_col = f"{stat}_y"
                            if proj_col in player_row:
                                val = player_row[proj_col]
                                proj_stats[stat] = None if pd.isna(val) else val

                        # League-adjusted and weighted league-adjusted projected stats
                        for stat in rate_stats:
                            la_col = f"{stat}_proj_la"
                            wla_col = f"{stat}_proj_wla"
                            if la_col in player_row:
                                val = player_row[la_col]
                                proj_stats[f"{stat}_la"] = None if pd.isna(val) else val
                            if wla_col in player_row:
                                val = player_row[wla_col]
                                proj_stats[f"{stat}_wla"] = (
                                    None if pd.isna(val) else val
                                )

                        type_data[system] = proj_stats

                if type_data:
                    year_data[player_type] = type_data

            if year_data:
                player_info["years"][year] = year_data

    # Determine primary type and filter out players with no data
    players_list = []
    for player_info in players_dict.values():
        if player_info["years"]:
            batting_years = sum(
                1
                for year_data in player_info["years"].values()
                if "batting" in year_data
            )
            pitching_years = sum(
                1
                for year_data in player_info["years"].values()
                if "pitching" in year_data
            )

            primary_type = "batting" if batting_years >= pitching_years else "pitching"
            player_info["primary_type"] = primary_type
            players_list.append(player_info)

    return players_list


def save_json_file(data: Any, filepath: Path) -> None:
    """Save data as JSON file with proper formatting"""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                if np.isnan(obj) or pd.isna(obj) or np.isinf(obj):
                    return None
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            return super().default(obj)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)


def run_evaluation():
    """Main function to run the complete evaluation and generate JSON files"""
    print("Starting projection evaluation...")

    # Process all year/system/player_type combinations
    all_results = []
    merged_dataframes = {}
    total_combinations = len(YEARS) * len(PROJECTION_SYSTEMS) * len(PLAYER_TYPES)
    current_combination = 0

    for year in YEARS:
        for system in PROJECTION_SYSTEMS:
            for player_type in PLAYER_TYPES:
                current_combination += 1
                print(f"\nProgress: {current_combination}/{total_combinations}")
                results, merged_df = process_year_system(year, system, player_type)
                all_results.extend(results)
                if merged_df is not None:
                    merged_dataframes[(year, system, player_type)] = merged_df

    print(f"\nCompleted evaluation. Total results: {len(all_results)}")

    # 8. Generate and save JSON files
    print("\nGenerating JSON data files...")

    # Create output directory
    data_dir = Path(OUTPUT_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Generate site data
    years = sorted(set(r.year for r in all_results))
    summary = calculate_summary_stats(all_results)

    site_data = {
        "meta": {
            "years": years,
            "projection_systems": PROJECTION_SYSTEMS,
            "generated_at": datetime.now(UTC).isoformat() + "Z",
        },
        "years": years,
        "summary": summary,
    }

    # Generate years data
    years_data = {}
    for year in YEARS:
        year_results = [r for r in all_results if r.year == year]
        if not year_results:
            continue

        batting_results = [r for r in year_results if r.player_type == "batting"]
        pitching_results = [r for r in year_results if r.player_type == "pitching"]

        # Convert to dictionaries
        batting_data = []
        for result in batting_results:
            batting_data.append(
                {
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
                }
            )

        pitching_data = []
        for result in pitching_results:
            pitching_data.append(
                {
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
                }
            )

        years_data[str(year)] = {"batting": batting_data, "pitching": pitching_data}

    # Generate players data using the stored merged dataframes
    players_data = generate_players_data_from_merged(merged_dataframes)

    # Save all files
    save_json_file(site_data, data_dir / "site.json")
    save_json_file(years_data, data_dir / "years.json")
    save_json_file(players_data, data_dir / "players.json")

    print(f"\nJSON generation complete!")
    print(f"  Site data: {len(site_data['years'])} years")
    print(f"  Years data: {len(years_data)} years with results")
    print(f"  Players data: {len(players_data)} players")
    print(f"  Files saved to: {data_dir}")


def process_year_system(
    year: int, system: str, player_type: str
) -> tuple[List[ProjectionResult], Optional[pd.DataFrame]]:
    """Process a specific year/system/player_type combination and return both results and merged df"""
    print(f"Processing {system} {year} {player_type}...")

    # 1. Load actual stats and projected stats
    actual_df = load_actual_stats(year, player_type)
    proj_df = load_projections(year, system, player_type)

    if actual_df.empty or proj_df.empty:
        print(f"  Skipping - missing data")
        return [], None

    # Ensure consistent data types
    actual_df["playerId"] = actual_df["playerId"].astype(str)
    proj_df["xMLBAMID"] = proj_df["xMLBAMID"].astype(str)

    # 2. Calculate league averages for actual stats
    rate_stats = BATTING_RATE_STATS if player_type == "batting" else PITCHING_RATE_STATS
    volume_stats = (
        BATTING_VOLUME_STATS if player_type == "batting" else PITCHING_VOLUME_STATS
    )
    playing_time_col = "PA" if player_type == "batting" else "BF"

    actual_league_avgs = {}
    for stat in rate_stats:
        if stat in actual_df.columns and playing_time_col in actual_df.columns:
            weights = actual_df[playing_time_col]
            actual_league_avgs[stat] = np.average(actual_df[stat], weights=weights)

    # 3. Join projection data, filling missing players with league averages
    merged_df = actual_df.merge(
        proj_df, left_on="playerId", right_on="xMLBAMID", how="left"
    )

    # Fill missing projections with league averages for rate stats
    for stat in rate_stats:
        if f"{stat}_y" in merged_df.columns and stat in actual_league_avgs:
            merged_df[f"{stat}_y"] = merged_df[f"{stat}_y"].fillna(
                actual_league_avgs[stat]
            )

    # Fill missing projections with 250 for playing-time stats
    for stat in volume_stats:
        if f"{stat}_y" in merged_df.columns:
            merged_df[f"{stat}_y"] = merged_df[f"{stat}_y"].fillna(250)

    # 4. Calculate league averages for projected stats
    proj_league_avgs = {}
    playing_time_col_y = f"{playing_time_col}_y"  # After merge, it becomes PA_y or BF_y
    for stat in rate_stats:
        proj_col = f"{stat}_y"
        if proj_col in merged_df.columns and playing_time_col_y in merged_df.columns:
            weights = merged_df[playing_time_col_y]
            proj_league_avgs[stat] = np.average(merged_df[proj_col], weights=weights)

    # Add league-adjusted and weighted league-adjusted columns to merged_df
    all_stats = rate_stats + volume_stats
    playing_time_col_x = f"{playing_time_col}_x"  # For actual data
    for stat in all_stats:
        actual_col = f"{stat}_x"
        proj_col = f"{stat}_y"

        if actual_col in merged_df.columns and proj_col in merged_df.columns:
            if (
                stat in rate_stats
                and stat in actual_league_avgs
                and stat in proj_league_avgs
            ):
                # League-adjusted actual
                merged_df[f"{stat}_actual_la"] = (
                    merged_df[actual_col] - actual_league_avgs[stat]
                )
                # League-adjusted projected
                merged_df[f"{stat}_proj_la"] = (
                    merged_df[proj_col] - proj_league_avgs[stat]
                )
                # Weighted league-adjusted (both use actual playing time for fair comparison)
                if playing_time_col_x in merged_df.columns:
                    merged_df[f"{stat}_actual_wla"] = (
                        merged_df[f"{stat}_actual_la"] * merged_df[playing_time_col_x]
                    )
                    merged_df[f"{stat}_proj_wla"] = (
                        merged_df[f"{stat}_proj_la"] * merged_df[playing_time_col_x]
                    )

    print(f"  Found {len(merged_df)} players")

    results = []

    for stat in all_stats:
        actual_col = f"{stat}_x"
        proj_col = f"{stat}_y"

        if actual_col not in merged_df.columns or proj_col not in merged_df.columns:
            continue

        # Get actual and projected values
        actual_vals = merged_df[actual_col]
        proj_vals = merged_df[proj_col]

        if actual_vals.isna().all() or proj_vals.isna().all():
            continue

        # Remove any rows with NaN values
        mask = ~(actual_vals.isna() | proj_vals.isna())
        actual_clean = actual_vals[mask].values
        proj_clean = proj_vals[mask].values

        if len(actual_clean) == 0:
            continue

        # 5 & 6. Calculate league-adjusted and weighted league-adjusted versions
        if stat in rate_stats:
            # League-adjusted (stat - league_avg)
            actual_la = actual_clean - actual_league_avgs[stat]
            proj_la = proj_clean - proj_league_avgs[stat]

            # Weighted league-adjusted (league_adjusted * playing_time)
            weights = merged_df[playing_time_col_x][mask].values
            actual_wla = actual_la * weights
            proj_wla = proj_la * weights
        else:
            # For volume stats, league-adjusted doesn't make as much sense
            actual_la = actual_clean  # Just use raw values
            proj_la = proj_clean
            actual_wla = actual_clean
            proj_wla = proj_clean

        # 7. Calculate metrics for all three versions
        raw_metrics = calculate_metrics(actual_clean, proj_clean)
        la_metrics = calculate_metrics(actual_la, proj_la)
        wla_metrics = calculate_metrics(actual_wla, proj_wla)

        # Find biggest misses (using weighted league-adjusted for rate stats, raw for volume stats)
        temp_df = merged_df[mask].copy()
        if stat in rate_stats:
            temp_df["actual_for_misses"] = actual_wla
            temp_df["proj_for_misses"] = proj_wla
        else:
            temp_df["actual_for_misses"] = actual_clean
            temp_df["proj_for_misses"] = proj_clean

        biggest_misses = find_biggest_misses(
            temp_df, stat, "actual_for_misses", "proj_for_misses"
        )

        result = ProjectionResult(
            year=year,
            system=system,
            player_type=player_type,
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
        )

        results.append(result)
        print(
            f"    {stat}: RMSE={raw_metrics['rmse']:.4f}, LA-RMSE={la_metrics['rmse']:.4f}, WLA-RMSE={wla_metrics['rmse']:.4f}"
        )

    return results, merged_df


if __name__ == "__main__":
    run_evaluation()
