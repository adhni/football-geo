from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

from src.ftg.build_nfl_site import (
    DEFAULT_COUNTRIES_CACHE,
    DEFAULT_GEONAMES_CACHE,
    GEONAMES_CITIES_URL,
    GEONAMES_COUNTRIES_URL,
    _download_binary,
    build_city_index,
    load_country_codes,
    normalize,
)
from src.ftg.http_cache import CachedHttpClient

ROOT = Path(__file__).resolve().parents[2]
SEASON_ID = 20252026
SEASON_LABEL = "2025–26"
SEASON_END = date(2026, 4, 16)
STANDINGS_URL = "https://api-web.nhle.com/v1/standings/2026-04-16"
CLUB_STATS_URL = "https://api-web.nhle.com/v1/club-stats/{team}/20252026/2"
PLAYER_PROFILE_URL = "https://api-web.nhle.com/v1/player/{player_id}/landing"
ADMIN1_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"

DEFAULT_OUTPUT = ROOT / "docs" / "nhl" / "data" / "dashboard.json"
DEFAULT_STANDINGS_CACHE = ROOT / "data" / "cache" / "nhl_standings_2025_26.json"
DEFAULT_CLUB_CACHE = ROOT / "data" / "cache" / "nhl_club_stats_2025_26"
DEFAULT_PROFILE_CACHE = ROOT / "data" / "cache" / "nhl_player_profiles_2025_26.json"
DEFAULT_ADMIN1_CACHE = ROOT / "data" / "cache" / "geonames_admin1_codes.txt"


def _write_json(path: Path, value: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    options = {"ensure_ascii": False, "sort_keys": pretty}
    if pretty:
        options["indent"] = 2
    else:
        options["separators"] = (",", ":")
    temporary.write_text(json.dumps(value, **options), encoding="utf-8")
    temporary.replace(path)


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


def parse_team_meta(standings: dict[str, Any]) -> dict[str, dict[str, str]]:
    teams: dict[str, dict[str, str]] = {}
    for row in standings.get("standings", []):
        code = str((row.get("teamAbbrev") or {}).get("default") or "")
        name = str((row.get("teamName") or {}).get("default") or "")
        conference = str(row.get("conferenceName") or "")
        division = str(row.get("divisionName") or "")
        if code and name and conference and division:
            teams[code] = {
                "team": name,
                "conference": f"{conference} Conference",
                "division": f"{division} Division",
            }
    if len(teams) != 32:
        raise ValueError(f"Expected 32 NHL teams in standings, found {len(teams)}")
    return dict(sorted(teams.items()))


def fetch_club_stats(
    team_codes: Iterable[str],
    cache_dir: Path = DEFAULT_CLUB_CACHE,
    *,
    workers: int = 8,
    force: bool = False,
) -> dict[str, dict[str, Any]]:
    codes = sorted(set(team_codes))
    results: dict[str, dict[str, Any]] = {}

    def fetch_one(code: str) -> tuple[str, dict[str, Any]]:
        return code, fetch_json(CLUB_STATS_URL.format(team=code), cache_dir / f"{code}.json", force=force)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_one, code) for code in codes]
        for index, future in enumerate(as_completed(futures), start=1):
            code, payload = future.result()
            results[code] = payload
            if index % 8 == 0 or index == len(codes):
                print(f"  fetched {index:,}/{len(codes):,} NHL club summaries", flush=True)
    return results


def _localized(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("default")
    return str(value) if value not in (None, "") else None


def aggregate_club_stats(
    club_stats: dict[str, dict[str, Any]],
    team_meta: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    players: dict[str, dict[str, Any]] = defaultdict(lambda: {"team_splits": []})
    for team_code, payload in sorted(club_stats.items()):
        if team_code not in team_meta:
            raise ValueError(f"Unknown NHL team code: {team_code}")
        for kind, position in (("skaters", None), ("goalies", "G")):
            for row in payload.get(kind, []):
                games = int(row.get("gamesPlayed") or 0)
                if games <= 0:
                    continue
                player_id = str(row["playerId"])
                minutes = round(
                    float(row.get("timeOnIce") or 0) / 60
                    if kind == "goalies"
                    else float(row.get("avgTimeOnIcePerGame") or 0) * games / 60
                )
                split = {
                    "team_code": team_code,
                    "team": team_meta[team_code]["team"],
                    "conference": team_meta[team_code]["conference"],
                    "division": team_meta[team_code]["division"],
                    "games": games,
                    "minutes": int(minutes),
                    "goals": int(row.get("goals") or 0),
                    "assists": int(row.get("assists") or 0),
                    "points": int(row.get("points") or 0),
                }
                player = players[player_id]
                player["player_id"] = player_id
                player["name"] = " ".join(
                    value for value in (_localized(row.get("firstName")), _localized(row.get("lastName"))) if value
                ) or player_id
                player["position"] = position or str(row.get("positionCode") or "") or None
                player["team_splits"].append(split)

    cohort = []
    for player in players.values():
        splits = sorted(player["team_splits"], key=lambda row: (-row["minutes"], row["team"]))
        primary = splits[0]
        cohort.append(
            {
                **{key: value for key, value in player.items() if key != "team_splits"},
                "team_code": primary["team_code"],
                "team_codes": [split["team_code"] for split in splits],
                "team_splits": splits,
                "games": sum(split["games"] for split in splits),
                "minutes": sum(split["minutes"] for split in splits),
                "goals": sum(split["goals"] for split in splits),
                "assists": sum(split["assists"] for split in splits),
                "points": sum(split["points"] for split in splits),
            }
        )
    return sorted(cohort, key=lambda row: (row["team_code"], row["name"]))


def profile_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": " ".join(
            value for value in (_localized(payload.get("firstName")), _localized(payload.get("lastName"))) if value
        ) or None,
        "birth_city": _localized(payload.get("birthCity")),
        "birth_state": _localized(payload.get("birthStateProvince")),
        "birth_country": str(payload.get("birthCountry") or "") or None,
        "dob": str(payload.get("birthDate") or "")[:10] or None,
        "shoots_catches": str(payload.get("shootsCatches") or "") or None,
    }


def fetch_profiles(
    player_ids: Iterable[str],
    cache_path: Path = DEFAULT_PROFILE_CACHE,
    *,
    workers: int = 12,
    force: bool = False,
) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    if cache_path.exists() and not force:
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}
    ids = sorted(set(str(player_id) for player_id in player_ids))
    missing = ids if force else [player_id for player_id in ids if player_id not in cache]

    def fetch_one(player_id: str) -> tuple[str, dict[str, Any] | None]:
        for attempt in range(3):
            try:
                response = requests.get(
                    PLAYER_PROFILE_URL.format(player_id=player_id),
                    timeout=40,
                    headers={"User-Agent": "TalentGeography/1.0"},
                )
                response.raise_for_status()
                return player_id, profile_summary(response.json())
            except (requests.RequestException, ValueError):
                time.sleep(0.35 * (attempt + 1))
        return player_id, None

    if missing:
        print(f"Fetching {len(missing):,} official NHL player profiles...", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(fetch_one, player_id) for player_id in missing]
            for index, future in enumerate(as_completed(futures), start=1):
                player_id, result = future.result()
                if result is not None:
                    cache[player_id] = result
                if index % 100 == 0 or index == len(missing):
                    _write_json(cache_path, cache, pretty=True)
                    print(f"  fetched {index:,}/{len(missing):,} player profiles", flush=True)
    return cache


def load_admin1_aliases(path: Path) -> dict[tuple[str, str], str]:
    aliases: dict[tuple[str, str], str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) < 3 or "." not in fields[0]:
            continue
        country_code, admin_code = fields[0].split(".", 1)
        for value in (admin_code, fields[1], fields[2]):
            if value:
                aliases[(country_code, normalize(value))] = admin_code
    return aliases


def resolve_birthplace(
    profile: dict[str, Any],
    city_index: dict[str, list[dict[str, Any]]],
    country_aliases: dict[str, str],
    country_names: dict[str, str],
    admin1_aliases: dict[tuple[str, str], str],
) -> dict[str, Any] | None:
    city = profile.get("birth_city")
    country_code = country_aliases.get(normalize(profile.get("birth_country")))
    if not city or not country_code:
        return None
    candidates = [
        candidate for candidate in city_index.get(normalize(city), [])
        if candidate["country_code"] == country_code
    ]
    state = normalize(profile.get("birth_state"))
    admin_code = admin1_aliases.get((country_code, state)) if state else None
    if admin_code:
        candidates = [candidate for candidate in candidates if candidate["admin1"] == admin_code]
    if not candidates:
        return None
    match = max(candidates, key=lambda candidate: candidate["population"])
    return {
        "place": str(city),
        "country": country_names.get(country_code, str(profile.get("birth_country") or country_code)),
        "lat": round(float(match["lat"]), 6),
        "lon": round(float(match["lon"]), 6),
        "geonames_id": str(match["geonames_id"]),
    }


def age_on(dob: str | None, on_date: date = SEASON_END) -> int | None:
    if not dob:
        return None
    try:
        born = date.fromisoformat(dob[:10])
    except ValueError:
        return None
    return on_date.year - born.year - ((on_date.month, on_date.day) < (born.month, born.day))


def build_payload(
    cohort: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
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
        profile = profiles.get(player["player_id"], {})
        birthplace = resolve_birthplace(profile, city_index, country_aliases, country_names, admin1_aliases)
        mapped = birthplace is not None
        status = "resolved" if mapped else (
            "player profile unavailable" if not profile
            else "birth city unavailable" if not profile.get("birth_city")
            else "birth country unavailable" if not profile.get("birth_country")
            else "birth country unrecognized" if normalize(profile.get("birth_country")) not in country_aliases
            else "birth city coordinates unavailable"
        )
        primary = team_meta[player["team_code"]]
        name = profile.get("name") or player["name"]
        birth_country_code = country_aliases.get(normalize(profile.get("birth_country")))
        record = {
            "id": f"nhl:{player['player_id']}",
            "nhlId": player["player_id"],
            "name": name,
            "team": primary["team"],
            "teamCode": player["team_code"],
            "teams": [team_meta[code]["team"] for code in player["team_codes"]],
            "teamSplits": [
                {
                    "team": split["team"],
                    "teamCode": split["team_code"],
                    "conference": split["conference"],
                    "division": split["division"],
                    "games": split["games"],
                    "minutes": split["minutes"],
                    "goals": split["goals"],
                    "assists": split["assists"],
                    "points": split["points"],
                }
                for split in player["team_splits"]
            ],
            "conference": primary["conference"],
            "division": primary["division"],
            "year": 2026,
            "games": player["games"],
            "minutes": player["minutes"],
            "goals": player["goals"],
            "assists": player["assists"],
            "points": player["points"],
            "rebounds": player["goals"],
            "position": player["position"],
            "nationality": country_names.get(birth_country_code, profile.get("birth_country")) if birth_country_code else None,
            "shootsCatches": profile.get("shoots_catches"),
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
            unresolved.append({"name": name, "status": status})

    records.sort(key=lambda record: (record["team"], record["name"]))
    mapped_records = [record for record in records if record["mapped"]]
    total_minutes = sum(record["minutes"] for record in records)
    mapped_minutes = sum(record["minutes"] for record in mapped_records)
    generated_at = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "meta": {
            "title": "NHL Talent Geography",
            "sport": "nhl",
            "scope": f"{SEASON_LABEL} NHL regular season",
            "season": SEASON_LABEL,
            "year": 2026,
            "teams": sorted((meta["team"] for meta in team_meta.values())),
            "conferences": ["Eastern Conference", "Western Conference"],
            "divisions": sorted({meta["division"] for meta in team_meta.values()}),
            "generated_at": generated_at,
            "stats_source_name": "NHL public API",
            "stats_source_url": STANDINGS_URL,
            "birthplace_source_name": "NHL player profiles",
            "coordinate_source_name": "GeoNames",
        },
        "summary": {
            "teams": len(team_meta),
            "players": len(records),
            "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "minutes": total_minutes,
            "mapped_minutes": mapped_minutes,
            "minute_coverage_pct": round(mapped_minutes / total_minutes * 100, 1) if total_minutes else 0,
            "birthplaces": len({(record["lat"], record["lon"], record["place"]) for record in mapped_records}),
            "birth_countries": len({record["country"] for record in mapped_records}),
            "unresolved_players": len(unresolved),
        },
        "records": records,
        "unresolved": unresolved,
    }


def run(
    output_path: Path = DEFAULT_OUTPUT,
    *,
    workers: int = 12,
    force: bool = False,
) -> dict[str, Any]:
    standings = fetch_json(STANDINGS_URL, DEFAULT_STANDINGS_CACHE, force=force)
    team_meta = parse_team_meta(standings)
    club_stats = fetch_club_stats(team_meta, workers=min(workers, 12), force=force)
    cohort = aggregate_club_stats(club_stats, team_meta)
    profiles = fetch_profiles((player["player_id"] for player in cohort), workers=workers, force=force)

    needed_names = {normalize(profile.get("birth_city")) for profile in profiles.values() if profile.get("birth_city")}
    cities_path = _download_binary(GEONAMES_CITIES_URL, DEFAULT_GEONAMES_CACHE, force=force)
    CachedHttpClient(delay=0.0, timeout=90).fetch_text(
        GEONAMES_COUNTRIES_URL, DEFAULT_COUNTRIES_CACHE, force=force
    )
    CachedHttpClient(delay=0.0, timeout=90).fetch_text(
        ADMIN1_URL, DEFAULT_ADMIN1_CACHE, force=force
    )
    country_aliases, country_names = load_country_codes(DEFAULT_COUNTRIES_CACHE)
    admin1_aliases = load_admin1_aliases(DEFAULT_ADMIN1_CACHE)
    city_index = build_city_index(cities_path, needed_names)
    payload = build_payload(
        cohort,
        profiles,
        city_index,
        country_aliases,
        country_names,
        admin1_aliases,
        team_meta,
    )
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']:,} NHL players with "
        f"{payload['summary']['player_coverage_pct']:.1f}% birthplace coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static NHL talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(args.output, workers=args.workers, force=args.force)


if __name__ == "__main__":
    main()
