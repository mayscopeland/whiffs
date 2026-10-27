"""Map fantasy-site ids onto nfl_slug using the ffb_ids crosswalk.

The crosswalk is ``player_ids.csv`` from
https://github.com/mayscopeland/ffb_ids. It is downloaded from that repo on
each load. A site id that already has an ``nfl_slug`` is used as-is. When the
player name matches one slug, a missing ESPN, Sleeper, FFToday, or FantasyPros
id is filled in memory for this run. The GitHub file is not modified.
"""

from __future__ import annotations

import io
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

FOOTBALL_ROOT = Path(__file__).resolve().parents[1]
STATS_DIR = FOOTBALL_ROOT / "stats"
FFB_IDS_URL = "https://raw.githubusercontent.com/mayscopeland/ffb_ids/main/player_ids.csv"

SOURCE_COLUMNS = {
    "espn": ("espn_id", "espn_name"),
    "sleeper": ("sleeper_id", "sleeper_name"),
    "fftoday": ("fftoday_id", "fftoday_name"),
    "fantasypros": ("fantasypros_id", "fantasypros_name"),
}

_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")


def clean_id(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "<na>"}:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return text


def name_keys(name: object) -> list[str]:
    """Normalized name, plus a form that joins initials (A.J. and AJ)."""
    text = unicodedata.normalize("NFKD", str(name or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace(".", " ").replace("'", " ").replace("’", " ").replace("`", " ")
    text = _SUFFIX.sub(" ", text)
    key = re.sub(r"[^a-z0-9]+", " ", text).strip()
    if not key:
        return []
    keys = [key]
    parts = key.split()
    if any(len(part) == 1 for part in parts):
        collapsed: list[str] = []
        letters = ""
        for part in parts:
            if len(part) == 1:
                letters += part
            else:
                if letters:
                    collapsed.append(letters)
                    letters = ""
                collapsed.append(part)
        if letters:
            collapsed.append(letters)
        folded = " ".join(collapsed)
        if folded != key:
            keys.append(folded)
    return keys


def _download_ffb_ids() -> pd.DataFrame:
    request = urllib.request.Request(FFB_IDS_URL, headers={"User-Agent": "whiffs"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not download ffb_ids from {FFB_IDS_URL}: {exc}") from exc
    return pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)


class PlayerIds:
    def __init__(self, frame: pd.DataFrame, stats: pd.DataFrame):
        self.frame = frame.reset_index(drop=True)
        self.url = FFB_IDS_URL
        self._stats = stats
        self._index()

    @classmethod
    def load(cls, stats_dir: Path = STATS_DIR) -> PlayerIds:
        frame = _download_ffb_ids()
        stat_files = sorted(stats_dir.glob("*.csv"))
        if stat_files:
            stats = pd.concat(
                [pd.read_csv(file, dtype=str, keep_default_na=False) for file in stat_files],
                ignore_index=True,
            )
        else:
            stats = pd.DataFrame(columns=["player_name", "nfl_slug"])
        return cls(frame, stats)

    def _index(self) -> None:
        self.by_slug: dict[str, int] = {}
        self.by_source: dict[str, dict[str, list[int]]] = {
            source: {} for source in SOURCE_COLUMNS
        }
        for pos, row in self.frame.iterrows():
            slug = row["nfl_slug"]
            if slug and slug not in self.by_slug:
                self.by_slug[slug] = int(pos)
            for source, (id_col, _name_col) in SOURCE_COLUMNS.items():
                source_id = clean_id(row[id_col])
                if source_id:
                    self.by_source[source].setdefault(source_id, []).append(int(pos))
        self.stats_index = _name_index(
            zip(self._stats.get("player_name", []), self._stats.get("nfl_slug", []))
        )
        named = self.frame[(self.frame["nfl_slug"] != "") & (self.frame["nfl_name"] != "")]
        self.ffb_index = _name_index(zip(named["nfl_name"], named["nfl_slug"]))
        self.slug_names: dict[str, str] = {}
        if "player_name" in self._stats.columns:
            for name, slug in zip(self._stats["player_name"], self._stats["nfl_slug"]):
                if slug and slug not in self.slug_names and name:
                    self.slug_names[slug] = name

    def _match_name(self, player_name: str) -> str:
        keys = name_keys(player_name)
        for index in (self.stats_index, self.ffb_index):
            for key in keys:
                slugs = index.get(key) or set()
                if len(slugs) == 1:
                    return next(iter(slugs))
        return ""

    def nfl_slug(
        self,
        source: str,
        source_id: object,
        player_name: str,
        *,
        match_name: bool = True,
    ) -> str:
        """Site id to nfl_slug. Fills a missing site id in memory when the name matches one slug.

        A historical page can carry an older id than the one already stored.
        When the name still matches that one slug, the slug is used and the
        stored id is left as it is. Nothing is written back to GitHub.
        """
        source_id = clean_id(source_id)
        if not source_id or source not in SOURCE_COLUMNS:
            return ""
        id_col, name_col = SOURCE_COLUMNS[source]
        positions = self.by_source[source].get(source_id, [])
        for pos in positions:
            slug = self.frame.at[pos, "nfl_slug"]
            if slug:
                return slug
        if not match_name:
            return ""
        slug = self._match_name(player_name)
        if not slug:
            return ""
        slug_pos = self.by_slug.get(slug)
        if slug_pos is None:
            if positions:
                self._write_slug(positions[0], slug)
                return slug
            self._append(slug, player_name, id_col, name_col, source_id)
            return slug
        current = clean_id(self.frame.at[slug_pos, id_col])
        if current:
            return slug
        self._write_source(slug_pos, id_col, name_col, source_id, player_name)
        return slug

    def _write_slug(self, pos: int, slug: str) -> None:
        if self.frame.at[pos, "nfl_slug"] or slug in self.by_slug:
            return
        self.frame.at[pos, "nfl_slug"] = slug
        if not self.frame.at[pos, "nfl_name"]:
            self.frame.at[pos, "nfl_name"] = self.slug_names.get(slug, "")
        self.by_slug[slug] = pos

    def _write_source(
        self, pos: int, id_col: str, name_col: str, source_id: str, player_name: str
    ) -> None:
        self.frame.at[pos, id_col] = source_id
        if player_name and not self.frame.at[pos, name_col]:
            self.frame.at[pos, name_col] = player_name
        source = next(key for key, (column, _name) in SOURCE_COLUMNS.items() if column == id_col)
        self.by_source[source].setdefault(source_id, []).append(pos)

    def _append(
        self, slug: str, player_name: str, id_col: str, name_col: str, source_id: str
    ) -> None:
        row = {column: "" for column in self.frame.columns}
        row["nfl_slug"] = slug
        row["nfl_name"] = self.slug_names.get(slug) or player_name
        row[id_col] = source_id
        if player_name:
            row[name_col] = player_name
        pos = len(self.frame)
        self.frame.loc[pos] = row
        self.by_slug[slug] = pos
        source = next(key for key, (column, _name) in SOURCE_COLUMNS.items() if column == id_col)
        self.by_source[source].setdefault(source_id, []).append(pos)


def _name_index(pairs) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for name, slug in pairs:
        if not slug:
            continue
        for key in name_keys(name):
            index.setdefault(key, set()).add(str(slug))
    return index
