"""Build the Tokyo 2025 World Athletics Championships geography edition."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.ftg.utils import write_json as _write_json
from src.ftg.wikidata_birthplaces import fetch_wikidata_birthplaces as fetch_title_birthplaces


ROOT = Path(__file__).resolve().parents[2]
COMPETITION_ID = 7190593
SEASON = 2025
SEASON_END = date(2025, 9, 21)
RESULTS_URL = f"https://worldathletics.org/competition/calendar-results/results/{COMPETITION_ID}"
DEFAULT_OUTPUT = ROOT / "docs" / "athletics" / "data" / "dashboard.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "athletics_tokyo_2025"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "athletics_wikidata_2025.json"
DEFAULT_WIKIDATA_TITLE_CACHE = ROOT / "data" / "cache" / "athletics_wikidata_title_2025.json"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
EXPECTED_EVENT_COUNT = 49
TERRITORY_COUNTRY_OVERRIDES = {
    "Road Town": "British Virgin Islands",
    "Sandy Ground": "Anguilla",
}
MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _read_input(path: Path, url: str, *, force: bool = False) -> tuple[bytes, str]:
    metadata_path = path.with_suffix(path.suffix + ".meta.json")
    if path.exists() and not force:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        retrieved_at = metadata.get("retrieved_at") or datetime.fromtimestamp(
            path.stat().st_mtime, timezone.utc
        ).isoformat()
        return path.read_bytes(), retrieved_at
    response = requests.get(
        url, timeout=180,
        headers={"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"},
    )
    response.raise_for_status()
    content = response.content
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    _write_json(metadata_path, {
        "source_url": url, "retrieved_at": retrieved_at,
        "status_code": response.status_code, "sha256": hashlib.sha256(content).hexdigest(),
    }, pretty=True)
    return content, retrieved_at


def parse_next_data(content: bytes) -> dict[str, Any]:
    match = re.search(
        rb'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', content, re.DOTALL,
    )
    if not match:
        raise ValueError("World Athletics page did not contain __NEXT_DATA__")
    payload = json.loads(match.group(1))
    return payload["props"]["pageProps"]["calendarEventsResults"]


def load_results_pages(cache_dir: Path, *, force: bool = False) -> tuple[list[dict[str, Any]], str]:
    pages, timestamps = [], []
    for day in range(1, 10):
        url = RESULTS_URL if day == 1 else f"{RESULTS_URL}?day={day}"
        content, timestamp = _read_input(cache_dir / f"day-{day}.html", url, force=force)
        page = parse_next_data(content)
        if page["parameters"]["day"] != day:
            raise ValueError(f"Expected championship day {day}; found {page['parameters']['day']}")
        pages.append(page)
        timestamps.append(timestamp)
    return pages, max(timestamps)


def _iso_dob(value: str | None) -> str | None:
    if not value:
        return None
    parts = value.split()
    if len(parts) != 3 or parts[1] not in MONTHS:
        return None
    return f"{int(parts[2]):04d}-{MONTHS[parts[1]]:02d}-{int(parts[0]):02d}"


def _display_name(value: str) -> str:
    return " ".join(part.title() if part.isupper() else part for part in value.split())


def _athlete_id(competitor: dict[str, Any]) -> str | None:
    slug = str(competitor.get("urlSlug") or "")
    match = re.search(r"-(\d+)$", slug)
    if match:
        return match.group(1)
    value = competitor.get("id") or competitor.get("iaafId")
    return str(value) if value is not None else None


def _discipline(event_name: str) -> str:
    if "Relay" in event_name:
        return "Relays"
    if "Decathlon" in event_name or "Heptathlon" in event_name:
        return "Combined events"
    if "Race Walk" in event_name:
        return "Race walks"
    if "Marathon" in event_name:
        return "Road"
    if any(word in event_name for word in ("Jump", "Vault")):
        return "Jumps"
    if any(word in event_name for word in ("Put", "Throw")):
        return "Throws"
    return "Track"


def _numeric_place(value: Any) -> int | None:
    match = re.match(r"(\d+)", str(value or ""))
    return int(match.group(1)) if match else None


def aggregate_results(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate one row per actual athlete, deduplicating rounds into event entries."""
    events: dict[int, dict[str, Any]] = {}
    race_keys: set[tuple[Any, ...]] = set()
    for page in pages:
        for group in page["eventTitles"]:
            if group.get("eventTitle") is not None:
                continue  # Combined-event disciplines; the overall event is included separately.
            for source_event in group["events"]:
                event = events.setdefault(source_event["eventId"], {
                    "id": source_event["eventId"], "name": source_event["event"],
                    "gender": source_event["gender"], "relay": source_event["isRelay"], "races": [],
                })
                for race in source_event["races"]:
                    results = race.get("results") or []
                    fingerprint = tuple(
                        (str((row.get("competitor") or {}).get("id")), row.get("place"), row.get("mark"))
                        for row in results
                    )
                    key = (event["id"], race.get("race"), race.get("raceNumber"), fingerprint)
                    if key not in race_keys:
                        event["races"].append(race)
                        race_keys.add(key)
    if len(events) != EXPECTED_EVENT_COUNT:
        raise ValueError(f"Expected {EXPECTED_EVENT_COUNT} championship events; found {len(events)}")

    athletes: dict[str, dict[str, Any]] = {}
    appearances: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    relay_members: dict[tuple[int, str], set[str]] = defaultdict(set)

    def ensure_athlete(competitor: dict[str, Any], nationality: str, gender: str) -> str | None:
        athlete_id = _athlete_id(competitor)
        if not athlete_id:
            return None
        athlete = athletes.setdefault(athlete_id, {
            "playerId": athlete_id, "sourcePlayerId": athlete_id,
            "name": _display_name(str(competitor.get("name") or "Unknown athlete")),
            "dob": _iso_dob(competitor.get("birthDate")), "nationality": nationality,
            "genders": set(), "events": {},
        })
        athlete["dob"] = athlete["dob"] or _iso_dob(competitor.get("birthDate"))
        athlete["nationality"] = athlete["nationality"] or nationality
        athlete["genders"].add(gender)
        return athlete_id

    for event in events.values():
        for race in event["races"]:
            for result in race.get("results") or []:
                competitor = result.get("competitor") or {}
                nationality = str(result.get("nationality") or "")
                if event["relay"]:
                    for member in competitor.get("teamMembers") or []:
                        athlete_id = ensure_athlete(member, nationality, event["gender"])
                        if athlete_id:
                            appearances[(athlete_id, event["id"])].append({"race": race, "result": result})
                            relay_members[(event["id"], nationality)].add(athlete_id)
                elif result.get("mark") != "DNS":
                    athlete_id = ensure_athlete(competitor, nationality, event["gender"])
                    if athlete_id:
                        appearances[(athlete_id, event["id"])].append({"race": race, "result": result})

    medals: dict[tuple[str, int], str] = {}
    medal_names = {1: "Gold", 2: "Silver", 3: "Bronze"}
    for event in events.values():
        finals = [race for race in event["races"] if str(race.get("race") or "").startswith("Final")]
        for race in finals:
            for result in race.get("results") or []:
                place = _numeric_place(result.get("place"))
                if place not in medal_names:
                    continue
                nationality = str(result.get("nationality") or "")
                if event["relay"]:
                    for athlete_id in relay_members[(event["id"], nationality)]:
                        medals[(athlete_id, event["id"])] = medal_names[place]
                else:
                    athlete_id = _athlete_id(result.get("competitor") or {})
                    if athlete_id:
                        medals[(athlete_id, event["id"])] = medal_names[place]

    for (athlete_id, event_id), rows in appearances.items():
        event = events[event_id]
        places = [_numeric_place(row["result"].get("place")) for row in rows]
        athlete = athletes[athlete_id]
        athlete["events"][event_id] = {
            "eventId": event_id, "event": event["name"], "discipline": _discipline(event["name"]),
            "gender": {"M": "Men", "W": "Women", "X": "Mixed"}[event["gender"]],
            "rounds": len(rows), "bestPlace": min((place for place in places if place), default=None),
            "medal": medals.get((athlete_id, event_id)),
        }

    output = []
    for athlete in athletes.values():
        event_rows = sorted(athlete.pop("events").values(), key=lambda row: (row["discipline"], row["event"]))
        if not event_rows:
            continue
        genders = athlete.pop("genders")
        conference = "Men" if "M" in genders else "Women" if "W" in genders else "Mixed relay only"
        disciplines = sorted({row["discipline"] for row in event_rows})
        medals_won = [row["medal"] for row in event_rows if row["medal"]]
        entries = len(event_rows)
        rounds = sum(row["rounds"] for row in event_rows)
        team = athlete["nationality"] or "Federation unavailable"
        athlete.update({
            "conference": conference, "series": [conference], "gender": conference,
            "team": team, "teamCode": team, "teams": [team],
            "position": disciplines[0] if len(disciplines) == 1 else "Multiple disciplines",
            "entries": entries, "games": rounds, "rounds": rounds, "medals": len(medals_won),
            "gold": medals_won.count("Gold"), "silver": medals_won.count("Silver"),
            "bronze": medals_won.count("Bronze"), "eventLog": event_rows,
            "teamSplits": [{
                "team": team, "teamCode": team, "conference": conference,
                "games": rounds, "entries": entries, "rounds": rounds,
                "medals": len(medals_won), "gold": medals_won.count("Gold"),
                "silver": medals_won.count("Silver"), "bronze": medals_won.count("Bronze"),
            }],
        })
        output.append(athlete)
    return sorted(output, key=lambda row: (row["conference"], row["name"]))


def _point(value: str | None) -> tuple[float | None, float | None]:
    match = re.match(r"Point\(([-0-9.]+) ([-0-9.]+)\)", value or "")
    return (float(match.group(2)), float(match.group(1))) if match else (None, None)


def fetch_wikidata_birthplaces(
    players: list[dict[str, Any]], cache_path: Path, *, force: bool = False,
) -> dict[str, dict[str, Any]]:
    """Resolve birthplaces through Wikidata's World Athletics athlete ID (P1146)."""
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    output: dict[str, dict[str, Any]] = {}
    player_by_id = {player["sourcePlayerId"]: player for player in players}
    identifiers = sorted(player_by_id)
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    for start in range(0, len(identifiers), 175):
        batch = identifiers[start:start + 175]
        values = " ".join(json.dumps(value) for value in batch)
        query = f"""
SELECT ?person ?waId ?dob ?birthplace ?birthplaceLabel ?coord ?countryLabel WHERE {{
  VALUES ?waId {{ {values} }}
  ?person wdt:P1146 ?waId; wdt:P19 ?birthplace.
  FILTER NOT EXISTS {{
    VALUES ?countryType {{ wd:Q6256 wd:Q3624078 }}
    ?birthplace wdt:P31 ?countryType.
  }}
  OPTIONAL {{ ?person wdt:P569 ?dob. }}
  OPTIONAL {{ ?birthplace wdt:P625 ?directCoord. }}
  OPTIONAL {{ ?birthplace wdt:P131 ?parent. ?parent wdt:P625 ?parentCoord. }}
  BIND(COALESCE(?directCoord, ?parentCoord) AS ?coord)
  OPTIONAL {{ ?birthplace wdt:P17 ?directCountry. }}
  OPTIONAL {{ ?birthplace wdt:P131 ?countryParent. ?countryParent wdt:P17 ?parentCountry. }}
  BIND(COALESCE(?directCountry, ?parentCountry) AS ?country)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}"""
        response = session.get(WIKIDATA_SPARQL, params={"query": query, "format": "json"}, timeout=180)
        response.raise_for_status()
        for binding in response.json()["results"]["bindings"]:
            athlete_id = binding["waId"]["value"]
            player = player_by_id.get(athlete_id)
            if not player:
                continue
            wikidata_dob = binding.get("dob", {}).get("value", "")[:10] or None
            if player.get("dob") and wikidata_dob and player["dob"] != wikidata_dob:
                continue
            lat, lon = _point(binding.get("coord", {}).get("value"))
            place = binding.get("birthplaceLabel", {}).get("value")
            country = binding.get("countryLabel", {}).get("value")
            if lat is None or lon is None or not place or not country:
                continue
            output[athlete_id] = {
                "place": place, "country": TERRITORY_COUNTRY_OVERRIDES.get(place, country),
                "lat": lat, "lon": lon,
                "wikidata_qid": binding["person"]["value"].rsplit("/", 1)[-1],
                "birth_place_qid": binding["birthplace"]["value"].rsplit("/", 1)[-1],
                "resolution_source": "Wikidata matched by official World Athletics athlete ID",
            }
        print(f"  resolved Wikidata batch {start // 175 + 1}/{(len(identifiers) + 174) // 175}", flush=True)
    _write_json(cache_path, output, pretty=True)
    return output


def age_on(dob: str | None) -> int | None:
    if not dob:
        return None
    born = date.fromisoformat(dob)
    return SEASON_END.year - born.year - ((SEASON_END.month, SEASON_END.day) < (born.month, born.day))


def build_payload(
    players: list[dict[str, Any]], places: dict[str, dict[str, Any]], retrieved_at: str,
    *, generated_at: str | None = None,
) -> dict[str, Any]:
    records, unresolved = [], []
    for player in players:
        place = places.get(player["sourcePlayerId"], {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        status = "verified birthplace" if mapped else "World Athletics identity has no coordinate-bearing Wikidata birthplace"
        record = {
            "id": f"athletics:{player['playerId']}", **player, "year": SEASON,
            "age": age_on(player.get("dob")), "representedCountry": player["nationality"],
            "place": place.get("place") if mapped else None, "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None, "lon": place.get("lon") if mapped else None,
            "mapped": mapped, "status": status, "locationType": "birthplace" if mapped else None,
            "wikidataQid": place.get("wikidata_qid"), "birthPlaceQid": place.get("birth_place_qid"),
            "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({
                "name": record["name"], "team": record["team"],
                "gender": record["conference"], "status": status,
            })
    mapped_records = [row for row in records if row["mapped"]]
    entries = sum(row["entries"] for row in records)
    mapped_entries = sum(row["entries"] for row in mapped_records)
    teams = sorted({row["team"] for row in records})
    conferences = [group for group in ("Women", "Men", "Mixed relay only") if any(row["conference"] == group for row in records)]
    return {
        "meta": {
            "title": "Athletics Talent Geography", "sport": "athletics",
            "scope": "Athletes who competed at the 2025 World Athletics Championships in Tokyo",
            "season": "Tokyo 2025", "year": SEASON, "teams": teams, "conferences": conferences,
            "comparison_groups": conferences, "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "classification_source_name": "Official World Athletics championship results",
            "classification_source_urls": [RESULTS_URL],
            "birthplace_source_name": "Wikidata via official World Athletics athlete IDs",
            "results_retrieved_at": retrieved_at,
        },
        "summary": {
            "teams": len(teams), "events": EXPECTED_EVENT_COUNT, "players": len(records),
            "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "entries": entries, "mapped_entries": mapped_entries,
            "entry_coverage_pct": round(mapped_entries / entries * 100, 1) if entries else 0,
            "rounds": sum(row["rounds"] for row in records), "medals": sum(row["medals"] for row in records),
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped_records}),
            "birth_countries": len({row["country"] for row in mapped_records}),
            "unresolved_players": len(unresolved),
        },
        "records": records, "unresolved": unresolved,
    }


def run(
    output_path: Path = DEFAULT_OUTPUT, *, cache_dir: Path = DEFAULT_CACHE,
    wikidata_cache: Path = DEFAULT_WIKIDATA_CACHE, force: bool = False,
) -> dict[str, Any]:
    pages, retrieved_at = load_results_pages(cache_dir, force=force)
    players = aggregate_results(pages)
    places = fetch_wikidata_birthplaces(players, wikidata_cache, force=force)
    title_targets = [
        player for player in players
        if player["sourcePlayerId"] not in places and player.get("dob")
    ]
    title_profiles = {
        player["playerId"]: {"dob": player["dob"]} for player in title_targets
    }
    places.update(fetch_title_birthplaces(
        title_targets, title_profiles, DEFAULT_WIKIDATA_TITLE_CACHE, force=force,
    ))
    payload = build_payload(players, places, retrieved_at)
    if len({row["id"] for row in payload["records"]}) != len(payload["records"]):
        raise ValueError("Athletics athlete identifiers are not unique")
    if sum(row["entries"] for row in payload["records"]) != payload["summary"]["entries"]:
        raise ValueError("Athletics event-entry totals do not reconcile")
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']} athletes / {payload['summary']['entries']} event entries "
        f"with {payload['summary']['player_coverage_pct']}% player coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Tokyo 2025 athletics talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--wikidata-cache", type=Path, default=DEFAULT_WIKIDATA_CACHE)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(args.output, cache_dir=args.cache_dir, wikidata_cache=args.wikidata_cache, force=args.force)


if __name__ == "__main__":
    main()
