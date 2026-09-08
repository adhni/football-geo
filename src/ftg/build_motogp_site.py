from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pdfplumber
import requests

from src.ftg.build_nfl_site import (
    DEFAULT_COUNTRIES_CACHE,
    DEFAULT_GEONAMES_CACHE,
    GEONAMES_CITIES_URL,
    GEONAMES_COUNTRIES_URL,
    _download_binary,
    build_city_index,
    load_country_codes,
)
from src.ftg.http_cache import CachedHttpClient
from src.ftg.enrich_wikidata import (
    _fetch_entities,
    _fetch_title_qids,
    claim_coordinates,
    claim_date,
    claim_entity,
    entity_label,
)

ROOT = Path(__file__).resolve().parents[2]
SEASON = 2025
SEASON_END = date(2025, 12, 31)
API_ROOT = "https://api.pulselive.motogp.com/motogp/v1"
RESULTS_ROOT = f"{API_ROOT}/results"
CLASSIFICATIONS_URL = "https://api.pulselive.motogp.com/motogp/v2/results/classifications"
RIDERS_URL = f"{API_ROOT}/riders"
SERIES = ("MotoGP", "Moto2", "Moto3", "MotoE", "WorldWCR")
SERIES_CODES = {series: series for series in SERIES}
EXPECTED_RACES = {"MotoGP": 44, "Moto2": 22, "Moto3": 22, "MotoE": 14, "WorldWCR": 12}
WCR_EVENTS = {
    "NED": "Dutch Round", "CRE": "Italian Round", "GBR": "UK Round",
    "HUN": "Hungarian Round", "FRA": "French Round", "JER": "Spanish Round",
}
WCR_RESULTS_URL = "https://resources.worldsbk.com/files/results/2025/{event}/WCR/{race}/CLA/Results.pdf"
WCR_BIO_URL = "https://resources.worldsbk.com/files/results/2025/{event}/WCR/L1A/RID/Entry.pdf"
WCR_POINTS = (25, 20, 16, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)
DEFAULT_OUTPUT = ROOT / "docs" / "motogp" / "data" / "dashboard.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "motogp_2025"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "motogp_wikidata_2025.json"
COUNTRY_PLACE_TYPES = {"Q6256", "Q3624078"}
NON_CITY_NAMES = {
    "argentina", "australia", "cantabria", "italy", "japan", "java", "larioja",
    "malaysia", "newzealand", "southafrica", "spain", "terengganu",
}


def normalize(value: object) -> str:
    text = str(value or "").translate(str.maketrans({"ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


def _write_json(path: Path, value: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    options = {"ensure_ascii": False, "indent": 2, "sort_keys": True} if pretty else {
        "ensure_ascii": False, "separators": (",", ":")
    }
    temporary.write_text(json.dumps(value, **options), encoding="utf-8")
    temporary.replace(path)


def _read_input(path: Path, url: str, *, force: bool = False) -> tuple[bytes, str]:
    metadata_path = path.with_suffix(path.suffix + ".meta.json")
    if path.exists() and not force:
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        timestamp = metadata.get("retrieved_at") or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        return path.read_bytes(), timestamp
    response = requests.get(url, timeout=120, headers={"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    response.raise_for_status()
    content = response.content
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    _write_json(metadata_path, {
        "source_url": url, "retrieved_at": timestamp, "status_code": response.status_code,
        "sha256": hashlib.sha256(content).hexdigest(),
    }, pretty=True)
    return content, timestamp


def _json(cache_dir: Path, stem: str, endpoint: str, params: dict[str, Any] | None = None, *, force: bool = False) -> tuple[Any, str]:
    url = endpoint if endpoint.startswith("http") else f"{RESULTS_ROOT}/{endpoint}"
    if params:
        url = f"{url}?{urlencode(params)}"
    content, timestamp = _read_input(cache_dir / f"{stem}.json", url, force=force)
    return json.loads(content), timestamp


def discover_motogp_sessions(cache_dir: Path, *, force: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    seasons, season_time = _json(cache_dir, "seasons", "seasons", force=force)
    season = next((row for row in seasons if row.get("year") == SEASON), None)
    if not season:
        raise ValueError(f"MotoGP API has no {SEASON} season")
    events, event_time = _json(cache_dir, "events", "events", {"seasonUuid": season["id"], "isFinished": "true"}, force=force)
    timestamps = [season_time, event_time]
    grand_prix = [event for event in events if not event.get("test") and str(event.get("date_start", "")).startswith(str(SEASON))]
    if len(grand_prix) != 22:
        raise ValueError(f"Expected 22 completed MotoGP weekends; found {len(grand_prix)}")
    output = []
    for event_index, event in enumerate(grand_prix, start=1):
        categories, timestamp = _json(cache_dir, f"categories_{event['short_name']}", "categories", {"eventUuid": event["id"]}, force=force)
        timestamps.append(timestamp)
        for category in categories:
            series = category["name"].replace("™", "")
            if series not in SERIES[:-1]:
                continue
            sessions, timestamp = _json(cache_dir, f"sessions_{event['short_name']}_{normalize(series)}", "sessions", {"eventUuid": event["id"], "categoryUuid": category["id"]}, force=force)
            timestamps.append(timestamp)
            for session in sessions:
                session_type = session.get("type")
                keep = (series == "MotoGP" and session_type in {"RAC", "SPR"}) or (series != "MotoGP" and session_type == "RAC")
                if not keep:
                    continue
                number = session.get("number")
                label = "Sprint" if session_type == "SPR" else (f"Race {number}" if number else "Grand Prix")
                output.append({
                    "id": session["id"], "series": series, "session": label,
                    "event": event.get("sponsored_name") or event["name"], "eventCode": event["short_name"],
                    "date": session.get("date"), "sequence": event_index * 10 + (number or (1 if session_type == "SPR" else 2)),
                })
    return output, [timestamp for timestamp in timestamps if timestamp]


def parse_motogp_classification(payload: dict[str, Any], session: dict[str, Any], source_url: str) -> list[dict[str, Any]]:
    output = []
    for row in payload.get("classification", []):
        rider = row.get("rider") or {}
        status = str(row.get("status") or "")
        if status.upper() in {"DNS", "NSTART", "DID NOT START"}:
            continue
        position = row.get("position") if isinstance(row.get("position"), int) else None
        output.append({
            "sourcePlayerId": rider.get("riders_id") or rider.get("riders_api_uuid") or rider.get("id"),
            "name": rider.get("full_name"), "representedCountry": (rider.get("country") or {}).get("name"),
            "series": session["series"], "team": row.get("team_name") or (row.get("constructor") or {}).get("name") or "Independent",
            "constructor": (row.get("constructor") or {}).get("name"), "event": session["event"],
            "eventCode": session["eventCode"], "session": session["session"], "date": session.get("date"),
            "sequence": session["sequence"], "laps": int(row.get("total_laps") or 0), "start": 1,
            "position": position, "points": float(row.get("points") or 0), "win": int(position == 1),
            "podium": int(position is not None and position <= 3), "dnf": int(status.upper() not in {"INSTND", "FINISHED"}),
            "status": status or "Classified", "sourceUrl": source_url,
        })
    return output


def _pdf_text(content: bytes, *, first_page_only: bool = False) -> str:
    with pdfplumber.open(io.BytesIO(content)) as document:
        pages = document.pages[:1] if first_page_only else document.pages
        return "\n".join(page.extract_text() or "" for page in pages)


def parse_worldwcr_classification(content: bytes, *, event: str, race: int, source_url: str, sequence: int) -> list[dict[str, Any]]:
    text = _pdf_text(content, first_page_only=True)
    output = []
    row_pattern = re.compile(
        r"^(?P<position>\d+P?|RET|DSQ|DNS)\s+(?P<grid>\d+)\s+(?P<number>\d+)\s*(?P<short>[A-Z]\.\s*[A-Z][A-Z\-']+)\s+"
        r"(?P<nation>[A-Z]{3})\s+(?P<team>.+?)\s+Yamaha YZF-R7\s+(?P<laps>\d+)(?:\s|$)"
    )
    for line in text.splitlines():
        match = row_pattern.match(line.strip())
        if not match:
            continue
        position_text = match.group("position").rstrip("P")
        if position_text == "DNS":
            continue
        position = int(position_text) if position_text.isdigit() else None
        points = WCR_POINTS[position - 1] if position and position <= len(WCR_POINTS) else 0
        output.append({
            "sourcePlayerId": f"worldwcr-{match.group('number')}", "riderNumber": match.group("number"),
            "shortName": match.group("short"), "name": None, "representedCountry": match.group("nation"),
            "series": "WorldWCR", "team": match.group("team").strip(), "constructor": "Yamaha",
            "event": event, "eventCode": next(code for code, label in WCR_EVENTS.items() if label == event),
            "session": f"Race {race}", "date": None, "sequence": sequence, "laps": int(match.group("laps")),
            "start": 1, "position": position, "points": float(points), "win": int(position == 1),
            "podium": int(position is not None and position <= 3), "dnf": int(position is None),
            "status": "Classified" if position is not None else position_text, "sourceUrl": source_url,
        })
    if len(output) < 10:
        raise ValueError(f"Only {len(output)} WorldWCR riders parsed from {source_url}")
    return output


def _display_worldwcr_name(raw: str) -> str:
    tokens = raw.split()
    surname, given = [], []
    for token in tokens:
        (surname if not given and token == token.upper() else given).append(token)
    if not given:
        return raw.title()
    return " ".join(given + [token.title() for token in surname])


def parse_worldwcr_biographies(content: bytes, team_names: set[str]) -> dict[str, dict[str, Any]]:
    lines = _pdf_text(content, first_page_only=True).splitlines()
    profiles: dict[str, dict[str, Any]] = {}
    first = re.compile(r"^\d+\*{0,2}\s*(\d+)\s+(.+?)\s+\([^)]+\)\s+([A-Z]{3})\s+Yamaha YZF-R7")
    second = re.compile(r"^\d+\s+(\d{2}/\d{2}/\d{4})\s+(.+)$")
    for index, line in enumerate(lines[:-1]):
        match = first.match(line.strip())
        if not match:
            continue
        next_row = second.match(lines[index + 1].strip())
        dob, birthplace = None, None
        if next_row:
            dob = datetime.strptime(next_row.group(1), "%d/%m/%Y").date().isoformat()
            tail = next_row.group(2)
            team = next((name for name in sorted(team_names, key=len, reverse=True) if f" {name} " in f" {tail} "), None)
            birthplace = tail.split(team, 1)[0].strip() if team else None
        profiles[match.group(1)] = {
            "name": _display_worldwcr_name(match.group(2)), "birth_city": birthplace,
            "birth_country": match.group(3), "dob": dob, "profile_source": "Official WorldWCR biographical entry list",
        }
    return profiles


def fetch_motogp_results(cache_dir: Path, sessions: list[dict[str, Any]], *, workers: int = 8, force: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    results, timestamps = [], []

    def fetch(session: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
        url = f"{CLASSIFICATIONS_URL}?{urlencode({'session': session['id'], 'test': 'false'})}"
        payload, timestamp = _json(cache_dir / "classifications", session["id"], url, force=force)
        return parse_motogp_classification(payload, session, url), timestamp

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(fetch, session) for session in sessions]
        for index, future in enumerate(as_completed(futures), start=1):
            rows, timestamp = future.result()
            if not rows:
                raise ValueError("A MotoGP classification returned no starters")
            results.extend(rows)
            timestamps.append(timestamp)
            if index % 20 == 0 or index == len(futures):
                print(f"  fetched {index}/{len(futures)} MotoGP classifications", flush=True)
    return results, timestamps


def fetch_rider_profiles(
    cache_dir: Path, source_ids: set[str], current_profiles: list[dict[str, Any]], *, workers: int = 8, force: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    profiles = {str(row.get("id")): row for row in current_profiles if row.get("id")}
    missing = sorted(source_ids - set(profiles))
    timestamps = []

    def fetch(rider_id: str) -> tuple[str, dict[str, Any], str]:
        profile, timestamp = _json(cache_dir / "rider_profiles", rider_id, f"{RIDERS_URL}/{rider_id}", force=force)
        return rider_id, profile, timestamp

    if missing:
        print(f"  fetching {len(missing)} historical rider profiles", flush=True)
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = [executor.submit(fetch, rider_id) for rider_id in missing]
            for index, future in enumerate(as_completed(futures), start=1):
                rider_id, profile, timestamp = future.result()
                profiles[rider_id] = profile
                timestamps.append(timestamp)
                if index % 20 == 0 or index == len(futures):
                    print(f"  fetched {index}/{len(futures)} historical rider profiles", flush=True)
    return list(profiles.values()), timestamps


def fetch_worldwcr(cache_dir: Path, *, force: bool = False) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    results, timestamps = [], []
    for event_index, (code, event) in enumerate(WCR_EVENTS.items(), start=1):
        for race in (1, 2):
            race_code = f"00{race}"
            url = WCR_RESULTS_URL.format(event=code, race=race_code)
            content, timestamp = _read_input(cache_dir / "worldwcr" / f"{code}_race_{race}.pdf", url, force=force)
            results.extend(parse_worldwcr_classification(content, event=event, race=race, source_url=url, sequence=1000 + event_index * 10 + race))
            timestamps.append(timestamp)
    team_names = {row["team"] for row in results}
    profiles: dict[str, dict[str, Any]] = {}
    for code in WCR_EVENTS:
        url = WCR_BIO_URL.format(event=code)
        content, timestamp = _read_input(cache_dir / "worldwcr" / f"{code}_biographies.pdf", url, force=force)
        profiles.update(parse_worldwcr_biographies(content, team_names))
        timestamps.append(timestamp)
    for row in results:
        profile = profiles.get(row["riderNumber"])
        if not profile:
            raise ValueError(f"WorldWCR rider #{row['riderNumber']} has no biographical entry")
        row["name"] = profile["name"]
    return results, profiles, timestamps


def aggregate_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    players: dict[str, dict[str, Any]] = {}
    splits: dict[tuple[str, str, str], dict[str, Any]] = {}
    for result in results:
        key = normalize(result["name"])
        player = players.setdefault(key, {
            "playerId": key, "name": result["name"], "sourcePlayerIds": set(), "raceLog": [],
            "representedCountries": set(), "constructors": set(),
        })
        player["sourcePlayerIds"].add(result["sourcePlayerId"])
        if result.get("representedCountry"):
            player["representedCountries"].add(result["representedCountry"])
        if result.get("constructor"):
            player["constructors"].add(result["constructor"])
        split_key = (key, result["series"], result["team"])
        display_team = f"{SERIES_CODES[result['series']]} · {result['team']}"
        split = splits.setdefault(split_key, {
            "team": display_team, "teamCode": SERIES_CODES[result["series"]], "constructor": result.get("constructor"),
            "conference": result["series"], "games": 0, "minutes": 0, "starts": 0, "laps": 0,
            "wins": 0, "podiums": 0, "dnfs": 0, "points": 0,
        })
        split["games"] += result["start"]
        split["starts"] += result["start"]
        split["minutes"] += result["laps"]
        split["laps"] += result["laps"]
        for target, source in (("wins", "win"), ("podiums", "podium"), ("dnfs", "dnf"), ("points", "points")):
            split[target] += result[source]
        player["raceLog"].append({key: result.get(key) for key in ("series", "event", "session", "position", "status", "laps", "team", "sequence")})
    for (key, _series, _team), split in splits.items():
        players[key].setdefault("teamSplits", []).append(split)
    output = []
    for player in players.values():
        player["teamSplits"].sort(key=lambda split: (-split["minutes"], split["team"]))
        for field in ("games", "minutes", "starts", "laps", "wins", "podiums", "dnfs", "points"):
            player[field] = sum(split[field] for split in player["teamSplits"])
        primary = player["teamSplits"][0]
        series = sorted({split["conference"] for split in player["teamSplits"]}, key=SERIES.index)
        player.update({
            "team": primary["team"], "teamCode": primary["teamCode"], "teams": [split["team"] for split in player["teamSplits"]],
            "conference": primary["conference"], "series": series, "position": " · ".join(series) + " rider",
            "gender": "Women" if "WorldWCR" in series else "Open",
            "sourcePlayerIds": sorted(player["sourcePlayerIds"]), "constructors": sorted(player["constructors"]),
            "representedCountry": sorted(player["representedCountries"])[0] if player["representedCountries"] else None,
            "nationality": sorted(player["representedCountries"])[0] if player["representedCountries"] else None,
        })
        player.pop("representedCountries")
        player["raceLog"].sort(key=lambda row: row["sequence"], reverse=True)
        output.append(player)
    return sorted(output, key=lambda row: row["name"])


def age_on(dob: str | None) -> int | None:
    if not dob:
        return None
    try:
        born = date.fromisoformat(dob[:10])
    except ValueError:
        return None
    return SEASON_END.year - born.year - ((SEASON_END.month, SEASON_END.day) < (born.month, born.day))


def _claim_ids(entity: dict[str, Any], property_id: str) -> set[str]:
    output = set()
    for claim in entity.get("claims", {}).get(property_id, []):
        value = (claim.get("mainsnak", {}).get("datavalue") or {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            output.add(value["id"])
    return output


def fetch_wikidata_birthplaces(
    players: list[dict[str, Any]], profiles: dict[str, dict[str, Any]], cache_path: Path,
    *, force: bool = False,
) -> dict[str, dict[str, Any]]:
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.06, retries=3, timeout=120)
    titles = [player["name"] for player in players]
    title_qids = _fetch_title_qids(client, titles, batch_size=40, force=force)
    people = _fetch_entities(
        client, [qid for qid in title_qids.values() if qid], "motogp_person_batches",
        batch_size=30, force=force, languages="en|es|it|fr|de|pt|nl|ja",
    )
    selected = {}
    for player in players:
        qid = title_qids.get(player["name"])
        entity = people.get(qid, {})
        source_dob = profiles.get(player["playerId"], {}).get("dob")
        if qid and claim_entity(entity, "P31") == "Q5" and source_dob and claim_date(entity) == source_dob:
            selected[player["playerId"]] = qid
    place_by_player = {key: claim_entity(people.get(qid, {}), "P19") for key, qid in selected.items()}
    places = _fetch_entities(client, [qid for qid in place_by_player.values() if qid], "motogp_place_batches", batch_size=30, force=force)
    parents = _fetch_entities(
        client, [qid for entity in places.values() if (qid := claim_entity(entity, "P131"))],
        "motogp_parent_batches", batch_size=30, force=force,
    )
    locations = {**parents, **places}
    countries = _fetch_entities(
        client, [qid for entity in locations.values() if (qid := claim_entity(entity, "P17"))],
        "motogp_country_batches", batch_size=30, force=force,
    )
    output: dict[str, dict[str, Any]] = {}
    for key, person_qid in selected.items():
        place_qid = place_by_player.get(key)
        place = places.get(place_qid, {})
        if not place_qid or _claim_ids(place, "P31") & COUNTRY_PLACE_TYPES:
            continue
        parent = parents.get(claim_entity(place, "P131"), {})
        coordinate_entity = place if claim_coordinates(place) != (None, None) else parent
        lat, lon = claim_coordinates(coordinate_entity)
        country_qid = claim_entity(place, "P17") or claim_entity(parent, "P17")
        country = entity_label(countries.get(country_qid, {}))
        if lat is None or lon is None or not country:
            continue
        output[key] = {
            "place": entity_label(place), "country": country, "lat": lat, "lon": lon,
            "wikidata_qid": person_qid, "birth_place_qid": place_qid,
            "resolution_source": "Wikidata identity verified against official DOB",
        }
    _write_json(cache_path, output, pretty=True)
    return output


def birth_city_search_name(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    text = value.strip()
    country_hint = None
    if "," in text:
        text, country_hint = [part.strip() for part in text.split(",", 1)]
    state_match = re.search(r"\s+(NSW|QLD|VIC|WA|SA|TAS|ACT|NT)$", text, re.I)
    if state_match:
        text = text[:state_match.start()].strip()
        country_hint = "AU"
    if normalize(text) in NON_CITY_NAMES:
        return None, None
    return text, country_hint


def resolve_official_birth_city(
    profile: dict[str, Any], city_index: dict[str, list[dict[str, Any]]],
    country_aliases: dict[str, str], country_names: dict[str, str],
) -> dict[str, Any] | None:
    city, hint = birth_city_search_name(profile.get("birth_city"))
    if not city:
        return None
    candidates = sorted(city_index.get(normalize(city), []), key=lambda row: row["population"], reverse=True)
    if hint:
        country_code = country_aliases.get(normalize(hint), hint if len(hint) == 2 else None)
        candidates = [row for row in candidates if row["country_code"] == country_code]
    if not candidates:
        return None
    countries = {row["country_code"] for row in candidates}
    second_population = candidates[1]["population"] if len(candidates) > 1 else 0
    dominant = candidates[0]["population"] >= 10_000 and candidates[0]["population"] >= max(1, second_population) * 3
    if len(candidates) > 1 and len(countries) > 1 and not dominant and not hint:
        return None
    match = candidates[0]
    return {
        "place": city, "country": country_names.get(match["country_code"], match["country_code"]),
        "lat": round(match["lat"], 6), "lon": round(match["lon"], 6),
        "geonames_id": match["geonames_id"], "resolution_source": "Official birth city; GeoNames coordinates",
    }


def prepare_profiles(
    content: list[dict[str, Any]], worldwcr: dict[str, dict[str, Any]], players: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_source_id = {str(row.get("id")): row for row in content if row.get("id")}
    by_name = {normalize(f"{row.get('name', '')} {row.get('surname', '')}"): row for row in content}
    worldwcr_by_name = {normalize(row["name"]): row for row in worldwcr.values()}
    profiles = {}
    for player in players:
        source = next((by_source_id.get(source_id) for source_id in player["sourcePlayerIds"] if by_source_id.get(source_id)), None)
        source = source or by_name.get(player["playerId"])
        if source:
            profiles[player["playerId"]] = {
                "dob": source.get("birth_date"), "birth_city": source.get("birth_city"),
                "birth_country": (source.get("country") or {}).get("name"), "profile_source": "Official MotoGP rider profile",
            }
        elif player["playerId"] in worldwcr_by_name:
            profiles[player["playerId"]] = worldwcr_by_name[player["playerId"]]
    return profiles


def build_payload(
    players: list[dict[str, Any]], profiles: dict[str, dict[str, Any]], city_index: dict[str, list[dict[str, Any]]],
    country_aliases: dict[str, str], country_names: dict[str, str], wikidata_places: dict[str, dict[str, Any]],
    source_meta: dict[str, Any], *, generated_at: str | None = None,
) -> dict[str, Any]:
    records, unresolved = [], []
    for player in players:
        profile = profiles.get(player["playerId"], {})
        place = wikidata_places.get(player["playerId"]) or resolve_official_birth_city(
            profile, city_index, country_aliases, country_names
        )
        mapped = place is not None
        status = "verified official birthplace" if mapped else (
            "official rider profile unavailable" if not profile else "birthplace unavailable" if not profile.get("birth_city")
            else "birthplace coordinates ambiguous or unavailable"
        )
        record = {
            "id": f"motogp:{player['playerId']}", "sourcePlayerId": player["sourcePlayerIds"][0], **player,
            "year": SEASON, "dob": profile.get("dob"), "age": age_on(profile.get("dob")),
            "place": place.get("place") if mapped else None, "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None, "lon": place.get("lon") if mapped else None,
            "mapped": mapped, "status": status, "locationType": "birthplace" if mapped else None,
            "geonamesId": place.get("geonames_id") if mapped else None,
            "wikidataQid": place.get("wikidata_qid") if mapped else None,
            "birthPlaceQid": place.get("birth_place_qid") if mapped else None,
            "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": record["name"], "series": record["series"], "status": status})
    mapped_records = [row for row in records if row["mapped"]]
    laps = sum(row["laps"] for row in records)
    mapped_laps = sum(row["laps"] for row in mapped_records)
    teams = sorted({split["team"] for row in records for split in row["teamSplits"]}, key=lambda team: (SERIES.index(team.split(" · ", 1)[0]), team))
    return {
        "meta": {
            "title": "MotoGP Talent Geography", "sport": "motogp",
            "scope": "Completed 2025 MotoGP, Moto2, Moto3, MotoE and WorldWCR championship races",
            "season": "2025 season", "year": SEASON, "teams": teams, "conferences": list(SERIES),
            "comparison_groups": list(SERIES), "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "classification_source_name": "Official MotoGP and WorldWCR race classifications",
            "classification_source_urls": [RESULTS_ROOT, "https://www.worldsbk.com/en/results%20statistics"],
            "birthplace_source_name": "Official MotoGP rider profiles and WorldWCR biographical entry lists",
            **source_meta,
        },
        "summary": {
            "teams": len(teams), "races": sum(source_meta["races_by_series"].values()), "players": len(records),
            "mapped_players": len(mapped_records), "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "laps": laps, "mapped_laps": mapped_laps, "lap_coverage_pct": round(mapped_laps / laps * 100, 1) if laps else 0,
            "starts": sum(row["starts"] for row in records),
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped_records}),
            "birth_countries": len({row["country"] for row in mapped_records}), "unresolved_players": len(unresolved),
        },
        "records": records, "unresolved": unresolved,
    }


def run(
    output_path: Path = DEFAULT_OUTPUT, *, cache_dir: Path = DEFAULT_CACHE, workers: int = 8,
    force: bool = False, geonames_input: Path | None = None,
) -> dict[str, Any]:
    sessions, timestamps = discover_motogp_sessions(cache_dir, force=force)
    motogp_results, result_times = fetch_motogp_results(cache_dir, sessions, workers=workers, force=force)
    worldwcr_results, worldwcr_profiles, worldwcr_times = fetch_worldwcr(cache_dir, force=force)
    results = motogp_results + worldwcr_results
    races_by_series = Counter(row["series"] for row in sessions)
    races_by_series["WorldWCR"] = len(WCR_EVENTS) * 2
    races_by_series = {series: races_by_series[series] for series in SERIES}
    if races_by_series != EXPECTED_RACES:
        raise ValueError(f"Race reconciliation failed: expected {EXPECTED_RACES}, found {races_by_series}")
    players = aggregate_results(results)
    rider_content, rider_time = _json(cache_dir, "riders", RIDERS_URL, force=force)
    motogp_source_ids = {
        str(row["sourcePlayerId"]) for row in motogp_results if row.get("sourcePlayerId")
    }
    rider_content, profile_times = fetch_rider_profiles(
        cache_dir, motogp_source_ids, rider_content, workers=workers, force=force
    )
    profiles = prepare_profiles(rider_content, worldwcr_profiles, players)
    cities_path = geonames_input or _download_binary(GEONAMES_CITIES_URL, DEFAULT_GEONAMES_CACHE, force=False)
    CachedHttpClient(delay=0.0, timeout=90).fetch_text(GEONAMES_COUNTRIES_URL, DEFAULT_COUNTRIES_CACHE, force=False)
    country_aliases, country_names = load_country_codes(DEFAULT_COUNTRIES_CACHE)
    country_aliases.update({
        "chi": "CL", "ger": "DE", "por": "PT", "rsa": "ZA", "tpe": "TW",
        normalize("Türkiye"): "TR",
        normalize("United Kingdom of Great Britain and Northern Ireland"): "GB",
    })
    search_names = [birth_city_search_name(profile.get("birth_city"))[0] for profile in profiles.values()]
    needed_names = {normalize(name) for name in search_names if name}
    city_index = build_city_index(cities_path, needed_names)
    wikidata_places = fetch_wikidata_birthplaces(
        players, profiles, DEFAULT_WIKIDATA_CACHE, force=force
    )
    source_meta = {
        "races_by_series": races_by_series,
        "results_retrieved_at": max(timestamps + result_times + worldwcr_times + [rider_time] + profile_times),
    }
    payload = build_payload(players, profiles, city_index, country_aliases, country_names, wikidata_places, source_meta)
    if len({row["id"] for row in payload["records"]}) != len(payload["records"]):
        raise ValueError("MotoGP rider identifiers are not unique")
    if sum(row["starts"] for row in payload["records"]) != len(results):
        raise ValueError("Rider starts do not reconcile to classification rows")
    if sum(row["laps"] for row in payload["records"]) != sum(row["laps"] for row in results):
        raise ValueError("Rider laps do not reconcile to classification rows")
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']} riders from {payload['summary']['races']} races "
        f"with {payload['summary']['player_coverage_pct']}% rider / {payload['summary']['lap_coverage_pct']}% lap coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the completed 2025 motorcycle grand-prix talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--geonames-input", type=Path)
    args = parser.parse_args()
    run(args.output, cache_dir=args.cache_dir, workers=args.workers, force=args.force, geonames_input=args.geonames_input)


if __name__ == "__main__":
    main()
