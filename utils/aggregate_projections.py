#!/usr/bin/env python3
"""Build an aggregate projection from the systems available in each season.

For each player, playing time is the unweighted mean of projected PA (batters)
or BF (pitchers) across systems that roster them. Counting stats are converted
to per-PA or per-BF rates, those rates are averaged across the systems that
publish the stat, and the mean rate is scaled to the mean playing time.

Writes projections/aggregate_YYYY_bat.csv and projections/aggregate_YYYY_pit.csv.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROJECTIONS_DIR = ROOT / "projections"

# File prefix matches projection_evaluation.load_projections.
# Marcel is left out of the aggregate.
SYSTEMS = [
    ("ATC", "atc"),
    ("The BAT", "thebat"),
    ("The BAT X", "thebatx"),
    ("OOPSY", "oopsy"),
    ("Razzball", "razzball"),
    ("Steamer", "steamer"),
    ("ZiPS", "zips"),
]

# Prefer MLB id columns. Bare "id" on OOPSY is a FanGraphs id.
ID_COLUMNS = ["xMLBAMID", "MLBID", "player_id"]

COLUMN_ALIASES = {
    "K": "SO",
    "TBF": "BF",
    "GDP": "GIDP",
}

# Counting stats scaled from a per-PA or per-BF rate. Playing time itself
# (PA / BF) is averaged separately and is not in these lists.
BATTING_COUNTING = [
    "G",
    "AB",
    "H",
    "1B",
    "2B",
    "3B",
    "HR",
    "R",
    "RBI",
    "SB",
    "CS",
    "BB",
    "SO",
    "IBB",
    "HBP",
    "SH",
    "SF",
    "GIDP",
]
PITCHING_COUNTING = [
    "G",
    "GS",
    "W",
    "L",
    "SV",
    "HLD",
    "BS",
    "QS",
    "IP",
    "H",
    "1B",
    "2B",
    "3B",
    "HR",
    "R",
    "ER",
    "BB",
    "SO",
    "IBB",
    "HBP",
    "WP",
    "BK",
    "SF",
    "SH",
]

BATTING_COLUMNS = ["player_id", "PA"] + BATTING_COUNTING
PITCHING_COLUMNS = ["player_id", "BF"] + PITCHING_COUNTING


def read_projection(path: Path) -> pd.DataFrame:
    last_error = None
    for encoding in ("utf-8", "latin-1", "cp1252", "iso-8859-1"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise OSError(f"Could not decode {path}") from last_error


def apply_aliases(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        src: dest
        for src, dest in COLUMN_ALIASES.items()
        if src in df.columns and dest not in df.columns
    }
    if rename:
        df = df.rename(columns=rename)
    return df


def extract_player_ids(df: pd.DataFrame) -> pd.Series | None:
    for column in ID_COLUMNS:
        if column in df.columns:
            return pd.to_numeric(df[column], errors="coerce")
    return None


def ensure_playing_time(df: pd.DataFrame, player_type: str) -> pd.DataFrame:
    """Fill PA or BF when a system leaves playing time blank.

    ZiPS pitching files before 2022 have an empty TBF column. BF is then
    estimated as IP*3 + H + BB + HBP, the same approximation used when
    evaluating projections.
    """
    if player_type == "bat":
        if "PA" not in df.columns:
            df["PA"] = np.nan
        missing = df["PA"].isna()
        if missing.any() and {"AB", "BB"}.issubset(df.columns):
            pa = df["AB"] + df["BB"]
            for column in ("HBP", "SF", "SH"):
                if column in df.columns:
                    pa = pa + df[column].fillna(0)
            df.loc[missing, "PA"] = pa.loc[missing]
        return df

    if "BF" not in df.columns:
        df["BF"] = np.nan
    missing = df["BF"].isna()
    if missing.any() and {"IP", "H", "BB"}.issubset(df.columns):
        bf = df["IP"] * 3 + df["H"] + df["BB"]
        if "HBP" in df.columns:
            bf = bf + df["HBP"].fillna(0)
        df.loc[missing, "BF"] = bf.loc[missing]
    return df


def derive_components(df: pd.DataFrame, player_type: str) -> pd.DataFrame:
    """Fill counting stats that are arithmetic combinations of others."""
    if {"1B", "2B", "3B", "HR"}.issubset(df.columns) and "H" not in df.columns:
        df["H"] = df["1B"] + df["2B"] + df["3B"] + df["HR"]
    if {"H", "2B", "3B", "HR"}.issubset(df.columns) and "1B" not in df.columns:
        df["1B"] = df["H"] - df["2B"] - df["3B"] - df["HR"]

    if player_type == "bat" and "AB" not in df.columns and "PA" in df.columns:
        ab = df["PA"].copy()
        for column in ("BB", "HBP", "SF", "SH"):
            if column in df.columns:
                ab = ab - df[column].fillna(0)
        df["AB"] = ab
    return df


def load_system_rates(path: Path, player_type: str) -> pd.DataFrame | None:
    """Return per-player playing time and per-playing-time rates for one system."""
    df = apply_aliases(read_projection(path))
    player_ids = extract_player_ids(df)
    if player_ids is None:
        print(f"  Skipping {path.name}: no MLB id column")
        return None

    df = df.copy()
    df["player_id"] = player_ids
    for column in df.columns:
        if column != "player_id":
            df[column] = pd.to_numeric(df[column], errors="coerce")

    pt_col = "PA" if player_type == "bat" else "BF"
    had_pt = int(df[pt_col].notna().sum()) if pt_col in df.columns else 0
    df = ensure_playing_time(df, player_type)
    filled_pt = int(df[pt_col].notna().sum()) - had_pt
    if filled_pt > 0:
        print(f"  {path.name}: estimated {filled_pt} missing {pt_col} values")
    if pt_col not in df.columns:
        print(f"  Skipping {path.name}: no {pt_col}")
        return None

    df = derive_components(df, player_type)
    counting = BATTING_COUNTING if player_type == "bat" else PITCHING_COUNTING
    stat_cols = [column for column in counting if column in df.columns]

    df = df[df["player_id"].notna() & (df["player_id"] > 0)]
    df = df.dropna(subset=[pt_col])
    df["player_id"] = df["player_id"].astype(int)

    before = len(df)
    df = df.sort_values(pt_col, ascending=False).drop_duplicates("player_id", keep="first")
    dropped = before - len(df)
    if dropped:
        print(f"  {path.name}: dropped {dropped} duplicate player rows")

    rates = df[["player_id", pt_col] + stat_cols].copy()
    positive_pt = rates[pt_col] > 0
    for column in stat_cols:
        rate = rates[column] / rates[pt_col]
        rates[column] = rate.where(positive_pt)
    return rates


def aggregate_year(year: int, player_type: str) -> pd.DataFrame | None:
    suffix = "bat" if player_type == "bat" else "pit"
    pt_col = "PA" if player_type == "bat" else "BF"
    frames = []
    used = []

    for label, prefix in SYSTEMS:
        path = PROJECTIONS_DIR / f"{prefix}_{year}_{suffix}.csv"
        if not path.exists():
            continue
        rates = load_system_rates(path, player_type)
        if rates is None or rates.empty:
            if rates is not None:
                print(f"  Skipping {path.name}: no players with {pt_col}")
            continue
        frames.append(rates)
        used.append(label)

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    means = combined.groupby("player_id").mean(numeric_only=True)
    means = means[means[pt_col] > 0]

    for column in means.columns:
        if column != pt_col:
            means[column] = means[column] * means[pt_col]

    columns = BATTING_COLUMNS if player_type == "bat" else PITCHING_COLUMNS
    for column in columns:
        if column not in means.columns and column != "player_id":
            means[column] = np.nan

    means = means.reset_index()
    means = means[columns]
    means["player_id"] = means["player_id"].astype(int)
    means = means.sort_values([pt_col, "player_id"], ascending=[False, True])
    numeric_cols = [column for column in means.columns if column != "player_id"]
    means[numeric_cols] = means[numeric_cols].round(3)

    out_path = PROJECTIONS_DIR / f"aggregate_{year}_{suffix}.csv"
    means.to_csv(out_path, index=False)
    print(
        f"{year} {suffix}: {len(used)} system{'s' if len(used) != 1 else ''} ({', '.join(used)}), "
        f"{len(means)} players -> {out_path.name}"
    )
    return means


def available_years() -> list[int]:
    years = set()
    for _label, prefix in SYSTEMS:
        for path in PROJECTIONS_DIR.glob(f"{prefix}_*_[bp][ai][at].csv"):
            parts = path.stem.split("_")
            if len(parts) >= 3 and parts[-2].isdigit():
                years.add(int(parts[-2]))
    return sorted(years)


def main() -> None:
    if not PROJECTIONS_DIR.exists():
        raise SystemExit(f"Missing projections directory: {PROJECTIONS_DIR}")

    years = available_years()
    if not years:
        raise SystemExit("No source projection files found")

    for year in years:
        aggregate_year(year, "bat")
        aggregate_year(year, "pit")


if __name__ == "__main__":
    main()
