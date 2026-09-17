from __future__ import annotations

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

from src.ftg.geonames import (
    ADMIN1_URL,
    DEFAULT_ADMIN1_CACHE,
    DEFAULT_COUNTRIES_CACHE,
    DEFAULT_GEONAMES_CACHE,
    GEONAMES_CITIES_URL,
    GEONAMES_COUNTRIES_URL,
    build_city_index,
    load_admin1_aliases,
    load_country_codes,
    resolve_birthplace_with_admin1 as resolve_birthplace,
)
from src.ftg.http_cache import CachedHttpClient
from src.ftg.utils import (
    age_on as _age_on,
    download_binary as _download_binary,
    normalize_key as normalize,
    write_json as _write_json,
)

ROOT = Path(__file__).resolve().parents[2]
SEASON = 2025
SEASON_LABEL = "2025"
SEASON_END = date(2025, 9, 28)
TEAMS_URL = "https://statsapi.mlb.com/api/v1/teams?sportId=1&season=2025&hydrate=division"
TEAM_STATS_URL = (
    "https://statsapi.mlb.com/api/v1/stats?stats=season&group={group}"
    "&teamId={team_id}&season=2025&playerPool=ALL&hydrate=person&limit=100"
)

DEFAULT_OUTPUT = ROOT / "docs" / "mlb" / "data" / "dashboard.json"
DEFAULT_TEAMS_CACHE = ROOT / "data" / "cache" / "mlb_teams_2025.json"
DEFAULT_STATS_CACHE = ROOT / "data" / "cache" / "mlb_team_stats_2025"


def fetch_json(url: str, cache_path: Path, *, force: bool = False) -> dict[str, Any]:
    if cache_path.exists() and not force:
        try:
            value = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                return value
        except (json.JSONDecodeError, OSError):
            pass
    response = requests.get(url, timeout=60, headers={"User-Agent": "TalentGeography/1.0"})
    response.raise_for_status()
    value = response.json()
    _write_json(cache_path, value)
    return value


def parse_team_meta(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    teams: dict[str, dict[str, str]] = {}
    for row in payload.get("teams", []):
        if (row.get("sport") or {}).get("id") != 1 or not row.get("active", True):
            continue
        team_id = str(row.get("id") or "")
        name = str(row.get("name") or "")
        code = str(row.get("abbreviation") or "")
        league = str((row.get("league") or {}).get("name") or "")
        division = str((row.get("division") or {}).get("nameShort") or "")
        if team_id and name and code and league and division:
            teams[team_id] = {
                "team": name,
                "code": code,
                "conference": league,
                "division": division,
            }
    if len(teams) != 30:
        raise ValueError(f"Expected 30 MLB teams, found {len(teams)}")
    return dict(sorted(teams.items(), key=lambda item: item[1]["team"]))


def fetch_team_stats(
    team_ids: Iterable[str],
    cache_dir: Path = DEFAULT_STATS_CACHE,
    *,
    workers: int = 10,
    force: bool = False,
) -> dict[tuple[str, str], dict[str, Any]]:
    requests_to_make = [(team_id, group) for team_id in sorted(set(team_ids)) for group in ("hitting", "pitching")]
    results: dict[tuple[str, str], dict[str, Any]] = {}

    def fetch_one(team_id: str, group: str) -> tuple[tuple[str, str], dict[str, Any]]:
        url = TEAM_STATS_URL.format(team_id=team_id, group=group)
        return (team_id, group), fetch_json(url, cache_dir / f"{team_id}_{group}.json", force=force)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_one, team_id, group) for team_id, group in requests_to_make]
        for index, future in enumerate(as_completed(futures), start=1):
            key, value = future.result()
            results[key] = value
            if index % 10 == 0 or index == len(requests_to_make):
                print(f"  fetched {index:,}/{len(requests_to_make):,} MLB team stat groups", flush=True)
    return results


def profile_summary(player: dict[str, Any]) -> dict[str, Any]:
    position = player.get("primaryPosition") or {}
    return {
        "name": str(player.get("fullName") or "") or None,
        "birth_city": str(player.get("birthCity") or "") or None,
        "birth_state": str(player.get("birthStateProvince") or "") or None,
        "birth_country": str(player.get("birthCountry") or "") or None,
        "dob": str(player.get("birthDate") or "")[:10] or None,
        "position": str(position.get("abbreviation") or position.get("name") or "") or None,
        "bats": str((player.get("batSide") or {}).get("code") or "") or None,
        "throws": str((player.get("pitchHand") or {}).get("code") or "") or None,
    }


def _splits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    stats = payload.get("stats") or []
    return list((stats[0] if stats else {}).get("splits") or [])


def aggregate_team_stats(
    team_stats: dict[tuple[str, str], dict[str, Any]],
    team_meta: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    players: dict[str, dict[str, Any]] = defaultdict(lambda: {"team_buckets": {}})
    for (team_id, group), payload in sorted(team_stats.items()):
        if team_id not in team_meta:
            raise ValueError(f"Unknown MLB team ID: {team_id}")
        meta = team_meta[team_id]
        for row in _splits(payload):
            stat = row.get("stat") or {}
            games = int(stat.get("gamesPlayed") or 0)
            player = row.get("player") or {}
            player_id = str(player.get("id") or "")
            if not player_id or games <= 0:
                continue
            aggregate = players[player_id]
            aggregate["player_id"] = player_id
            aggregate["profile"] = profile_summary(player)
            bucket = aggregate["team_buckets"].setdefault(team_id, {
                "team_id": team_id,
                "team_code": meta["code"],
                "team": meta["team"],
                "conference": meta["conference"],
                "division": meta["division"],
                "hitting_games": 0,
                "pitching_games": 0,
                "plate_appearances": 0,
                "batters_faced": 0,
                "hits": 0,
                "home_runs": 0,
                "rbi": 0,
                "pitching_strikeouts": 0,
            })
            if group == "hitting":
                bucket["hitting_games"] = max(bucket["hitting_games"], games)
                bucket["plate_appearances"] = int(stat.get("plateAppearances") or 0)
                bucket["hits"] = int(stat.get("hits") or 0)
                bucket["home_runs"] = int(stat.get("homeRuns") or 0)
                bucket["rbi"] = int(stat.get("rbi") or 0)
            else:
                bucket["pitching_games"] = max(bucket["pitching_games"], games)
                bucket["batters_faced"] = int(stat.get("battersFaced") or 0)
                bucket["pitching_strikeouts"] = int(stat.get("strikeOuts") or 0)

    cohort = []
    for player in players.values():
        splits = []
        for bucket in player["team_buckets"].values():
            games = max(bucket["hitting_games"], bucket["pitching_games"])
            workload = bucket["plate_appearances"] + bucket["batters_faced"]
            splits.append({
                **{key: value for key, value in bucket.items() if key not in {"hitting_games", "pitching_games"}},
                "games": games,
                "minutes": workload,
            })
        splits.sort(key=lambda row: (-row["minutes"], -row["games"], row["team"]))
        primary = splits[0]
        total = lambda key: sum(split[key] for split in splits)
        cohort.append({
            "player_id": player["player_id"],
            "profile": player["profile"],
            "team_id": primary["team_id"],
            "team_ids": [split["team_id"] for split in splits],
            "team_splits": splits,
            "games": total("games"),
            "minutes": total("minutes"),
            "plate_appearances": total("plate_appearances"),
            "batters_faced": total("batters_faced"),
            "hits": total("hits"),
            "home_runs": total("home_runs"),
            "rbi": total("rbi"),
            "pitching_strikeouts": total("pitching_strikeouts"),
        })
    return sorted(cohort, key=lambda row: (team_meta[row["team_id"]]["team"], row["profile"].get("name") or ""))


def age_on(dob: str | None, on_date: date = SEASON_END) -> int | None:
    return _age_on(dob, on_date)


def build_payload(
    cohort: list[dict[str, Any]],
    city_index: dict[str, list[dict[str, Any]]],
    country_aliases: dict[str, str],
    country_names: dict[str, str],
    admin1_aliases: dict[tuple[str, str], str],
    team_meta: dict[str, dict[str, str]],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    records = []
    unresolved = []
    for player in cohort:
        profile = player["profile"]
        birthplace = resolve_birthplace(profile, city_index, country_aliases, country_names, admin1_aliases)
        mapped = birthplace is not None
        status = "resolved" if mapped else (
            "birth city unavailable" if not profile.get("birth_city")
            else "birth country unavailable" if not profile.get("birth_country")
            else "birth country unrecognized" if normalize(profile.get("birth_country")) not in country_aliases
            else "birth city coordinates unavailable"
        )
        primary = team_meta[player["team_id"]]
        birth_country_code = country_aliases.get(normalize(profile.get("birth_country")))
        birth_country = (
            country_names.get(birth_country_code, profile.get("birth_country"))
            if birth_country_code else profile.get("birth_country")
        )
        record = {
            "id": f"mlb:{player['player_id']}",
            "mlbId": player["player_id"],
            "name": profile.get("name") or player["player_id"],
            "team": primary["team"],
            "teamCode": primary["code"],
            "teams": [team_meta[team_id]["team"] for team_id in player["team_ids"]],
            "teamSplits": [{
                "team": split["team"],
                "teamCode": split["team_code"],
                "conference": split["conference"],
                "division": split["division"],
                "games": split["games"],
                "minutes": split["minutes"],
                "plateAppearances": split["plate_appearances"],
                "battersFaced": split["batters_faced"],
                "hits": split["hits"],
                "homeRuns": split["home_runs"],
                "rbi": split["rbi"],
                "pitchingStrikeouts": split["pitching_strikeouts"],
            } for split in player["team_splits"]],
            "conference": primary["conference"],
            "division": primary["division"],
            "year": SEASON,
            "games": player["games"],
            "minutes": player["minutes"],
            "plateAppearances": player["plate_appearances"],
            "battersFaced": player["batters_faced"],
            "hits": player["hits"],
            "homeRuns": player["home_runs"],
            "rbi": player["rbi"],
            "pitchingStrikeouts": player["pitching_strikeouts"],
            "position": profile.get("position"),
            "birthCity": profile.get("birth_city"),
            "birthStateProvince": profile.get("birth_state"),
            "birthCountry": birth_country,
            "bats": profile.get("bats"),
            "throws": profile.get("throws"),
            "age": age_on(profile.get("dob")),
            "dob": profile.get("dob"),
            "place": birthplace["place"] if mapped else None,
            "country": birthplace["country"] if mapped else None,
            "lat": birthplace["lat"] if mapped else None,
            "lon": birthplace["lon"] if mapped else None,
            "mapped": mapped,
            "status": status,
            "geonamesId": birthplace["geonames_id"] if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({
                "mlbId": player["player_id"],
                "name": record["name"],
                "birthCity": profile.get("birth_city"),
                "birthStateProvince": profile.get("birth_state"),
                "birthCountry": profile.get("birth_country"),
                "status": status,
            })

    records.sort(key=lambda record: (record["team"], record["name"]))
    unresolved.sort(key=lambda record: record["name"])
    mapped_records = [record for record in records if record["mapped"]]
    total_workload = sum(record["minutes"] for record in records)
    mapped_workload = sum(record["minutes"] for record in mapped_records)
    generated_at = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "meta": {
            "title": "MLB Talent Geography",
            "sport": "mlb",
            "scope": "2025 MLB regular season",
            "season": SEASON_LABEL,
            "year": SEASON,
            "teams": sorted(meta["team"] for meta in team_meta.values()),
            "conferences": ["American League", "National League"],
            "divisions": sorted({meta["division"] for meta in team_meta.values()}),
            "generated_at": generated_at,
            "workload_definition": "Plate appearances plus batters faced",
            "stats_source_name": "MLB Stats API",
            "stats_source_url": TEAMS_URL,
            "birthplace_source_name": "MLB player records",
            "coordinate_source_name": "GeoNames",
        },
        "summary": {
            "teams": len(team_meta),
            "players": len(records),
            "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "minutes": total_workload,
            "mapped_minutes": mapped_workload,
            "minute_coverage_pct": round(mapped_workload / total_workload * 100, 1) if total_workload else 0,
            "birthplaces": len({(record["lat"], record["lon"], record["place"]) for record in mapped_records}),
            "birth_countries": len({record["country"] for record in mapped_records}),
            "unresolved_players": len(unresolved),
        },
        "records": records,
        "unresolved": unresolved,
    }


def run(output_path: Path = DEFAULT_OUTPUT, *, workers: int = 10, force: bool = False) -> dict[str, Any]:
    teams_payload = fetch_json(TEAMS_URL, DEFAULT_TEAMS_CACHE, force=force)
    team_meta = parse_team_meta(teams_payload)
    team_stats = fetch_team_stats(team_meta, workers=workers, force=force)
    cohort = aggregate_team_stats(team_stats, team_meta)

    needed_names = {normalize(player["profile"].get("birth_city")) for player in cohort if player["profile"].get("birth_city")}
    cities_path = _download_binary(GEONAMES_CITIES_URL, DEFAULT_GEONAMES_CACHE, force=force)
    CachedHttpClient(delay=0.0, timeout=90).fetch_text(GEONAMES_COUNTRIES_URL, DEFAULT_COUNTRIES_CACHE, force=force)
    CachedHttpClient(delay=0.0, timeout=90).fetch_text(ADMIN1_URL, DEFAULT_ADMIN1_CACHE, force=force)
    country_aliases, country_names = load_country_codes(DEFAULT_COUNTRIES_CACHE)
    country_aliases["republicofkorea"] = "KR"
    admin1_aliases = load_admin1_aliases(DEFAULT_ADMIN1_CACHE)
    city_index = build_city_index(cities_path, needed_names)
    payload = build_payload(cohort, city_index, country_aliases, country_names, admin1_aliases, team_meta)
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']:,} MLB players with "
        f"{payload['summary']['player_coverage_pct']:.1f}% birthplace coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static MLB talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(args.output, workers=args.workers, force=args.force)


if __name__ == "__main__":
    main()
