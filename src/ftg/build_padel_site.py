from __future__ import annotations

import argparse
import html
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.ftg.geonames import (
    DEFAULT_COUNTRIES_CACHE,
    DEFAULT_GEONAMES_CACHE,
    GEONAMES_CITIES_URL,
    GEONAMES_COUNTRIES_URL,
    build_city_index,
    load_country_codes,
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
SEASON_END = date(2025, 12, 22)
RANKING_DATE = "2025-12-22"
RANKING_API = "https://www.padelfip.com/wp-json/fip/v1/ranking/load-more"
RANKING_SPECS = {
    "Men": {"gender": "male", "year": 2025, "week": 51},
    # The rebuilt FIP endpoint no longer returns the archived 2025 women's rows.
    # Week 3 of 2026 is the unchanged opening list carried forward from year-end.
    "Women": {"gender": "female", "year": 2026, "week": 3},
}
DEFAULT_OUTPUT = ROOT / "docs" / "padel" / "data" / "dashboard.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "padel_2025"

# Conservative spelling/region expansions and country selections for FIP labels
# that are not globally unique. These describe the named birthplace; a player's
# represented country is deliberately never used by the resolver.
PLACE_HINTS = {
    "posadasmisiones": ("Posadas", "AR"),
    "valencia": ("Valencia", "ES"),
    "sanluis": ("San Luis", "AR"),
    "granada": ("Granada", "ES"),
    "deaireaux": ("Daireaux", "AR"),
    "villamercedes": ("Villa Mercedes", "AR"),
    "stauxiaderibeira": ("Ribeira", "ES"),
    "sanfernando": ("San Fernando", "ES"),
    "concaransanluis": ("Concaran", "AR"),
    "malabrigo": ("Malabrigo", "AR"),
    "mahon": ("Mao", "ES"),
    "siracusa": ("Siracusa", "IT"),
    "barcelona": ("Barcelona", "ES"),
    "capitalfederal": ("Buenos Aires", "AR"),
    "toledo": ("Toledo", "ES"),
    "salamanca": ("Salamanca", "ES"),
    "caceres": ("Caceres", "ES"),
    "cadiz": ("Cadiz", "ES"),
    "segovia": ("Segovia", "ES"),
    "jesusmariacba": ("Jesus Maria", "AR"),
    "santander": ("Santander", "ES"),
    "rotacadiz": ("Rota", "ES"),
    "zaragoza": ("Zaragoza", "ES"),
    "pueblodelrio": ("La Puebla del Rio", "ES"),
    "porto": ("Porto", "PT"),
}
PLAYER_PLACE_HINTS = {
    "P000016": ("Cordoba", "ES"),  # Javier Garrido
    "P000023": ("Cordoba", "ES"),  # Francisco Manuel Gil
    "P000099": ("Merida", "ES"),  # Pablo Cardona
    "P000054": ("Merida", "ES"),  # Teodoro Zapata
    "P000035": ("Cartagena", "ES"),  # Victor Ruiz
    "P200008": ("Cartagena", "ES"),  # Patricia Llaguno
    "P101734": ("Cuenca", "ES"),  # Luis Hernandez Quesada
}
NON_CITY_BIRTHPLACE_KEYS = {"chaco", "sakhalin"}
PLACE_OVERRIDES: dict[str, dict[str, Any]] = {
    "leidschendam": {
        "place": "Leidschendam", "country": "The Netherlands", "lat": 52.08167, "lon": 4.39281,
        "geonames_id": "2751769", "resolution_source": "Official FIP birthplace; GeoNames coordinates",
    },
}


def ranking_url(division: str) -> str:
    spec = RANKING_SPECS[division]
    return (
        f"{RANKING_API}?limit=100&offset=0&gender={spec['gender']}"
        f"&category=master&circuit=premierpadel&year={spec['year']}"
        f"&week={spec['week']}&lang=en"
    )


def parse_ranking(payload: list[dict[str, Any]], division: str) -> list[dict[str, Any]]:
    if division not in RANKING_SPECS:
        raise ValueError(f"Unsupported division: {division}")
    if len(payload) != 100:
        raise ValueError(f"Expected 100 {division.lower()} in the FIP cohort, found {len(payload)}")
    output = []
    seen_ids: set[str] = set()
    for row in payload:
        player_id = str(row.get("player_id") or "").strip()
        name = " ".join(str(row.get(field) or "").strip() for field in ("name", "surname")).strip()
        rank = int(row.get("rank") or 0)
        points = int(row.get("points") or 0)
        profile_url = str(row.get("url") or "").strip()
        if not player_id or player_id in seen_ids or not name or not 1 <= rank <= 100:
            raise ValueError(f"Invalid {division} FIP ranking row: {row}")
        if points <= 0 or not profile_url.startswith("https://www.padelfip.com/player/"):
            raise ValueError(f"Incomplete {division} FIP ranking row at rank {rank}")
        seen_ids.add(player_id)
        output.append({
            "division": division,
            "gender": division,
            "ranking_date": RANKING_DATE,
            "rank": rank,
            "points": points,
            "player_id": player_id,
            "name": name,
            "represented_country": str(row.get("country_name") or "").strip() or None,
            "profile_url": profile_url,
        })
    if max(row["rank"] for row in output) != 100:
        raise ValueError(f"Expected {division} cohort to finish at rank 100")
    return sorted(output, key=lambda row: (row["rank"], row["name"]))


def parse_profile(profile_html: str, expected_name: str, expected_id: str) -> dict[str, Any]:
    id_match = re.search(r"summary__player\s+playerID-([A-Za-z0-9]+)", profile_html)
    if id_match and id_match.group(1) != expected_id:
        raise ValueError(f"FIP profile ID mismatch for {expected_name}")
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        profile_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    person: dict[str, Any] | None = None

    def people(value: Any):
        if isinstance(value, dict):
            entity_type = value.get("@type")
            if entity_type == "Person" or isinstance(entity_type, list) and "Person" in entity_type:
                yield value
            for child in value.values():
                yield from people(child)
        elif isinstance(value, list):
            for child in value:
                yield from people(child)

    for raw in scripts:
        try:
            value = json.loads(html.unescape(raw.strip()))
        except json.JSONDecodeError:
            continue
        person = next(people(value), None)
        if person:
            break
    if not person or normalize(person.get("name")) != normalize(expected_name):
        raise ValueError(f"FIP profile identity mismatch for {expected_name}")
    birthplace = person.get("birthPlace") or {}
    nationality = person.get("nationality") or {}
    description = str(person.get("description") or "")
    position_match = re.search(r"Playing Position:\s*([^;]+)", description, flags=re.IGNORECASE)
    height_raw = str(person.get("height") or "").strip()
    try:
        height_cm = round(float(height_raw.replace(",", ".")) * 100) if height_raw else None
    except ValueError:
        height_cm = None
    return {
        "name": str(person["name"]),
        "dob": str(person.get("birthDate") or "").strip() or None,
        "birth_place": str(birthplace.get("name") or "").strip() or None,
        "nationality": str(nationality.get("name") or "").strip() or None,
        "height_cm": height_cm,
        "playing_position": position_match.group(1).strip() if position_match else None,
    }


def fetch_rankings(cache_dir: Path = DEFAULT_CACHE, *, force: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0, retries=3, timeout=120)
    cohort: list[dict[str, Any]] = []
    retrieval: dict[str, str] = {}
    for division in RANKING_SPECS:
        result = client.fetch_text(
            ranking_url(division), cache_dir / f"ranking_{division.lower()}.json", force=force
        )
        cohort.extend(parse_ranking(json.loads(result.text), division))
        retrieval[f"{division.lower()}_ranking_retrieved_at"] = result.retrieved_at
    return cohort, retrieval


def fetch_profiles(
    cohort: list[dict[str, Any]], cache_dir: Path = DEFAULT_CACHE, *, workers: int = 8, force: bool = False,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    def fetch_one(player: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str | None, str | None]:
        session = requests.Session()
        session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
        client = CachedHttpClient(session, delay=0, retries=3, timeout=120)
        try:
            result = client.fetch_text(
                player["profile_url"], cache_dir / "profiles" / f"{player['player_id']}.html", force=force
            )
            return (
                player["player_id"],
                parse_profile(result.text, player["name"], player["player_id"]),
                result.retrieved_at,
                None,
            )
        except (requests.RequestException, ValueError, json.JSONDecodeError) as error:
            return player["player_id"], None, None, str(error)

    retrieved_at: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(fetch_one, player) for player in cohort]
        for index, future in enumerate(as_completed(futures), start=1):
            player_id, profile, retrieved, error = future.result()
            if profile:
                profiles[player_id] = profile
            if retrieved:
                retrieved_at.append(retrieved)
            if error:
                errors[player_id] = error
            if index % 25 == 0 or index == len(futures):
                print(f"  fetched {index}/{len(futures)} FIP profiles", flush=True)
    return profiles, {
        "profile_pages_retrieved_at": max(retrieved_at) if retrieved_at else None,
        "profile_fetch_errors": errors,
    }


def _candidate_countries(candidates: list[dict[str, Any]]) -> set[str]:
    return {str(candidate["country_code"]) for candidate in candidates}


def resolve_place(
    player_id: str,
    place_name: str | None,
    city_index: dict[str, list[dict[str, Any]]],
    country_names: dict[str, str],
) -> dict[str, Any] | None:
    if not place_name:
        return None
    place_key = normalize(place_name)
    if place_key in NON_CITY_BIRTHPLACE_KEYS:
        return None
    if place_key in PLACE_OVERRIDES:
        return PLACE_OVERRIDES[place_key]
    search_name, country_hint = PLAYER_PLACE_HINTS.get(
        player_id, PLACE_HINTS.get(place_key, (place_name, None))
    )
    candidates = sorted(
        city_index.get(normalize(search_name), []), key=lambda candidate: candidate["population"], reverse=True
    )
    if country_hint:
        candidates = [candidate for candidate in candidates if candidate["country_code"] == country_hint]
    if not candidates:
        return None
    top = candidates[0]
    second_population = candidates[1]["population"] if len(candidates) > 1 else 0
    countries = _candidate_countries(candidates)
    unambiguous = len(candidates) == 1 or len(countries) == 1
    dominant = top["population"] >= 10_000 and top["population"] >= max(1, second_population) * 3
    if not (unambiguous or dominant):
        return None
    return {
        "place": place_name,
        "country": country_names.get(top["country_code"], top["country_code"]),
        "lat": round(top["lat"], 6),
        "lon": round(top["lon"], 6),
        "geonames_id": str(top["geonames_id"]),
        "resolution_source": "Official FIP birthplace; GeoNames exact-name coordinates",
    }


def age_on(dob: str | None) -> int | None:
    return _age_on(dob, SEASON_END)


def build_payload(
    cohort: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    city_index: dict[str, list[dict[str, Any]]],
    country_names: dict[str, str],
    source_meta: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    records, unresolved = [], []
    for player in cohort:
        profile = profiles.get(player["player_id"], {})
        place = resolve_place(player["player_id"], profile.get("birth_place"), city_index, country_names)
        mapped = place is not None
        status = (
            "verified birthplace" if mapped
            else "official FIP profile unavailable" if not profile
            else "birthplace unavailable in official FIP profile" if not profile.get("birth_place")
            else "birthplace coordinates ambiguous or unavailable"
        )
        record = {
            "id": f"padel:{player['division'].lower()}:{player['player_id'].lower()}",
            "sourcePlayerId": player["player_id"],
            "profileUrl": player["profile_url"],
            "name": player["name"],
            "team": player["division"],
            "teamCode": player["division"],
            "teams": [player["division"]],
            "conference": player["division"],
            "division": player["division"],
            "gender": player["gender"],
            "year": SEASON,
            "rankingDate": player["ranking_date"],
            "rank": player["rank"],
            "points": player["points"],
            "games": 1,
            "position": f"{player['division']} · {profile.get('playing_position') or 'side unavailable'}",
            "playingPosition": profile.get("playing_position"),
            "heightCm": profile.get("height_cm"),
            "dob": profile.get("dob"),
            "age": age_on(profile.get("dob")),
            "nationality": player.get("represented_country"),
            "representedCountry": player.get("represented_country"),
            "officialBirthplace": profile.get("birth_place"),
            "place": place.get("place") if mapped else None,
            "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None,
            "lon": place.get("lon") if mapped else None,
            "mapped": mapped,
            "status": status,
            "locationType": "birthplace" if mapped else None,
            "geonamesId": place.get("geonames_id") if mapped else None,
            "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({
                "name": record["name"], "division": record["division"],
                "officialBirthplace": record["officialBirthplace"], "status": status,
            })
    records.sort(key=lambda row: (row["division"], row["rank"], row["name"]))
    mapped_records = [row for row in records if row["mapped"]]
    points = sum(row["points"] for row in records)
    mapped_points = sum(row["points"] for row in mapped_records)
    return {
        "meta": {
            "title": "Padel Talent Geography",
            "sport": "padel",
            "scope": "2025 year-end FIP men's and women's top 100",
            "season": "2025 year-end",
            "year": SEASON,
            "teams": ["Men", "Women"],
            "conferences": ["Men", "Women"],
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "ranking_date": RANKING_DATE,
            "ranking_source_name": "International Padel Federation ranking",
            "ranking_source_url": "https://www.padelfip.com/fip-rankings/",
            "ranking_snapshot_note": (
                "Men use the archived 2025 week-51 feed; women use the unchanged 2026 week-3 "
                "opening ranking carried forward from the 2025 year-end list."
            ),
            "birthplace_source_name": "Official FIP player profiles",
            "birthplace_source_url": "https://www.padelfip.com/fip-rankings/",
            "coordinate_source_name": "GeoNames",
            "coordinate_source_url": "https://www.geonames.org/",
            **source_meta,
        },
        "summary": {
            "teams": 2,
            "players": len(records),
            "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "points": points,
            "mapped_points": mapped_points,
            "point_coverage_pct": round(mapped_points / points * 100, 1) if points else 0,
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped_records}),
            "birth_countries": len({row["country"] for row in mapped_records}),
            "unresolved_players": len(unresolved),
        },
        "records": records,
        "unresolved": unresolved,
    }


def run(
    output_path: Path = DEFAULT_OUTPUT,
    *,
    cache_dir: Path = DEFAULT_CACHE,
    geonames_input: Path | None = None,
    countries_input: Path | None = None,
    workers: int = 8,
    force: bool = False,
) -> dict[str, Any]:
    cohort, source_meta = fetch_rankings(cache_dir, force=force)
    profiles, profile_meta = fetch_profiles(cohort, cache_dir, workers=workers, force=force)
    source_meta.update(profile_meta)
    cities_path = geonames_input or _download_binary(GEONAMES_CITIES_URL, DEFAULT_GEONAMES_CACHE, force=force)
    countries_path = countries_input or _download_binary(
        GEONAMES_COUNTRIES_URL, DEFAULT_COUNTRIES_CACHE, force=force
    )
    _, country_names = load_country_codes(countries_path)
    needed_names = set()
    for profile in profiles.values():
        place_name = profile.get("birth_place")
        if not place_name:
            continue
        search_name, _ = PLACE_HINTS.get(normalize(place_name), (place_name, None))
        needed_names.add(normalize(search_name))
    needed_names.update(normalize(name) for name, _ in PLAYER_PLACE_HINTS.values())
    city_index = build_city_index(cities_path, needed_names)
    payload = build_payload(cohort, profiles, city_index, country_names, source_meta)
    if len(payload["records"]) != 200 or any(
        len([row for row in payload["records"] if row["division"] == division]) != 100
        for division in RANKING_SPECS
    ):
        raise ValueError("Padel top-100 reconciliation failed")
    _write_json(output_path, payload)
    print(
        f"Wrote 100 men and 100 women with {payload['summary']['player_coverage_pct']}% "
        f"birthplace coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the 2025 year-end FIP padel talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--geonames-input", type=Path)
    parser.add_argument("--countries-input", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(
        args.output,
        cache_dir=args.cache_dir,
        geonames_input=args.geonames_input,
        countries_input=args.countries_input,
        workers=args.workers,
        force=args.force,
    )


if __name__ == "__main__":
    main()
