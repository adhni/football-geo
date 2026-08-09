from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE = "https://www.11v11.com"


@dataclass
class TeamSeasonPlayer:
    player_name: str
    player_url: str | None
    starts: int
    sub_appearances: int
    goals: int
    position: str | None


def _to_int(value: str | None) -> int:
    if value is None:
        return 0
    value = value.strip()
    if not value or value in {"-", "–", "—"}:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def parse_team_season_html(html: str) -> list[TeamSeasonPlayer]:
    """Parse a 11v11 national-team season squad statistics table.

    Expected meaningful headers include Player, A, S, G and Position.
    For national-team squad pages in this project, A is treated as starts and
    S as substitute appearances, consistent with the source's player stats.
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    target = None
    header_map: dict[str, int] = {}

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [c.get_text(" ", strip=True) for c in rows[0].find_all(["th", "td"])]
        normalized = {h.strip(): i for i, h in enumerate(headers)}
        if "Player" in normalized and "A" in normalized and "S" in normalized:
            target = table
            header_map = normalized
            break

    if target is None:
        return []

    out: list[TeamSeasonPlayer] = []
    rows = target.find_all("tr")[1:]
    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        vals = [c.get_text(" ", strip=True) for c in cells]
        if len(vals) <= header_map["Player"]:
            continue
        player_cell = cells[header_map["Player"]]
        player_name = vals[header_map["Player"]].strip()
        if not player_name:
            continue
        link = player_cell.find("a")
        player_url = urljoin(BASE, link.get("href")) if link and link.get("href") else None
        out.append(
            TeamSeasonPlayer(
                player_name=player_name,
                player_url=player_url,
                starts=_to_int(vals[header_map["A"]] if header_map["A"] < len(vals) else None),
                sub_appearances=_to_int(vals[header_map["S"]] if header_map["S"] < len(vals) else None),
                goals=_to_int(vals[header_map["G"]] if "G" in header_map and header_map["G"] < len(vals) else None),
                position=(vals[header_map["Position"]].strip() if "Position" in header_map and header_map["Position"] < len(vals) else None),
            )
        )
    return out


def rows_as_dicts(rows: Iterable[TeamSeasonPlayer]) -> list[dict]:
    return [asdict(r) for r in rows]
