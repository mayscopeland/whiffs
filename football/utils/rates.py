"""Counting columns and per-game rates shared by the NFL scrape and evaluation."""

from __future__ import annotations

import pandas as pd

# Box-score counting columns shared by projection fetchers. Games played (G) is
# attached on actuals only; projections without G assume a full season.
COUNTING_COLS = [
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

# player type -> per-game rates. membership is the season-total opportunity
# used to decide who belongs in the pool. weight is games played for WLA.
# volume is the primary charted rate (still scored as a rate).
POOLS: dict[str, dict] = {
    "passing": {
        "label": "Passing",
        "volume": "ATT/G",
        "volume_label": "ATT/G",
        "rates": ["CMP/G", "PASS_YDS/G", "PASS_TD/G", "INT/G"],
        "counting": ["G", "ATT", "CMP", "PASS_YDS", "PASS_TD", "INT"],
        "membership": "ATT",
        "weight": "G",
        "volume_as_rate": True,
        "prior": None,
    },
    "rushing": {
        "label": "Rushing",
        "volume": "CAR/G",
        "volume_label": "CAR/G",
        "rates": ["RUSH_YDS/G", "RUSH_TD/G"],
        "counting": ["G", "CAR", "RUSH_YDS", "RUSH_TD"],
        "membership": "CAR",
        "weight": "G",
        "volume_as_rate": True,
        "prior": None,
    },
    "receiving": {
        "label": "Receiving",
        "volume": "TGT/G",
        "volume_label": "TGT/G",
        "rates": ["REC/G", "REC_YDS/G", "REC_TD/G"],
        "counting": ["G", "TGT", "REC", "REC_YDS", "REC_TD"],
        "membership": "TGT",
        "weight": "G",
        "volume_as_rate": True,
        "prior": None,
    },
}

PLAYER_TYPES = list(POOLS)

# Home-page charts. Everything else is on the all-time stats pages.
OVERVIEW_STATS = {
    "passing": ["ATT/G", "PASS_YDS/G", "PASS_TD/G"],
    "rushing": ["CAR/G", "RUSH_YDS/G"],
    "receiving": ["TGT/G", "REC_YDS/G", "REC/G"],
}

STAT_DISPLAY_NAMES = {
    "ATT/G": "ATT/G",
    "CMP/G": "CMP/G",
    "PASS_YDS/G": "YDS/G",
    "PASS_TD/G": "TD/G",
    "INT/G": "INT/G",
    "CAR/G": "CAR/G",
    "RUSH_YDS/G": "YDS/G",
    "RUSH_TD/G": "TD/G",
    "TGT/G": "TGT/G",
    "REC/G": "REC/G",
    "REC_YDS/G": "YDS/G",
    "REC_TD/G": "TD/G",
}

RATE_FORMULAS = [
    ("ATT/G", "ATT", "G"),
    ("CMP/G", "CMP", "G"),
    ("PASS_YDS/G", "PASS_YDS", "G"),
    ("PASS_TD/G", "PASS_TD", "G"),
    ("INT/G", "INT", "G"),
    ("CAR/G", "CAR", "G"),
    ("RUSH_YDS/G", "RUSH_YDS", "G"),
    ("RUSH_TD/G", "RUSH_TD", "G"),
    ("TGT/G", "TGT", "G"),
    ("REC/G", "REC", "G"),
    ("REC_YDS/G", "REC_YDS", "G"),
    ("REC_TD/G", "REC_TD", "G"),
]


def full_season_games(season: int) -> int:
    """Regular-season games on the schedule (16 through 2020, 17 from 2021)."""
    return 17 if int(season) >= 2021 else 16


def ensure_projection_games(df: pd.DataFrame, season: int) -> pd.DataFrame:
    """Fill missing projection games with a full-season slate."""
    out = df.copy()
    games = full_season_games(season)
    if "G" not in out.columns:
        out["G"] = float(games)
        return out
    values = pd.to_numeric(out["G"], errors="coerce")
    out["G"] = values.where(values > 0, float(games))
    return out


def _safe_div(numer: pd.Series, denom: pd.Series) -> pd.Series:
    numer = pd.to_numeric(numer, errors="coerce")
    denom = pd.to_numeric(denom, errors="coerce")
    result = numer / denom
    return result.where(denom > 0)


def add_rate_stats(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for rate, numer, denom in RATE_FORMULAS:
        if numer in out.columns and denom in out.columns:
            out[rate] = _safe_div(out[numer], out[denom])
    return out


def scored_rate_stats(pool: dict) -> list[str]:
    """Stats scored with league adjustment and game weighting."""
    rates = list(pool["rates"])
    if pool.get("volume_as_rate"):
        volume = pool["volume"]
        if volume not in rates:
            return [volume, *rates]
    return rates


def stat_base_name(player_type: str, stat: str) -> str:
    clean = stat.replace("fan_", "").replace("/", "").replace("-", "")
    return f"{player_type}{clean}"


def stat_display_name(stat: str) -> str:
    return STAT_DISPLAY_NAMES.get(stat, stat)
