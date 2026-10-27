"""Counting columns and rate stats shared by the NFL scrape and evaluation."""

from __future__ import annotations

import pandas as pd

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

# player type -> volume weight, rates, and unprojected-volume prior.
# Each prior is about the mean volume among players who recorded that stat and
# were absent from a projection (30 attempts, 10 carries, 8 targets).
POOLS: dict[str, dict] = {
    "passing": {
        "label": "Passing",
        "volume": "ATT",
        "volume_label": "Attempts",
        "rates": ["CMP/ATT", "YDS/CMP", "TD/CMP", "INT/ATT"],
        "counting": ["ATT", "CMP", "PASS_YDS", "PASS_TD", "INT"],
        "prior": 30,
    },
    "rushing": {
        "label": "Rushing",
        "volume": "CAR",
        "volume_label": "Carries",
        "rates": ["YDS/CAR", "TD/CAR"],
        "counting": ["CAR", "RUSH_YDS", "RUSH_TD"],
        "prior": 10,
    },
    "receiving": {
        "label": "Receiving",
        "volume": "TGT",
        "volume_label": "Targets",
        "rates": ["REC/TGT", "YDS/REC", "TD/REC"],
        "counting": ["TGT", "REC", "REC_YDS", "REC_TD"],
        "prior": 8,
    },
}

PLAYER_TYPES = list(POOLS)

# Home-page charts. Everything else is on the all-time stats pages.
OVERVIEW_STATS = {
    "passing": ["ATT", "YDS/CMP"],
    "rushing": ["CAR", "YDS/CAR"],
    "receiving": ["TGT", "YDS/REC", "REC/TGT"],
}

RATE_FORMULAS = [
    ("CMP/ATT", "CMP", "ATT"),
    ("YDS/CMP", "PASS_YDS", "CMP"),
    ("TD/CMP", "PASS_TD", "CMP"),
    ("INT/ATT", "INT", "ATT"),
    ("YDS/CAR", "RUSH_YDS", "CAR"),
    ("TD/CAR", "RUSH_TD", "CAR"),
    ("REC/TGT", "REC", "TGT"),
    ("YDS/REC", "REC_YDS", "REC"),
    ("TD/REC", "REC_TD", "REC"),
]


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


def stat_base_name(player_type: str, stat: str) -> str:
    clean = stat.replace("fan_", "").replace("/", "").replace("-", "")
    return f"{player_type}{clean}"
