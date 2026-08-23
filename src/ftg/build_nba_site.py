from __future__ import annotations

import argparse
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from src.ftg.http_cache import CachedHttpClient

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATS_URL = (
    "https://raw.githubusercontent.com/EasySportsApps/nba_api_25_26_data/"
    "refs/heads/main/nba_players_25_26_regular_season_wide_data.csv"
)
NBA_STATS_URL = "https://www.nba.com/stats/players/traditional?PerMode=Totals&Season=2025-26"
WIKIDATA_URL = "https://query.wikidata.org/sparql"
DEFAULT_OUTPUT = ROOT / "docs" / "nba" / "data" / "dashboard.json"
DEFAULT_STATS_CACHE = ROOT / "data" / "cache" / "nba_players_25_26.csv"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "nba_wikidata.json"

TEAM_META = {
    "ATL": ("Atlanta Hawks", "Eastern Conference"),
    "BKN": ("Brooklyn Nets", "Eastern Conference"),
    "BOS": ("Boston Celtics", "Eastern Conference"),
    "CHA": ("Charlotte Hornets", "Eastern Conference"),
    "CHI": ("Chicago Bulls", "Eastern Conference"),
    "CLE": ("Cleveland Cavaliers", "Eastern Conference"),
    "DAL": ("Dallas Mavericks", "Western Conference"),
    "DEN": ("Denver Nuggets", "Western Conference"),
    "DET": ("Detroit Pistons", "Eastern Conference"),
    "GSW": ("Golden State Warriors", "Western Conference"),
    "HOU": ("Houston Rockets", "Western Conference"),
    "IND": ("Indiana Pacers", "Eastern Conference"),
    "LAC": ("LA Clippers", "Western Conference"),
    "LAL": ("Los Angeles Lakers", "Western Conference"),
    "MEM": ("Memphis Grizzlies", "Western Conference"),
    "MIA": ("Miami Heat", "Eastern Conference"),
    "MIL": ("Milwaukee Bucks", "Eastern Conference"),
    "MIN": ("Minnesota Timberwolves", "Western Conference"),
    "NOP": ("New Orleans Pelicans", "Western Conference"),
    "NYK": ("New York Knicks", "Eastern Conference"),
    "OKC": ("Oklahoma City Thunder", "Western Conference"),
    "ORL": ("Orlando Magic", "Eastern Conference"),
    "PHI": ("Philadelphia 76ers", "Eastern Conference"),
    "PHX": ("Phoenix Suns", "Western Conference"),
    "POR": ("Portland Trail Blazers", "Western Conference"),
    "SAC": ("Sacramento Kings", "Western Conference"),
    "SAS": ("San Antonio Spurs", "Western Conference"),
    "TOR": ("Toronto Raptors", "Eastern Conference"),
    "UTA": ("Utah Jazz", "Western Conference"),
    "WAS": ("Washington Wizards", "Eastern Conference"),
}


def _value(binding: dict, key: str) -> str | None:
    value = binding.get(key, {}).get("value")
    return str(value) if value is not None else None


def _qid(value: str | None) -> str | None:
    return value.rsplit("/", 1)[-1] if value else None


def parse_point(value: str | None) -> tuple[float | None, float | None]:
    if not value:
        return None, None
    match = re.fullmatch(r"Point\((-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)\)", value)
    if not match:
        return None, None
    return float(match.group(2)), float(match.group(1))


def wikidata_query(player_ids: Iterable[str]) -> str:
    values = " ".join(json.dumps(str(player_id)) for player_id in player_ids)
    return f"""
SELECT ?nbaId ?player ?playerLabel ?dob ?birthplace ?birthplaceLabel ?coord ?country ?countryLabel WHERE {{
  VALUES ?nbaId {{ {values} }}
  ?player wdt:P3647 ?nbaId.
  OPTIONAL {{ ?player wdt:P569 ?dob. }}
  OPTIONAL {{
    ?player wdt:P19 ?birthplace.
    OPTIONAL {{ ?birthplace wdt:P625 ?coord. }}
    OPTIONAL {{ ?birthplace wdt:P17 ?country. }}
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
""".strip()


def choose_wikidata_rows(bindings: list[dict]) -> dict[str, dict]:
    selected: dict[str, dict] = {}
    for binding in bindings:
        player_id = _value(binding, "nbaId")
        if not player_id:
            continue
        lat, lon = parse_point(_value(binding, "coord"))
        candidate = {
            "wikidata_qid": _qid(_value(binding, "player")),
            "wikidata_name": _value(binding, "playerLabel"),
            "dob": (_value(binding, "dob") or "")[:10] or None,
            "birth_place_qid": _qid(_value(binding, "birthplace")),
            "place": _value(binding, "birthplaceLabel"),
            "birth_country_qid": _qid(_value(binding, "country")),
            "country": _value(binding, "countryLabel"),
            "lat": lat,
            "lon": lon,
        }
        score = 4 * int(lat is not None and lon is not None) + 2 * int(bool(candidate["place"])) + int(bool(candidate["dob"]))
        current = selected.get(player_id)
        if current is None or score > current["_score"]:
            selected[player_id] = {**candidate, "_score": score}
    return {player_id: {key: value for key, value in row.items() if key != "_score"} for player_id, row in selected.items()}


def fetch_wikidata(
    player_ids: list[str],
    cache_path: Path = DEFAULT_WIKIDATA_CACHE,
    *,
    batch_size: int = 50,
    delay: float = 0.25,
) -> dict[str, dict]:
    cache: dict[str, dict] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}
    missing = [player_id for player_id in player_ids if player_id not in cache]
    session = requests.Session()
    session.headers.update({"User-Agent": "FootballGeo/1.0 (https://github.com/adhni/football-geo)"})
    for start in range(0, len(missing), batch_size):
        batch = missing[start : start + batch_size]
        response = session.get(
            WIKIDATA_URL,
            params={"query": wikidata_query(batch), "format": "json"},
            timeout=60,
        )
        response.raise_for_status()
        matches = choose_wikidata_rows(response.json()["results"]["bindings"])
        for player_id in batch:
            cache[player_id] = matches.get(player_id, {})
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        if start + batch_size < len(missing) and delay:
            time.sleep(delay)
    return cache


def load_stats(stats_input: Path | None = None, *, force: bool = False) -> pd.DataFrame:
    if stats_input is not None:
        return pd.read_csv(stats_input)
    result = CachedHttpClient(delay=0.0).fetch_text(DEFAULT_STATS_URL, DEFAULT_STATS_CACHE, force=force)
    return pd.read_csv(io.StringIO(result.text))


def build_payload(stats: pd.DataFrame, wikidata: dict[str, dict], *, generated_at: str | None = None) -> dict:
    required = {
        "player_id", "player_name", "team", "position", "country", "age_completed_years",
        "birthdate", "minutes_played", "wins", "losses", "one_point_made", "two_point_made",
        "three_point_made", "offensive_rebounds", "defensive_rebounds", "assists", "steals", "blocks",
    }
    if missing := required - set(stats.columns):
        raise ValueError(f"NBA export is missing columns: {', '.join(sorted(missing))}")
    unknown_teams = sorted(set(stats["team"].dropna().astype(str)) - set(TEAM_META))
    if unknown_teams:
        raise ValueError(f"NBA export has unknown team codes: {', '.join(unknown_teams)}")

    records: list[dict] = []
    unresolved: list[dict] = []
    for row in stats.sort_values(["team", "player_name"]).itertuples(index=False):
        player_id = str(row.player_id)
        place = wikidata.get(player_id, {})
        team, conference = TEAM_META[str(row.team)]
        mapped = place.get("lat") is not None and place.get("lon") is not None
        status = "resolved" if mapped else (
            "identity unmatched" if not place else "birthplace coordinates unavailable"
        )
        games = int(row.wins) + int(row.losses)
        minutes = int(round(float(row.minutes_played)))
        points = int(row.one_point_made) + 2 * int(row.two_point_made) + 3 * int(row.three_point_made)
        rebounds = int(row.offensive_rebounds) + int(row.defensive_rebounds)
        record = {
            "id": f"nba:{player_id}",
            "nbaId": player_id,
            "name": str(row.player_name),
            "team": team,
            "teamCode": str(row.team),
            "conference": conference,
            "year": 2026,
            "games": games,
            "minutes": minutes,
            "points": points,
            "rebounds": rebounds,
            "assists": int(row.assists),
            "steals": int(row.steals),
            "blocks": int(row.blocks),
            "position": str(row.position),
            "nationality": str(row.country),
            "age": int(float(row.age_completed_years)) if pd.notna(row.age_completed_years) else None,
            "dob": str(row.birthdate)[:10] if pd.notna(row.birthdate) else place.get("dob"),
            "place": place.get("place") if mapped else None,
            "country": place.get("country") if mapped else None,
            "lat": round(float(place["lat"]), 6) if mapped else None,
            "lon": round(float(place["lon"]), 6) if mapped else None,
            "mapped": mapped,
            "status": status,
            "wikidataQid": place.get("wikidata_qid"),
            "birthPlaceQid": place.get("birth_place_qid"),
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": record["name"], "status": status})

    mapped_records = [record for record in records if record["mapped"]]
    total_minutes = sum(record["minutes"] for record in records)
    mapped_minutes = sum(record["minutes"] for record in mapped_records)
    birthplaces = {record["birthPlaceQid"] for record in mapped_records if record["birthPlaceQid"]}
    generated_at = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "meta": {
            "title": "Basketball Talent Geography",
            "sport": "nba",
            "scope": "2025–26 NBA regular season",
            "season": "2025–26",
            "year": 2026,
            "teams": [TEAM_META[code][0] for code in TEAM_META],
            "conferences": ["Eastern Conference", "Western Conference"],
            "generated_at": generated_at,
            "stats_source_name": "NBA Stats API",
            "stats_source_url": NBA_STATS_URL,
            "snapshot_source_url": DEFAULT_STATS_URL,
            "birthplace_source_name": "Wikidata",
            "birthplace_source_url": "https://www.wikidata.org/",
        },
        "summary": {
            "teams": len({record["team"] for record in records}),
            "players": len(records),
            "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "minutes": total_minutes,
            "mapped_minutes": mapped_minutes,
            "minute_coverage_pct": round(mapped_minutes / total_minutes * 100, 1) if total_minutes else 0,
            "birthplaces": len(birthplaces),
            "birth_countries": len({record["country"] for record in mapped_records if record["country"]}),
            "unresolved_players": len(unresolved),
        },
        "records": records,
        "unresolved": unresolved,
    }


def run(
    stats_input: Path | None = None,
    output_path: Path = DEFAULT_OUTPUT,
    wikidata_cache: Path = DEFAULT_WIKIDATA_CACHE,
    *,
    force_stats: bool = False,
) -> dict:
    stats = load_stats(stats_input, force=force_stats)
    player_ids = [str(player_id) for player_id in stats["player_id"]]
    wikidata = fetch_wikidata(player_ids, wikidata_cache)
    payload = build_payload(stats, wikidata)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {payload['summary']['players']:,} NBA players with "
        f"{payload['summary']['player_coverage_pct']:.1f}% birthplace coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static NBA geography dataset")
    parser.add_argument("--stats-input", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--wikidata-cache", type=Path, default=DEFAULT_WIKIDATA_CACHE)
    parser.add_argument("--force-stats", action="store_true")
    args = parser.parse_args()
    run(args.stats_input, args.output, args.wikidata_cache, force_stats=args.force_stats)


if __name__ == "__main__":
    main()
