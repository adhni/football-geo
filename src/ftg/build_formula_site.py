from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

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
SEASON_END = date(2025, 12, 31)
SERIES = ("Formula 1", "Formula 2", "Formula 3", "F1 Academy")
SERIES_CODES = {"Formula 1": "F1", "Formula 2": "F2", "Formula 3": "F3", "F1 Academy": "F1A"}
ROSTER_URLS = {
    "Formula 1": "https://en.wikipedia.org/wiki/2025_Formula_One_World_Championship",
    "Formula 2": "https://en.wikipedia.org/wiki/2025_Formula_2_Championship",
    "Formula 3": "https://en.wikipedia.org/wiki/2025_FIA_Formula_3_Championship",
    "F1 Academy": "https://en.wikipedia.org/wiki/2025_F1_Academy_season",
}
F1_ARCHIVE_URL = "https://www.fia.com/f1-archives"
F3_ARCHIVE_URL = "https://www.fia.com/formula-3-championship-archives"
F1_RACE_URL = "https://api.jolpi.ca/ergast/f1/2025/results.json"
F1_SPRINT_URL = "https://api.jolpi.ca/ergast/f1/2025/sprint.json"
F1A_RESULTS = {
    15: "Shanghai", 16: "Jeddah", 17: "Miami", 18: "Montreal",
    19: "Zandvoort", 20: "Singapore", 21: "Las Vegas",
}
F2_HTML_SESSIONS = [
    ("Grand Prix of Australia", "grand-prix-australia", "Sprint Race"),
    ("Sakhir", "sakhir", "Sprint Race"), ("Sakhir", "sakhir", "Feature Race"),
    ("Jeddah", "jeddah", "Sprint Race"), ("Jeddah", "jeddah", "Feature Race"),
    ("Imola", "imola", "Sprint Race"), ("Imola", "imola", "Feature Race"),
    ("Monte-Carlo", "monte-carlo", "Sprint Race"), ("Monte-Carlo", "monte-carlo", "Feature Race"),
    ("Barcelona", "barcelona", "Feature Race"),
    ("Spielberg", "spielberg", "Feature Race"),
    ("Silverstone", "silverstone", "Feature Race"),
    ("Spa-Francorchamps", "spa-francorchamps", "Sprint Race"),
    ("Budapest", "budapest", "Sprint Race"), ("Budapest", "budapest", "Feature Race"),
    ("Monza", "monza", "Sprint Race"), ("Monza", "monza", "Feature Race"),
    ("Baku", "baku", "Sprint Race"), ("Baku", "baku", "Feature Race"),
    ("Lusail", "lusail", "Sprint Race"), ("Lusail", "lusail", "Feature Race"),
]
F2_PDF_SESSIONS = [
    ("Barcelona", "Sprint Race", "2025_barcelona_event_-_f2_race_1_sprint_-_final_classification.pdf"),
    ("Spielberg", "Sprint Race", "2025_spielberg_event_-_f2_race_1_sprint_-_final_classification.pdf"),
    ("Silverstone", "Sprint Race", "2025_silverstone_event_-_f2_race_1_-_final_classification.pdf"),
    ("Yas Marina", "Sprint Race", "2025_yas_marina_event_-_f2_race_1_sprint_-_final_classification.pdf"),
    ("Yas Marina", "Feature Race", "2025_yas_marina_event_-_f2_race_2_feature_-_final_classification.pdf"),
]
FIA_DOCUMENT_ROOT = "https://www.fia.com/system/files/decision-document/"
F2_TEAMS = (
    "Van Amersfoort Racing", "DAMS Lucas Oil", "Rodin Motorsport", "Campos Racing",
    "PREMA Racing", "Invicta Racing", "MP Motorsport", "ART Grand Prix",
    "Hitech TGR", "AIX Racing", "TRIDENT",
)
EXPECTED_RACES = {"Formula 1": 30, "Formula 2": 26, "Formula 3": 20, "F1 Academy": 14}
DEFAULT_OUTPUT = ROOT / "docs" / "formula" / "data" / "dashboard.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "formula_2025"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "formula_wikidata_2025.json"
COUNTRY_PLACE_TYPES = {"Q6256", "Q3624078"}
CITY_STATE_EXCEPTIONS = {"Q334"}
DRIVER_ALIASES = {"wshi": "Shi Wei", "falyousef": "Farah AlYousef"}


def normalize(value: object) -> str:
    text = str(value or "").translate(str.maketrans({"ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ð": "d", "Ð": "D"}))
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
    response = requests.get(url, timeout=180, headers={
        "User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"
    })
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


def parse_roster_html(html: str, series: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    tables = []
    for table in soup.select("table.wikitable"):
        first = table.select_one("tr")
        heading = first.get_text(" ", strip=True) if first else ""
        if "Pos." in heading and "Driver" in heading and "Points" in heading:
            tables.append(table)
    if not tables:
        raise ValueError(f"No championship table found for {series}")
    table = tables[-1]
    rows = []
    for tr in table.select("tr")[1:]:
        cells = tr.select("th,td")
        if len(cells) < 3 or not cells[0].get_text(" ", strip=True).isdigit():
            continue
        driver_cell = cells[1]
        named_links = [a for a in driver_cell.select("a[href]") if a.get_text(" ", strip=True)]
        if not named_links:
            continue
        driver_link = named_links[-1]
        name = driver_link.get_text(" ", strip=True)
        country_link = next((a for a in driver_cell.select("a[title]") if a is not driver_link), None)
        points_text = re.sub(r"[^0-9.]", "", cells[-1].get_text(" ", strip=True))
        rows.append({
            "series": series, "rank": int(cells[0].get_text(" ", strip=True)), "name": name,
            "points": float(points_text or 0), "representedCountry": country_link.get("title") if country_link else None,
            "wikipediaTitle": driver_link.get("title") or name,
            "wikipediaUrl": urljoin("https://en.wikipedia.org/", driver_link.get("href", "")),
        })
    if not rows:
        raise ValueError(f"No drivers parsed for {series}")
    if series == "F1 Academy":
        for rank, name, country in ((25, "Farah AlYousef", "Saudi Arabia"), (26, "Shi Wei", "China")):
            if not any(row["name"] == name for row in rows):
                rows.append({
                    "series": series, "rank": rank, "name": name, "points": 0.0,
                    "representedCountry": country, "wikipediaTitle": name,
                    "wikipediaUrl": None,
                })
    return rows


def driver_candidates(short_name: str, roster: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = re.sub(r"\s*\(WCD\)\s*", " ", short_name, flags=re.I).strip()
    alias = DRIVER_ALIASES.get(normalize(cleaned))
    if alias:
        return [row for row in roster if row["name"] == alias]
    exact = [row for row in roster if normalize(row["name"]) == normalize(cleaned)]
    if exact:
        return exact
    match = re.match(r"^([A-Za-z])\.?\s+(.+)$", cleaned)
    if not match:
        return []
    initial, surname = match.groups()
    surname_key = normalize(surname)
    candidates = []
    for row in roster:
        full_key = re.sub(r"(?:jr|junior)$", "", normalize(row["name"]))
        if full_key.startswith(initial.casefold()) and full_key.endswith(surname_key):
            candidates.append(row)
    if not candidates:
        candidates = [
            row for row in roster
            if re.sub(r"(?:jr|junior)$", "", normalize(row["name"])).endswith(surname_key)
        ]
    return candidates


def match_driver(short_name: str, roster: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = driver_candidates(short_name, roster)
    if not candidates and len(short_name.split()) > 1:
        surname_key = normalize(short_name.split()[-1])
        candidates = [
            row for row in roster
            if re.sub(r"(?:jr|junior)$", "", normalize(row["name"])).endswith(surname_key)
        ]
    if len(candidates) != 1:
        raise ValueError(f"Expected one roster match for {short_name!r}; found {[row['name'] for row in candidates]}")
    return candidates[0]


def discover_archive_links(html: str, archive_url: str, series: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    wanted = (
        {"Race Classification", "Race Qualification", "Sprint Classification"}
        if series == "Formula 1" else {"Sprint Race Classification", "Feature Race Classification"}
    )
    output, seen = [], set()
    for anchor in soup.select("a[href]"):
        label = anchor.get_text(" ", strip=True)
        href = anchor.get("href", "")
        if label not in wanted or "/season-2025/" not in href:
            continue
        tail = href.split("/season-2025/", 1)[1].strip("/").split("/")
        if len(tail) < 2:
            continue
        event_slug = tail[0]
        session = "Sprint" if "Sprint" in label else ("Feature Race" if series == "Formula 3" else "Grand Prix")
        key = (event_slug, session)
        if key in seen:
            continue
        seen.add(key)
        output.append({
            "series": series, "event": event_slug.replace("-grand-prix", "").replace("grand-prix-", "").replace("-", " ").title(),
            "session": session, "url": urljoin(archive_url, href),
        })
    return output


def _integer(value: str) -> int:
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else 0


def parse_fia_classification_html(
    html: str, *, series: str, event: str, session: str, url: str,
    roster: list[dict[str, Any]], sequence: int,
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    table = next((table for table in soup.select("table") if all(word in table.get_text(" ") for word in ("Driver", "Team", "Laps"))), None)
    if table is None:
        return []
    rows = table.select("tr")
    headers = [normalize(cell.get_text(" ", strip=True)) for cell in rows[0].select("th,td")]
    index = {key: i for i, key in enumerate(headers)}
    output = []
    for tr in rows[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in tr.select("th,td")]
        if len(cells) != len(headers):
            continue
        driver_text = cells[index["driver"]]
        driver_text = re.sub(r"\s+(?:Image\s*)?[A-Z]{3}$", "", driver_text).strip()
        if not driver_text:
            continue
        driver = match_driver(driver_text, roster)
        position_text = cells[index.get("pos", 0)]
        position = int(position_text) if position_text.isdigit() else None
        status_text = " ".join(cells).upper()
        points_key = "points" if "points" in index else "pts"
        points = float(cells[index[points_key]] or 0) if points_key in index and re.fullmatch(r"\d+(?:\.\d+)?", cells[index[points_key]]) else 0
        team = cells[index["team"]]
        output.append({
            "series": series, "name": driver["name"], "team": team, "event": event,
            "session": session, "sequence": sequence, "laps": _integer(cells[index["laps"]]),
            "start": 0 if "DNS" in status_text else 1, "position": position, "points": points,
            "win": int(position == 1), "podium": int(position is not None and position <= 3),
            "dnf": int("DNF" in status_text or "DSQ" in status_text), "status": position_text,
            "sourceUrl": url,
        })
    return output


def parse_f2_pdf(
    content: bytes, *, event: str, session: str, url: str, roster: list[dict[str, Any]], sequence: int,
) -> list[dict[str, Any]]:
    with pdfplumber.open(io.BytesIO(content)) as document:
        text = "\n".join(page.extract_text() or "" for page in document.pages)
    lines = text.splitlines()
    start_index = next((i for i, line in enumerate(lines) if line.startswith("NO DRIVER") and "LAPS" in line), None)
    if start_index is None:
        raise ValueError(f"F2 classification table missing in {url}")
    output, classified = [], True
    for line in lines[start_index + 1:]:
        if line.startswith("NOT CLASSIFIED"):
            classified = False
            continue
        if line.startswith(("OVERALL FASTEST", "FASTEST LAP", "* PENALTIES", "Timekeeper")):
            break
        team = next((team for team in sorted(F2_TEAMS, key=len, reverse=True) if f" {team} " in f" {line} "), None)
        if not team:
            continue
        left, right = line.split(team, 1)
        left_tokens = left.replace(" *", "").split()
        if classified and len(left_tokens) >= 3 and left_tokens[0].isdigit() and left_tokens[1].isdigit():
            position, name_tokens = int(left_tokens[0]), left_tokens[2:]
        elif not classified and len(left_tokens) >= 2 and left_tokens[0].isdigit():
            position, name_tokens = None, left_tokens[1:]
        else:
            continue
        full_name = " ".join(token.title() if token.isupper() else token for token in name_tokens)
        driver = match_driver(full_name, roster)
        right_tokens = right.strip().split()
        laps = int(right_tokens[0]) if right_tokens and right_tokens[0].isdigit() else 0
        upper = line.upper()
        output.append({
            "series": "Formula 2", "name": driver["name"], "team": team, "event": event,
            "session": session, "sequence": sequence, "laps": laps, "start": 0 if "DNS" in upper else 1,
            "position": position, "points": 0, "win": int(position == 1),
            "podium": int(position is not None and position <= 3),
            "dnf": int("DNF" in upper or "DSQ" in upper), "status": "DNF" if "DNF" in upper else str(position or "NC"),
            "sourceUrl": url,
        })
    return output


def parse_f1academy_html(
    html: str, *, event: str, url: str, roster: list[dict[str, Any]], sequence: int,
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    output = []
    race_tables = []
    for table in soup.select("table"):
        heading = table.find_previous(["h2", "h3"])
        label = heading.get_text(" ", strip=True) if heading else ""
        match = re.search(r"Race\s+(\d+)\s+Results", label, re.I)
        if match and "LAPS" in table.select_one("tr").get_text(" ", strip=True).upper():
            race_tables.append((int(match.group(1)), table))
    for race_number, table in race_tables:
        for tr in table.select("tr")[1:]:
            cells = tr.select("th,td")
            if len(cells) < 3:
                continue
            position_text = cells[0].get_text(" ", strip=True)
            wrapper = cells[1]
            short = wrapper.select_one(".visible-desktop-up")
            team_node = wrapper.select_one(".team-name")
            if not short or not team_node:
                continue
            driver = match_driver(short.get_text(" ", strip=True), roster)
            position = int(position_text) if position_text.isdigit() else None
            status = " ".join(cell.get_text(" ", strip=True) for cell in cells).upper()
            output.append({
                "series": "F1 Academy", "name": driver["name"], "team": team_node.get_text(" ", strip=True),
                "event": event, "session": f"Race {race_number}", "sequence": sequence * 10 + race_number,
                "laps": _integer(cells[2].get_text(" ", strip=True)), "start": 0 if "DNS" in status else 1,
                "position": position, "points": 0, "win": int(position == 1),
                "podium": int(position is not None and position <= 3),
                "dnf": int("DNF" in status or "DSQ" in status), "status": position_text, "sourceUrl": url,
            })
    return output


def parse_f1_json(payload: dict[str, Any], roster: list[dict[str, Any]], *, sprint: bool) -> list[dict[str, Any]]:
    races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    output = []
    for race in races:
        result_key = "SprintResults" if sprint else "Results"
        session = "Sprint" if sprint else "Grand Prix"
        for item in race.get(result_key, []):
            driver_data = item["Driver"]
            name = f"{driver_data['givenName']} {driver_data['familyName']}"
            driver = match_driver(name, roster)
            position_text = item.get("positionText") or item.get("position") or ""
            position = int(item["position"]) if str(item.get("position", "")).isdigit() else None
            status = str(item.get("status") or position_text)
            output.append({
                "series": "Formula 1", "name": driver["name"], "team": item["Constructor"]["name"],
                "event": race["raceName"], "session": session,
                "sequence": int(race["round"]) * 10 + int(sprint), "laps": int(item.get("laps") or 0),
                "start": 0 if status.upper() in {"DNS", "DID NOT START"} else 1,
                "position": position, "points": float(item.get("points") or 0),
                "win": int(position == 1), "podium": int(position is not None and position <= 3),
                "dnf": int(status not in {"Finished"} and not status.startswith("+")),
                "status": status, "sourceUrl": race.get("url") or F1_RACE_URL,
            })
    return output


def aggregate_results(results: list[dict[str, Any]], rosters: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    roster_by_key = {(series, row["name"]): row for series, rows in rosters.items() for row in rows}
    players: dict[str, dict[str, Any]] = {}
    splits: dict[tuple[str, str, str], dict[str, Any]] = {}
    series_seen: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        key = normalize(result["name"])
        roster = roster_by_key[(result["series"], result["name"])]
        player = players.setdefault(key, {
            "playerId": key, "name": result["name"], "rosters": [], "raceLog": [],
        })
        if not any(row["series"] == roster["series"] for row in player["rosters"]):
            player["rosters"].append(roster)
        split_key = (key, result["series"], result["team"])
        display_team = f"{SERIES_CODES[result['series']]} · {result['team']}"
        split = splits.setdefault(split_key, {
            "team": display_team, "teamCode": SERIES_CODES[result["series"]], "constructor": result["team"],
            "conference": result["series"], "games": 0, "minutes": 0, "starts": 0, "laps": 0,
            "wins": 0, "podiums": 0, "dnfs": 0, "points": 0,
        })
        split["games"] += result["start"]
        split["starts"] += result["start"]
        split["minutes"] += result["laps"]
        split["laps"] += result["laps"]
        for field in ("wins", "podiums", "dnfs", "points"):
            source = {"wins": "win", "podiums": "podium", "dnfs": "dnf", "points": "points"}[field]
            split[field] += result[source]
        series_seen[(key, result["series"])].append(split)
        player["raceLog"].append({
            "series": result["series"], "event": result["event"], "session": result["session"],
            "position": result["position"], "status": result["status"], "laps": result["laps"],
            "team": result["team"], "sequence": result["sequence"],
        })
    # Championship points are canonical. Allocate any gap (notably F1 Academy,
    # whose result tables omit points) to the driver's main team in that series.
    for (series, name), roster in roster_by_key.items():
        key = normalize(name)
        candidates = series_seen.get((key, series), [])
        if not candidates:
            continue
        unique = {id(split): split for split in candidates}.values()
        current = sum(split["points"] for split in unique)
        primary = max(unique, key=lambda split: (split["starts"], split["laps"]))
        primary["points"] += roster["points"] - current
    for (key, _series, _team), split in splits.items():
        players[key].setdefault("teamSplits", []).append(split)
    output = []
    for player in players.values():
        player["teamSplits"].sort(key=lambda split: (-split["minutes"], split["team"]))
        for field in ("games", "minutes", "starts", "laps", "wins", "podiums", "dnfs", "points"):
            player[field] = sum(split[field] for split in player["teamSplits"])
        primary = player["teamSplits"][0]
        player.update({
            "team": primary["team"], "teamCode": primary["teamCode"],
            "teams": [split["team"] for split in player["teamSplits"]], "conference": primary["conference"],
            "series": sorted({split["conference"] for split in player["teamSplits"]}, key=SERIES.index),
            "gender": "Women" if all(split["conference"] == "F1 Academy" for split in player["teamSplits"]) else "Open",
            "position": " · ".join(sorted({split["conference"] for split in player["teamSplits"]}, key=SERIES.index)) + " driver",
        })
        primary_roster = sorted(player["rosters"], key=lambda row: SERIES.index(row["series"]))[0]
        player["representedCountry"] = primary_roster.get("representedCountry")
        player["nationality"] = primary_roster.get("representedCountry")
        player["wikipediaTitle"] = primary_roster.get("wikipediaTitle")
        player["wikipediaUrl"] = primary_roster.get("wikipediaUrl")
        player["raceLog"].sort(key=lambda row: row["sequence"], reverse=True)
        output.append(player)
    return sorted(output, key=lambda row: row["name"])


def _claim_ids(entity: dict[str, Any], property_id: str) -> set[str]:
    output = set()
    for claim in entity.get("claims", {}).get(property_id, []):
        value = (claim.get("mainsnak", {}).get("datavalue") or {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            output.add(value["id"])
    return output


def fetch_birthplaces(
    players: list[dict[str, Any]], cache_path: Path = DEFAULT_WIKIDATA_CACHE, *, force: bool = False,
) -> dict[str, dict[str, Any]]:
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.08, retries=3, timeout=120)
    titles = [player["wikipediaTitle"] or player["name"] for player in players]
    title_qids = _fetch_title_qids(client, titles, batch_size=40, force=force)
    people = _fetch_entities(
        client, [qid for qid in title_qids.values() if qid], "formula_person_batches",
        batch_size=30, force=force, languages="en|fr|es|pt|de|it|nl",
    )
    selected = {}
    for player in players:
        title = player["wikipediaTitle"] or player["name"]
        qid = title_qids.get(title)
        entity = people.get(qid, {})
        if qid and claim_entity(entity, "P31") == "Q5":
            selected[player["playerId"]] = qid
    place_by_player = {key: claim_entity(people.get(qid, {}), "P19") for key, qid in selected.items()}
    places = _fetch_entities(client, [qid for qid in place_by_player.values() if qid], "formula_place_batches", batch_size=30, force=force)
    parents = _fetch_entities(
        client, [qid for entity in places.values() if (qid := claim_entity(entity, "P131"))],
        "formula_parent_batches", batch_size=30, force=force,
    )
    locations = {**parents, **places}
    countries = _fetch_entities(
        client, [qid for entity in locations.values() if (qid := claim_entity(entity, "P17"))],
        "formula_country_batches", batch_size=30, force=force,
    )
    output: dict[str, dict[str, Any]] = {"_meta": {"schema_version": 1, "source": "Wikidata exact linked identities"}}
    for key, person_qid in selected.items():
        place_qid = place_by_player.get(key)
        place = places.get(place_qid, {})
        output[key] = {"wikidata_qid": person_qid, "dob": claim_date(people.get(person_qid, {}))}
        if _claim_ids(place, "P31") & COUNTRY_PLACE_TYPES and place_qid not in CITY_STATE_EXCEPTIONS:
            continue
        parent = parents.get(claim_entity(place, "P131"), {})
        coordinate_entity = place if claim_coordinates(place) != (None, None) else parent
        lat, lon = claim_coordinates(coordinate_entity)
        country_qid = claim_entity(place, "P17") or claim_entity(parent, "P17")
        country = entity_label(countries.get(country_qid, {}))
        if lat is None or lon is None or not country:
            continue
        output[key].update({
            "birth_place_qid": place_qid, "place": entity_label(place), "country": country,
            "lat": lat, "lon": lon, "resolution_source": "Wikidata exact linked driver identity",
        })
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
    players: list[dict[str, Any]], places: dict[str, dict[str, Any]], source_meta: dict[str, Any],
    *, generated_at: str | None = None,
) -> dict[str, Any]:
    records, unresolved = [], []
    for player in players:
        place = places.get(player["playerId"], {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        dob = place.get("dob")
        record = {
            "id": f"formula:{player['playerId']}", "sourcePlayerId": player["playerId"], **player,
            "year": SEASON, "dob": dob, "age": age_on(dob),
            "place": place.get("place") if mapped else None, "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None, "lon": place.get("lon") if mapped else None,
            "mapped": mapped, "status": "verified birthplace" if mapped else "birthplace or coordinates unresolved",
            "locationType": "birthplace" if mapped else None, "wikidataQid": place.get("wikidata_qid"),
            "birthPlaceQid": place.get("birth_place_qid"), "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        record.pop("rosters", None)
        records.append(record)
        if not mapped:
            unresolved.append({"name": record["name"], "series": record["series"], "status": record["status"]})
    mapped_records = [row for row in records if row["mapped"]]
    laps = sum(row["laps"] for row in records)
    mapped_laps = sum(row["laps"] for row in mapped_records)
    teams = sorted({split["team"] for row in records for split in row["teamSplits"]}, key=lambda team: (SERIES.index(next(s for s, code in SERIES_CODES.items() if team.startswith(code + " ·"))), team))
    return {
        "meta": {
            "title": "Formula Talent Geography", "sport": "formula",
            "scope": "Completed 2025 Formula 1, Formula 2, Formula 3 and F1 Academy championship races",
            "season": "2025 season", "year": SEASON, "teams": teams, "conferences": list(SERIES),
            "comparison_groups": list(SERIES),
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "classification_source_name": "FIA and F1 Academy official race classifications",
            "classification_source_urls": [F1_RACE_URL, F3_ARCHIVE_URL, "https://www.f1academy.com/Racing-Series/Calendar?seasonid=3"],
            "roster_source_name": "2025 championship tables", "roster_source_urls": ROSTER_URLS,
            "birthplace_source_name": "Wikidata", "birthplace_source_url": "https://www.wikidata.org/", **source_meta,
        },
        "summary": {
            "teams": len(teams), "races": sum(source_meta["races_by_series"].values()),
            "players": len(records), "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "laps": laps, "mapped_laps": mapped_laps,
            "lap_coverage_pct": round(mapped_laps / laps * 100, 1) if laps else 0,
            "starts": sum(row["starts"] for row in records),
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped_records}),
            "birth_countries": len({row["country"] for row in mapped_records}), "unresolved_players": len(unresolved),
        },
        "records": records, "unresolved": unresolved,
    }


def fetch_all_results(
    cache_dir: Path, rosters: dict[str, list[dict[str, Any]]], *, workers: int = 8, force: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    timestamps = []
    archive_specs = []
    content, timestamp = _read_input(cache_dir / "f3_archive.html", F3_ARCHIVE_URL, force=force)
    timestamps.append(timestamp)
    archive_specs.extend(discover_archive_links(content.decode("utf-8"), F3_ARCHIVE_URL, "Formula 3"))
    f1_payloads: list[tuple[bytes, bool]] = []
    for stem, base_url, offsets, sprint in (
        ("f1_races", F1_RACE_URL, range(0, 500, 100), False),
        ("f1_sprints", F1_SPRINT_URL, range(0, 200, 100), True),
    ):
        for offset in offsets:
            url = f"{base_url}?limit=100&offset={offset}"
            content, retrieved_at = _read_input(cache_dir / f"{stem}_{offset}.json", url, force=force)
            f1_payloads.append((content, sprint))
            timestamps.append(retrieved_at)
    f2_specs = []
    for event, slug, session in F2_HTML_SESSIONS:
        path = session.casefold().replace(" ", "-") + "-classification"
        f2_specs.append({
            "series": "Formula 2", "event": event, "session": session,
            "url": f"https://www.fia.com/events/formula-2-championship/season-2025/{slug}/{path}",
        })

    def fetch_html(spec: dict[str, str], sequence: int) -> list[dict[str, Any]]:
        digest = hashlib.sha1(spec["url"].encode()).hexdigest()[:16]
        content, _ = _read_input(cache_dir / "classifications" / f"{digest}.html", spec["url"], force=force)
        return parse_fia_classification_html(
            content.decode("utf-8"), series=spec["series"], event=spec["event"], session=spec["session"],
            url=spec["url"], roster=rosters[spec["series"]], sequence=sequence,
        )

    results = []
    for content, sprint in f1_payloads:
        results.extend(parse_f1_json(json.loads(content), rosters["Formula 1"], sprint=sprint))
    specs = archive_specs + f2_specs
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(fetch_html, spec, index): spec for index, spec in enumerate(specs, start=1)}
        for index, future in enumerate(as_completed(futures), start=1):
            rows = future.result()
            if not rows:
                raise ValueError(f"No classification rows parsed from {futures[future]['url']}")
            results.extend(rows)
            if index % 15 == 0 or index == len(futures):
                print(f"  fetched {index}/{len(futures)} FIA classification pages", flush=True)
    for index, (event, session, filename) in enumerate(F2_PDF_SESSIONS, start=len(specs) + 1):
        url = FIA_DOCUMENT_ROOT + filename
        content, _ = _read_input(cache_dir / "classifications" / filename, url, force=force)
        results.extend(parse_f2_pdf(content, event=event, session=session, url=url, roster=rosters["Formula 2"], sequence=index))
    for race_id, event in F1A_RESULTS.items():
        url = f"https://www.f1academy.com/Racing-Series/Results?raceid={race_id}"
        content, _ = _read_input(cache_dir / "f1academy" / f"race_{race_id}.html", url, force=force)
        results.extend(parse_f1academy_html(
            content.decode("utf-8"), event=event, url=url, roster=rosters["F1 Academy"], sequence=race_id,
        ))
    sessions = {(row["series"], row["event"], row["session"]) for row in results}
    races_by_series = {series: len({key for key in sessions if key[0] == series}) for series in SERIES}
    if races_by_series != EXPECTED_RACES:
        raise ValueError(f"Race reconciliation failed: expected {EXPECTED_RACES}, found {races_by_series}")
    return results, {"races_by_series": races_by_series, "archive_retrieved_at": max(timestamps)}


def run(
    output_path: Path = DEFAULT_OUTPUT, *, cache_dir: Path = DEFAULT_CACHE,
    wikidata_cache: Path = DEFAULT_WIKIDATA_CACHE, workers: int = 8,
    force: bool = False, force_birthplaces: bool = False,
) -> dict[str, Any]:
    rosters, roster_times = {}, {}
    for series, url in ROSTER_URLS.items():
        code = SERIES_CODES[series].casefold()
        content, timestamp = _read_input(cache_dir / f"{code}_roster.html", url, force=force)
        rosters[series] = parse_roster_html(content.decode("utf-8"), series)
        roster_times[series] = timestamp
    results, source_meta = fetch_all_results(cache_dir, rosters, workers=workers, force=force)
    players = aggregate_results(results, rosters)
    if len({row["playerId"] for row in players}) != len(players):
        raise ValueError("Formula driver identifiers are not unique")
    if sum(row["starts"] for row in players) != sum(row["start"] for row in results):
        raise ValueError("Driver starts do not reconcile to classification rows")
    if sum(row["laps"] for row in players) != sum(row["laps"] for row in results):
        raise ValueError("Driver laps do not reconcile to classification rows")
    source_meta["roster_retrieved_at"] = roster_times
    payload = build_payload(players, fetch_birthplaces(players, wikidata_cache, force=force_birthplaces), source_meta)
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']} drivers from {payload['summary']['races']} races "
        f"with {payload['summary']['player_coverage_pct']}% driver / {payload['summary']['lap_coverage_pct']}% lap coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the completed 2025 Formula pathway talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--wikidata-cache", type=Path, default=DEFAULT_WIKIDATA_CACHE)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--force-birthplaces", action="store_true")
    args = parser.parse_args()
    run(
        args.output, cache_dir=args.cache_dir, wikidata_cache=args.wikidata_cache,
        workers=args.workers, force=args.force, force_birthplaces=args.force_birthplaces,
    )


if __name__ == "__main__":
    main()
