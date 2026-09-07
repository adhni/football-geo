from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

from src.ftg.enrich_wikidata import (
    _fetch_entities,
    claim_coordinates,
    claim_date,
    claim_entity,
    entity_label,
)
from src.ftg.http_cache import CachedHttpClient

ROOT = Path(__file__).resolve().parents[2]
SEASON = 2025
RANKING_DATE = "2025-12-30"
SEASON_END = date.fromisoformat(RANKING_DATE)
ARCHIVE_YEAR = 2026
ARCHIVE_WEEK = 1
RANKING_ROOT = "https://bwfbadminton.com/confederation-rankings/2/bwf-world-rankings"
JINA_ROOT = "https://r.jina.ai/http://bwfbadminton.com/confederation-rankings/2/bwf-world-rankings"
EVENTS = {
    "MS": {"name": "Men's Singles", "conference": "Men", "category": 6, "slug": "men-s-singles", "limit": 100},
    "WS": {"name": "Women's Singles", "conference": "Women", "category": 7, "slug": "women-s-singles", "limit": 100},
    "MD": {"name": "Men's Doubles", "conference": "Men", "category": 8, "slug": "men-s-doubles", "limit": 50},
    "WD": {"name": "Women's Doubles", "conference": "Women", "category": 9, "slug": "women-s-doubles", "limit": 50},
    "XD": {"name": "Mixed Doubles", "conference": "Mixed", "category": 10, "slug": "mixed-doubles", "limit": 50},
}
DEFAULT_OUTPUT = ROOT / "docs" / "badminton" / "data" / "dashboard.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "badminton_2025"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "badminton_wikidata_2025.json"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
COUNTRY_PLACE_TYPES = {"Q6256", "Q3624078"}  # country; sovereign state
CITY_STATE_BIRTHPLACE_EXCEPTIONS = {"Q334"}  # Singapore is both a city and country


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


def claim_entity_ids(entity: dict[str, Any], property_id: str) -> set[str]:
    values: set[str] = set()
    for claim in entity.get("claims", {}).get(property_id, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            values.add(value["id"])
    return values


def _write_json(path: Path, value: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    options = {"ensure_ascii": False, "indent": 2, "sort_keys": True} if pretty else {
        "ensure_ascii": False, "separators": (",", ":")
    }
    temporary.write_text(json.dumps(value, **options), encoding="utf-8")
    temporary.replace(path)


def ranking_url(code: str, *, proxy: bool = False) -> str:
    spec = EVENTS[code]
    root = JINA_ROOT if proxy else RANKING_ROOT
    separator = "%26" if proxy else "&"
    return (
        f"{root}/{spec['category']}/{spec['slug']}/{ARCHIVE_YEAR}/{ARCHIVE_WEEK}/"
        f"?page_no=1{separator}rows={spec['limit']}"
    )


def parse_ranking(markdown: str, code: str) -> list[dict[str, Any]]:
    if code not in EVENTS:
        raise ValueError(f"Unsupported badminton event: {code}")
    spec = EVENTS[code]
    rows: list[dict[str, Any]] = []
    for line in markdown.splitlines():
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        rank = int(cells[0])
        if rank > spec["limit"]:
            continue
        player_matches = re.findall(
            r"\[([^\]]+)\]\(https?://bwfbadminton\.com/player/(\d+)/[^\s\)]+(?:\s+\"[^\"]*\")?\)",
            cells[2],
        )
        expected_players = 1 if code.endswith("S") else 2
        if len(player_matches) != expected_players:
            raise ValueError(f"Expected {expected_players} players in {code} rank {rank}: {cells[2]}")
        countries = re.findall(r"Image\s+\d+:\s+([A-Z]{3})", cells[1])
        if len(countries) < expected_players:
            countries = re.findall(r"\b[A-Z]{3}\b", cells[1])
        points_match = re.search(r"([\d,]+)\s*/\s*(\d+)", cells[6])
        if not points_match:
            raise ValueError(f"Missing points/tournaments in {code} rank {rank}")
        players = [
            {
                "name": " ".join(name.split()),
                "player_id": player_id,
                "represented_country": countries[index] if index < len(countries) else None,
                "profile_url": f"https://bwfbadminton.com/player/{player_id}/",
            }
            for index, (name, player_id) in enumerate(player_matches)
        ]
        rows.append({
            "event": code,
            "event_name": spec["name"],
            "conference": spec["conference"],
            "ranking_date": RANKING_DATE,
            "rank": rank,
            "points": int(points_match.group(1).replace(",", "")),
            "tournaments": int(points_match.group(2)),
            "players": players,
        })
    ranks = sorted(row["rank"] for row in rows)
    if ranks != list(range(1, spec["limit"] + 1)):
        raise ValueError(f"Expected exact {code} ranks 1-{spec['limit']}; found {len(rows)} rows")
    return sorted(rows, key=lambda row: row["rank"])


def fetch_rankings(
    cache_dir: Path = DEFAULT_CACHE, *, rankings_input_dir: Path | None = None, force: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.1, retries=3, timeout=180)
    rows: list[dict[str, Any]] = []
    retrieval: dict[str, str] = {}
    for code in EVENTS:
        input_path = rankings_input_dir / f"{code.lower()}.md" if rankings_input_dir else None
        if input_path:
            text = input_path.read_text(encoding="utf-8")
            retrieved_at = datetime.fromtimestamp(input_path.stat().st_mtime, timezone.utc).isoformat()
        else:
            result = client.fetch_text(ranking_url(code, proxy=True), cache_dir / f"{code.lower()}.md", force=force)
            text, retrieved_at = result.text, result.retrieved_at
        rows.extend(parse_ranking(text, code))
        retrieval[f"{code.lower()}_ranking_retrieved_at"] = retrieved_at
    return rows, retrieval


def unique_players(rankings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    players: dict[str, dict[str, Any]] = {}
    for row in rankings:
        for player in row["players"]:
            current = players.setdefault(player["player_id"], dict(player))
            if normalize(current["name"]) != normalize(player["name"]):
                raise ValueError(f"BWF ID {player['player_id']} has inconsistent names")
    return sorted(players.values(), key=lambda row: int(row["player_id"]))


def fetch_bwf_qids(
    client: CachedHttpClient, player_ids: list[str], cache_dir: Path = DEFAULT_CACHE / "wikidata_ids",
    *, force: bool = False,
) -> dict[str, str]:
    """Resolve official BWF IDs through Wikidata property P3620."""
    output: dict[str, set[str]] = defaultdict(set)
    for offset in range(0, len(player_ids), 80):
        batch = sorted(set(player_ids[offset:offset + 80]))
        values = " ".join(f'"{value}" "P{value}"' for value in batch)
        query = (
            "SELECT ?item ?bwf WHERE { VALUES ?bwf { " + values
            + " } ?item wdt:P3620 ?bwf. }"
        )
        url = f"{WIKIDATA_SPARQL}?{urlencode({'format': 'json', 'query': query})}"
        digest = hashlib.sha1("|".join(batch).encode("utf-8")).hexdigest()[:16]
        result = client.fetch_text(url, cache_dir / f"{digest}.json", force=force)
        for binding in json.loads(result.text).get("results", {}).get("bindings", []):
            player_id = binding["bwf"]["value"].removeprefix("P")
            output[player_id].add(binding["item"]["value"].rsplit("/", 1)[-1])
    return {player_id: next(iter(qids)) for player_id, qids in output.items() if len(qids) == 1}


def fetch_birthplaces(
    players: list[dict[str, Any]], cache_path: Path = DEFAULT_WIKIDATA_CACHE, *, force: bool = False,
) -> dict[str, dict[str, Any]]:
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.1, retries=3, timeout=120)
    selected = fetch_bwf_qids(client, [row["player_id"] for row in players], force=force)
    people = _fetch_entities(
        client, list(selected.values()), "badminton_person_batches", batch_size=30, force=force,
        languages="en|zh|ko|ja|id|ms|th|fr|da",
    )

    place_by_player = {player_id: claim_entity(people.get(qid, {}), "P19") for player_id, qid in selected.items()}
    places = _fetch_entities(
        client, [qid for qid in place_by_player.values() if qid], "badminton_place_batches",
        batch_size=30, force=force, languages="en|zh|ko|ja|id|ms|th|fr|da",
    )
    country_qids = [qid for entity in places.values() if (qid := claim_entity(entity, "P17"))]
    countries = _fetch_entities(
        client, country_qids, "badminton_country_batches", batch_size=30, force=force,
        languages="en|zh|ko|ja|id|ms|th|fr|da",
    )
    output: dict[str, dict[str, Any]] = {"_meta": {"schema_version": 1, "source": "Wikidata"}}
    for player_id, person_qid in selected.items():
        place_qid = place_by_player.get(player_id)
        place = places.get(place_qid, {})
        is_country_only = bool(claim_entity_ids(place, "P31") & COUNTRY_PLACE_TYPES)
        if is_country_only and place_qid not in CITY_STATE_BIRTHPLACE_EXCEPTIONS:
            continue
        lat, lon = claim_coordinates(place)
        country_qid = claim_entity(place, "P17")
        country = entity_label(countries.get(country_qid, {}))
        if lat is None or lon is None or not country:
            continue
        output[player_id] = {
            "wikidata_qid": person_qid,
            "birth_place_qid": place_qid,
            "dob": claim_date(people.get(person_qid, {})),
            "place": entity_label(place),
            "country": country,
            "lat": lat,
            "lon": lon,
            "resolution_source": "Wikidata identity matched by official BWF player ID (P3620)",
        }
    _write_json(cache_path, output, pretty=True)
    return output


def age_on(dob: str | None) -> int | None:
    if not dob:
        return None
    try:
        born = date.fromisoformat(dob[:10])
    except ValueError:
        return None
    return SEASON_END.year - born.year - ((SEASON_END.month, SEASON_END.day) < (born.month, born.day))


def build_payload(
    rankings: list[dict[str, Any]], places: dict[str, dict[str, Any]], source_meta: dict[str, Any],
    *, generated_at: str | None = None,
) -> dict[str, Any]:
    entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
    identity: dict[str, dict[str, Any]] = {}
    pair_count = 0
    for row in rankings:
        if len(row["players"]) == 2:
            pair_count += 1
        allocation = row["points"] / len(row["players"])
        for index, player in enumerate(row["players"]):
            identity[player["player_id"]] = player
            partner = row["players"][1 - index]["name"] if len(row["players"]) == 2 else None
            entries[player["player_id"]].append({
                "team": row["event_name"], "teamCode": row["event"], "conference": row["conference"],
                "division": row["event_name"], "games": 1, "minutes": allocation, "points": allocation,
                "rank": row["rank"], "pairPoints": row["points"], "tournaments": row["tournaments"],
                "partner": partner,
            })

    records: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    event_order = {code: index for index, code in enumerate(EVENTS)}
    for player_id, splits in entries.items():
        splits.sort(key=lambda split: event_order[split["teamCode"]])
        player = identity[player_id]
        place = places.get(player_id, {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        primary = max(splits, key=lambda split: (split["minutes"], -event_order[split["teamCode"]]))
        dob = place.get("dob")
        record = {
            "id": f"badminton:bwf:{player_id}", "sourcePlayerId": player_id, "name": player["name"],
            "team": primary["team"], "teamCode": primary["teamCode"],
            "teams": [split["team"] for split in splits], "conference": primary["conference"],
            "discipline": primary["team"], "year": SEASON, "rankingDate": RANKING_DATE,
            "rank": min(split["rank"] for split in splits), "points": sum(split["points"] for split in splits),
            "minutes": sum(split["minutes"] for split in splits), "games": len(splits),
            "rankedEntries": len(splits), "position": " · ".join(split["teamCode"] for split in splits),
            "representedCountry": player.get("represented_country"), "nationality": player.get("represented_country"),
            "profileUrl": player["profile_url"], "teamSplits": splits, "dob": dob, "age": age_on(dob),
            "place": place.get("place") if mapped else None, "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None, "lon": place.get("lon") if mapped else None,
            "mapped": mapped, "status": "verified birthplace" if mapped else "birthplace or coordinates unresolved",
            "locationType": "birthplace" if mapped else None, "wikidataQid": place.get("wikidata_qid"),
            "birthPlaceQid": place.get("birth_place_qid"),
            "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({
                "name": record["name"], "events": record["position"], "bwf_id": player_id,
                "status": record["status"],
            })
    records.sort(key=lambda row: (row["rank"], row["name"]))
    mapped_records = [row for row in records if row["mapped"]]
    points = sum(row["points"] for row in records)
    mapped_points = sum(row["points"] for row in mapped_records)
    expected_points = sum(row["points"] for row in rankings)
    if points != expected_points:
        raise ValueError(f"Allocated points do not reconcile: {points} != {expected_points}")
    return {
        "meta": {
            "title": "Badminton Talent Geography", "sport": "badminton",
            "scope": "30 December 2025 BWF world ranking: top 100 singles and top 50 doubles pairs",
            "season": "2025 year-end", "year": SEASON,
            "teams": [spec["name"] for spec in EVENTS.values()], "conferences": ["Men", "Women", "Mixed"],
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "ranking_date": RANKING_DATE, "ranking_source_name": "BWF World Rankings",
            "ranking_source_url": "https://bwfbadminton.com/rankings/",
            "ranking_archive_urls": {code: ranking_url(code) for code in EVENTS},
            "birthplace_source_name": "Wikidata", "birthplace_source_url": "https://www.wikidata.org/",
            "doubles_allocation": "Each pair's points are divided equally between its two partners.",
            **source_meta,
        },
        "summary": {
            "teams": len(EVENTS), "events": len(EVENTS), "players": len(records),
            "ranked_entries": sum(row["rankedEntries"] for row in records), "pairs": pair_count,
            "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "points": points, "mapped_points": mapped_points,
            "point_coverage_pct": round(mapped_points / points * 100, 1) if points else 0,
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped_records}),
            "birth_countries": len({row["country"] for row in mapped_records}),
            "unresolved_players": len(unresolved),
        },
        "records": records, "unresolved": unresolved,
    }


def run(
    output_path: Path = DEFAULT_OUTPUT, *, cache_dir: Path = DEFAULT_CACHE,
    wikidata_cache: Path = DEFAULT_WIKIDATA_CACHE, rankings_input_dir: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    rankings, source_meta = fetch_rankings(cache_dir, rankings_input_dir=rankings_input_dir, force=force)
    players = unique_players(rankings)
    payload = build_payload(rankings, fetch_birthplaces(players, wikidata_cache, force=force), source_meta)
    expected_rows = sum(spec["limit"] for spec in EVENTS.values())
    if len(rankings) != expected_rows or payload["summary"]["ranked_entries"] != 500:
        raise ValueError("Badminton cohort reconciliation failed")
    _write_json(output_path, payload)
    print(
        f"Wrote {len(payload['records'])} unique athletes across 500 ranked entries with "
        f"{payload['summary']['player_coverage_pct']}% birthplace coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the 2025 year-end badminton talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--wikidata-cache", type=Path, default=DEFAULT_WIKIDATA_CACHE)
    parser.add_argument("--rankings-input-dir", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(
        args.output, cache_dir=args.cache_dir, wikidata_cache=args.wikidata_cache,
        rankings_input_dir=args.rankings_input_dir, force=args.force,
    )


if __name__ == "__main__":
    main()
