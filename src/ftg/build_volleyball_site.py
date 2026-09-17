from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from src.ftg.enrich_wikidata import (
    _fetch_entities,
    claim_coordinates,
    claim_date,
    claim_entity,
    entity_label,
)
from src.ftg.http_cache import CachedHttpClient
from src.ftg.utils import write_json as _write_json
from src.ftg.wikidata_birthplaces import fetch_wikidata_birthplaces


ROOT = Path(__file__).resolve().parents[2]
SEASON = 2025
SEASON_END = date(2025, 12, 31)
BASE_URL = "https://en.volleyballworld.com"
SCHEDULE_URL = f"{BASE_URL}/api/v1/volley-tournament/2025-06-01/2025-08-10/1542;1543"
MATCH_URL = f"{BASE_URL}/volleyball/competitions/volleyball-nations-league/2025/schedule/{{match_id}}/"
STATS_SUFFIX = "_libraries/live/_volley-match-statistics-by-player"
COURT_SUFFIX = "_libraries/live/_court-graphic"
EXPECTED_MATCHES = {"Women": 116, "Men": 116}
EXPECTED_TEAMS = {"Women": 18, "Men": 18}
DEFAULT_OUTPUT = ROOT / "docs" / "volleyball" / "data" / "dashboard.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "volleyball_vnl_2025"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "volleyball_wikidata_2025.json"
DEFAULT_WIKIDATA_SEARCH_CACHE = ROOT / "data" / "cache" / "volleyball_wikidata_search_2025.json"
POSITION_NAMES = {
    "S": "Setter", "O": "Opposite", "OH": "Outside hitter",
    "MB": "Middle blocker", "L": "Libero",
}


def normalize(value: object) -> str:
    import unicodedata

    text = str(value or "").translate(str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "đ": "d", "Đ": "D"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


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


def load_schedule(cache_dir: Path, *, force: bool = False) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], str]:
    content, timestamp = _read_input(cache_dir / "schedule.json", SCHEDULE_URL, force=force)
    payload = json.loads(content)
    matches = [row for row in payload["matches"] if row.get("matchStatus") == 2]
    counts = Counter(row["gender"] for row in matches)
    if dict(counts) != EXPECTED_MATCHES:
        raise ValueError(f"Expected {EXPECTED_MATCHES}; found {dict(counts)}")
    teams = {int(row["no"]): row for row in payload["allTeams"]}
    team_counts = Counter()
    for gender in EXPECTED_TEAMS:
        team_counts[gender] = len({row[f"team{side}No"] for row in matches if row["gender"] == gender for side in ("A", "B")})
    if dict(team_counts) != EXPECTED_TEAMS:
        raise ValueError(f"Expected {EXPECTED_TEAMS}; found {dict(team_counts)}")
    return matches, teams, timestamp


def _integer(cell: Any) -> int:
    text = cell.get_text(" ", strip=True) if cell else ""
    match = re.search(r"-?\d+", text)
    return int(match.group()) if match else 0


def parse_match_stats(content: bytes) -> dict[str, dict[str, dict[str, Any]]]:
    soup = BeautifulSoup(content, "html.parser")
    tables = soup.select("table.vbw-stats-scoring.vbw-set-all")
    if len(tables) != 2:
        raise ValueError(f"Expected two all-set scoring tables; found {len(tables)}")
    output: dict[str, dict[str, dict[str, Any]]] = {"A": {}, "B": {}}
    for side, table in zip(("A", "B"), tables):
        for row in table.select("tbody tr"):
            player_no = str(row.get("data-player-no") or "")
            link = row.select_one(".playername a")
            if not player_no or not link:
                continue
            profile_match = re.search(r"/players/(\d+)", link.get("href", ""))
            output[side][player_no] = {
                "playerNo": player_no,
                "profileId": profile_match.group(1) if profile_match else None,
                "shortName": link.get_text(" ", strip=True),
                "positionCode": (row.select_one(".position").get_text(" ", strip=True).split() or [None])[0] if row.select_one(".position") else None,
                "points": _integer(row.select_one(".total-abs")),
                "attackPoints": _integer(row.select_one(".attacks")),
                "blockPoints": _integer(row.select_one(".blocks")),
                "servePoints": _integer(row.select_one(".serves")),
            }
    return output


def _player_name(element: Any) -> str | None:
    first = element.select_one(".player-firstname, .libero-firstname")
    last = element.select_one(".player-lastname, .libero-lastname")
    name = " ".join(part.get_text(" ", strip=True) for part in (first, last) if part)
    return name or None


def parse_set_participation(content: bytes) -> dict[str, dict[str, dict[str, Any]]]:
    soup = BeautifulSoup(content, "html.parser")
    set_wrappers = soup.select(".vbw-sets-lineup-wrapper > .vbw-set-lineup-wrapper")
    if not set_wrappers:
        raise ValueError("Match has no set lineups")
    output: dict[str, dict[str, dict[str, Any]]] = {"A": {}, "B": {}}
    for set_number, wrapper in enumerate(set_wrappers, start=1):
        for side, css_class in (("A", "team-a"), ("B", "team-b")):
            team_wrapper = next((child for child in wrapper.find_all(recursive=False) if css_class in (child.get("class") or [])), None)
            if team_wrapper is None:
                raise ValueError(f"Set {set_number} has no team {side} lineup")
            seen: set[str] = set()
            for element in team_wrapper.select("[data-player-id]"):
                player_no = str(element.get("data-player-id"))
                if player_no in seen:
                    continue
                seen.add(player_no)
                player = output[side].setdefault(player_no, {"name": _player_name(element), "sets": set()})
                player["name"] = player["name"] or _player_name(element)
                player["sets"].add(set_number)
    return output


def parse_match(
    stats_content: bytes, court_content: bytes, match: dict[str, Any], teams: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    stats = parse_match_stats(stats_content)
    participation = parse_set_participation(court_content)
    rows = []
    for side in ("A", "B"):
        team_no = int(match[f"team{side}No"])
        team = teams[team_no]
        for player_no, participation_row in participation[side].items():
            stat = stats[side].get(player_no)
            if not stat:
                raise ValueError(f"Match {match['matchNo']} player {player_no} missing scoring row")
            rows.append({
                **stat, "name": participation_row["name"] or stat["shortName"],
                "gender": match["gender"], "team": team["name"], "teamCode": team["code"],
                "matchId": int(match["matchNo"]), "matchNumber": int(match["matchNoInTournament"]),
                "date": match["matchDateUtc"][:10], "round": match.get("roundName") or match.get("phase"),
                "opponent": teams[int(match[f"team{'B' if side == 'A' else 'A'}No"])]["name"],
                "sets": len(participation_row["sets"]), "matches": 1,
            })
    return rows


def fetch_matches(
    cache_dir: Path, matches: list[dict[str, Any]], teams: dict[int, dict[str, Any]],
    *, workers: int = 12, force: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    def fetch(match: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
        match_id = int(match["matchNo"])
        base_url = MATCH_URL.format(match_id=match_id)
        stats, stats_time = _read_input(cache_dir / "matches" / f"{match_id}_stats.html", urljoin(base_url, STATS_SUFFIX), force=force)
        court, court_time = _read_input(cache_dir / "matches" / f"{match_id}_court.html", urljoin(base_url, COURT_SUFFIX), force=force)
        return parse_match(stats, court, match, teams), [stats_time, court_time]

    results, timestamps = [], []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(fetch, match) for match in matches]
        for index, future in enumerate(as_completed(futures), start=1):
            rows, times = future.result()
            results.extend(rows)
            timestamps.extend(times)
            if index % 25 == 0 or index == len(futures):
                print(f"  processed {index}/{len(futures)} VNL matches", flush=True)
    return results, timestamps


def parse_profile(content: bytes) -> dict[str, Any]:
    soup = BeautifulSoup(content, "html.parser")
    name = soup.select_one("h1")
    fields = {}
    for heading in soup.select(".vbw-player-bio-head"):
        value = heading.find_next_sibling(class_="vbw-player-bio-text")
        if value:
            fields[heading.get_text(" ", strip=True)] = value.get_text(" ", strip=True)
    dob = None
    if fields.get("Birth date"):
        try:
            dob = datetime.strptime(fields["Birth date"], "%d/%m/%Y").date().isoformat()
        except ValueError:
            pass
    return {
        "name": name.get_text(" ", strip=True) if name else None,
        "dob": dob, "nationality": fields.get("Nationality"),
        "position": fields.get("Position"), "height": _integer_text(fields.get("Height")),
    }


def _integer_text(value: str | None) -> int | None:
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else None


def fetch_profiles(
    cache_dir: Path, profile_ids: set[str], *, workers: int = 12, force: bool = False,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    def fetch(profile_id: str) -> tuple[str, dict[str, Any], str]:
        url = f"{BASE_URL}/volleyball/competitions/volleyball-nations-league/2025/players/{profile_id}"
        content, timestamp = _read_input(cache_dir / "profiles" / f"{profile_id}.html", url, force=force)
        return profile_id, parse_profile(content), timestamp

    profiles, timestamps = {}, []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(fetch, profile_id) for profile_id in sorted(profile_ids)]
        for index, future in enumerate(as_completed(futures), start=1):
            profile_id, profile, timestamp = future.result()
            profiles[profile_id] = profile
            timestamps.append(timestamp)
            if index % 50 == 0 or index == len(futures):
                print(f"  processed {index}/{len(futures)} official player profiles", flush=True)
    return profiles, timestamps


def aggregate_results(results: list[dict[str, Any]], profiles_by_id: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    players: dict[str, dict[str, Any]] = {}
    profile_map: dict[str, dict[str, Any]] = {}
    for row in results:
        key = f"{row['gender'].lower()}-{row['playerNo']}"
        profile = profiles_by_id.get(row["profileId"], {})
        name = profile.get("name") or row["name"]
        player = players.setdefault(key, {
            "playerId": key, "sourcePlayerId": row["playerNo"], "profileId": row["profileId"],
            "name": name, "gender": row["gender"], "nationality": profile.get("nationality") or row["team"],
            "position": profile.get("position") or POSITION_NAMES.get(row["positionCode"], row["positionCode"]),
            "height": profile.get("height"), "matchLog": [], "teamSplits": {},
        })
        profile_map[key] = {"dob": profile.get("dob")}
        display_team = f"{row['gender']} · {row['team']}"
        split = player["teamSplits"].setdefault(display_team, {
            "team": display_team, "teamCode": row["teamCode"], "conference": row["gender"],
            "games": 0, "minutes": 0, "matches": 0, "sets": 0, "points": 0,
            "attackPoints": 0, "blockPoints": 0, "servePoints": 0,
        })
        split["games"] += 1
        split["matches"] += 1
        split["minutes"] += row["sets"]
        split["sets"] += row["sets"]
        for field in ("points", "attackPoints", "blockPoints", "servePoints"):
            split[field] += row[field]
        player["matchLog"].append({key: row[key] for key in ("matchId", "date", "round", "opponent", "sets", "points", "team")})
    output = []
    for player in players.values():
        splits = sorted(player["teamSplits"].values(), key=lambda row: (-row["sets"], row["team"]))
        player["teamSplits"] = splits
        for field in ("games", "minutes", "matches", "sets", "points", "attackPoints", "blockPoints", "servePoints"):
            player[field] = sum(split[field] for split in splits)
        primary = splits[0]
        player.update({
            "team": primary["team"], "teamCode": primary["teamCode"], "teams": [row["team"] for row in splits],
            "conference": player["gender"], "series": [player["gender"]],
        })
        player["matchLog"].sort(key=lambda row: row["date"], reverse=True)
        output.append(player)
    return sorted(output, key=lambda row: (row["gender"], row["name"])), profile_map


def age_on(dob: str | None) -> int | None:
    if not dob:
        return None
    born = date.fromisoformat(dob)
    return SEASON_END.year - born.year - ((SEASON_END.month, SEASON_END.day) < (born.month, born.day))


def search_wikidata_places(
    players: list[dict[str, Any]], profiles: dict[str, dict[str, Any]], existing: dict[str, dict[str, Any]],
    cache_dir: Path, *, workers: int = 12, force: bool = False,
) -> dict[str, dict[str, Any]]:
    if DEFAULT_WIKIDATA_SEARCH_CACHE.exists() and not force:
        return json.loads(DEFAULT_WIKIDATA_SEARCH_CACHE.read_text(encoding="utf-8"))
    targets = [player for player in players if player["playerId"] not in existing and profiles.get(player["playerId"], {}).get("dob")]

    def search(player: dict[str, Any]) -> tuple[str, list[str]]:
        params = {
            "action": "wbsearchentities", "search": player["name"], "language": "en",
            "uselang": "en", "type": "item", "limit": "7", "format": "json",
        }
        url = f"https://www.wikidata.org/w/api.php?{urlencode(params)}"
        search_path = cache_dir / "wikidata_search" / f"{player['playerId']}.json"
        for attempt in range(6):
            try:
                if not search_path.exists():
                    time.sleep(1.1)
                content, _ = _read_input(search_path, url, force=force)
                break
            except requests.HTTPError as error:
                if error.response is None or error.response.status_code != 429 or attempt == 5:
                    raise
                time.sleep(min(30, 3 * (attempt + 1)))
        return player["playerId"], [row["id"] for row in json.loads(content).get("search", []) if row.get("id")]

    candidates: dict[str, list[str]] = {}
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(search, player) for player in targets]
        for index, future in enumerate(as_completed(futures), start=1):
            player_id, qids = future.result()
            candidates[player_id] = qids
            if index % 100 == 0 or index == len(futures):
                print(f"  searched {index}/{len(futures)} unresolved player identities", flush=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.04, retries=3, timeout=120)
    people = _fetch_entities(
        client, [qid for values in candidates.values() for qid in values], "volleyball_search_people",
        batch_size=30, force=force, languages="en|es|pt|fr|it|de|pl|tr|ja|ko|zh|ru|sr|bg|th",
    )
    selected: dict[str, str] = {}
    for player in targets:
        player_id = player["playerId"]
        dob = profiles[player_id]["dob"]
        for qid in candidates.get(player_id, []):
            entity = people.get(qid, {})
            if claim_entity(entity, "P31") == "Q5" and claim_date(entity) == dob:
                selected[player_id] = qid
                break
    place_by_player = {player_id: claim_entity(people.get(qid, {}), "P19") for player_id, qid in selected.items()}
    places = _fetch_entities(
        client, [qid for qid in place_by_player.values() if qid], "volleyball_search_places",
        batch_size=30, force=force, languages="en|es|pt|fr|it|de|pl|tr|ja|ko|zh|ru|sr|bg|th",
    )
    parents = _fetch_entities(
        client, [qid for place in places.values() if (qid := claim_entity(place, "P131"))],
        "volleyball_search_parents", batch_size=30, force=force,
        languages="en|es|pt|fr|it|de|pl|tr|ja|ko|zh|ru|sr|bg|th",
    )
    locations = {**parents, **places}
    countries = _fetch_entities(
        client, [qid for location in locations.values() if (qid := claim_entity(location, "P17"))],
        "volleyball_search_countries", batch_size=30, force=force,
        languages="en|es|pt|fr|it|de|pl|tr|ja|ko|zh|ru|sr|bg|th",
    )
    output: dict[str, dict[str, Any]] = {}
    for player_id, person_qid in selected.items():
        place_qid = place_by_player.get(player_id)
        place = places.get(place_qid, {})
        parent = parents.get(claim_entity(place, "P131"), {})
        coordinate_entity = place if claim_coordinates(place) != (None, None) else parent
        lat, lon = claim_coordinates(coordinate_entity)
        country_qid = claim_entity(place, "P17") or claim_entity(parent, "P17")
        country = entity_label(countries.get(country_qid, {}))
        if place_qid and lat is not None and lon is not None and country:
            output[player_id] = {
                "place": entity_label(place), "country": country, "lat": lat, "lon": lon,
                "wikidata_qid": person_qid, "birth_place_qid": place_qid,
                "resolution_source": "Wikidata entity search verified against official DOB",
            }
    _write_json(DEFAULT_WIKIDATA_SEARCH_CACHE, output, pretty=True)
    return output


def build_payload(
    players: list[dict[str, Any]], profiles: dict[str, dict[str, Any]], places: dict[str, dict[str, Any]],
    source_meta: dict[str, Any], *, generated_at: str | None = None,
) -> dict[str, Any]:
    records, unresolved = [], []
    for player in players:
        profile = profiles.get(player["playerId"], {})
        place = places.get(player["playerId"], {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        status = "verified birthplace" if mapped else "identity or coordinate-bearing birthplace unavailable"
        record = {
            "id": f"volleyball:{player['playerId']}", **player, "year": SEASON,
            "dob": profile.get("dob"), "age": age_on(profile.get("dob")),
            "place": place.get("place") if mapped else None, "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None, "lon": place.get("lon") if mapped else None,
            "mapped": mapped, "status": status, "locationType": "birthplace" if mapped else None,
            "wikidataQid": place.get("wikidata_qid"), "birthPlaceQid": place.get("birth_place_qid"),
            "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": record["name"], "team": record["team"], "gender": record["gender"], "status": status})
    mapped_records = [row for row in records if row["mapped"]]
    sets = sum(row["sets"] for row in records)
    mapped_sets = sum(row["sets"] for row in mapped_records)
    teams = sorted({row["team"] for row in records})
    return {
        "meta": {
            "title": "Volleyball Talent Geography", "sport": "volleyball",
            "scope": "Completed 2025 men's and women's Volleyball Nations League",
            "season": "2025 VNL", "year": SEASON, "teams": teams, "conferences": ["Women", "Men"],
            "comparison_groups": ["Women", "Men"], "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "classification_source_name": "Official Volleyball World VNL match centre",
            "classification_source_urls": [SCHEDULE_URL], "birthplace_source_name": "Official Volleyball World profiles and Wikidata",
            **source_meta,
        },
        "summary": {
            "teams": sum(EXPECTED_TEAMS.values()), "matches": sum(source_meta["matches_by_gender"].values()),
            "players": len(records), "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "sets": sets, "mapped_sets": mapped_sets,
            "set_coverage_pct": round(mapped_sets / sets * 100, 1) if sets else 0,
            "player_matches": sum(row["matches"] for row in records), "points": sum(row["points"] for row in records),
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped_records}),
            "birth_countries": len({row["country"] for row in mapped_records}), "unresolved_players": len(unresolved),
        },
        "records": records, "unresolved": unresolved,
    }


def run(
    output_path: Path = DEFAULT_OUTPUT, *, cache_dir: Path = DEFAULT_CACHE, workers: int = 12, force: bool = False,
) -> dict[str, Any]:
    matches, teams, schedule_time = load_schedule(cache_dir, force=force)
    results, match_times = fetch_matches(cache_dir, matches, teams, workers=workers, force=force)
    profile_ids = {row["profileId"] for row in results if row.get("profileId")}
    official_profiles, profile_times = fetch_profiles(cache_dir, profile_ids, workers=workers, force=force)
    players, profiles = aggregate_results(results, official_profiles)
    places = fetch_wikidata_birthplaces(players, profiles, DEFAULT_WIKIDATA_CACHE, force=force)
    places.update(search_wikidata_places(players, profiles, places, cache_dir, workers=workers, force=force))
    payload = build_payload(players, profiles, places, {
        "matches_by_gender": EXPECTED_MATCHES,
        "results_retrieved_at": max([schedule_time, *match_times, *profile_times]),
    })
    if len({row["id"] for row in payload["records"]}) != len(payload["records"]):
        raise ValueError("Volleyball player identifiers are not unique")
    if sum(row["matches"] for row in payload["records"]) != len(results):
        raise ValueError("Player-match totals do not reconcile")
    if sum(row["sets"] for row in payload["records"]) != sum(row["sets"] for row in results):
        raise ValueError("Player-set totals do not reconcile")
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']} players from {payload['summary']['matches']} matches "
        f"with {payload['summary']['player_coverage_pct']}% player / {payload['summary']['set_coverage_pct']}% set coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the completed 2025 men's and women's VNL talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(args.output, cache_dir=args.cache_dir, workers=args.workers, force=args.force)


if __name__ == "__main__":
    main()
