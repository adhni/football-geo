from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, unquote, urljoin, urlparse

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
EXPECTED_EVENTS = 42
EXPECTED_BOUTS = 520
EVENT_INDEX_URL = "https://en.wikipedia.org/wiki/2025_in_UFC"
COMPETITIONS_URL = "https://raw.githubusercontent.com/DanMcInerney/mma-ai/main/data/raw/ufcstats/competitions.csv"
INDIVIDUALS_URL = "https://raw.githubusercontent.com/DanMcInerney/mma-ai/main/data/raw/ufcstats/individuals.csv"
DEFAULT_CACHE = ROOT / "data" / "cache" / "ufc_2025"
DEFAULT_OUTPUT = ROOT / "docs" / "ufc" / "data" / "dashboard.json"
DEFAULT_WIKIDATA_CACHE = DEFAULT_CACHE / "birthplaces.json"
DEFAULT_OVERRIDES = ROOT / "data" / "ufc_birthplace_overrides.json"
COUNTRY_PLACE_TYPES = {"Q6256", "Q3624078"}
CITY_STATE_EXCEPTIONS = {"Q334"}


def _write_json(path: Path, value: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    kwargs = {"ensure_ascii": False, "indent": 2, "sort_keys": True} if pretty else {
        "ensure_ascii": False, "separators": (",", ":")
    }
    temporary.write_text(json.dumps(value, **kwargs), encoding="utf-8")
    temporary.replace(path)


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


def iso_date(value: object) -> str | None:
    text = str(value or "").strip()
    for pattern in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            pass
    return None


def age_on(dob: str | None) -> int | None:
    if not dob:
        return None
    try:
        born = date.fromisoformat(dob[:10])
    except ValueError:
        return None
    return SEASON_END.year - born.year - ((SEASON_END.month, SEASON_END.day) < (born.month, born.day))


def fighter_id(url: str | None, name: str) -> str:
    if url:
        value = str(url).rstrip("/").rsplit("/", 1)[-1]
        if re.fullmatch(r"[0-9a-f]{16}", value):
            return value
    return "wiki-" + hashlib.sha1(normalize(name).encode()).hexdigest()[:16]


def parse_event_index(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find(id="Past_events")
    table = heading.find_next("table") if heading else None
    events: list[dict[str, str]] = []
    if not table:
        return events
    for row in table.select("tr"):
        cells = row.find_all("td")
        if len(cells) < 6 or not cells[0].get_text(" ", strip=True).isdigit():
            continue
        link = cells[1].find("a", href=True)
        event_date = iso_date(cells[2].get_text(" ", strip=True))
        if not link or not event_date or not event_date.startswith(str(SEASON)):
            continue
        events.append({
            "name": cells[1].get_text(" ", strip=True),
            "date": event_date,
            "venue": cells[3].get_text(" ", strip=True),
            "city": cells[4].get_text(" ", strip=True),
            "country": cells[5].get_text(" ", strip=True),
            "url": urljoin(EVENT_INDEX_URL, link["href"]),
        })
    return events


def _event_type(name: str) -> str:
    if re.match(r"^UFC\s+\d", name):
        return "Numbered PPV"
    return "Fight Night"


def _outcomes(relation: str, method: str) -> tuple[str, str]:
    combined = f"{relation} {method}".casefold()
    if "no contest" in combined or relation.strip().casefold() in {"nc", "n/c"}:
        return "NC", "NC"
    if "draw" in combined or relation.strip().casefold() == "vs.":
        return "D", "D"
    return "W", "L"


def _clean_fighter_name(value: str) -> str:
    return re.sub(r"\s+\((?:c|ic)\)\s*$", "", value.strip(), flags=re.I)


def _template_bout_notes(table: Any) -> list[str]:
    try:
        parts = json.loads(table.get("data-mw") or "{}").get("parts", [])
    except (TypeError, json.JSONDecodeError):
        return []
    notes = []
    for part in parts:
        template = part.get("template") if isinstance(part, dict) else None
        if not template or "MMAevent bout" not in template.get("target", {}).get("wt", ""):
            continue
        notes.append(template.get("params", {}).get("8", {}).get("wt", "").strip())
    return notes


def parse_event_results(html: str, event: dict[str, str]) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find(id="Results")
    table = heading.find_next("table") if heading else None
    output: list[dict[str, Any]] = []
    if not table:
        return output
    template_notes = iter(_template_bout_notes(table))
    for row in table.select("tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 7:
            continue
        division = cells[0].get_text(" ", strip=True)
        first_raw = cells[1].get_text(" ", strip=True)
        first = _clean_fighter_name(first_raw)
        relation = cells[2].get_text(" ", strip=True)
        second_raw = cells[3].get_text(" ", strip=True)
        second = _clean_fighter_name(second_raw)
        method = cells[4].get_text(" ", strip=True)
        if not division or not first or not second or relation.casefold() not in {"def.", "vs.", "nc", "n/c"}:
            continue
        rendered_notes = cells[7].get_text(" ", strip=True) if len(cells) > 7 else ""
        notes = next(template_notes, "") or rendered_notes
        first_link = cells[1].find("a", href=True)
        second_link = cells[3].find("a", href=True)
        first_result, second_result = _outcomes(relation, method)
        output.append({
            "event": event["name"], "eventDate": event["date"], "eventUrl": event["url"],
            "eventType": _event_type(event["name"]), "eventLocation": ", ".join(
                part for part in (event.get("city"), event.get("country")) if part
            ),
            "division": division, "gender": "Women" if division.startswith("Women's") else "Men",
            "fighter1": first, "fighter2": second,
            "fighter1WikiUrl": urljoin(event["url"], first_link["href"]) if first_link else None,
            "fighter2WikiUrl": urljoin(event["url"], second_link["href"]) if second_link else None,
            "fighter1Result": first_result, "fighter2Result": second_result,
            "method": method, "round": _integer(cells[5].get_text(" ", strip=True)),
            "time": cells[6].get_text(" ", strip=True),
            "titleBout": "championship" in notes.casefold() or "(c)" in first_raw.casefold() or "(c)" in second_raw.casefold(),
            "notes": notes,
        })
    return output


def _integer(value: object) -> int:
    try:
        return int(float(str(value or "0").strip()))
    except ValueError:
        return 0


def _landed_attempted(value: object) -> tuple[int, int]:
    match = re.match(r"\s*(\d+)\s+of\s+(\d+)", str(value or ""), re.I)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def parse_detailed_stats(text: str) -> list[dict[str, Any]]:
    rows = []
    for source in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        event_date = iso_date(source.get("event_date"))
        if not event_date or not event_date.startswith(str(SEASON)):
            continue
        stats: dict[str, dict[str, int]] = {}
        for side in ("p1", "p2"):
            totals = {
                "knockdowns": 0, "significantStrikesLanded": 0, "significantStrikesAttempted": 0,
                "totalStrikesLanded": 0, "totalStrikesAttempted": 0, "takedownsLanded": 0,
                "takedownsAttempted": 0, "submissionAttempts": 0,
            }
            for round_number in range(1, 6):
                totals["knockdowns"] += _integer(source.get(f"{side}_rd{round_number}_KD"))
                for source_name, landed_key, attempted_key in (
                    ("Sig_str", "significantStrikesLanded", "significantStrikesAttempted"),
                    ("Total_str", "totalStrikesLanded", "totalStrikesAttempted"),
                    ("Td", "takedownsLanded", "takedownsAttempted"),
                ):
                    landed, attempted = _landed_attempted(source.get(f"{side}_rd{round_number}_{source_name}"))
                    totals[landed_key] += landed
                    totals[attempted_key] += attempted
                totals["submissionAttempts"] += _integer(source.get(f"{side}_rd{round_number}_Sub_att"))
            stats[side] = totals
        rows.append({
            "eventDate": event_date, "eventUrl": source.get("event_url"),
            "fighter1": source.get("player1", "").strip(), "fighter2": source.get("player2", "").strip(),
            "fighter1Url": source.get("player1_url"), "fighter2Url": source.get("player2_url"),
            "stats1": stats["p1"], "stats2": stats["p2"],
        })
    return rows


def parse_individuals(text: str) -> dict[str, dict[str, Any]]:
    output = {}
    for source in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        url = source.get("url")
        identifier = fighter_id(url, source.get("name", ""))
        output[identifier] = {
            "name": source.get("name", "").strip(), "ufcStatsUrl": url,
            "dob": iso_date(source.get("dob")), "nickname": source.get("nickname") or None,
            "height": source.get("height") or None, "reach": source.get("reach") or None,
            "stance": source.get("stance") or None,
        }
    return output


def _fight_key(first: str, second: str) -> tuple[str, str]:
    return tuple(sorted((normalize(first), normalize(second))))


def _pair_similarity(fight: dict[str, Any], detail: dict[str, Any]) -> float:
    first, second = normalize(fight["fighter1"]), normalize(fight["fighter2"])
    detail_first, detail_second = normalize(detail["fighter1"]), normalize(detail["fighter2"])
    ratio = lambda left, right: SequenceMatcher(None, left, right).ratio()
    return max(
        (ratio(first, detail_first) + ratio(second, detail_second)) / 2,
        (ratio(first, detail_second) + ratio(second, detail_first)) / 2,
    )


def merge_details(
    fights: list[dict[str, Any]], detailed: list[dict[str, Any]], individuals: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    details_by_key: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in detailed:
        details_by_key[_fight_key(row["fighter1"], row["fighter2"])].append(row)
    used_details: set[int] = set()
    ids_by_name: defaultdict[str, set[str]] = defaultdict(set)
    for identifier, profile in individuals.items():
        ids_by_name[normalize(profile["name"])].add(identifier)
    for fight in fights:
        candidates = [row for row in details_by_key.get(_fight_key(fight["fighter1"], fight["fighter2"]), []) if id(row) not in used_details]
        if not candidates:
            fight_names = {normalize(fight["fighter1"]), normalize(fight["fighter2"])}
            candidates = [
                row for row in detailed if id(row) not in used_details
                and fight_names & {normalize(row["fighter1"]), normalize(row["fighter2"])}
                and abs((date.fromisoformat(row["eventDate"]) - date.fromisoformat(fight["eventDate"])).days) <= 2
            ]
        if not candidates:
            same_card = [
                row for row in detailed if id(row) not in used_details
                and abs((date.fromisoformat(row["eventDate"]) - date.fromisoformat(fight["eventDate"])).days) <= 2
            ]
            ranked = sorted(same_card, key=lambda row: _pair_similarity(fight, row), reverse=True)
            if ranked and _pair_similarity(fight, ranked[0]) >= 0.55:
                candidates = [ranked[0]]
        if candidates:
            candidates.sort(key=lambda row: abs(
                (date.fromisoformat(row["eventDate"]) - date.fromisoformat(fight["eventDate"])).days
            ))
        detail = candidates[0] if candidates else None
        if detail:
            used_details.add(id(detail))
        fight["detailedStatsAvailable"] = bool(detail)
        for index in (1, 2):
            name = fight[f"fighter{index}"]
            identifier = None
            stats = {}
            if detail:
                opponent = fight[f"fighter{2 if index == 1 else 1}"]
                if normalize(detail["fighter1"]) == normalize(name) or normalize(detail["fighter2"]) == normalize(opponent):
                    detail_index = 1
                else:
                    detail_index = 2
                identifier = fighter_id(detail[f"fighter{detail_index}Url"], name)
                stats = detail[f"stats{detail_index}"]
            if not identifier:
                candidates = ids_by_name.get(normalize(name), set())
                identifier = next(iter(candidates)) if len(candidates) == 1 else fighter_id(None, name)
            fight[f"fighter{index}Id"] = identifier
            fight[f"stats{index}"] = stats
    return fights


def infer_fight_genders(fights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve catchweight gender from each fighter's unambiguous 2025 bouts."""
    known: defaultdict[str, set[str]] = defaultdict(set)
    for fight in fights:
        division = fight["division"]
        if "Catchweight" in division:
            continue
        gender = "Women" if division.startswith("Women's") else "Men"
        known[fight["fighter1Id"]].add(gender)
        known[fight["fighter2Id"]].add(gender)
    for fight in fights:
        if "Catchweight" not in fight["division"]:
            continue
        candidates = known[fight["fighter1Id"]] | known[fight["fighter2Id"]]
        # UFC result cards do not prefix every women's catchweight row. A known
        # women's participant is decisive; otherwise the men's cohort is the
        # documented default for an unqualified UFC weight class.
        fight["gender"] = "Women" if candidates == {"Women"} else "Men"
        if fight["gender"] == "Women" and not fight["division"].startswith("Women's"):
            fight["division"] = "Women's " + fight["division"]
    return fights


STAT_FIELDS = (
    "bouts", "wins", "losses", "draws", "noContests", "koTkoWins", "submissionWins",
    "decisionWins", "knockdowns", "significantStrikesLanded", "significantStrikesAttempted",
    "totalStrikesLanded", "totalStrikesAttempted", "takedownsLanded", "takedownsAttempted",
    "submissionAttempts", "detailedStatsBouts", "titleBouts",
)


def _empty_stats() -> dict[str, int]:
    return {field: 0 for field in STAT_FIELDS}


def aggregate_fights(fights: Iterable[dict[str, Any]], individuals: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    players: dict[str, dict[str, Any]] = {}
    splits: dict[tuple[str, str], dict[str, Any]] = {}
    for fight in fights:
        for index in (1, 2):
            identifier = fight[f"fighter{index}Id"]
            name = fight[f"fighter{index}"]
            result = fight[f"fighter{index}Result"]
            profile = individuals.get(identifier, {})
            player = players.setdefault(identifier, {
                "playerId": identifier, "name": profile.get("name") or name,
                "ufcStatsUrl": profile.get("ufcStatsUrl"), "dob": profile.get("dob"),
                "nickname": profile.get("nickname"), "height": profile.get("height"),
                "reach": profile.get("reach"), "stance": profile.get("stance"),
                "wikipediaUrl": fight.get(f"fighter{index}WikiUrl"),
                "gender": fight["gender"], "fightLog": [],
            })
            player["wikipediaUrl"] = player.get("wikipediaUrl") or fight.get(f"fighter{index}WikiUrl")
            if player["gender"] != fight["gender"]:
                raise ValueError(f"Fighter {identifier} appears in both gender cohorts")
            key = (identifier, fight["division"])
            split = splits.setdefault(key, {
                "team": fight["division"], "teamCode": re.sub(r"[^A-Z]", "", fight["division"].upper())[:5],
                "conference": fight["gender"], **_empty_stats(),
            })
            split["bouts"] += 1
            split[{"W": "wins", "L": "losses", "D": "draws", "NC": "noContests"}[result]] += 1
            split["titleBouts"] += int(fight["titleBout"])
            if result == "W":
                method = fight["method"].casefold()
                if "ko" in method:
                    split["koTkoWins"] += 1
                elif "submission" in method:
                    split["submissionWins"] += 1
                elif "decision" in method:
                    split["decisionWins"] += 1
            if fight["detailedStatsAvailable"]:
                split["detailedStatsBouts"] += 1
                for field, value in fight[f"stats{index}"].items():
                    split[field] += value
            opponent_index = 2 if index == 1 else 1
            player["fightLog"].append({
                "event": fight["event"], "date": fight["eventDate"], "opponent": fight[f"fighter{opponent_index}"],
                "division": fight["division"], "result": result, "method": fight["method"],
                "round": fight["round"], "time": fight["time"], "eventType": fight["eventType"],
                "titleBout": fight["titleBout"], "detailedStatsAvailable": fight["detailedStatsAvailable"],
            })
    for (identifier, _), split in splits.items():
        players[identifier].setdefault("teamSplits", []).append(split)
    output = []
    for player in players.values():
        player["teamSplits"].sort(key=lambda row: (-row["bouts"], row["team"]))
        for field in STAT_FIELDS:
            player[field] = sum(row[field] for row in player["teamSplits"])
        player["team"] = player["teamSplits"][0]["team"]
        player["teamCode"] = player["teamSplits"][0]["teamCode"]
        player["teams"] = [row["team"] for row in player["teamSplits"]]
        player["conference"] = player["gender"]
        player["fightLog"].sort(key=lambda row: row["date"], reverse=True)
        output.append(player)
    return sorted(output, key=lambda row: (row["gender"], row["name"]))


def _claim_ids(entity: dict[str, Any], property_id: str) -> set[str]:
    output = set()
    for claim in entity.get("claims", {}).get(property_id, []):
        value = (claim.get("mainsnak", {}).get("datavalue") or {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            output.add(value["id"])
    return output


def wikipedia_birthplace(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    birthplace = soup.select_one(".birthplace")
    link = birthplace.select_one("a[title], a[href*='/wiki/']") if birthplace else None
    bday = soup.select_one(".bday")
    title = link.get("title") if link else None
    if not title and link and "/wiki/" in link.get("href", ""):
        title = unquote(link["href"].split("/wiki/", 1)[1]).replace("_", " ")
    return title, bday.get_text(strip=True) if bday else None


def ufc_hometown(html: str, expected_name: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one(".hero-profile__name")
    if not heading or normalize(heading.get_text(" ", strip=True)) != normalize(expected_name):
        return None
    for field in soup.select(".c-bio__field"):
        label = field.select_one(".c-bio__label")
        value = field.select_one(".c-bio__text")
        if label and value and label.get_text(" ", strip=True).casefold() == "hometown":
            return value.get_text(" ", strip=True) or None
    return None


def ufc_profile_url(name: str) -> str:
    slug = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return f"https://www.ufc.com/athlete/{slug}"


def fetch_birthplaces(
    players: list[dict[str, Any]], cache_path: Path = DEFAULT_WIKIDATA_CACHE, *, force: bool = False,
) -> dict[str, dict[str, Any]]:
    if cache_path.exists() and not force:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("_meta", {}).get("schema_version", 0) >= 4:
            return cached
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.08, retries=3, timeout=120)
    titles_by_id = {
        row["playerId"]: [row["name"], f"{row['name']} (fighter)", f"{row['name']} (mixed martial artist)"]
        for row in players
    }
    title_qids = _fetch_title_qids(
        client, [title for titles in titles_by_id.values() for title in titles], batch_size=40, force=force,
    )
    people = _fetch_entities(
        client, [qid for qid in title_qids.values() if qid], "ufc_person_batches", batch_size=30, force=force,
    )
    selected: dict[str, str] = {}
    for player in players:
        qids = {title_qids.get(title) for title in titles_by_id[player["playerId"]]} - {None}
        matches = set()
        for qid in qids:
            entity = people.get(qid, {})
            same_name = normalize(entity_label(entity)) == normalize(player["name"])
            entity_dob = claim_date(entity)
            dob_matches = bool(player.get("dob") and entity_dob == player["dob"])
            direct_title = title_qids.get(player["name"]) == qid
            if same_name and (dob_matches or (not player.get("dob") and direct_title)):
                matches.add(qid)
        if len(matches) == 1:
            selected[player["playerId"]] = matches.pop()
    place_by_player = {identifier: claim_entity(people.get(qid, {}), "P19") for identifier, qid in selected.items()}
    places = _fetch_entities(client, [qid for qid in place_by_player.values() if qid], "ufc_place_batches", batch_size=30, force=force)
    parent_qids = [qid for entity in places.values() if (qid := claim_entity(entity, "P131"))]
    parents = _fetch_entities(client, parent_qids, "ufc_parent_batches", batch_size=30, force=force)
    grandparent_qids = [qid for entity in parents.values() if (qid := claim_entity(entity, "P131"))]
    grandparents = _fetch_entities(client, grandparent_qids, "ufc_grandparent_batches", batch_size=30, force=force)
    locations = {**grandparents, **parents, **places}
    country_qids = [qid for entity in locations.values() if (qid := claim_entity(entity, "P17"))]
    countries = _fetch_entities(client, country_qids, "ufc_country_batches", batch_size=30, force=force)
    output: dict[str, dict[str, Any]] = {"_meta": {"schema_version": 4, "source": "Wikidata, English Wikipedia, and official UFC fighter origins"}}
    for identifier, person_qid in selected.items():
        place_qid = place_by_player.get(identifier)
        place = places.get(place_qid, {})
        output[identifier] = {"wikidata_qid": person_qid, "dob": claim_date(people.get(person_qid, {}))}
        if _claim_ids(place, "P31") & COUNTRY_PLACE_TYPES and place_qid not in CITY_STATE_EXCEPTIONS:
            continue
        coordinate_entity = place
        country_qid = claim_entity(place, "P17")
        cursor = claim_entity(place, "P131")
        for _ in range(2):
            parent = locations.get(cursor, {})
            if claim_coordinates(coordinate_entity) == (None, None) and parent:
                coordinate_entity = parent
            country_qid = country_qid or claim_entity(parent, "P17")
            cursor = claim_entity(parent, "P131")
        lat, lon = claim_coordinates(coordinate_entity)
        country = entity_label(countries.get(country_qid, {}))
        if lat is None or lon is None or not country:
            continue
        output[identifier].update({
            "birth_place_qid": place_qid, "place": entity_label(place), "country": country,
            "lat": lat, "lon": lon, "resolution_source": "Wikidata identity matched by exact name and DOB",
        })

    # Event result cards link directly to the fighter's biography, providing a
    # stronger identity connection than name search alone. Accept only an
    # explicit infobox birthplace link; hometown and fighting base are ignored.
    fallback_profiles = []
    for row in players:
        if output.get(row["playerId"], {}).get("lat"):
            continue
        source_url = row.get("wikipediaUrl")
        if not source_url and row["playerId"] in selected:
            person_qid = selected[row["playerId"]]
            page_title = next((title for title in titles_by_id[row["playerId"]] if title_qids.get(title) == person_qid), None)
            if page_title:
                source_url = f"https://en.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'), safe='()_,-.')}"
        if source_url:
            fallback_profiles.append({**row, "profileWikipediaUrl": source_url})

    def fetch_profile(row: dict[str, Any]) -> tuple[str, str | None, str | None, str]:
        source_url = row["profileWikipediaUrl"]
        title = unquote(urlparse(source_url).path.split("/wiki/", 1)[-1]).replace("_", " ")
        rest_url = f"https://en.wikipedia.org/w/rest.php/v1/page/{quote(title.replace(' ', '_'), safe='()_,-.')}/html?redirect=yes"
        digest = hashlib.sha1(source_url.encode()).hexdigest()[:16]
        try:
            content, _ = _read_input(DEFAULT_CACHE / "wikipedia_profiles" / f"{digest}.html", rest_url, force=force)
            place_title, dob = wikipedia_birthplace(content.decode("utf-8"))
            return row["playerId"], place_title, dob, source_url
        except (requests.RequestException, OSError, UnicodeDecodeError):
            return row["playerId"], None, None, source_url

    fallback_titles: dict[str, tuple[str, str | None, str]] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_profile, row) for row in fallback_profiles]
        for future in as_completed(futures):
            identifier, title, dob, source_url = future.result()
            if title:
                fallback_titles[identifier] = (title, dob, source_url)
    if fallback_titles:
        fallback_qids = _fetch_title_qids(
            client, [value[0] for value in fallback_titles.values()], batch_size=40, force=force,
        )
        fallback_places = _fetch_entities(
            client, [qid for qid in fallback_qids.values() if qid], "ufc_wikipedia_place_batches",
            batch_size=30, force=force,
        )
        fallback_parent_qids = [qid for entity in fallback_places.values() if (qid := claim_entity(entity, "P131"))]
        fallback_parents = _fetch_entities(
            client, fallback_parent_qids, "ufc_wikipedia_parent_batches", batch_size=30, force=force,
        )
        fallback_locations = {**fallback_parents, **fallback_places}
        fallback_country_qids = [qid for entity in fallback_locations.values() if (qid := claim_entity(entity, "P17"))]
        fallback_countries = _fetch_entities(
            client, fallback_country_qids, "ufc_wikipedia_country_batches", batch_size=30, force=force,
        )
        for identifier, (title, dob, source_url) in fallback_titles.items():
            place_qid = fallback_qids.get(title)
            place = fallback_places.get(place_qid, {})
            if _claim_ids(place, "P31") & COUNTRY_PLACE_TYPES and place_qid not in CITY_STATE_EXCEPTIONS:
                continue
            parent = fallback_parents.get(claim_entity(place, "P131"), {})
            coordinate_entity = place if claim_coordinates(place) != (None, None) else parent
            lat, lon = claim_coordinates(coordinate_entity)
            country_qid = claim_entity(place, "P17") or claim_entity(parent, "P17")
            country = entity_label(fallback_countries.get(country_qid, {}))
            if lat is None or lon is None or not country:
                continue
            output.setdefault(identifier, {}).update({
                "birth_place_qid": place_qid, "dob": dob or output.get(identifier, {}).get("dob"),
                "place": entity_label(place) or title, "country": country, "lat": lat, "lon": lon,
                "resolution_source": f"Event-linked English Wikipedia infobox; coordinates from Wikidata ({source_url})",
            })

    origin_candidates = [row for row in players if not output.get(row["playerId"], {}).get("lat")]

    def fetch_origin(row: dict[str, Any]) -> tuple[str, str | None, str]:
        profile_url = ufc_profile_url(row["name"])
        digest = hashlib.sha1(profile_url.encode()).hexdigest()[:16]
        try:
            content, _ = _read_input(DEFAULT_CACHE / "ufc_profiles" / f"{digest}.html", profile_url, force=False)
            return row["playerId"], ufc_hometown(content.decode("utf-8"), row["name"]), profile_url
        except (requests.RequestException, OSError, UnicodeDecodeError):
            return row["playerId"], None, profile_url

    origins: dict[str, tuple[str, str]] = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(fetch_origin, row) for row in origin_candidates]
        for future in as_completed(futures):
            identifier, hometown, profile_url = future.result()
            if hometown:
                origins[identifier] = (hometown, profile_url)
    if origins:
        origin_city = {identifier: value[0].split(",", 1)[0].strip() for identifier, value in origins.items()}
        origin_qids = _fetch_title_qids(client, list(origin_city.values()), batch_size=40, force=False)
        origin_places = _fetch_entities(
            client, [qid for qid in origin_qids.values() if qid], "ufc_origin_place_batches",
            batch_size=30, force=False,
        )
        origin_country_qids = [qid for entity in origin_places.values() if (qid := claim_entity(entity, "P17"))]
        origin_countries = _fetch_entities(
            client, origin_country_qids, "ufc_origin_country_batches", batch_size=30, force=False,
        )
        for identifier, (hometown, profile_url) in origins.items():
            city = origin_city[identifier]
            place_qid = origin_qids.get(city)
            place = origin_places.get(place_qid, {})
            lat, lon = claim_coordinates(place)
            if lat is None or lon is None:
                continue
            country = entity_label(origin_countries.get(claim_entity(place, "P17"), {}))
            country = country or (hometown.rsplit(",", 1)[-1].strip() if "," in hometown else "Country unavailable")
            output.setdefault(identifier, {}).update({
                "origin_place_qid": place_qid, "place": city, "country": country,
                "lat": lat, "lon": lon, "location_type": "fighter_origin",
                "resolution_source": f"Official UFC Hometown field; coordinates from Wikidata ({profile_url})",
            })
    _write_json(cache_path, output, pretty=True)
    return output


def build_payload(
    players: list[dict[str, Any]], places: dict[str, dict[str, Any]], source_meta: dict[str, Any],
    *, generated_at: str | None = None,
) -> dict[str, Any]:
    records, unresolved = [], []
    for player in players:
        place = places.get(player["playerId"], {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        dob = player.get("dob") or place.get("dob")
        location_type = place.get("location_type") or ("birthplace" if mapped else None)
        status = "verified birthplace" if mapped and location_type == "birthplace" else "official UFC fighter origin" if mapped else "birthplace or fighter origin unresolved"
        record = {
            "id": f"ufc:ufcstats:{player['playerId']}", **player, "year": SEASON,
            "position": player["team"], "dob": dob, "age": age_on(dob), "nationality": None,
            "representedCountry": None, "place": place.get("place") if mapped else None,
            "country": place.get("country") if mapped else None, "lat": place.get("lat") if mapped else None,
            "lon": place.get("lon") if mapped else None, "mapped": mapped, "status": status,
            "locationType": location_type, "wikidataQid": place.get("wikidata_qid"),
            "birthPlaceQid": place.get("birth_place_qid"),
            "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({
                "name": record["name"], "dob": dob, "ufcStatsUrl": record.get("ufcStatsUrl"),
                "divisions": record["teams"], "status": status,
            })
    records.sort(key=lambda row: (row["conference"], row["name"]))
    mapped_records = [row for row in records if row["mapped"]]
    birthplace_records = [row for row in mapped_records if row["locationType"] == "birthplace"]
    bouts = sum(row["bouts"] for row in records)
    mapped_bouts = sum(row["bouts"] for row in mapped_records)
    divisions = sorted({split["team"] for row in records for split in row["teamSplits"]})
    return {
        "meta": {
            "title": "UFC Talent Geography", "sport": "ufc", "scope": "All 42 UFC events in calendar-year 2025",
            "season": "2025 calendar year", "year": SEASON, "teams": divisions,
            "conferences": ["Men", "Women"], "comparison_groups": ["Men", "Women"],
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "results_source_name": "2025 in UFC event result cards", "results_source_url": EVENT_INDEX_URL,
            "stats_source_name": "UFCStats-derived fight statistics", "stats_source_url": COMPETITIONS_URL,
            "profile_source_name": "UFCStats fighter profiles", "profile_source_url": INDIVIDUALS_URL,
            "birthplace_source_name": "Wikidata", "birthplace_source_url": "https://www.wikidata.org/",
            **source_meta,
        },
        "summary": {
            "events": source_meta["events"], "fights": source_meta["fights"], "teams": len(divisions),
            "players": len(records), "mapped_players": len(mapped_records),
            "birthplace_mapped_players": len(birthplace_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "bouts": bouts, "mapped_bouts": mapped_bouts,
            "birthplace_mapped_bouts": sum(row["bouts"] for row in birthplace_records),
            "bout_coverage_pct": round(mapped_bouts / bouts * 100, 1) if bouts else 0,
            "detailed_fights": source_meta["detailed_fights"],
            "detailed_stat_coverage_pct": round(source_meta["detailed_fights"] / source_meta["fights"] * 100, 1),
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in birthplace_records}),
            "birth_countries": len({row["country"] for row in birthplace_records}),
            "unresolved_players": len(unresolved),
        },
        "records": records, "unresolved": unresolved,
    }


def _read_input(path: Path, url: str, *, force: bool) -> tuple[bytes, str]:
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    if path.exists() and not force:
        metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        timestamp = metadata.get("retrieved_at") or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        return path.read_bytes(), timestamp
    response = requests.get(url, timeout=180, headers={"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    response.raise_for_status()
    content = response.content
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    _write_json(meta_path, {
        "source_url": url, "retrieved_at": retrieved_at, "status_code": response.status_code,
        "sha256": hashlib.sha256(content).hexdigest(),
    }, pretty=True)
    return content, retrieved_at


def fetch_results(cache_dir: Path, *, workers: int = 8, force: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index_bytes, retrieved_at = _read_input(cache_dir / "2025_in_UFC.html", EVENT_INDEX_URL, force=force)
    events = parse_event_index(index_bytes.decode("utf-8"))
    if len(events) != EXPECTED_EVENTS:
        raise ValueError(f"Expected {EXPECTED_EVENTS} UFC events, found {len(events)}")

    def fetch_event(event: dict[str, str]) -> list[dict[str, Any]]:
        digest = hashlib.sha1(event["url"].encode()).hexdigest()[:16]
        content, _ = _read_input(cache_dir / "events" / f"{digest}.html", event["url"], force=force)
        return parse_event_results(content.decode("utf-8"), event)

    fights: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(fetch_event, event): event for event in events}
        for index, future in enumerate(as_completed(futures), start=1):
            event_fights = future.result()
            if not event_fights:
                raise ValueError(f"No completed fights parsed for {futures[future]['name']}")
            fights.extend(event_fights)
            if index % 10 == 0 or index == len(futures):
                print(f"  fetched {index}/{len(futures)} UFC event cards", flush=True)
    fights.sort(key=lambda row: (row["eventDate"], row["event"], row["fighter1"]))
    if len(fights) != EXPECTED_BOUTS:
        raise ValueError(f"Expected {EXPECTED_BOUTS} UFC bouts, found {len(fights)}")
    return fights, {"events": len(events), "fights": len(fights), "results_retrieved_at": retrieved_at}


def run(
    output_path: Path = DEFAULT_OUTPUT, *, competitions_input: Path | None = None,
    individuals_input: Path | None = None, results_input: Path | None = None,
    cache_dir: Path = DEFAULT_CACHE, wikidata_cache: Path = DEFAULT_WIKIDATA_CACHE,
    overrides_path: Path = DEFAULT_OVERRIDES, workers: int = 8, force: bool = False,
    force_birthplaces: bool = False,
) -> dict[str, Any]:
    competition_path = competitions_input or cache_dir / "competitions.csv"
    individual_path = individuals_input or cache_dir / "individuals.csv"
    competition_bytes, stats_at = _read_input(competition_path, COMPETITIONS_URL, force=force and competitions_input is None)
    individual_bytes, profiles_at = _read_input(individual_path, INDIVIDUALS_URL, force=force and individuals_input is None)
    if results_input:
        fights = json.loads(results_input.read_text(encoding="utf-8"))
        source_meta = {"events": len({row["eventUrl"] for row in fights}), "fights": len(fights), "results_retrieved_at": datetime.fromtimestamp(results_input.stat().st_mtime, timezone.utc).isoformat()}
    else:
        fights, source_meta = fetch_results(cache_dir, workers=workers, force=force)
    individuals = parse_individuals(individual_bytes.decode("utf-8-sig"))
    detailed = parse_detailed_stats(competition_bytes.decode("utf-8-sig"))
    merge_details(fights, detailed, individuals)
    infer_fight_genders(fights)
    detailed_fights = sum(row["detailedStatsAvailable"] for row in fights)
    source_meta.update({
        "detailed_fights": detailed_fights, "stats_retrieved_at": stats_at,
        "profiles_retrieved_at": profiles_at, "stats_sha256": hashlib.sha256(competition_bytes).hexdigest(),
        "profiles_sha256": hashlib.sha256(individual_bytes).hexdigest(),
    })
    players = aggregate_fights(fights, individuals)
    if source_meta["events"] != EXPECTED_EVENTS or source_meta["fights"] != EXPECTED_BOUTS:
        raise ValueError("UFC event/fight reconciliation failed")
    if sum(row["bouts"] for row in players) != EXPECTED_BOUTS * 2:
        raise ValueError("UFC fighter appearances do not reconcile to two per bout")
    if len({row["playerId"] for row in players}) != len(players):
        raise ValueError("UFC fighter identifiers are not unique")
    places = fetch_birthplaces(players, wikidata_cache, force=force_birthplaces)
    if overrides_path.exists():
        places.update(json.loads(overrides_path.read_text(encoding="utf-8")))
    payload = build_payload(players, places, source_meta)
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']} UFC fighters from {payload['summary']['fights']} fights "
        f"with {payload['summary']['player_coverage_pct']}% fighter / {payload['summary']['bout_coverage_pct']}% bout coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the complete 2025 UFC talent geography dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--competitions-input", type=Path)
    parser.add_argument("--individuals-input", type=Path)
    parser.add_argument("--results-input", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--wikidata-cache", type=Path, default=DEFAULT_WIKIDATA_CACHE)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--force-birthplaces", action="store_true")
    args = parser.parse_args()
    run(
        args.output, competitions_input=args.competitions_input, individuals_input=args.individuals_input,
        results_input=args.results_input, cache_dir=args.cache_dir, wikidata_cache=args.wikidata_cache,
        overrides_path=args.overrides, workers=args.workers, force=args.force,
        force_birthplaces=args.force_birthplaces,
    )


if __name__ == "__main__":
    main()
