"""Build the men's elite Kigali 2025 road cycling championship edition."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pdfplumber
import requests

from src.ftg.http_cache import CachedHttpClient
from src.ftg.enrich_wikidata import claim_date, claim_entity, entity_label
from src.ftg.utils import age_on, download_binary, normalize_key, write_json

ROOT = Path(__file__).resolve().parents[2]
SEASON = 2025
SNAPSHOT_DATE = date(2025, 9, 28)
API = "https://prod.server.tissottiming.com/competitions/crdwch2025"
RESULTS_URL = "https://archive.tissottiming.com/2025/crdwch/"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
DEFAULT_CACHE = ROOT / "data/cache/cycling_2025"
DEFAULT_OUTPUT = ROOT / "docs/cycling/data/dashboard.json"
EVENTS = {
    "road": {"number": 13, "name": "Road race", "source_name": "Men Elite Road Race", "date": "2025-09-28", "entries": 165, "starts": 164},
    "itt": {"number": 2, "name": "Individual time trial", "source_name": "Men Elite Individual Time Trial", "date": "2025-09-21", "entries": 55, "starts": 54},
}
ITT_STARTLIST_URL = "https://prod.server.tissottiming.com/file/0003180200010601FFFFFFFFFFFFFF01"
STAT_FIELDS = ("starts", "finishes", "medals", "gold", "silver", "bronze")
MONTHS = {name: index for index, name in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), 1)}


def display_name(raw: str) -> str:
    """Move the timing feed's capitalized surname ahead of the given name."""
    parts = raw.split()
    particles = {"van", "von", "der", "den", "de", "del", "da", "do", "du", "le", "la"}
    split = next((i for i, part in enumerate(parts) if part.lower() not in particles and not part.isupper()), len(parts))
    surname = [part.title() if part.isupper() else part for part in parts[:split]]
    return " ".join(parts[split:] + surname)


def name_key(value: str) -> str:
    # Compare exact name tokens independent of feed order, punctuation and accents.
    value = value.translate(str.maketrans({"ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D"}))
    return " ".join(sorted(normalize_key(token) for token in re.findall(r"[^\W_]+", value, re.UNICODE)))


def parse_dobs(content: bytes) -> dict[str, str]:
    output: dict[str, str] = {}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        if "Men Elite Individual Time Trial" not in (pdf.pages[0].extract_text() or ""):
            raise ValueError("Expected the men's elite time-trial start list")
        for page in pdf.pages:
            for identifier, day, month, year in re.findall(r"\b(\d{11})\s+[A-Z]{3}\s+(\d{1,2})\s+([A-Z]{3})\s+(\d{4})\b", page.extract_text() or ""):
                dob = date(int(year), MONTHS[month], int(day)).isoformat()
                if identifier in output and output[identifier] != dob:
                    raise ValueError(f"Conflicting source DOB for {identifier}")
                output[identifier] = dob
    if not output:
        raise ValueError("No dated rider identities in the official start list")
    return output


def aggregate_results(
    pages: dict[str, dict[str, Any]], dobs: dict[str, str], teams: dict[str, str],
    *, validate_counts: bool = True,
) -> list[dict[str, Any]]:
    if set(pages) != set(EVENTS):
        raise ValueError("Both men's elite events are required")
    riders: dict[str, dict[str, Any]] = {}
    for key, spec in EVENTS.items():
        page = pages[key]
        if page.get("event", {}).get("name") != spec["source_name"] or page["event"].get("number") != spec["number"]:
            raise ValueError(f"Wrong event supplied for {key}")
        results = page["results"]
        seen: set[str] = set()
        starts = 0
        for result in results:
            source = result["rider"]
            identifier = str(source.get("uciRiderId") or "")
            if not re.fullmatch(r"\d{11}", identifier) or identifier in seen:
                raise ValueError(f"Missing or duplicate UCI ID in {key}: {identifier}")
            seen.add(identifier)
            status = str(result.get("value") or "").strip()
            rank = result.get("rank", 0)
            if status == "DNS":
                continue
            if result.get("resultType") == "Time" and isinstance(rank, int) and rank > 0:
                status = "Finished"
            elif status not in {"DNF", "OTL", "DSQ"}:
                raise ValueError(f"Unknown race result for {identifier}: {status}")
            starts += 1
            nation = source["nation"]
            if nation not in teams:
                raise ValueError(f"Missing official team label: {nation}")
            rider = riders.setdefault(identifier, {
                "sourcePlayerId": identifier, "name": display_name(source["name"]),
                "officialName": source["name"], "dob": dobs.get(identifier),
                "team": teams[nation], "teamCode": nation, "eventLog": [],
            })
            if rider["teamCode"] != nation:
                raise ValueError(f"Conflicting represented teams for {identifier}")
            rider["eventLog"].append({
                "event": spec["name"], "date": spec["date"], "bib": source["bib"],
                "position": rank if status == "Finished" else None, "status": status,
                "time": result.get("time") if status == "Finished" else None,
                "medal": {1: "Gold", 2: "Silver", 3: "Bronze"}.get(rank) if status == "Finished" else None,
                "sourceUrl": f"{API}/events/{spec['number']}/phases/1/results",
            })
        if validate_counts and (len(results) != spec["entries"] or starts != spec["starts"]):
            raise ValueError(f"Incomplete {key} cohort: {len(results)} entries / {starts} starts")
    return sorted(riders.values(), key=lambda rider: rider["sourcePlayerId"])


def candidate_names(rider: dict[str, Any]) -> set[str]:
    return {rider["name"], " ".join(part.title() if part.isupper() else part for part in rider["officialName"].split())}


def birthplace_query(names: list[str]) -> str:
    values = " ".join(json.dumps(name, ensure_ascii=False) + "@en" for name in names)
    return f'''SELECT DISTINCT ?lookup ?person ?personLabel ?dob ?birthplace ?birthplaceLabel ?coord ?countryLabel WHERE {{
      VALUES ?lookup {{ {values} }}
      ?person (rdfs:label|skos:altLabel) ?lookup; wdt:P31 wd:Q5; wdt:P1663 ?cyclingId.
      OPTIONAL {{ ?person wdt:P569 ?dob. }}
      OPTIONAL {{ ?person wdt:P19 ?birthplace.
        FILTER NOT EXISTS {{ ?birthplace wdt:P31/wdt:P279* wd:Q6256. }}
        OPTIONAL {{ ?birthplace wdt:P625 ?coord. }}
        OPTIONAL {{ ?birthplace wdt:P17 ?country. }}
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}'''


def resolve_identities(riders: list[dict[str, Any]], bindings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for binding in bindings:
        index[name_key(binding["lookup"]["value"])].append(binding)
    output = {}
    for rider in riders:
        candidates = [item for name in candidate_names(rider) for item in index.get(name_key(name), [])]
        # A known official DOB must agree; a contradictory same-name entity must never enter the map.
        candidates = [item for item in candidates if not rider.get("dob") or item.get("dob", {}).get("value", "")[:10] == rider["dob"]]
        qids = {item["person"]["value"] for item in candidates}
        if len(qids) != 1:
            continue
        identity = candidates[0]
        locations = set()
        for item in candidates:
            point = re.fullmatch(r"Point\(([-\d.eE+]+) ([-\d.eE+]+)\)", item.get("coord", {}).get("value", ""))
            country = item.get("countryLabel", {}).get("value")
            place = item.get("birthplaceLabel", {}).get("value")
            if not point or not country or not place or re.fullmatch(r"Q\d+", country) or re.fullmatch(r"Q\d+", place):
                continue
            lon, lat = map(float, point.groups())
            if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
                locations.add((place, country, lat, lon, item["birthplace"]["value"].rsplit("/", 1)[-1]))
        dob_values = {item["dob"]["value"][:10] for item in candidates if item.get("dob")}
        output[rider["sourcePlayerId"]] = {
            "name": identity["personLabel"]["value"], "wikidataQid": identity["person"]["value"].rsplit("/", 1)[-1],
            "dob": next(iter(dob_values)) if len(dob_values) == 1 else None,
            "identityMethod": "exact name + cycling identifier + official DOB" if rider.get("dob") else "unique exact name + cycling identifier",
        }
        if len(locations) == 1:
            place, country, lat, lon, place_qid = next(iter(locations))
            output[rider["sourcePlayerId"]].update(place=place, country=country, lat=lat, lon=lon, birthPlaceQid=place_qid)
    return output


def search_identity_bindings(
    riders: list[dict[str, Any]], client: CachedHttpClient, cache_dir: Path,
    sources: list[dict[str, str]], *, force: bool = False,
) -> list[dict[str, Any]]:
    """Search is candidate discovery only; exact documented names and DOBs still decide identity."""
    def fetch(params: dict[str, str]) -> dict[str, Any]:
        url = WIKIDATA_API + "?" + urlencode({"format": "json", **params})
        digest = hashlib.sha256(url.encode()).hexdigest()[:20]
        result = client.fetch_text(url, cache_dir / "wikidata_api" / f"{digest}.json", force=force)
        sources.append({"url": url, "retrieved_at": result.retrieved_at})
        data = json.loads(result.text)
        if data.get("error"):
            raise ValueError(f"Wikidata API error: {data['error']}")
        return data

    def entities(ids: set[str]) -> dict[str, dict[str, Any]]:
        output = {}
        ordered = sorted(ids)
        for index in range(0, len(ordered), 40):
            output.update(fetch({
                "action": "wbgetentities", "ids": "|".join(ordered[index:index + 40]),
                "props": "claims|labels|aliases", "languages": "en|es|fr|de|nl|it|pt",
            }).get("entities", {}))
        return output

    def claim_values(entity: dict[str, Any], prop: str) -> list[Any]:
        claims = [claim for claim in entity.get("claims", {}).get(prop, []) if claim.get("rank") != "deprecated"]
        preferred = [claim for claim in claims if claim.get("rank") == "preferred"]
        return [claim["mainsnak"]["datavalue"]["value"] for claim in preferred or claims if claim.get("mainsnak", {}).get("datavalue")]

    candidates = {}
    for index, rider in enumerate(riders, 1):
        result = fetch({"action": "wbsearchentities", "search": rider["name"], "language": "en", "limit": "5"})
        candidates[rider["sourcePlayerId"]] = {item["id"] for item in result.get("search", [])}
        if index % 10 == 0:
            print(f"Checked exact cyclist aliases {index}/{len(riders)}", flush=True)
    people = entities(set().union(*candidates.values()) if candidates else set())
    selected: dict[str, list[str]] = {}
    for rider in riders:
        matches = []
        source_keys = {name_key(name) for name in candidate_names(rider)}
        for qid in candidates[rider["sourcePlayerId"]]:
            entity = people.get(qid, {})
            names = [item["value"] for item in entity.get("labels", {}).values()]
            names.extend(item["value"] for aliases in entity.get("aliases", {}).values() for item in aliases)
            if claim_entity(entity, "P31") != "Q5" or not claim_values(entity, "P1663"):
                continue
            if not source_keys.intersection(name_key(name) for name in names):
                continue
            if rider.get("dob") and claim_date(entity) != rider["dob"]:
                continue
            matches.append(qid)
        selected[rider["sourcePlayerId"]] = matches
    place_ids = {value["id"] for ids in selected.values() for qid in ids for value in claim_values(people[qid], "P19")}
    places = entities(place_ids)
    country_ids = {value["id"] for place in places.values() for value in claim_values(place, "P17")}
    countries = entities(country_ids)
    bindings = []
    for rider in riders:
        for qid in selected[rider["sourcePlayerId"]]:
            entity = people[qid]
            base = {
                "lookup": {"value": rider["name"]}, "person": {"value": f"http://www.wikidata.org/entity/{qid}"},
                "personLabel": {"value": entity_label(entity) or rider["name"]},
            }
            if claim_date(entity):
                base["dob"] = {"value": claim_date(entity)}
            bindings.append(base)
            for value in claim_values(entity, "P19"):
                place_id = value["id"]
                place = places.get(place_id, {})
                if any(value.get("id") in {"Q6256", "Q3624078"} for value in claim_values(place, "P31")):
                    continue
                for coord in claim_values(place, "P625"):
                    for country in claim_values(place, "P17"):
                        bindings.append({
                            **base, "birthplace": {"value": f"http://www.wikidata.org/entity/{place_id}"},
                            "birthplaceLabel": {"value": entity_label(place) or place_id},
                            "countryLabel": {"value": entity_label(countries.get(country["id"], {})) or country["id"]},
                            "coord": {"value": f"Point({coord['longitude']} {coord['latitude']})"},
                        })
    return bindings


def event_stats(events: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "starts": len(events), "finishes": sum(event["status"] == "Finished" for event in events),
        "medals": sum(bool(event["medal"]) for event in events),
        **{medal.lower(): sum(event["medal"] == medal for event in events) for medal in ("Gold", "Silver", "Bronze")},
    }


def build_payload(riders: list[dict[str, Any]], identities: dict[str, dict[str, Any]], source_meta: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    records, unresolved = [], []
    for rider in riders:
        identity = identities.get(rider["sourcePlayerId"], {})
        mapped = all(identity.get(key) is not None for key in ("place", "country", "lat", "lon", "birthPlaceQid"))
        stats = event_stats(rider["eventLog"])
        dob = rider.get("dob") or identity.get("dob")
        status = "verified birthplace" if mapped else "birthplace unavailable or ambiguous" if identity else "cycling identity unresolved"
        splits = [{
            "team": rider["team"], "teamCode": rider["teamCode"], "conference": event["event"],
            "games": 1, **event_stats([event]),
        } for event in rider["eventLog"]]
        record = {
            **rider, **stats, "id": f"cycling:{rider['sourcePlayerId']}",
            "name": identity.get("name") or rider["name"], "year": SEASON, "gender": "Men",
            "dob": dob, "dobSource": "Tissot official start list" if rider.get("dob") else "Wikidata" if dob else None,
            "age": age_on(dob, SNAPSHOT_DATE), "games": stats["starts"],
            "teams": [rider["team"]], "teamSplits": splits,
            "conference": splits[0]["conference"], "representedCountry": rider["team"],
            "eventNames": [event["event"] for event in rider["eventLog"]],
            "mapped": mapped, "status": status, "locationType": "birthplace" if mapped else None,
            **{key: identity.get(key) if mapped else None for key in ("place", "country", "lat", "lon", "birthPlaceQid")},
            "wikidataQid": identity.get("wikidataQid"), "identityMethod": identity.get("identityMethod"),
            "birthplaceSource": f"https://www.wikidata.org/wiki/{identity['wikidataQid']}" if identity else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({"id": record["id"], "name": record["name"], "team": record["team"], "status": status})
    records.sort(key=lambda row: (-row["starts"], -row["medals"], row["name"]))
    mapped = [row for row in records if row["mapped"]]
    totals = {key: sum(row[key] for row in records) for key in STAT_FIELDS}
    teams = sorted({row["team"] for row in records})
    return {
        "meta": {
            "title": "Road Cycling Talent Geography", "sport": "cycling", "year": SEASON,
            "season": "Kigali 2025", "scope": "2025 UCI Road World Championships men's elite road race and individual time trial actual starters",
            "snapshot_date": SNAPSHOT_DATE.isoformat(), "conferences": [spec["name"] for spec in EVENTS.values()], "teams": teams,
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "results_source_name": "Official UCI / Tissot Timing championship results", "results_source_url": RESULTS_URL,
            "birthplace_source_name": "Wikidata: exact names restricted to identified cyclists; official DOB checked when supplied",
            "birthplace_source_url": "https://www.wikidata.org/", "birthplace_license": "CC0",
            "cohort_note": "Men's elite individual events only. DNS excluded; DNF, OTL and DSQ retained as actual starts. National teams are represented teams, not birth countries. This is a championship snapshot, not the full WorldTour season.",
            **source_meta,
        },
        "summary": {
            "players": len(records), "teams": len(teams), "events": len(EVENTS), **totals,
            "mapped_players": len(mapped), "unresolved_players": len(unresolved),
            "player_coverage_pct": round(len(mapped) / len(records) * 100, 1) if records else 0,
            "mapped_starts": sum(row["starts"] for row in mapped),
            "start_coverage_pct": round(sum(row["starts"] for row in mapped) / totals["starts"] * 100, 1) if totals["starts"] else 0,
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped}),
            "birth_countries": len({row["country"] for row in mapped}),
        },
        "records": records, "unresolved": unresolved,
    }


def run(output: Path = DEFAULT_OUTPUT, *, cache_dir: Path = DEFAULT_CACHE, force: bool = False) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (public research; https://github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.3, retries=3, timeout=120)
    pages, teams, sources = {}, {}, []
    for key, spec in EVENTS.items():
        for kind in ("results", "teams"):
            url = f"{API}/events/{spec['number']}/phases/1/{kind}"
            result = client.fetch_text(url, cache_dir / f"{key}_{kind}.json", force=force)
            data = json.loads(result.text)
            sources.append({"url": url, "retrieved_at": result.retrieved_at})
            if kind == "results":
                pages[key] = data
            else:
                for team in data:
                    # The development centre may reuse SUI for riders representing other delegations.
                    if team["name"] != "UCI WORLD CYCLING CENTRE":
                        teams[team["nation"]] = team["name"].title()
    # These official result codes are sporting delegations, not birth countries.
    teams.update({"REF": "Refugee Team", "AIN": "Individual Neutral Athletes"})
    dob_path = download_binary(ITT_STARTLIST_URL, cache_dir / "itt_startlist.pdf", force=force)
    dobs = parse_dobs(dob_path.read_bytes())
    sources.append({"url": ITT_STARTLIST_URL, "retrieved_at": datetime.fromtimestamp(dob_path.stat().st_mtime, timezone.utc).isoformat()})
    if len(dobs) != EVENTS["itt"]["entries"]:
        raise ValueError("Incomplete official time-trial DOB list")
    riders = aggregate_results(pages, dobs, teams)
    names = sorted({name for rider in riders for name in candidate_names(rider)})
    bindings = []
    for index in range(0, len(names), 25):
        query = birthplace_query(names[index:index + 25])
        digest = hashlib.sha256(query.encode()).hexdigest()[:20]
        url = WIKIDATA_SPARQL + "?" + urlencode({"query": query, "format": "json"})
        result = client.fetch_text(url, cache_dir / "wikidata" / f"{digest}.json", force=force)
        bindings.extend(json.loads(result.text)["results"]["bindings"])
        sources.append({"url": url, "retrieved_at": result.retrieved_at})
        print(f"Resolved lookup batch {index // 25 + 1}/{math.ceil(len(names) / 25)}", flush=True)
    identities = resolve_identities(riders, bindings)
    unmatched = [rider for rider in riders if rider["sourcePlayerId"] not in identities]
    bindings.extend(search_identity_bindings(unmatched, client, cache_dir, sources, force=force))
    identities = resolve_identities(riders, bindings)
    payload = build_payload(riders, identities, {"sources": sources, "dob_source_url": ITT_STARTLIST_URL})
    if len(riders) != 182 or payload["summary"]["starts"] != 218 or payload["summary"]["medals"] != 6:
        raise ValueError("Cycling championship totals do not reconcile")
    write_json(output, payload)
    print(f"Wrote {len(riders)} riders / 218 starts, {payload['summary']['player_coverage_pct']}% birthplace coverage: {output}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(args.output, cache_dir=args.cache_dir, force=args.force)


if __name__ == "__main__":
    main()
