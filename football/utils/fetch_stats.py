"""Scrape NFL.com regular-season player leaderboards into football/stats.

Passing, rushing, and receiving pages are fetched with requests and
BeautifulSoup. Each player is stored under the slug from /players/{slug}/.
"""

from __future__ import annotations

import argparse
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = ROOT / "stats"
BASE = "https://www.nfl.com"
PAGE = (
    BASE + "/stats/player-stats/category/{category}/{season}/reg/all/{sort}/desc"
)

HEADERS = {
    "Accept": "text/html",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
}

# Leaderboard header -> counting column. Headers are lowercased.
CATEGORIES = {
    "passing": {
        "sort": "passingyards",
        "columns": {
            "pass yds": "PASS_YDS",
            "att": "ATT",
            "cmp": "CMP",
            "td": "PASS_TD",
            "int": "INT",
        },
    },
    "rushing": {
        "sort": "rushingyards",
        "columns": {
            "rush yds": "RUSH_YDS",
            "att": "CAR",
            "td": "RUSH_TD",
        },
    },
    "receiving": {
        "sort": "receivingreceptions",
        "columns": {
            "rec": "REC",
            "yds": "REC_YDS",
            "td": "REC_TD",
            "tgts": "TGT",
        },
    },
}

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

REQUEST_PAUSE = 0.25


def header_key(text: str) -> str:
    return " ".join(text.split()).lower()


def parse_number(text: str) -> float:
    cleaned = text.replace(",", "").strip()
    if cleaned in {"", "-", "—"}:
        return 0.0
    return float(cleaned)


def player_slug(href: str) -> str:
    parts = [part for part in href.split("/") if part]
    if "players" not in parts:
        return ""
    index = parts.index("players")
    if index + 1 >= len(parts):
        return ""
    return parts[index + 1]


class Leaderboard:
    def __init__(self, session: requests.Session) -> None:
        self.session = session

    def get(self, url: str) -> BeautifulSoup:
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        time.sleep(REQUEST_PAUSE)
        return BeautifulSoup(response.text, "lxml")

    def parse_page(self, soup: BeautifulSoup, columns: dict[str, str]) -> list[dict]:
        table = soup.find("table")
        if table is None:
            return []
        header_cells = table.find("thead")
        if header_cells is None:
            return []
        headers = [header_key(cell.get_text(" ", strip=True)) for cell in header_cells.find_all("th")]
        indexes = {}
        for key, column in columns.items():
            if key not in headers:
                found = ", ".join(headers)
                raise SystemExit(f"NFL.com table is missing {key!r}. Headers: {found}")
            indexes[column] = headers.index(key)

        rows = []
        body = table.find("tbody") or table
        for tr in body.find_all("tr"):
            link = tr.find("a", href=True)
            if link is None:
                continue
            slug = player_slug(link["href"])
            if not slug:
                continue
            cells = tr.find_all("td")
            record = {
                "slug": slug,
                "table_name": link.get_text(" ", strip=True),
            }
            for column, index in indexes.items():
                if index >= len(cells):
                    record[column] = 0.0
                    continue
                record[column] = parse_number(cells[index].get_text(" ", strip=True))
            rows.append(record)
        return rows

    def next_url(self, soup: BeautifulSoup, current: str) -> str | None:
        for link in soup.find_all("a", href=True):
            if "aftercursor" not in link["href"]:
                continue
            if "next" not in link.get_text(" ", strip=True).lower():
                continue
            nxt = urljoin(current, link["href"])
            if nxt != current:
                return nxt
        return None

    def canonical(self, url: str) -> str:
        parts = [part for part in urlsplit(url).path.split("/") if part]
        if parts and parts[-1].lower() in {"asc", "desc"}:
            parts[-1] = parts[-1].upper()
        return BASE + "/" + "/".join(parts)

    def sort_roots(self, season: int, category: str) -> list[str]:
        """Every column sort, both directions.

        The Next Page link on these leaderboards repeats the second page, so
        a single sort stops at 50 players. Walking each column both ways
        collects the top and bottom of every stat the table can rank.
        """
        spec = CATEGORIES[category]
        first = PAGE.format(category=category, season=season, sort=spec["sort"])
        soup = self.get(first)
        roots = {self.canonical(first)}
        for link in soup.select("thead a[href]"):
            href = urljoin(first, link["href"])
            if f"/category/{category}/" not in urlsplit(href).path.lower():
                continue
            roots.add(self.canonical(href))
        flipped = set()
        for root in roots:
            if root.endswith("/DESC"):
                flipped.add(root[:-4] + "ASC")
            elif root.endswith("/ASC"):
                flipped.add(root[:-3] + "DESC")
        return sorted(roots | flipped)

    def walk(self, start: str, columns: dict[str, str]) -> list[dict]:
        url = start
        seen_urls: set[str] = set()
        seen_first: set[str] = set()
        rows: list[dict] = []
        while url and url not in seen_urls:
            seen_urls.add(url)
            soup = self.get(url)
            page_rows = self.parse_page(soup, columns)
            if not page_rows:
                break
            first = page_rows[0]["slug"]
            if first in seen_first:
                break
            seen_first.add(first)
            rows.extend(page_rows)
            url = self.next_url(soup, url)
        return rows

    def has_players(self, season: int, category: str) -> bool:
        spec = CATEGORIES[category]
        url = PAGE.format(category=category, season=season, sort=spec["sort"])
        soup = self.get(url)
        return bool(self.parse_page(soup, spec["columns"]))

    def scrape_category(self, season: int, category: str) -> list[dict]:
        spec = CATEGORIES[category]
        by_slug: dict[str, dict] = {}
        for root in self.sort_roots(season, category):
            for row in self.walk(root, spec["columns"]):
                by_slug.setdefault(row["slug"], row)
        return list(by_slug.values())


def category_frame(rows: list[dict]) -> pd.DataFrame:
    records = []
    for row in rows:
        records.append(
            {
                "nfl_slug": row["slug"],
                "player_name": row["table_name"],
                **{key: row[key] for key in row if key not in {"slug", "table_name"}},
            }
        )
    if not records:
        return pd.DataFrame(columns=["nfl_slug", "player_name"])
    return pd.DataFrame(records)


def scrape_season(board: Leaderboard, season: int) -> pd.DataFrame:
    frames = []
    for category in CATEGORIES:
        rows = board.scrape_category(season, category)
        print(f"  {season} {category}: {len(rows)} players")
        frame = category_frame(rows)
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="nfl_slug", how="outer", suffixes=("", "_dup"))
        if "player_name_dup" in merged.columns:
            merged["player_name"] = merged["player_name"].fillna(merged["player_name_dup"])
            merged = merged.drop(columns=["player_name_dup"])
    for column in COUNTING_COLS:
        if column not in merged.columns:
            merged[column] = 0
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0)
    merged.insert(0, "season", season)
    return merged[["season", "nfl_slug", "player_name", *COUNTING_COLS]].sort_values(
        ["player_name", "nfl_slug"]
    )


def latest_season(board: Leaderboard) -> int:
    year = date.today().year + 1
    while year >= 1920:
        if board.has_players(year, "passing"):
            return year
        year -= 1
    raise SystemExit("NFL.com returned no passing leaderboard.")


def seasons_to_fetch(board: Leaderboard, args: argparse.Namespace) -> list[int]:
    if args.season:
        return sorted(set(args.season))
    start = args.last if args.last is not None else latest_season(board)
    stop = args.first if args.first is not None else 1920
    seasons = []
    year = start
    while year >= stop:
        if not board.has_players(year, "passing"):
            if args.first is None:
                break
            year -= 1
            continue
        seasons.append(year)
        year -= 1
    return seasons


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape NFL.com player leaderboards")
    parser.add_argument("--season", type=int, action="append", help="Scrape this season only. Repeatable.")
    parser.add_argument("--first", type=int, help="Oldest season to include when walking backward.")
    parser.add_argument("--last", type=int, help="Newest season to include when walking backward.")
    parser.add_argument("--refresh", action="store_true", help="Rewrite seasons that already have a CSV.")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(HEADERS)
    board = Leaderboard(session)
    STATS_DIR.mkdir(parents=True, exist_ok=True)

    for season in seasons_to_fetch(board, args):
        path = STATS_DIR / f"{season}.csv"
        if path.exists() and not args.refresh and not args.season:
            print(f"Skipping {season}; {path.name} exists")
            continue
        print(f"Scraping {season}...")
        # Walking the default range probes passing once to find the edge, then
        # scrapes it again here. --season scrapes each category once.
        frame = scrape_season(board, season)
        if frame.empty:
            print(f"  No players for {season}")
            continue
        frame.to_csv(path, index=False)
        print(f"  Wrote {path.name} ({len(frame)} players)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
