"""DOB-validated Wikipedia/Wikidata birthplace lookup shared by sport builders."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from .enrich_wikidata import (
    _fetch_entities, _fetch_title_qids, claim_coordinates, claim_date, claim_entity, entity_label,
)
from .http_cache import CachedHttpClient
from .utils import write_json as _write_json

COUNTRY_PLACE_TYPES = {"Q6256", "Q3624078"}


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
