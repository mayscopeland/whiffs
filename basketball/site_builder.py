"""Render the Bricks static site from cached evaluation data via Jinja2."""

from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
SITE_DIR = ROOT / "_site"
REPORTS_DIR = ROOT / "reports"
CACHE_DIR = REPORTS_DIR / "site_cache"
CACHE_FILES = ("site.json", "years.json", "misses.json", "players.json")

SYSTEM_COLORS = {
    "SPS": "text-amber-900 dark:text-amber-700",
    "ESPN": "text-red-600 dark:text-red-400",
}


def end_year_to_season(end_year: int | str) -> str:
    end = int(end_year)
    return f"{end - 1}-{str(end)[-2:]}"


def to_fixed(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "-"
    try:
        if isinstance(value, (float, np.floating)) and (math.isnan(value) or math.isinf(value)):
            return "-"
        if pd.isna(value):
            return "-"
    except (TypeError, ValueError):
        pass
    try:
        return f"{float(value):.{int(decimals)}f}"
    except (TypeError, ValueError):
        return "-"


def sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            str(k) if isinstance(k, (np.integer, np.floating)) else k: sanitize(v)
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return round(float(obj), 6)
    if isinstance(obj, np.ndarray):
        return sanitize(obj.tolist())
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return obj


def create_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["toFixed"] = to_fixed
    env.filters["season"] = end_year_to_season
    return env


def _write(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _stat_num(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        if isinstance(value, (float, np.floating)) and (math.isnan(value) or math.isinf(value)):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def player_rank_score(player: dict[str, Any]) -> float:
    """Career Actual PTS for search ranking."""
    total = 0.0
    for year_data in (player.get("years") or {}).values():
        actual = ((year_data.get("player") or {}).get("Actual")) or {}
        total += _stat_num(actual.get("PTS"))
    return total


def build_players_index(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = [
        {
            "id": str(player["id"]),
            "name": player.get("name") or "",
            "score": player_rank_score(player),
        }
        for player in players
    ]
    index.sort(key=lambda row: (-row["score"], row["name"].lower()))
    for row in index:
        del row["score"]
    return index


def write_players_index(
    players: list[dict[str, Any]],
    site_dir: Path = SITE_DIR,
) -> Path:
    out_dir = site_dir / "assets" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "players-index.json"
    out_path.write_text(
        json.dumps(build_players_index(players), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return out_path


def copy_static_assets(site_dir: Path = SITE_DIR) -> None:
    for sub in ("img", "js"):
        src = ASSETS_DIR / sub
        dest = site_dir / "assets" / sub
        if dest.exists():
            shutil.rmtree(dest)
        if src.exists():
            shutil.copytree(src, dest)
    (site_dir / "assets" / "css").mkdir(parents=True, exist_ok=True)
    (site_dir / "assets" / "data").mkdir(parents=True, exist_ok=True)


def prepare_site_dir(site_dir: Path = SITE_DIR) -> None:
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True)
    copy_static_assets(site_dir)


def save_site_cache(
    site: dict[str, Any],
    years: dict[str, Any],
    misses: dict[str, Any],
    players: list[dict[str, Any]],
    cache_dir: Path = CACHE_DIR,
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "site.json": site,
        "years.json": years,
        "misses.json": misses,
        "players.json": players,
    }
    for name, data in payloads.items():
        (cache_dir / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"  Cached site data to {cache_dir}")


def load_site_cache(
    cache_dir: Path = CACHE_DIR,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    missing = [name for name in CACHE_FILES if not (cache_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Site cache incomplete in {cache_dir} (missing: {', '.join(missing)}). "
            "Run evaluation first: npm run basketball:evals"
        )
    site = json.loads((cache_dir / "site.json").read_text(encoding="utf-8"))
    years = json.loads((cache_dir / "years.json").read_text(encoding="utf-8"))
    misses = json.loads((cache_dir / "misses.json").read_text(encoding="utf-8"))
    players = json.loads((cache_dir / "players.json").read_text(encoding="utf-8"))
    return site, years, misses, players


def build_site(
    site: dict[str, Any],
    years: dict[str, Any],
    misses: dict[str, Any],
    players: list[dict[str, Any]],
    site_dir: Path = SITE_DIR,
) -> None:
    print("\nBuilding HTML site...")
    prepare_site_dir(site_dir)

    site = sanitize(site)
    years = sanitize(years)
    misses = sanitize(misses)
    players = sanitize(players)
    save_site_cache(site, years, misses, players)

    index_path = write_players_index(players, site_dir)
    print(f"  Wrote {index_path.relative_to(site_dir)} ({len(players)} players)")

    env = create_env()
    base_ctx = {
        "site": site,
        "years": years,
        "misses": misses,
        "system_colors": SYSTEM_COLORS,
        "brand": "Bricks",
    }

    pages = [
        ("index.html", "index.html", "/", {"title": "NBA Projection Accuracy"}),
        ("stats.html", "stats/index.html", "/stats/", {"title": "All-Time Projection Accuracy"}),
        ("fantasy.html", "fantasy/index.html", "/fantasy/", {"title": "Fantasy Leaderboards"}),
        ("methodology.html", "methodology/index.html", "/methodology/", {"title": "Methodology"}),
        ("404.html", "404.html", "/404.html", {"title": "Page Not Found"}),
    ]

    for template_name, out_rel, page_url, extra in pages:
        html = env.get_template(template_name).render(
            **base_ctx,
            page_url=page_url,
            **extra,
        )
        _write(site_dir / out_rel, html)
        print(f"  Wrote {out_rel}")

    for year in site.get("years", []):
        year_key = str(year)
        season = end_year_to_season(year)
        html = env.get_template("season.html").render(
            **base_ctx,
            page_url=f"/seasons/{year}/",
            year=year,
            year_key=year_key,
            season=season,
            yearData=years.get(year_key),
            title=f"{season} Projection Accuracy",
        )
        _write(site_dir / "seasons" / year_key / "index.html", html)
    print(f"  Wrote {len(site.get('years', []))} season pages")

    for year in site.get("years", []):
        year_key = str(year)
        season = end_year_to_season(year)
        html = env.get_template("fantasy_season.html").render(
            **base_ctx,
            page_url=f"/fantasy/{year}/",
            year=year,
            year_key=year_key,
            season=season,
            yearData=years.get(year_key),
            title=f"{season} Fantasy Projection Accuracy",
        )
        _write(site_dir / "fantasy" / year_key / "index.html", html)
    print(f"  Wrote {len(site.get('years', []))} fantasy season pages")

    for i, player in enumerate(players):
        html = env.get_template("player.html").render(
            **base_ctx,
            page_url=f"/players/{player['id']}/",
            player=player,
            title=f"{player.get('name', 'Player')} Projection Accuracy",
        )
        _write(site_dir / "players" / str(player["id"]) / "index.html", html)
        if (i + 1) % 500 == 0 or (i + 1) == len(players):
            print(f"  Wrote {i + 1}/{len(players)} player pages")

    print(f"HTML site written to {site_dir}")


def main() -> int:
    try:
        site, years, misses, players = load_site_cache()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    build_site(site, years, misses, players)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
