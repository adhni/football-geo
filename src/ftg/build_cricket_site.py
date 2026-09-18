from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlencode

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
from src.ftg.utils import age_on as _age_on, normalize_key as normalize, write_json as _write_json

ROOT = Path(__file__).resolve().parents[2]
SEASON = 2025
SEASON_END = date(2025, 12, 31)
CRICSHEET_URL = "https://cricsheet.org/downloads/t20s_json.zip"
REGISTER_URL = "https://cricsheet.org/register/people.csv"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
DEFAULT_CACHE = ROOT / "data" / "cache" / "cricket_2025"
DEFAULT_OUTPUT = ROOT / "docs" / "cricket" / "data" / "dashboard.json"
DEFAULT_WIKIDATA_CACHE = DEFAULT_CACHE / "birthplaces.json"
DEFAULT_OVERRIDES = ROOT / "data" / "cricket_birthplace_overrides.json"
FULL_MEMBERS = (
    "Afghanistan", "Australia", "Bangladesh", "England", "India", "Ireland",
    "New Zealand", "Pakistan", "South Africa", "Sri Lanka", "West Indies", "Zimbabwe",
)
TEAM_CODES = {
    "Afghanistan": "AFG", "Australia": "AUS", "Bangladesh": "BAN", "England": "ENG",
    "India": "IND", "Ireland": "IRE", "New Zealand": "NZL", "Pakistan": "PAK",
    "South Africa": "RSA", "Sri Lanka": "SRI", "West Indies": "WI", "Zimbabwe": "ZIM",
}
NON_BOWLER_WICKETS = {
    "obstructing the field", "retired hurt", "retired out", "run out", "timed out",
}
COUNTRY_PLACE_TYPES = {"Q6256", "Q3624078"}
CITY_STATE_EXCEPTIONS = {"Q334"}  # Singapore is both a city and a country.


def iso_date(value: object) -> str | None:
    text = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], pattern).date().isoformat()
        except ValueError:
            pass
    return None


def parse_register(text: str) -> dict[str, dict[str, str]]:
    rows = {}
    for row in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        identifier = row.get("identifier", "").strip()
        if identifier:
            rows[identifier] = {key: (value or "").strip() for key, value in row.items()}
    return rows


def is_eligible_match(match: dict[str, Any]) -> bool:
    info = match.get("info", {})
    dates = info.get("dates") or []
    return bool(
        dates and str(dates[0]).startswith(str(SEASON))
        and info.get("team_type") == "international"
        and info.get("match_type") == "T20"
        and match.get("innings")
        and set(info.get("teams") or []) & set(FULL_MEMBERS)
    )


def _new_stats() -> dict[str, int]:
    return {
        "appearances": 0, "games": 0, "battingInnings": 0, "runs": 0, "ballsFaced": 0,
        "fours": 0, "sixes": 0, "ballsBowled": 0, "runsConceded": 0, "wickets": 0,
        "catches": 0, "stumpings": 0, "runOuts": 0, "playerOfMatch": 0,
    }


def _fielder_names(wicket: dict[str, Any]) -> list[str]:
    output = []
    for fielder in wicket.get("fielders") or []:
        name = fielder if isinstance(fielder, str) else fielder.get("name")
        if name:
            output.append(name)
    return output


def parse_archive(content: bytes, register: dict[str, dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    splits: dict[tuple[str, str, str], dict[str, Any]] = {}
    matches = 0
    matches_by_gender: defaultdict[str, int] = defaultdict(int)
    represented_sides = 0
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for filename in sorted(name for name in archive.namelist() if name.endswith(".json")):
            match = json.loads(archive.read(filename))
            if not is_eligible_match(match):
                continue
            info = match["info"]
            gender = "Women" if info.get("gender") == "female" else "Men"
            match_id = Path(filename).stem
            people = info.get("registry", {}).get("people", {})
            selected_ids: set[str] = set()
            for team, names in info.get("players", {}).items():
                if team not in FULL_MEMBERS:
                    continue
                represented_sides += 1
                seen: set[str] = set()
                for name in names:
                    player_id = people.get(name)
                    if not player_id or player_id in seen:
                        continue
                    seen.add(player_id)
                    selected_ids.add(player_id)
                    key = (player_id, team, gender)
                    split = splits.setdefault(key, {
                        "sourcePlayerId": player_id, "name": register.get(player_id, {}).get("unique_name")
                        or register.get(player_id, {}).get("name") or name,
                        "cricinfoId": register.get(player_id, {}).get("key_cricinfo") or None,
                        "team": team, "teamCode": TEAM_CODES[team], "conference": gender,
                        "gender": gender, **_new_stats(), "matchIds": [],
                    })
                    split["appearances"] += 1
                    split["games"] += 1
                    split["matchIds"].append(match_id)
            if not selected_ids:
                continue
            matches += 1
            matches_by_gender[gender] += 1

            match_split: dict[str, dict[str, Any]] = {}
            for key, split in splits.items():
                if key[0] in selected_ids and match_id in split["matchIds"]:
                    match_split[key[0]] = split
            for name in info.get("player_of_match") or []:
                player_id = people.get(name)
                if player_id in match_split:
                    match_split[player_id]["playerOfMatch"] += 1

            for innings in match.get("innings") or []:
                if innings.get("super_over"):
                    continue
                batters: set[str] = set()
                for over in innings.get("overs") or []:
                    for delivery in over.get("deliveries") or []:
                        batter_id = people.get(delivery.get("batter"))
                        bowler_id = people.get(delivery.get("bowler"))
                        runs = delivery.get("runs") or {}
                        extras = delivery.get("extras") or {}
                        if batter_id in match_split:
                            batters.add(batter_id)
                            batter = match_split[batter_id]
                            batter_runs = int(runs.get("batter") or 0)
                            batter["runs"] += batter_runs
                            batter["fours"] += int(batter_runs == 4)
                            batter["sixes"] += int(batter_runs == 6)
                            batter["ballsFaced"] += int("wides" not in extras)
                        if bowler_id in match_split:
                            bowler = match_split[bowler_id]
                            bowler["ballsBowled"] += int("wides" not in extras and "noballs" not in extras)
                            bowler["runsConceded"] += int(runs.get("total") or 0) - int(extras.get("byes") or 0) - int(extras.get("legbyes") or 0) - int(extras.get("penalty") or 0)
                        for wicket in delivery.get("wickets") or []:
                            kind = str(wicket.get("kind") or "").casefold()
                            if bowler_id in match_split and kind not in NON_BOWLER_WICKETS:
                                match_split[bowler_id]["wickets"] += 1
                            fielders = _fielder_names(wicket)
                            if kind == "caught and bowled" and not fielders:
                                fielders = [delivery.get("bowler")]
                            stat = "catches" if kind in {"caught", "caught and bowled"} else "stumpings" if kind == "stumped" else "runOuts" if kind == "run out" else None
                            if stat:
                                for fielder_name in fielders:
                                    fielder_id = people.get(fielder_name)
                                    if fielder_id in match_split:
                                        match_split[fielder_id][stat] += 1
                for batter_id in batters:
                    match_split[batter_id]["battingInnings"] += 1

    rows = sorted(splits.values(), key=lambda row: (row["conference"], row["team"], row["name"]))
    return rows, {
        "matches": matches, "matches_by_gender": dict(sorted(matches_by_gender.items())),
        "represented_team_sides": represented_sides,
    }


def aggregate_players(splits: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    players: dict[str, dict[str, Any]] = {}
    stat_fields = list(_new_stats())
    for source in splits:
        player_id = source["sourcePlayerId"]
        row = players.setdefault(player_id, {
            "sourcePlayerId": player_id, "name": source["name"], "cricinfoId": source["cricinfoId"],
            "gender": source["gender"], "conference": source["conference"], "teamSplits": [],
        })
        if row["gender"] != source["gender"]:
            raise ValueError(f"Player {player_id} appears in both gender cohorts")
        split = {key: source[key] for key in (
            "team", "teamCode", "conference", *stat_fields
        )}
        row["teamSplits"].append(split)
    for row in players.values():
        row["teamSplits"].sort(key=lambda split: (-split["appearances"], split["team"]))
        for field in stat_fields:
            row[field] = sum(split[field] for split in row["teamSplits"])
        row["team"] = row["teamSplits"][0]["team"]
        row["teamCode"] = row["teamSplits"][0]["teamCode"]
        row["teams"] = [split["team"] for split in row["teamSplits"]]
    return sorted(players.values(), key=lambda row: (row["conference"], row["name"]))


def fetch_profiles(players: list[dict[str, Any]], cache_dir: Path, *, workers: int = 12, force: bool = False) -> None:
    """Enrich presentation fields from ESPN's public profile JSON; stats remain Cricsheet-only."""
    def fetch(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        player_id = row["sourcePlayerId"]
        cricinfo_id = row.get("cricinfoId")
        if not cricinfo_id:
            return player_id, {}
        path = cache_dir / f"{cricinfo_id}.json"
        if path.exists() and not force:
            try:
                return player_id, json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/cricket/8048/athletes/{cricinfo_id}"
        try:
            response = requests.get(url, timeout=30, headers={"User-Agent": "TalentGeography/1.0"})
            response.raise_for_status()
            payload = response.json().get("athlete") or {}
            path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(path, payload)
            return player_id, payload
        except (requests.RequestException, ValueError, OSError):
            return player_id, {}

    profiles = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(fetch, row) for row in players]
        for future in as_completed(futures):
            player_id, profile = future.result()
            profiles[player_id] = profile
    for row in players:
        profile = profiles.get(row["sourcePlayerId"], {})
        row["name"] = profile.get("fullName") or profile.get("displayName") or row["name"]
        row["dob"] = iso_date(profile.get("displayDOB"))
        row["position"] = (profile.get("position") or {}).get("name") or "International cricketer"


def _property_qids(client: CachedHttpClient, values: list[str], cache_dir: Path, *, force: bool) -> dict[str, str]:
    found: dict[str, set[str]] = defaultdict(set)
    for offset in range(0, len(values), 70):
        batch = sorted(set(values[offset:offset + 70]))
        query = f'SELECT ?item ?value WHERE {{ VALUES ?value {{ {" ".join(json.dumps(v) for v in batch)} }} ?item wdt:P2697 ?value. }}'
        url = f"{WIKIDATA_SPARQL}?{urlencode({'format': 'json', 'query': query})}"
        digest = hashlib.sha1("|".join(batch).encode()).hexdigest()[:16]
        response = client.fetch_text(url, cache_dir / f"P2697_{digest}.json", force=force)
        for binding in json.loads(response.text).get("results", {}).get("bindings", []):
            found[binding["value"]["value"]].add(binding["item"]["value"].rsplit("/", 1)[-1])
    return {value: next(iter(qids)) for value, qids in found.items() if len(qids) == 1}


def _claim_entity_ids(entity: dict[str, Any], property_id: str) -> set[str]:
    output = set()
    for claim in entity.get("claims", {}).get(property_id, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            output.add(value["id"])
    return output


def wikipedia_birthplace(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    birthplace = soup.select_one(".birthplace")
    link = birthplace.select_one("a[title]") if birthplace else None
    bday = soup.select_one(".bday")
    return (link.get("title") if link else None, bday.get_text(strip=True) if bday else None)


def _fetch_sitelinks(client: CachedHttpClient, qids: list[str], *, force: bool) -> dict[str, str]:
    output = {}
    for offset in range(0, len(qids), 40):
        batch = sorted(set(qids[offset:offset + 40]))
        digest = hashlib.sha1("|".join(batch).encode()).hexdigest()[:16]
        url = "https://www.wikidata.org/w/api.php?" + urlencode({
            "action": "wbgetentities", "ids": "|".join(batch), "props": "sitelinks",
            "sitefilter": "enwiki", "format": "json",
        })
        response = client.fetch_text(url, DEFAULT_CACHE / "wikidata_sitelinks" / f"{digest}.json", force=force)
        for qid, entity in json.loads(response.text).get("entities", {}).items():
            title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
            if title:
                output[qid] = title
    return output


def fetch_birthplaces(players: list[dict[str, Any]], cache_path: Path = DEFAULT_WIKIDATA_CACHE, *, force: bool = False) -> dict[str, dict[str, Any]]:
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.05, retries=3, timeout=120)
    id_rows = [row for row in players if row.get("cricinfoId")]
    qids_by_id = _property_qids(client, [row["cricinfoId"] for row in id_rows], DEFAULT_CACHE / "wikidata_ids", force=force)
    selected = {row["sourcePlayerId"]: qids_by_id[row["cricinfoId"]] for row in id_rows if row["cricinfoId"] in qids_by_id}

    titles_by_id = {row["sourcePlayerId"]: [row["name"], f"{row['name']} (cricketer)"] for row in players}
    title_qids = _fetch_title_qids(client, [title for titles in titles_by_id.values() for title in titles], batch_size=40, force=force)
    candidate_qids = set(selected.values()) | {qid for qid in title_qids.values() if qid}
    people = _fetch_entities(client, list(candidate_qids), "cricket_person_batches", batch_size=30, force=force, languages="en|ur|hi|bn|si")
    for row in players:
        player_id = row["sourcePlayerId"]
        if player_id in selected:
            continue
        matches = set()
        for title in titles_by_id[player_id]:
            qid = title_qids.get(title)
            entity = people.get(qid, {})
            cricinfo_values = {
                str(claim.get("mainsnak", {}).get("datavalue", {}).get("value"))
                for claim in entity.get("claims", {}).get("P2697", [])
            }
            exact_dob = row.get("dob") and claim_date(entity) == str(row["dob"])[:10]
            if qid and (row.get("cricinfoId") in cricinfo_values or exact_dob):
                matches.add(qid)
        if len(matches) == 1:
            selected[player_id] = matches.pop()

    place_by_player = {player_id: claim_entity(people.get(qid, {}), "P19") for player_id, qid in selected.items()}
    places = _fetch_entities(client, [qid for qid in place_by_player.values() if qid], "cricket_place_batches", batch_size=30, force=force, languages="en|ur|hi|bn|si")
    parent_qids = [qid for entity in places.values() if (qid := claim_entity(entity, "P131"))]
    parents = _fetch_entities(client, parent_qids, "cricket_parent_batches", batch_size=30, force=force, languages="en")
    grandparent_qids = [qid for entity in parents.values() if (qid := claim_entity(entity, "P131"))]
    grandparents = _fetch_entities(client, grandparent_qids, "cricket_grandparent_batches", batch_size=30, force=force, languages="en")
    all_locations = {**grandparents, **parents, **places}
    country_qids = {
        qid for entity in all_locations.values() if (qid := claim_entity(entity, "P17"))
    }
    countries = _fetch_entities(client, list(country_qids), "cricket_country_batches", batch_size=30, force=force)

    output: dict[str, dict[str, Any]] = {"_meta": {"schema_version": 1, "source": "Wikidata and English Wikipedia"}}
    for player_id, person_qid in selected.items():
        output[player_id] = {
            "wikidata_qid": person_qid, "dob": claim_date(people.get(person_qid, {})),
            "display_name": entity_label(people.get(person_qid, {})),
        }
        place_qid = place_by_player.get(player_id)
        place = places.get(place_qid, {})
        if _claim_entity_ids(place, "P31") & COUNTRY_PLACE_TYPES and place_qid not in CITY_STATE_EXCEPTIONS:
            continue
        coordinate_entity, country_qid = place, claim_entity(place, "P17")
        cursor = claim_entity(place, "P131")
        for _ in range(2):
            parent = all_locations.get(cursor, {})
            if claim_coordinates(coordinate_entity) == (None, None) and parent:
                coordinate_entity = parent
            country_qid = country_qid or claim_entity(parent, "P17")
            cursor = claim_entity(parent, "P131")
        lat, lon = claim_coordinates(coordinate_entity)
        country = entity_label(countries.get(country_qid, {}))
        if lat is None or lon is None or not country:
            continue
        output[player_id].update({
            "wikidata_qid": person_qid, "birth_place_qid": place_qid,
            "dob": claim_date(people.get(person_qid, {})), "place": entity_label(place),
            "country": country, "lat": lat, "lon": lon,
            "resolution_source": "Wikidata identity matched by ESPNcricinfo ID",
        })

    # Wikipedia infobox fallback is accepted only for an already identified player.
    fallback_titles: dict[str, tuple[str, str | None, str]] = {}
    sitelinks = _fetch_sitelinks(client, list(selected.values()), force=force)
    for player_id, person_qid in selected.items():
        if output.get(player_id, {}).get("lat") is not None:
            continue
        page_title = sitelinks.get(person_qid) or next((title for title in titles_by_id[player_id] if title_qids.get(title) == person_qid), None)
        if not page_title:
            continue
        url = f"https://en.wikipedia.org/w/rest.php/v1/page/{quote(page_title.replace(' ', '_'), safe='()_,-.')}/html?redirect=yes"
        digest = hashlib.sha1(page_title.encode()).hexdigest()[:16]
        try:
            result = client.fetch_text(url, DEFAULT_CACHE / "wikipedia_profiles" / f"{digest}.html", force=force)
        except RuntimeError:
            continue
        title, dob = wikipedia_birthplace(result.text)
        if title:
            fallback_titles[player_id] = (title, dob, f"https://en.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}")
    if fallback_titles:
        fallback_qids = _fetch_title_qids(client, [value[0] for value in fallback_titles.values()], batch_size=40, force=force)
        fallback_places = _fetch_entities(client, [qid for qid in fallback_qids.values() if qid], "cricket_wikipedia_place_batches", batch_size=30, force=force, languages="en")
        fallback_parents = _fetch_entities(client, [qid for entity in fallback_places.values() if (qid := claim_entity(entity, "P131"))], "cricket_wikipedia_parent_batches", batch_size=30, force=force, languages="en")
        fallback_locations = {**fallback_parents, **fallback_places}
        fallback_country_qids = [qid for entity in fallback_locations.values() if (qid := claim_entity(entity, "P17"))]
        fallback_countries = _fetch_entities(client, fallback_country_qids, "cricket_wikipedia_country_batches", batch_size=30, force=force)
        for player_id, (title, dob, source_url) in fallback_titles.items():
            place_qid = fallback_qids.get(title)
            place = fallback_places.get(place_qid, {})
            if _claim_entity_ids(place, "P31") & COUNTRY_PLACE_TYPES and place_qid not in CITY_STATE_EXCEPTIONS:
                continue
            parent = fallback_parents.get(claim_entity(place, "P131"), {})
            lat, lon = claim_coordinates(place)
            if lat is None or lon is None:
                lat, lon = claim_coordinates(parent)
            country_qid = claim_entity(place, "P17") or claim_entity(parent, "P17")
            country = entity_label(fallback_countries.get(country_qid, {}))
            if lat is None or lon is None or not country:
                continue
            output[player_id].update({
                "wikidata_qid": selected[player_id], "birth_place_qid": place_qid, "dob": dob,
                "place": entity_label(place) or title, "country": country, "lat": lat, "lon": lon,
                "resolution_source": f"English Wikipedia infobox; coordinates from Wikidata ({source_url})",
            })
    _write_json(cache_path, output, pretty=True)
    return output


def age_on(dob: str | None) -> int | None:
    return _age_on(dob, SEASON_END)


def build_payload(players: list[dict[str, Any]], places: dict[str, dict[str, Any]], source_meta: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    records, unresolved = [], []
    for player in players:
        place = places.get(player["sourcePlayerId"], {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        dob = place.get("dob")
        name = place.get("display_name") or player["name"]
        record = {
            "id": f"cricket:cricsheet:{player['sourcePlayerId']}", **player, "name": name,
            "year": SEASON, "position": player.get("position") or "International cricketer", "dob": dob or player.get("dob"), "age": age_on(dob or player.get("dob")),
            "nationality": player["team"], "representedCountry": player["team"],
            "place": place.get("place") if mapped else None, "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None, "lon": place.get("lon") if mapped else None,
            "mapped": mapped, "status": "verified birthplace" if mapped else "birthplace or coordinates unresolved",
            "locationType": "birthplace" if mapped else None, "wikidataQid": place.get("wikidata_qid"),
            "birthPlaceQid": place.get("birth_place_qid"), "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": record["name"], "gender": record["gender"], "teams": record["teams"], "cricinfoId": record["cricinfoId"], "status": record["status"]})
    records.sort(key=lambda row: (row["conference"], row["name"]))
    mapped_records = [row for row in records if row["mapped"]]
    appearances = sum(row["appearances"] for row in records)
    mapped_appearances = sum(row["appearances"] for row in mapped_records)
    teams = sorted({split["team"] for row in records for split in row["teamSplits"]})
    return {
        "meta": {
            "title": "Cricket Talent Geography", "sport": "cricket", "scope": "2025 men's and women's T20 internationals involving ICC Full Members",
            "season": "2025 calendar year", "year": SEASON, "teams": teams, "conferences": ["Men", "Women"],
            "comparison_groups": ["Men", "Women"], "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "stats_source_name": "Cricsheet T20 international JSON archive", "stats_source_url": "https://cricsheet.org/downloads/",
            "registry_source_name": "Cricsheet Register", "registry_source_url": "https://cricsheet.org/register/",
            "birthplace_source_name": "Wikidata and English Wikipedia", "birthplace_source_url": "https://www.wikidata.org/", **source_meta,
        },
        "summary": {
            "teams": len(teams), "matches": source_meta.get("matches", 0), "players": len(records), "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "appearances": appearances, "mapped_appearances": mapped_appearances,
            "appearance_coverage_pct": round(mapped_appearances / appearances * 100, 1) if appearances else 0,
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped_records}),
            "birth_countries": len({row["country"] for row in mapped_records}), "unresolved_players": len(unresolved),
        },
        "records": records, "unresolved": unresolved,
    }


def _read_input(path: Path, url: str, *, force: bool) -> tuple[bytes, str]:
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    if path.exists() and not force:
        metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        timestamp = metadata.get("retrieved_at") or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        return path.read_bytes(), timestamp
    response = requests.get(url, timeout=180, headers={"User-Agent": "TalentGeography/1.0"})
    response.raise_for_status()
    content = response.content
    retrieved_at = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    _write_json(meta_path, {"source_url": url, "retrieved_at": retrieved_at, "status_code": response.status_code, "sha256": hashlib.sha256(content).hexdigest()}, pretty=True)
    return content, retrieved_at


def run(output_path: Path = DEFAULT_OUTPUT, *, archive_input: Path | None = None, register_input: Path | None = None, cache_dir: Path = DEFAULT_CACHE, wikidata_cache: Path = DEFAULT_WIKIDATA_CACHE, overrides_path: Path = DEFAULT_OVERRIDES, workers: int = 12, force: bool = False, force_birthplaces: bool = False) -> dict[str, Any]:
    archive_path = archive_input or cache_dir / "t20s_json.zip"
    register_path = register_input or cache_dir / "people.csv"
    archive, archive_at = _read_input(archive_path, CRICSHEET_URL, force=force and archive_input is None)
    register_bytes, register_at = _read_input(register_path, REGISTER_URL, force=force and register_input is None)
    register = parse_register(register_bytes.decode("utf-8-sig"))
    splits, match_meta = parse_archive(archive, register)
    players = aggregate_players(splits)
    fetch_profiles(players, cache_dir / "espn_profiles", workers=workers, force=force)
    if len({row["sourcePlayerId"] for row in players}) != len(players):
        raise ValueError("Cricsheet player identifiers are not unique")
    if sum(row["appearances"] for row in players) != sum(row["appearances"] for row in splits):
        raise ValueError("Player/team appearance totals do not reconcile")
    source_meta = {**match_meta, "archive_retrieved_at": archive_at, "register_retrieved_at": register_at, "archive_sha256": hashlib.sha256(archive).hexdigest(), "register_sha256": hashlib.sha256(register_bytes).hexdigest()}
    places = fetch_birthplaces(players, wikidata_cache, force=force_birthplaces)
    if overrides_path.exists():
        places.update(json.loads(overrides_path.read_text(encoding="utf-8")))
    payload = build_payload(players, places, source_meta)
    _write_json(output_path, payload)
    print(f"Wrote {payload['summary']['players']} cricketers from {payload['summary']['matches']} matches with {payload['summary']['player_coverage_pct']}% player / {payload['summary']['appearance_coverage_pct']}% appearance coverage to {output_path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the 2025 men's and women's T20I talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--archive-input", type=Path)
    parser.add_argument("--register-input", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--wikidata-cache", type=Path, default=DEFAULT_WIKIDATA_CACHE)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--force-birthplaces", action="store_true")
    args = parser.parse_args()
    run(args.output, archive_input=args.archive_input, register_input=args.register_input, cache_dir=args.cache_dir, wikidata_cache=args.wikidata_cache, overrides_path=args.overrides, workers=args.workers, force=args.force, force_birthplaces=args.force_birthplaces)


if __name__ == "__main__":
    main()
