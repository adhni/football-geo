from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

import pandas as pd
import requests

from src.ftg.build_nfl_site import _download_binary
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
STATS_URL = "https://github.com/jimmyday12/fitzroy_data/releases/download/data/afltables_player_stats.parquet"
WIKIDATA_URL = "https://query.wikidata.org/sparql"
ENWIKI_URL = "https://en.wikipedia.org/w/api.php"
DEFAULT_OUTPUT = ROOT / "docs" / "afl" / "data" / "dashboard.json"
DEFAULT_STATS_CACHE = ROOT / "data" / "cache" / "afl_afltables_player_stats.parquet"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "afl_wikidata_2025.json"

TEAM_NAMES = {
    "Adelaide": "Adelaide Crows",
    "Brisbane Lions": "Brisbane Lions",
    "Carlton": "Carlton",
    "Collingwood": "Collingwood",
    "Essendon": "Essendon",
    "Footscray": "Western Bulldogs",
    "Fremantle": "Fremantle",
    "Geelong": "Geelong Cats",
    "Gold Coast": "Gold Coast Suns",
    "GWS": "GWS Giants",
    "Hawthorn": "Hawthorn",
    "Melbourne": "Melbourne",
    "North Melbourne": "North Melbourne",
    "Port Adelaide": "Port Adelaide",
    "Richmond": "Richmond",
    "St Kilda": "St Kilda",
    "Sydney": "Sydney Swans",
    "West Coast": "West Coast Eagles",
}


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


def filter_home_and_away(stats: pd.DataFrame, season: int = SEASON) -> pd.DataFrame:
    required = {
        "Season", "Round", "Date", "ID", "Player", "Team", "DOB", "Disposals",
        "Goals", "Marks", "Tackles", "url",
    }
    if missing := required - set(stats.columns):
        raise ValueError(f"AFL snapshot is missing columns: {', '.join(sorted(missing))}")
    rows = stats[stats["Season"].eq(season)].copy()
    rows = rows[rows["Round"].astype(str).str.fullmatch(r"\d+")].copy()
    rows = rows[rows["ID"].notna() & rows["Player"].notna() & rows["Team"].notna()]
    unknown = sorted(set(rows["Team"].astype(str)) - set(TEAM_NAMES))
    if unknown:
        raise ValueError(f"AFL snapshot has unknown teams: {', '.join(unknown)}")
    if rows["Team"].nunique() != 18:
        raise ValueError(f"Expected 18 AFL clubs, found {rows['Team'].nunique()}")
    return rows


def _integer(value: object) -> int:
    return int(float(value)) if pd.notna(value) else 0


def _iso_dob(value: object) -> str | None:
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    return parsed.date().isoformat() if pd.notna(parsed) else None


def aggregate_afl_stats(stats: pd.DataFrame) -> list[dict[str, Any]]:
    rows = filter_home_and_away(stats)
    output: list[dict[str, Any]] = []
    for source_id, player_rows in rows.groupby("ID", sort=True):
        splits = []
        for source_team, team_rows in player_rows.groupby("Team", sort=True):
            splits.append({
                "team_code": str(source_team),
                "team": TEAM_NAMES[str(source_team)],
                "games": len(team_rows),
                "disposals": _integer(team_rows["Disposals"].fillna(0).sum()),
                "goals": _integer(team_rows["Goals"].fillna(0).sum()),
                "marks": _integer(team_rows["Marks"].fillna(0).sum()),
                "tackles": _integer(team_rows["Tackles"].fillna(0).sum()),
            })
        splits.sort(key=lambda split: (-split["games"], split["team"]))
        primary = splits[0]
        first = player_rows.sort_values("Date").iloc[0]
        output.append({
            "player_id": str(int(float(source_id))),
            "name": str(first["Player"]),
            "dob": _iso_dob(first["DOB"]),
            "source_url": str(first["url"]),
            "team_code": primary["team_code"],
            "team_codes": [split["team_code"] for split in splits],
            "team_splits": splits,
            "games": sum(split["games"] for split in splits),
            "disposals": sum(split["disposals"] for split in splits),
            "goals": sum(split["goals"] for split in splits),
            "marks": sum(split["marks"] for split in splits),
            "tackles": sum(split["tackles"] for split in splits),
        })
    return output


def wikidata_query(players: Iterable[dict[str, Any]]) -> str:
    values = " ".join(
        f"({json.dumps(player['player_id'])} {json.dumps(player['name'], ensure_ascii=False)}@en {json.dumps(player['dob'])})"
        for player in players if player.get("dob")
    )
    return f"""
SELECT DISTINCT ?sourceId ?name ?expectedDob ?item ?dob ?place ?placeLabel ?coord ?country ?countryLabel WHERE {{
  VALUES (?sourceId ?name ?expectedDob) {{ {values} }}
  ?item (rdfs:label|skos:altLabel) ?name; wdt:P569 ?dob; wdt:P19 ?place.
  FILTER(SUBSTR(STR(?dob), 1, 10) = ?expectedDob)
  OPTIONAL {{ ?place wdt:P625 ?coord. }}
  OPTIONAL {{ ?place wdt:P17 ?country. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
""".strip()


def _value(binding: dict[str, Any], key: str) -> str | None:
    return binding.get(key, {}).get("value")


def _qid(value: str | None) -> str | None:
    return value.rsplit("/", 1)[-1] if value else None


def _point(value: str | None) -> tuple[float | None, float | None]:
    match = re.fullmatch(r"Point\(([-0-9.]+) ([-0-9.]+)\)", value or "")
    return (float(match.group(2)), float(match.group(1))) if match else (None, None)


def choose_wikidata_rows(bindings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[tuple[str | None, str | None], dict[str, Any]]] = {}
    for binding in bindings:
        player_id = str(_value(binding, "sourceId"))
        lat, lon = _point(_value(binding, "coord"))
        row = {
            "wikidata_qid": _qid(_value(binding, "item")),
            "birth_place_qid": _qid(_value(binding, "place")),
            "place": _value(binding, "placeLabel"),
            "country": _value(binding, "countryLabel"),
            "lat": lat,
            "lon": lon,
        }
        candidates.setdefault(player_id, {})[(row["wikidata_qid"], row["birth_place_qid"])] = row
    output = {}
    for player_id, rows in candidates.items():
        usable = [row for row in rows.values() if row["lat"] is not None and row["lon"] is not None]
        if len(usable) == 1:
            output[player_id] = usable[0]
    return output


def wikipedia_birthplace(wikitext: str) -> tuple[str | None, str | None]:
    """Return the explicit infobox birthplace and its most specific wiki title."""
    match = re.search(r"(?im)^[ \t]*\|[ \t]*birth_place[ \t]*=[ \t]*(.*?)[ \t]*$", wikitext)
    if not match or not match.group(1).strip():
        return None, None
    raw = re.sub(r"<!--.*?-->|<ref\b[^>]*>.*?</ref>|<ref\b[^>]*/>", "", match.group(1), flags=re.I | re.S)
    links = re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]", raw)
    title = links[0][0].strip() if links else None
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", raw)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\{\{(?:flagicon|flag|country)[^}]*\}\}", "", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", ", ", text, flags=re.I)
    text = re.sub(r"'{2,}|<[^>]+>", "", text)
    text = re.sub(r"\s*,\s*", ", ", text).strip(" ,")
    return (text or None), title


ORIGIN_NON_PLACE_TITLES = re.compile(
    r"(?:football league|football netball league|football association|talent league|nab league|"
    r"tac cup|sanfl|wafl|victorian football league|vfl|associated public schools|"
    r"afl academy|north east australian football league)",
    re.I,
)


def wikipedia_football_origin(wikitext: str) -> tuple[str | None, str | None]:
    """Return the documented original-team label and first geocodable wiki title.

    The AFL biography infobox calls this field ``originalteam``. It is a
    football-development origin, never a place of birth.
    """
    match = re.search(r"(?im)^[ \t]*\|[ \t]*originalteam[ \t]*=[ \t]*(.*?)[ \t]*$", wikitext)
    if not match or not match.group(1).strip():
        return None, None
    raw = re.sub(r"<!--.*?-->|<ref\b[^>]*>.*?</ref>|<ref\b[^>]*/>", "", match.group(1), flags=re.I | re.S)
    links = re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]", raw)
    title = next((target.strip() for target, _ in links if not ORIGIN_NON_PLACE_TITLES.search(target)), None)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", raw)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    text = re.sub(r"<br\s*/?>", " / ", text, flags=re.I)
    text = re.sub(r"'{2,}|<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ,/;")
    if not title:
        candidate = re.split(r"\s*(?:/|;|,|\()\s*", text, maxsplit=1)[0].strip()
        title = candidate or None
    return (text or None), title


def wikipedia_club_location_titles(wikitext: str) -> list[str]:
    """Return linked grounds or locations explicitly published by a club page."""
    titles: list[str] = []
    for field in ("ground", "grounds", "groundname", "location", "headquarters"):
        match = re.search(rf"(?im)^[ \t]*\|[ \t]*{field}[ \t]*=[ \t]*(.*?)[ \t]*$", wikitext)
        if not match:
            continue
        titles.extend(
            target.strip() for target, _ in re.findall(
                r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]", match.group(1),
            ) if not ORIGIN_NON_PLACE_TITLES.search(target)
        )
    if not titles:
        lead = wikitext[:5000]
        match = re.search(r"(?i)\b(?:based|located|headquartered) in\s+\[\[([^\]|#]+)", lead)
        if match:
            titles.append(match.group(1).strip())
    return list(dict.fromkeys(titles))


def fetch_wikipedia_wikitext(
    client: CachedHttpClient, qids: Iterable[str], *, force: bool = False,
) -> dict[str, dict[str, str]]:
    lichen = {}
    for start in range(0, len(unique := sorted(set(qids))), 35):
        batch = unique[start:start + 35]
        params = {
            "action": "wbgetentities", "ids": "|".join(batch), "props": "sitelinks",
            "sitefilter": "enwiki", "format": "json",
        }
        digest = hashlib.sha1("|".join(batch).encode()).hexdigest()[:20]
        result = client.fetch_text(
            f"https://www.wikidata.org/w/api.php?{urlencode(params)}",
            ROOT / "data" / "cache" / "afl_wikipedia_sitelink_batches" / f"{digest}.json",
            force=force,
        )
        for qid, entity in json.loads(result.text).get("entities", {}).items():
            title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
            if title:
                lichen[qid] = {"title": title}
    by_title = {value["title"]: qid for qid, value in lichen.items()}
    titles = sorted(by_title)
    for start in range(0, len(titles), 25):
        batch = titles[start:start + 25]
        params = {
            "action": "query", "prop": "pageprops|revisions", "ppprop": "wikibase_item",
            "rvprop": "content", "rvslots": "main",
            "redirects": "1", "titles": "|".join(batch), "format": "json", "formatversion": "2",
        }
        digest = hashlib.sha1("|".join(batch).encode()).hexdigest()[:20]
        result = client.fetch_text(
            f"{ENWIKI_URL}?{urlencode(params)}",
            ROOT / "data" / "cache" / "afl_wikipedia_page_batches" / f"{digest}.json",
            force=force,
        )
        for page in json.loads(result.text).get("query", {}).get("pages", []):
            page_qid = by_title.get(page.get("title")) or page.get("pageprops", {}).get("wikibase_item")
            revisions = page.get("revisions") or []
            content = revisions[0].get("slots", {}).get("main", {}).get("content", "") if revisions else ""
            if page_qid in lichen:
                lichen[page_qid]["wikitext"] = content
    return lichen


def resolve_wikipedia_birthplaces(
    client: CachedHttpClient,
    players: list[dict[str, Any]],
    people: dict[str, dict[str, Any]],
    qids_by_title: dict[str, str | None],
    *,
    force: bool = False,
) -> dict[str, dict[str, Any]]:
    selected: dict[str, str] = {}
    for player in players:
        titles = [
            player["name"], f"{player['name']} (footballer)",
            f"{player['name']} (Australian footballer)",
            f"{player['name']} (Australian rules footballer)",
        ]
        qids = [qids_by_title.get(title) for title in titles]
        matches = {qid for qid in qids if qid and claim_date(people.get(qid, {})) == player["dob"]}
        if len(matches) == 1:
            selected[player["player_id"]] = matches.pop()
    pages = fetch_wikipedia_wikitext(client, selected.values(), force=force)
    raw_places: dict[str, tuple[str, str | None, str, str]] = {}
    for player_id, qid in selected.items():
        page = pages.get(qid, {})
        place, place_title = wikipedia_birthplace(page.get("wikitext", ""))
        if place:
            raw_places[player_id] = (place, place_title, qid, page.get("title", ""))
    titles = [place_title or place.split(",", 1)[0] for place, place_title, _, _ in raw_places.values()]
    place_qids_by_title = _fetch_title_qids(client, titles, batch_size=35, force=force)
    place_entities = _fetch_entities(
        client, [qid for qid in place_qids_by_title.values() if qid], "afl_wikipedia_place_batches",
        batch_size=30, force=force,
    )
    countries = _fetch_entities(
        client, [qid for entity in place_entities.values() if (qid := claim_entity(entity, "P17"))],
        "afl_wikipedia_country_batches", batch_size=30, force=force,
    )
    output = {}
    for player_id, (place, place_title, person_qid, page_title) in raw_places.items():
        lookup_title = place_title or place.split(",", 1)[0]
        place_qid = place_qids_by_title.get(lookup_title)
        entity = place_entities.get(place_qid, {})
        lat, lon = claim_coordinates(entity)
        country_qid = claim_entity(entity, "P17")
        if lat is None or lon is None:
            continue
        output[player_id] = {
            "wikidata_qid": person_qid, "birth_place_qid": place_qid,
            "place": place, "country": entity_label(countries.get(country_qid, {})),
            "lat": lat, "lon": lon, "resolution_source": "English Wikipedia infobox",
            "wikipedia_title": page_title,
        }
    return output


def _origin_coordinate(
    entity: dict[str, Any], related: dict[str, dict[str, Any]],
) -> tuple[float | None, float | None, str | None, str]:
    """Choose a documented club coordinate, preferring base then home venue."""
    lat, lon = claim_coordinates(entity)
    if lat is not None and lon is not None:
        return lat, lon, None, "original-team entity"
    for property_id, precision in (("P159", "club headquarters"), ("P115", "home venue"), ("P131", "administrative area")):
        related_qid = claim_entity(entity, property_id)
        related_entity = related.get(related_qid, {})
        lat, lon = claim_coordinates(related_entity)
        if lat is not None and lon is not None:
            return lat, lon, related_qid, precision
    return None, None, None, "unresolved"


def _australian_coordinate(lat: float | None, lon: float | None) -> bool:
    return lat is not None and lon is not None and -44.5 <= lat <= -9.0 and 112.0 <= lon <= 154.5


def resolve_wikipedia_origins(
    client: CachedHttpClient,
    players: list[dict[str, Any]],
    people: dict[str, dict[str, Any]],
    qids_by_title: dict[str, str | None],
    *,
    force: bool = False,
) -> dict[str, dict[str, Any]]:
    """Resolve exact-DOB-verified Wikipedia ``originalteam`` fields to coordinates."""
    selected: dict[str, str] = {}
    for player in players:
        titles = [
            player["name"], f"{player['name']} (footballer)",
            f"{player['name']} (Australian footballer)",
            f"{player['name']} (Australian rules footballer)",
        ]
        matches = {
            qid for title in titles
            if (qid := qids_by_title.get(title)) and claim_date(people.get(qid, {})) == player["dob"]
        }
        if len(matches) == 1:
            selected[player["player_id"]] = matches.pop()
    pages = fetch_wikipedia_wikitext(client, selected.values(), force=force)
    raw_origins: dict[str, tuple[str, str, str, str]] = {}
    for player_id, person_qid in selected.items():
        page = pages.get(person_qid, {})
        label, title = wikipedia_football_origin(page.get("wikitext", ""))
        if label and title:
            raw_origins[player_id] = (label, title, person_qid, page.get("title", ""))

    origin_qids_by_title = _fetch_title_qids(
        client, [title for _, title, _, _ in raw_origins.values()], batch_size=35, force=force,
    )
    origin_entities = _fetch_entities(
        client, [qid for qid in origin_qids_by_title.values() if qid], "afl_origin_team_batches",
        batch_size=30, force=force,
    )
    origin_pages = fetch_wikipedia_wikitext(client, origin_entities, force=force)
    club_location_titles = {
        origin_qid: wikipedia_club_location_titles(page.get("wikitext", ""))
        for origin_qid, page in origin_pages.items()
    }
    location_qids_by_title = _fetch_title_qids(
        client,
        [title for titles in club_location_titles.values() for title in titles],
        batch_size=35,
        force=force,
    )
    location_entities = _fetch_entities(
        client,
        [qid for qid in location_qids_by_title.values() if qid],
        "afl_origin_location_batches",
        batch_size=30,
        force=force,
    )
    related_qids = [
        qid for entity in origin_entities.values()
        for property_id in ("P159", "P115", "P131")
        if (qid := claim_entity(entity, property_id))
    ]
    related_entities = _fetch_entities(
        client, related_qids, "afl_origin_related_batches", batch_size=30, force=force,
    )
    country_qids = [
        qid for entity in [*origin_entities.values(), *related_entities.values(), *location_entities.values()]
        if (qid := claim_entity(entity, "P17"))
    ]
    countries = _fetch_entities(
        client, country_qids, "afl_origin_country_batches", batch_size=30, force=force,
    )

    output: dict[str, dict[str, Any]] = {}
    for player_id, (origin_label, origin_title, person_qid, page_title) in raw_origins.items():
        origin_qid = origin_qids_by_title.get(origin_title)
        entity = origin_entities.get(origin_qid, {})
        lat, lon, related_qid, precision = _origin_coordinate(entity, related_entities)
        location_entity: dict[str, Any] = {}
        if lat is None or lon is None:
            for location_title in club_location_titles.get(origin_qid, []):
                location_qid = location_qids_by_title.get(location_title)
                candidate = location_entities.get(location_qid, {})
                lat, lon = claim_coordinates(candidate)
                if lat is not None and lon is not None:
                    related_qid = location_qid
                    location_entity = candidate
                    precision = "club article ground/location"
                    break
        if lat is None or lon is None:
            continue
        related_entity = related_entities.get(related_qid, {})
        country_qid = (
            claim_entity(entity, "P17")
            or claim_entity(related_entity, "P17")
            or claim_entity(location_entity, "P17")
        )
        country = entity_label(countries.get(country_qid, {}))
        if not country and _australian_coordinate(lat, lon):
            country = "Australia"
        if not country:
            continue
        place_label = entity_label(entity) or origin_title
        output[player_id] = {
            "wikidata_qid": person_qid,
            "origin_qid": origin_qid,
            "place": place_label,
            "country": country,
            "lat": lat,
            "lon": lon,
            "location_type": "football_origin",
            "origin_label": origin_label,
            "origin_title": origin_title,
            "origin_precision": precision,
            "resolution_source": "English Wikipedia original-team field + Wikidata",
            "wikipedia_title": page_title,
        }
    return output


def fetch_wikidata(
    players: list[dict[str, Any]], cache_path: Path = DEFAULT_WIKIDATA_CACHE, *, force: bool = False,
) -> dict[str, dict[str, Any]]:
    cache = {}
    if cache_path.exists() and not force:
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}
    pending = [player for player in players if player.get("dob") and player["player_id"] not in cache]
    session = requests.Session()
    session.headers.update({"User-Agent": "football-geo/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.25, retries=3, timeout=90)
    for start in range(0, len(pending), 40):
        batch = pending[start:start + 40]
        query = wikidata_query(batch)
        digest = hashlib.sha1(query.encode()).hexdigest()[:20]
        result = client.fetch_text(
            f"{WIKIDATA_URL}?{urlencode({'query': query, 'format': 'json'})}",
            ROOT / "data" / "cache" / "afl_wikidata_batches" / f"{digest}.json",
            force=force,
        )
        matches = choose_wikidata_rows(json.loads(result.text)["results"]["bindings"])
        for player in batch:
            cache[player["player_id"]] = matches.get(player["player_id"], {})

    # An empty object is a deliberate reviewed miss. Once every DOB-bearing
    # player has a cache entry, do not repeat the slower Wikipedia-title pass.
    cache_version = int((cache.get("_meta") or {}).get("schema_version", 1))
    cache_complete = all(player["player_id"] in cache for player in players if player.get("dob"))
    unresolved = [] if cache_complete and cache_version >= 3 and not force and not pending else [
        player for player in players if player.get("dob") and not cache.get(player["player_id"], {}).get("lat")
    ]
    if unresolved:
        titles_by_id = {
            player["player_id"]: [
                player["name"],
                f"{player['name']} (footballer)",
                f"{player['name']} (Australian footballer)",
                f"{player['name']} (Australian rules footballer)",
            ]
            for player in unresolved
        }
        qids_by_title = _fetch_title_qids(
            client, [title for titles in titles_by_id.values() for title in titles], batch_size=40, force=force,
        )
        people = _fetch_entities(
            client, [qid for qid in qids_by_title.values() if qid], "afl_person_batches",
            batch_size=30, force=force,
        )
        selected: dict[str, tuple[str, str]] = {}
        for player in unresolved:
            qids = {qids_by_title.get(title) for title in titles_by_id[player["player_id"]]}
            matches = []
            for qid in qids - {None}:
                entity = people.get(qid, {})
                place_qid = claim_entity(entity, "P19")
                if claim_date(entity) == player["dob"] and place_qid:
                    matches.append((qid, place_qid))
            if len(set(matches)) == 1:
                selected[player["player_id"]] = matches[0]
            elif len(matches) == 0:
                identity_matches = {
                    qid for qid in qids - {None}
                    if claim_date(people.get(qid, {})) == player["dob"]
                }
                if len(identity_matches) == 1:
                    cache[player["player_id"]] = {"wikidata_qid": identity_matches.pop()}
        place_entities = _fetch_entities(
            client, [place for _, place in selected.values()], "afl_place_batches",
            batch_size=30, force=force,
        )
        for player_id, (person_qid, place_qid) in selected.items():
            cache.setdefault(player_id, {}).update({
                "wikidata_qid": person_qid,
                "birth_place_qid": place_qid,
            })
        country_qids = [claim_entity(entity, "P17") for entity in place_entities.values()]
        countries = _fetch_entities(
            client, [qid for qid in country_qids if qid], "afl_country_batches",
            batch_size=30, force=force,
        )
        for player_id, (qid, place_qid) in selected.items():
            entity = place_entities.get(place_qid, {})
            lat, lon = claim_coordinates(entity)
            country_qid = claim_entity(entity, "P17")
            if lat is None or lon is None:
                continue
            cache[player_id] = {
                "wikidata_qid": qid, "birth_place_qid": place_qid,
                "place": entity_label(entity), "country": entity_label(countries.get(country_qid, {})),
                "lat": lat, "lon": lon, "resolution_source": "Wikidata",
            }
        wikipedia_matches = resolve_wikipedia_birthplaces(
            client,
            [player for player in unresolved if not cache.get(player["player_id"], {}).get("lat")],
            people,
            qids_by_title,
            force=force,
        )
        cache.update(wikipedia_matches)
        origin_matches = resolve_wikipedia_origins(
            client,
            [player for player in unresolved if not cache.get(player["player_id"], {}).get("lat")],
            people,
            qids_by_title,
            force=force,
        )
        cache.update(origin_matches)
    cache["_meta"] = {
        "schema_version": 3,
        "sources": ["Wikidata", "English Wikipedia infobox", "Wikipedia original-team field"],
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return cache


def age_on(dob: str | None, on_date: date = date(2025, 8, 24)) -> int | None:
    if not dob:
        return None
    try:
        born = date.fromisoformat(dob[:10])
    except ValueError:
        return None
    return on_date.year - born.year - ((on_date.month, on_date.day) < (born.month, born.day))


def build_payload(
    cohort: list[dict[str, Any]], places: dict[str, dict[str, Any]], *, generated_at: str | None = None,
    stats_retrieved_at: str | None = None, stats_sha256: str | None = None,
) -> dict[str, Any]:
    records, unresolved = [], []
    for player in cohort:
        place = places.get(player["player_id"], {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        location_type = place.get("location_type", "birthplace") if mapped else None
        birthplace_mapped = mapped and location_type == "birthplace"
        status = (
            "verified birthplace" if birthplace_mapped else
            "documented football-origin fallback" if mapped else
            "date of birth unavailable" if not player.get("dob") else
            "birthplace and football origin unresolved"
        )
        splits = [{
            "team": split["team"], "teamCode": split["team_code"], "conference": "League-wide",
            "games": split["games"], "disposals": split["disposals"], "goals": split["goals"],
            "marks": split["marks"], "tackles": split["tackles"],
        } for split in player["team_splits"]]
        primary = splits[0]
        record = {
            "id": f"afl:{player['player_id']}", "aflTablesId": player["player_id"], "name": player["name"],
            "team": primary["team"], "teamCode": primary["teamCode"], "teams": [split["team"] for split in splits],
            "teamSplits": splits, "conference": "League-wide", "year": 2025, "games": player["games"],
            "disposals": player["disposals"], "goals": player["goals"], "marks": player["marks"],
            "tackles": player["tackles"], "position": None, "nationality": None, "age": age_on(player.get("dob")),
            "dob": player.get("dob"), "sourceUrl": player["source_url"], "place": place.get("place") if mapped else None,
            "country": place.get("country") if mapped else None, "lat": place.get("lat") if mapped else None,
            "lon": place.get("lon") if mapped else None, "mapped": mapped, "status": status,
            "locationType": location_type, "birthplaceMapped": birthplace_mapped,
            "wikidataQid": place.get("wikidata_qid"), "birthPlaceQid": place.get("birth_place_qid"),
            "birthplaceSource": place.get("resolution_source", "Wikidata") if birthplace_mapped else None,
            "originQid": place.get("origin_qid"),
            "originLabel": place.get("origin_label"),
            "originTitle": place.get("origin_title"),
            "originPrecision": place.get("origin_precision"),
            "originSource": place.get("resolution_source") if location_type == "football_origin" else None,
            "wikipediaTitle": place.get("wikipedia_title"),
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": record["name"], "status": status})
    records.sort(key=lambda row: (row["team"], row["name"]))
    mapped = [row for row in records if row["mapped"]]
    birthplaces = [row for row in records if row["birthplaceMapped"]]
    origin_fallbacks = [row for row in records if row["locationType"] == "football_origin"]
    games = sum(row["games"] for row in records)
    mapped_games = sum(row["games"] for row in mapped)
    birthplace_games = sum(row["games"] for row in birthplaces)
    origin_games = sum(row["games"] for row in origin_fallbacks)
    return {
        "meta": {
            "title": "AFL Talent Geography", "sport": "afl", "scope": "2025 AFL home-and-away season",
            "season": "2025", "year": 2025, "teams": sorted(TEAM_NAMES.values()), "conferences": ["League-wide"],
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "stats_source_name": "AFL Tables via fitzRoy", "stats_source_url": STATS_URL,
            "stats_retrieved_at": stats_retrieved_at, "stats_sha256": stats_sha256,
            "birthplace_source_name": "Wikidata and English Wikipedia infoboxes",
            "birthplace_source_url": "https://www.wikidata.org/",
            "origin_source_name": "English Wikipedia original-team fields and Wikidata",
            "origin_source_url": "https://en.wikipedia.org/",
        },
        "summary": {
            "teams": len({row["team"] for row in records}), "players": len(records), "mapped_players": len(mapped),
            "player_coverage_pct": round(len(mapped) / len(records) * 100, 1) if records else 0,
            "games": games, "mapped_games": mapped_games,
            "game_coverage_pct": round(mapped_games / games * 100, 1) if games else 0,
            "birthplace_mapped_players": len(birthplaces),
            "birthplace_player_coverage_pct": round(len(birthplaces) / len(records) * 100, 1) if records else 0,
            "birthplace_mapped_games": birthplace_games,
            "birthplace_game_coverage_pct": round(birthplace_games / games * 100, 1) if games else 0,
            "origin_fallback_players": len(origin_fallbacks), "origin_fallback_games": origin_games,
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in birthplaces}),
            "origin_locations": len({(row["lat"], row["lon"], row["place"]) for row in origin_fallbacks}),
            "birth_countries": len({row["country"] for row in birthplaces}),
            "location_countries": len({row["country"] for row in mapped}),
            "unresolved_players": len(unresolved),
        },
        "records": records, "unresolved": unresolved,
    }


def run(
    stats_input: Path | None = None, output_path: Path = DEFAULT_OUTPUT,
    wikidata_cache: Path = DEFAULT_WIKIDATA_CACHE, *, force_stats: bool = False,
) -> dict[str, Any]:
    path = stats_input or _download_binary(STATS_URL, DEFAULT_STATS_CACHE, force=force_stats)
    cohort = aggregate_afl_stats(pd.read_parquet(path))
    payload = build_payload(
        cohort, fetch_wikidata(cohort, wikidata_cache),
        stats_retrieved_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
        stats_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {payload['summary']['players']:,} AFL players with "
        f"{payload['summary']['player_coverage_pct']:.1f}% known-location coverage "
        f"({payload['summary']['birthplace_player_coverage_pct']:.1f}% verified birthplace) to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static AFL talent geography dataset")
    parser.add_argument("--stats-input", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--wikidata-cache", type=Path, default=DEFAULT_WIKIDATA_CACHE)
    parser.add_argument("--force-stats", action="store_true")
    args = parser.parse_args()
    run(args.stats_input, args.output, args.wikidata_cache, force_stats=args.force_stats)


if __name__ == "__main__":
    main()
