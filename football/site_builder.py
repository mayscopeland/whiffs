"""Render the Drops static site from cached evaluation data via Jinja2."""

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

sys.path.insert(0, str(ROOT / "utils"))
from rates import OVERVIEW_STATS, POOLS, stat_base_name, stat_display_name  # noqa: E402

SYSTEM_COLORS = {
    "ESPN": "text-red-600 dark:text-red-400",
    "Sleeper": "text-teal-600 dark:text-teal-400",
    "FFToday": "text-orange-600 dark:text-orange-400",
    "FantasyPros": "text-blue-700 dark:text-blue-300",
}


def season_label(year: int | str) -> str:
    return str(year)


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


def stat_slug(stat: str) -> str:
    display = stat[4:] if stat.startswith("fan_") else stat
    return display.replace("/", "-").replace("(", "").replace(")", "").lower()


def page_slug(pool: str, stat: str) -> str:
    return f"{pool}-{stat_slug(stat)}"


def chart_clean(stat: str) -> str:
    display = stat[4:] if stat.startswith("fan_") else stat
    return display.replace("/", "").replace("-", "")


def template_pools() -> list[dict[str, Any]]:
    pools = []
    for key, pool in POOLS.items():
        overview = set(OVERVIEW_STATS[key])
        volume_stat = pool["volume"]
        volume_as_rate = bool(pool.get("volume_as_rate"))
        rates = [
            {
                "name": stat_display_name(stat),
                "stat": stat,
                "baseName": stat_base_name(key, stat),
                "isVolume": False,
                "overview": stat in overview,
                "slug": page_slug(key, stat),
            }
            for stat in pool["rates"]
        ]
        pools.append(
            {
                "key": key,
                "label": pool["label"],
                "volumeLabel": pool["volume_label"],
                "prior": pool["prior"],
                "counting": pool["counting"],
                "volume": {
                    "name": pool["volume_label"],
                    "stat": volume_stat,
                    "baseName": stat_base_name(key, volume_stat),
                    "isVolume": not volume_as_rate,
                    "overview": volume_stat in overview,
                    "slug": page_slug(key, volume_stat),
                },
                "rates": rates,
            }
        )
    return pools


def season_stat_defs(pools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages = []
    for pool in pools:
        volume = pool["volume"]
        pages.append(
            {
                "pool": pool["key"],
                "pool_label": pool["label"],
                "name": volume["name"],
                "stat": volume["stat"],
                "slug": volume["slug"],
                "is_volume": volume["isVolume"],
                "chart_id": (
                    f"{pool['key']}Volume"
                    if volume["isVolume"]
                    else f"{pool['key']}{chart_clean(volume['stat'])}"
                ),
            }
        )
        for rate in pool["rates"]:
            pages.append(
                {
                    "pool": pool["key"],
                    "pool_label": pool["label"],
                    "name": rate["name"],
                    "stat": rate["stat"],
                    "slug": rate["slug"],
                    "is_volume": False,
                    "chart_id": f"{pool['key']}{chart_clean(rate['stat'])}",
                }
            )
    return pages


def filter_year_data(year_data: dict[str, Any] | None, pool: str, stats: set[str]) -> dict[str, Any]:
    if not year_data:
        return {}
    rows = year_data.get(pool) or []
    return {pool: [row for row in rows if row.get("stat") in stats]}


def filter_year_data_summary(year_data: dict[str, Any] | None, pools: list[dict[str, Any]], fantasy: bool) -> dict[str, Any]:
    if not year_data:
        return {}
    out: dict[str, Any] = {}
    for pool in pools:
        wanted = {pool["volume"]["stat"], *[r["stat"] for r in pool["rates"]]}
        if fantasy:
            wanted = {f"fan_{s}" for s in wanted}
        rows = year_data.get(pool["key"]) or []
        out[pool["key"]] = [row for row in rows if row.get("stat") in wanted]
    return out


def pools_for_charts(pools: list[dict[str, Any]], summary_url: str) -> list[dict[str, Any]]:
    """Pools for season pages: hash nav + miss page links under each chart."""
    enriched = []
    for pool in pools:
        volume = {
            **pool["volume"],
            "miss_href": f"{summary_url}{pool['volume']['slug']}/",
        }
        rates = [
            {**rate, "miss_href": f"{summary_url}{rate['slug']}/"}
            for rate in pool["rates"]
        ]
        enriched.append({**pool, "volume": volume, "rates": rates})
    return enriched


def pools_for_misses(pools: list[dict[str, Any]], summary_url: str) -> list[dict[str, Any]]:
    """Pools for miss pages: path links between miss pages."""
    enriched = []
    for pool in pools:
        volume = {**pool["volume"], "href": f"{summary_url}{pool['volume']['slug']}/"}
        rates = [{**rate, "href": f"{summary_url}{rate['slug']}/"} for rate in pool["rates"]]
        enriched.append({**pool, "volume": volume, "rates": rates})
    return enriched


def create_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["toFixed"] = to_fixed
    env.filters["season"] = season_label
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
    """Career attempts, carries, and targets, for search ranking."""
    total = 0.0
    membership_stats = {
        key: pool.get("membership", pool["volume"]) for key, pool in POOLS.items()
    }
    for year_data in (player.get("years") or {}).values():
        for player_type, membership_stat in membership_stats.items():
            actual = ((year_data.get(player_type) or {}).get("Actual")) or {}
            total += _stat_num(actual.get(membership_stat))
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


def write_players_index(players: list[dict[str, Any]], site_dir: Path = SITE_DIR) -> Path:
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


def load_site_cache(cache_dir: Path = CACHE_DIR) -> tuple:
    missing = [name for name in ("site.json", "years.json", "misses.json", "players.json") if not (cache_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing {', '.join(missing)} in {cache_dir}. Run `npm run football:evals` first."
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
    pools = template_pools()
    base_ctx = {
        "site": site,
        "years": years,
        "misses": misses,
        "system_colors": SYSTEM_COLORS,
        "brand": "Drops",
    }

    static_pages = [
        ("index.html", "index.html", "/", {"title": "NFL Projection Accuracy"}),
        ("stats.html", "stats/index.html", "/stats/", {"title": "All-Time Projection Accuracy"}),
        ("fantasy.html", "fantasy/index.html", "/fantasy/", {"title": "Fantasy Leaderboards"}),
        ("methodology.html", "methodology/index.html", "/methodology/", {"title": "Methodology"}),
        ("404.html", "404.html", "/404.html", {"title": "Page Not Found"}),
    ]

    for template_name, out_rel, page_url, extra in static_pages:
        html = env.get_template(template_name).render(**base_ctx, pools=pools, page_url=page_url, **extra)
        _write(site_dir / out_rel, html)
        print(f"  Wrote {out_rel}")

    pages = season_stat_defs(pools)

    def write_season_variant(
        *,
        fantasy: bool,
        section: str,
        title_suffix: str,
        back_label_fmt: str,
        stat_qualifier: str = "",
    ) -> None:
        summary_count = 0
        stat_count = 0
        for year in site.get("years", []):
            year_key = str(year)
            summary_url = f"/{section}/{year}/"
            year_full = years.get(year_key)
            year_misses = misses.get(year_key) or {}
            chart_pools = pools_for_charts(pools, summary_url)
            miss_pools = pools_for_misses(pools, summary_url)
            html = env.get_template("season.html" if not fantasy else "fantasy_season.html").render(
                **base_ctx,
                pools=chart_pools,
                page_url=summary_url,
                summary_url=summary_url,
                year=year,
                year_key=year_key,
                season=str(year),
                yearData=year_full,
                title=f"{year} {title_suffix}",
                fantasy=fantasy,
            )
            _write(site_dir / section / year_key / "index.html", html)
            summary_count += 1

            for page in pages:
                data_stat = f"fan_{page['stat']}" if fantasy else page["stat"]
                page_url = f"{summary_url}{page['slug']}/"
                pool_obj = next(p for p in miss_pools if p["key"] == page["pool"])
                parts = [str(year)]
                if stat_qualifier:
                    parts.append(stat_qualifier)
                parts.extend([page["pool_label"], page["name"]])
                page_heading = " ".join(parts)
                html = env.get_template("season_stat.html").render(
                    **base_ctx,
                    pools=miss_pools,
                    page_url=page_url,
                    summary_url=summary_url,
                    year=year,
                    year_key=year_key,
                    season=str(year),
                    yearData=filter_year_data(year_full, page["pool"], {data_stat}),
                    yearMisses=year_misses,
                    title=page_heading,
                    heading=page_heading,
                    back_label=back_label_fmt.format(year=year),
                    fantasy=fantasy,
                    current_slug=page["slug"],
                    stat_page={**page, "data_stat": data_stat},
                    pool=pool_obj,
                )
                _write(site_dir / section / year_key / page["slug"] / "index.html", html)
                stat_count += 1
        print(f"  Wrote {summary_count} {section} season pages and {stat_count} {section} miss pages")

    write_season_variant(
        fantasy=False,
        section="seasons",
        title_suffix="Projection Accuracy",
        back_label_fmt="{year} stats",
    )
    write_season_variant(
        fantasy=True,
        section="fantasy",
        title_suffix="Fantasy Projection Accuracy",
        back_label_fmt="{year} fantasy stats",
        stat_qualifier="Fantasy",
    )

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
