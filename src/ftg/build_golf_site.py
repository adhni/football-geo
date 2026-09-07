from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import pdfplumber
import requests
from bs4 import BeautifulSoup

from src.ftg.enrich_wikidata import (
    _fetch_entities,
    _fetch_title_qids,
    claim_coordinates,
    claim_date,
    claim_entity,
    entity_label,
)
from src.ftg.http_cache import CachedHttpClient

ROOT = Path(__file__).resolve().parents[2]
SEASON = 2025
SEASON_END = date(2025, 12, 29)
TOURS = {
    "OWGR": {"gender": "Men", "ranking_date": "2025-12-28", "id_property": "P3568"},
    "WWGR": {"gender": "Women", "ranking_date": "2025-12-29", "id_property": "P12018"},
}
OWGR_URL = "https://assets-us-01.kc-usercontent.com:443/00be6aeb-6ab1-00f0-f77a-4c8f38e69314/a4e8413e-b9e5-4132-89a9-286a3be535cd/owgr52f2025.pdf"
WWGR_URL = "https://www.wwgr.net/reports/weekrankings?weekId=1253&format=csv"
OFFICIAL_SOURCES = {
    "OWGR": "https://www.owgr.com/archive",
    "WWGR": "https://www.wwgr.net/rankings/2025-12-28",
}
DEFAULT_OUTPUT = ROOT / "docs" / "golf" / "data" / "dashboard.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "golf_2025"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "golf_wikidata_2025.json"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
COUNTRY_PLACE_TYPES = {"Q6256", "Q3624078"}
CITY_STATE_BIRTHPLACE_EXCEPTIONS = {"Q334"}
OWGR_COUNTRIES = {
    "United States", "Northern Ireland", "England", "Scotland", "Sweden", "Austria", "Norway",
    "Japan", "Ireland", "Canada", "Finland", "New Zealand", "South Korea", "Australia", "Denmark",
    "Colombia", "Belgium", "South Africa", "Philippines", "France", "Spain", "Venezuela", "China",
    "Germany", "Taiwan",
}


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


def _write_json(path: Path, value: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    options = {"ensure_ascii": False, "indent": 2, "sort_keys": True} if pretty else {
        "ensure_ascii": False, "separators": (",", ":")
    }
    temporary.write_text(json.dumps(value, **options), encoding="utf-8")
    temporary.replace(path)


def _fetch_bytes(url: str, cache_path: Path, *, force: bool = False) -> tuple[bytes, str]:
    metadata_path = cache_path.with_suffix(cache_path.suffix + ".meta.json")
    if cache_path.exists() and not force:
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        retrieved_at = metadata.get("retrieved_at") or datetime.fromtimestamp(
            cache_path.stat().st_mtime, timezone.utc
        ).isoformat()
        return cache_path.read_bytes(), retrieved_at
    response = requests.get(url, timeout=180, headers={
        "User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"
    })
    response.raise_for_status()
    content = response.content
    retrieved_at = datetime.now(timezone.utc).isoformat()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(cache_path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(cache_path)
    _write_json(metadata_path, {
        "source_url": url, "retrieved_at": retrieved_at, "status_code": response.status_code,
        "sha256": hashlib.sha256(content).hexdigest(),
    }, pretty=True)
    return content, retrieved_at


def _owgr_name_country(words: list[dict[str, Any]]) -> tuple[str, str]:
    combined = " ".join(
        word["text"] for word in sorted(words, key=lambda item: item["x0"])
        if 145 <= word["x0"] < 307
    )
    for country in sorted(OWGR_COUNTRIES, key=len, reverse=True):
        index = combined.find(country)
        if index >= 0:
            return combined[:index].strip(), country
    raise ValueError(f"Could not separate OWGR player and country: {combined}")


def parse_owgr_pdf(content: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with pdfplumber.open(io.BytesIO(content)) as document:
        for page in document.pages[:2]:
            words = page.extract_words()
            rank_words = [
                word for word in words if 70 <= word["x0"] <= 90 and word["text"].isdigit()
                and 1 <= int(word["text"]) <= 100
            ]
            for rank_word in rank_words:
                rank = int(rank_word["text"])
                line = [word for word in words if abs(word["top"] - rank_word["top"]) < 3]
                name, country = _owgr_name_country(line)
                field = lambda left, right: "".join(
                    word["text"] for word in line if left <= word["x0"] < right
                )
                total_points = float(field(340, 380))
                divisor_events = int(field(380, 410))
                actual_events = int(field(500, 525))
                rows.append({
                    "tour": "OWGR", "gender": "Men", "ranking_date": TOURS["OWGR"]["ranking_date"],
                    "rank": rank, "name": name.replace("(Oct1994)", "").strip(), "country_code": country,
                    "total_points": total_points, "average_points": round(total_points / divisor_events, 4),
                    "events": actual_events, "source_player_id": f"{normalize(name)}-{normalize(country)}",
                })
    rows.sort(key=lambda row: row["rank"])
    if [row["rank"] for row in rows] != list(range(1, 101)):
        raise ValueError(f"Expected exact OWGR ranks 1–100; found {len(rows)} rows")
    return rows


def parse_wwgr_csv(text: str) -> list[dict[str, Any]]:
    lines = text.lstrip("\ufeff").splitlines()
    header_index = next((index for index, line in enumerate(lines) if line.startswith("Week,WwgrId,")), None)
    if header_index is None:
        raise ValueError("WWGR CSV header not found")
    rows = []
    for source in csv.DictReader(lines[header_index:]):
        rank = int(source["Rank"])
        if rank > 100:
            continue
        rows.append({
            "tour": "WWGR", "gender": "Women", "ranking_date": TOURS["WWGR"]["ranking_date"],
            "rank": rank, "name": " ".join(source["Name"].split()), "country_code": source["Country"],
            "total_points": float(source["TotalPoints"]), "average_points": float(source["AveragePoints"]),
            "events": int(source["Events"]), "source_player_id": source["WwgrId"],
        })
    rows.sort(key=lambda row: row["rank"])
    if [row["rank"] for row in rows] != list(range(1, 101)):
        raise ValueError(f"Expected exact WWGR ranks 1–100; found {len(rows)} rows")
    return rows


def fetch_cohort(
    cache_dir: Path = DEFAULT_CACHE, *, owgr_input: Path | None = None, wwgr_input: Path | None = None,
    force: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if owgr_input:
        owgr_content = owgr_input.read_bytes()
        owgr_at = datetime.fromtimestamp(owgr_input.stat().st_mtime, timezone.utc).isoformat()
    else:
        owgr_content, owgr_at = _fetch_bytes(OWGR_URL, cache_dir / "owgr_week_52.pdf", force=force)
    if wwgr_input:
        wwgr_text = wwgr_input.read_text(encoding="utf-8-sig")
        wwgr_at = datetime.fromtimestamp(wwgr_input.stat().st_mtime, timezone.utc).isoformat()
    else:
        session = requests.Session()
        session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
        result = CachedHttpClient(session, delay=0, retries=3, timeout=180).fetch_text(
            WWGR_URL, cache_dir / "wwgr_2025-12-29.csv", force=force
        )
        wwgr_text, wwgr_at = result.text, result.retrieved_at
    return parse_owgr_pdf(owgr_content) + parse_wwgr_csv(wwgr_text), {
        "owgr_retrieved_at": owgr_at, "wwgr_retrieved_at": wwgr_at,
    }


def _property_qids(
    client: CachedHttpClient, values: list[str], property_id: str, cache_dir: Path, *, force: bool,
) -> dict[str, str]:
    output: dict[str, set[str]] = {}
    for offset in range(0, len(values), 70):
        batch = sorted(set(values[offset:offset + 70]))
        query = f'SELECT ?item ?value WHERE {{ VALUES ?value {{ {" ".join(json.dumps(v) for v in batch)} }} ?item wdt:{property_id} ?value. }}'
        url = f"{WIKIDATA_SPARQL}?{urlencode({'format': 'json', 'query': query})}"
        digest = hashlib.sha1("|".join(batch).encode()).hexdigest()[:16]
        result = client.fetch_text(url, cache_dir / f"{property_id}_{digest}.json", force=force)
        for binding in json.loads(result.text).get("results", {}).get("bindings", []):
            value = binding["value"]["value"]
            output.setdefault(value, set()).add(binding["item"]["value"].rsplit("/", 1)[-1])
    return {value: next(iter(qids)) for value, qids in output.items() if len(qids) == 1}


def _claim_entity_ids(entity: dict[str, Any], property_id: str) -> set[str]:
    values = set()
    for claim in entity.get("claims", {}).get(property_id, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            values.add(value["id"])
    return values


def wikipedia_birthplace(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".birthplace")
    link = container.select_one("a[title]") if container else None
    bday = soup.select_one(".bday")
    return (link.get("title") if link else None, bday.get_text(strip=True) if bday else None)


def fetch_birthplaces(
    players: list[dict[str, Any]], cache_path: Path = DEFAULT_WIKIDATA_CACHE, *, force: bool = False,
) -> dict[str, dict[str, Any]]:
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.1, retries=3, timeout=120)
    women = [row for row in players if row["tour"] == "WWGR"]
    women_qids = _property_qids(
        client, [item["source_player_id"] for item in women], "P12018",
        DEFAULT_CACHE / "wikidata_ids", force=force,
    )
    selected = {
        f"WWGR:{row['source_player_id']}": qid
        for row in women
        if (qid := women_qids.get(row["source_player_id"]))
    }
    titles_by_key = {
        f"{row['tour']}:{row['source_player_id']}": [row["name"], f"{row['name']} (golfer)"]
        for row in players
    }
    title_qids = _fetch_title_qids(
        client, [title for titles in titles_by_key.values() for title in titles], batch_size=40, force=force
    )
    candidate_qids = set(selected.values()) | {qid for qid in title_qids.values() if qid}
    people = _fetch_entities(
        client, list(candidate_qids), "golf_person_batches", batch_size=30, force=force,
        languages="en|ko|ja|zh|th|es|fr|de|sv",
    )
    for row in players:
        key = f"{row['tour']}:{row['source_player_id']}"
        if key in selected:
            continue
        matches = {
            qid for title in titles_by_key[key] if (qid := title_qids.get(title))
            and claim_entity(people.get(qid, {}), "P31") == "Q5"
        }
        if len(matches) == 1:
            selected[key] = matches.pop()
    place_by_player = {key: claim_entity(people.get(qid, {}), "P19") for key, qid in selected.items()}
    places = _fetch_entities(
        client, [qid for qid in place_by_player.values() if qid], "golf_place_batches",
        batch_size=30, force=force, languages="en|ko|ja|zh|th|es|fr|de|sv",
    )
    countries = _fetch_entities(
        client, [qid for entity in places.values() if (qid := claim_entity(entity, "P17"))],
        "golf_country_batches", batch_size=30, force=force,
    )
    output: dict[str, dict[str, Any]] = {"_meta": {"schema_version": 1, "source": "Wikidata"}}
    for key, person_qid in selected.items():
        place_qid = place_by_player.get(key)
        place = places.get(place_qid, {})
        if _claim_entity_ids(place, "P31") & COUNTRY_PLACE_TYPES and place_qid not in CITY_STATE_BIRTHPLACE_EXCEPTIONS:
            continue
        lat, lon = claim_coordinates(place)
        country_qid = claim_entity(place, "P17")
        country = entity_label(countries.get(country_qid, {}))
        if lat is None or lon is None or not country:
            continue
        output[key] = {
            "wikidata_qid": person_qid, "birth_place_qid": place_qid,
            "dob": claim_date(people.get(person_qid, {})), "place": entity_label(place),
            "country": country, "lat": lat, "lon": lon,
            "resolution_source": "Wikidata identity matched by ranking ID or exact golfer page",
        }

    fallback_titles: dict[str, tuple[str, str | None, str]] = {}
    for key, person_qid in selected.items():
        if key in output:
            continue
        page_title = next(
            (title for title in titles_by_key[key] if title_qids.get(title) == person_qid), None
        )
        if not page_title:
            continue
        url = f"https://en.wikipedia.org/w/rest.php/v1/page/{quote(page_title.replace(' ', '_'), safe='()_,-.')}/html?redirect=yes"
        digest = hashlib.sha1(page_title.encode()).hexdigest()[:16]
        try:
            result = client.fetch_text(url, DEFAULT_CACHE / "wikipedia_profiles" / f"{digest}.html", force=force)
        except RuntimeError:
            continue
        birthplace_title, dob = wikipedia_birthplace(result.text)
        if birthplace_title:
            fallback_titles[key] = (birthplace_title, dob, f"https://en.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}")
    if fallback_titles:
        fallback_qids = _fetch_title_qids(
            client, [value[0] for value in fallback_titles.values()], batch_size=40, force=force
        )
        fallback_places = _fetch_entities(
            client, [qid for qid in fallback_qids.values() if qid], "golf_wikipedia_place_batches",
            batch_size=30, force=force,
        )
        fallback_countries = _fetch_entities(
            client, [qid for entity in fallback_places.values() if (qid := claim_entity(entity, "P17"))],
            "golf_wikipedia_country_batches", batch_size=30, force=force,
        )
        for key, (title, dob, source_url) in fallback_titles.items():
            place_qid = fallback_qids.get(title)
            place = fallback_places.get(place_qid, {})
            if _claim_entity_ids(place, "P31") & COUNTRY_PLACE_TYPES and place_qid not in CITY_STATE_BIRTHPLACE_EXCEPTIONS:
                continue
            lat, lon = claim_coordinates(place)
            country_qid = claim_entity(place, "P17")
            country = entity_label(fallback_countries.get(country_qid, {}))
            if lat is None or lon is None or not country:
                continue
            output[key] = {
                "wikidata_qid": selected[key], "birth_place_qid": place_qid, "dob": dob,
                "place": entity_label(place) or title, "country": country, "lat": lat, "lon": lon,
                "resolution_source": f"English Wikipedia infobox; coordinates from Wikidata ({source_url})",
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
    cohort: list[dict[str, Any]], places: dict[str, dict[str, Any]], source_meta: dict[str, Any],
    *, generated_at: str | None = None,
) -> dict[str, Any]:
    records, unresolved = [], []
    for player in cohort:
        source_key = f"{player['tour']}:{player['source_player_id']}"
        place = places.get(source_key, {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        dob = place.get("dob")
        record = {
            "id": f"golf:{player['tour'].lower()}:{player['source_player_id']}",
            "sourcePlayerId": player["source_player_id"], "name": player["name"],
            "team": player["tour"], "teamCode": player["tour"], "teams": [player["tour"]],
            "conference": player["tour"], "tour": player["tour"], "gender": player["gender"],
            "year": SEASON, "rankingDate": player["ranking_date"], "rank": player["rank"],
            "points": player["total_points"], "averagePoints": player["average_points"],
            "eventsPlayed": player["events"], "games": 1,
            "position": f"{player['gender']}’s world ranking", "dob": dob, "age": age_on(dob),
            "nationality": player["country_code"], "representedCountry": player["country_code"],
            "place": place.get("place") if mapped else None, "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None, "lon": place.get("lon") if mapped else None,
            "mapped": mapped, "status": "verified birthplace" if mapped else "birthplace or coordinates unresolved",
            "locationType": "birthplace" if mapped else None, "wikidataQid": place.get("wikidata_qid"),
            "birthPlaceQid": place.get("birth_place_qid"),
            "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": record["name"], "tour": record["tour"], "status": record["status"]})
    records.sort(key=lambda row: (row["tour"], row["rank"]))
    mapped_records = [row for row in records if row["mapped"]]
    points = round(sum(row["points"] for row in records), 4)
    mapped_points = round(sum(row["points"] for row in mapped_records), 4)
    return {
        "meta": {
            "title": "Golf Talent Geography", "sport": "golf",
            "scope": "Final 2025 OWGR and WWGR top 100", "season": "2025 year-end", "year": SEASON,
            "teams": list(TOURS), "conferences": list(TOURS),
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "ranking_dates": {tour: details["ranking_date"] for tour, details in TOURS.items()},
            "ranking_source_name": "Official World Golf Ranking and Women's World Golf Rankings",
            "ranking_source_urls": OFFICIAL_SOURCES, "birthplace_source_name": "Wikidata",
            "birthplace_source_url": "https://www.wikidata.org/", **source_meta,
        },
        "summary": {
            "teams": 2, "players": len(records), "mapped_players": len(mapped_records),
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
    wikidata_cache: Path = DEFAULT_WIKIDATA_CACHE, owgr_input: Path | None = None,
    wwgr_input: Path | None = None, force: bool = False,
) -> dict[str, Any]:
    cohort, source_meta = fetch_cohort(
        cache_dir, owgr_input=owgr_input, wwgr_input=wwgr_input, force=force
    )
    payload = build_payload(cohort, fetch_birthplaces(cohort, wikidata_cache, force=force), source_meta)
    if len(payload["records"]) != 200 or any(
        len([row for row in payload["records"] if row["tour"] == tour]) != 100 for tour in TOURS
    ):
        raise ValueError("Golf top-100 reconciliation failed")
    _write_json(output_path, payload)
    print(
        f"Wrote 100 OWGR and 100 WWGR golfers with {payload['summary']['player_coverage_pct']}% "
        f"birthplace coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the final 2025 golf talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--wikidata-cache", type=Path, default=DEFAULT_WIKIDATA_CACHE)
    parser.add_argument("--owgr-input", type=Path)
    parser.add_argument("--wwgr-input", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(
        args.output, cache_dir=args.cache_dir, wikidata_cache=args.wikidata_cache,
        owgr_input=args.owgr_input, wwgr_input=args.wwgr_input, force=args.force,
    )


if __name__ == "__main__":
    main()
