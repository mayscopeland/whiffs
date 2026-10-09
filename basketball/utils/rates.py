"""Counting columns and per-minute rates shared by projections and evaluation."""

from __future__ import annotations

import pandas as pd

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
    "REB/MIN",
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


def ensure_total_rebounds(df: pd.DataFrame) -> pd.DataFrame:
    """Use a published REB total, or OREB + DREB when a source splits them.

    Rows that have both components use the sum. Rows that have only REB keep
    that total. REB/MIN is filled when minutes are present.
    """
    out = df.copy()
    published = (
        pd.to_numeric(out["REB"], errors="coerce") if "REB" in out.columns else None
    )
    if "OREB" in out.columns and "DREB" in out.columns:
        split = pd.to_numeric(out["OREB"], errors="coerce") + pd.to_numeric(
            out["DREB"], errors="coerce"
        )
        out["REB"] = split if published is None else split.where(split.notna(), published)
    elif published is not None:
        out["REB"] = published
    if "REB" in out.columns and "MIN" in out.columns:
        out["REB/MIN"] = _safe_div(out["REB"], out["MIN"])
    return out


def add_rate_stats(df: pd.DataFrame) -> pd.DataFrame:
    out = ensure_total_rebounds(df)
    out["PTS/MIN"] = _safe_div(out["PTS"], out["MIN"])
    out["OREB/MIN"] = _safe_div(out["OREB"], out["MIN"])
    out["DREB/MIN"] = _safe_div(out["DREB"], out["MIN"])
    out["REB/MIN"] = _safe_div(out["REB"], out["MIN"])
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
