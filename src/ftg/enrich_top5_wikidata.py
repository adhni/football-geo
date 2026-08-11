from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests

from .enrich_wikidata import (
    API,
    _fetch_entities,
    _fetch_title_qids,
    claim_date,
    claim_coordinates,
    claim_entity,
    entity_label,
)
from .http_cache import CachedHttpClient

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
CACHE = ROOT / "data" / "raw" / "wikidata" / "top5_sparql"
QA = ROOT / "data" / "qa"
SPARQL_API = "https://query.wikidata.org/sparql"


def _normal_name(value: object) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", ascii_value.casefold())


def sparql_query(rows: list[tuple[str, int]]) -> str:
    values = " ".join(
        f"({json.dumps(name, ensure_ascii=False)}@en {int(year)})" for name, year in rows
    )
    return f"""
SELECT DISTINCT ?searchName ?birthYear ?item ?dob ?place WHERE {{
  VALUES (?searchName ?birthYear) {{ {values} }}
  ?item (rdfs:label|skos:altLabel) ?searchName;
        wdt:P569 ?dob.
  FILTER(YEAR(?dob) = ?birthYear)
  OPTIONAL {{ ?item wdt:P19 ?place. }}
}}
""".strip()


def choose_matches(
    requested: pd.DataFrame,
    bindings: list[dict],
) -> dict[str, dict]:
    candidates: dict[tuple[str, int], dict[str, dict]] = {}
    for row in bindings:
        name = row["searchName"]["value"]
        year = int(row["birthYear"]["value"])
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        candidates.setdefault((name, year), {})[qid] = {
            "wikidata_qid": qid,
            "wikidata_dob": row["dob"]["value"][:10],
            "birth_place_qid": row.get("place", {}).get("value", "").rsplit("/", 1)[-1] or None,
        }

    output: dict[str, dict] = {}
    for row in requested.itertuples(index=False):
        if pd.isna(row.birth_year):
            output[row.player_id] = {"resolution_status": "birth_year_missing"}
            continue
        matches = candidates.get((row.player_name, int(row.birth_year)), {})
        if len(matches) == 1:
            match = next(iter(matches.values()))
            match["resolution_status"] = "resolved" if match["birth_place_qid"] else "birthplace_missing"
            output[row.player_id] = match
        elif len(matches) > 1:
            output[row.player_id] = {"resolution_status": "ambiguous_name_birth_year"}
        else:
            output[row.player_id] = {"resolution_status": "name_birth_year_not_found"}
    return output


def choose_search_match(search_results: list[dict], entities: dict[str, dict], birth_year: int) -> dict | None:
    matches: dict[str, dict] = {}
    descriptions = {row.get("id"): str(row.get("description", "")).casefold() for row in search_results}
    for result in search_results:
        qid = result.get("id")
        entity = entities.get(qid, {})
        dob = claim_date(entity)
        place_qid = claim_entity(entity, "P19")
        if not qid or not dob or int(dob[:4]) != int(birth_year) or not place_qid:
            continue
        matches[qid] = {
            "wikidata_qid": qid,
            "wikidata_dob": dob,
            "birth_place_qid": place_qid,
            "resolution_status": "resolved",
        }
    if len(matches) == 1:
        return next(iter(matches.values()))
    football_matches = [
        match for qid, match in matches.items()
        if "football" in descriptions.get(qid, "") or "soccer" in descriptions.get(qid, "")
    ]
    return football_matches[0] if len(football_matches) == 1 else None


def _search_fallback(
    client: CachedHttpClient,
    players: pd.DataFrame,
    *,
    force: bool,
) -> dict[str, dict]:
    search_rows: dict[str, list[dict]] = {}
    candidate_qids: set[str] = set()
    eligible = players[players["birth_year"].notna()]
    for number, row in enumerate(eligible.itertuples(index=False), start=1):
        params = {
            "action": "wbsearchentities",
            "search": row.player_name,
            "language": "en",
            "uselang": "en",
            "type": "item",
            "limit": "10",
            "format": "json",
        }
        digest = hashlib.sha1(f"{row.player_name}|{int(row.birth_year)}".encode("utf-8")).hexdigest()[:20]
        response = client.fetch_text(
            f"{API}?{urlencode(params)}",
            CACHE / "entity_search" / f"{digest}.json",
            force=force,
        )
        results = json.loads(response.text).get("search", [])
        search_rows[row.player_id] = results
        candidate_qids.update(result["id"] for result in results if result.get("id"))
        if number % 25 == 0 or number == len(eligible):
            print(f"Wikidata search fallback {number}/{len(eligible)}", flush=True)

    entities = _fetch_entities(
        client,
        sorted(candidate_qids),
        "top5_search_candidate_batches",
        batch_size=30,
        force=force,
    )
    output: dict[str, dict] = {}
    for row in eligible.itertuples(index=False):
        match = choose_search_match(search_rows.get(row.player_id, []), entities, int(row.birth_year))
        if match:
            output[row.player_id] = match
    return output


def _wikipedia_title_fallback(
    client: CachedHttpClient,
    players: pd.DataFrame,
    *,
    force: bool,
) -> dict[str, dict]:
    eligible = players[players["birth_year"].notna()].copy()
    titles_by_player: dict[str, list[str]] = {}
    all_titles: list[str] = []
    for row in eligible.itertuples(index=False):
        titles = [
            row.player_name,
            f"{row.player_name} (footballer)",
            f"{row.player_name} (footballer, born {int(row.birth_year)})",
        ]
        titles_by_player[row.player_id] = titles
        all_titles.extend(titles)
    qids_by_title = _fetch_title_qids(client, all_titles, batch_size=50, force=force)
    candidate_qids = {qid for qid in qids_by_title.values() if qid}
    entities = _fetch_entities(
        client,
        sorted(candidate_qids),
        "top5_wikipedia_candidate_batches",
        batch_size=30,
        force=force,
    )
    output: dict[str, dict] = {}
    for row in eligible.itertuples(index=False):
        qids = {
            qids_by_title.get(title)
            for title in titles_by_player[row.player_id]
            if qids_by_title.get(title)
        }
        result_rows = [{"id": qid, "description": "association football player"} for qid in qids]
        match = choose_search_match(result_rows, entities, int(row.birth_year))
        if match:
            output[row.player_id] = match
    print(f"Wikipedia title fallback resolved {len(output):,}/{len(eligible):,}", flush=True)
    return output


def _reuse_existing(profiles: pd.DataFrame, path: Path | None) -> tuple[pd.DataFrame, set[str]]:
    profiles = profiles.copy()
    profiles["_normal_name"] = profiles["player_name"].map(_normal_name)
    reused: set[str] = set()
    if path is None or not path.exists():
        return profiles, reused
    old = pd.read_parquet(path).copy()
    old = old[old["resolution_status"].eq("resolved")].copy()
    old["birth_year"] = pd.to_datetime(old["wikidata_dob"], errors="coerce").dt.year.astype("Int64")
    old["_normal_name"] = old["player_name"].map(_normal_name)
    old = old.drop_duplicates(["_normal_name", "birth_year"], keep=False)
    keep = [
        "_normal_name", "birth_year", "wikidata_qid", "wikidata_dob", "birth_place_qid",
        "birthplace_wikidata", "birth_country_qid", "birth_country", "birth_lat", "birth_lon",
    ]
    merged = profiles.merge(old[keep], on=["_normal_name", "birth_year"], how="left", validate="many_to_one")
    reused = set(merged.loc[merged["wikidata_qid"].notna(), "player_id"])
    merged["resolution_status"] = pd.NA
    merged.loc[merged["player_id"].isin(reused), "resolution_status"] = "resolved"
    merged["resolution_method"] = pd.NA
    merged.loc[merged["player_id"].isin(reused), "resolution_method"] = "reused_dob_validated_identity"
    return merged, reused


def run(
    players_path: Path = PROCESSED / "top5_players_source.parquet",
    output_path: Path = PROCESSED / "top5_players_enriched.parquet",
    *,
    reuse_path: Path | None = PROCESSED / "players_enriched.parquet",
    batch_size: int = 50,
    delay: float = 0.25,
    force: bool = False,
    wikipedia_fallback: bool = True,
    search_fallback: bool = False,
) -> pd.DataFrame:
    source = pd.read_parquet(players_path)
    if source["player_id"].duplicated().any():
        raise ValueError("Top-five player source must contain one row per player_id")
    players, reused = _reuse_existing(source, reuse_path)

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "football-geo/1.0 (research; github.com/adhni/football-geo)"}
    )
    client = CachedHttpClient(session, delay=delay, retries=3, timeout=90)
    pending = players[~players["player_id"].isin(reused)].copy()
    known_year = pending[pending["birth_year"].notna()].copy()
    all_bindings: list[dict] = []
    for number, start in enumerate(range(0, len(known_year), batch_size), start=1):
        batch = known_year.iloc[start : start + batch_size]
        pairs = [(row.player_name, int(row.birth_year)) for row in batch.itertuples(index=False)]
        query = sparql_query(pairs)
        digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:20]
        url = f"{SPARQL_API}?{urlencode({'query': query, 'format': 'json'})}"
        response = client.fetch_text(url, CACHE / f"{digest}.json", force=force)
        all_bindings.extend(json.loads(response.text)["results"]["bindings"])
        print(f"Wikidata batch {number}/{(len(known_year) + batch_size - 1) // batch_size}", flush=True)

    matches = choose_matches(pending, all_bindings)
    for index, row in players.loc[~players["player_id"].isin(reused)].iterrows():
        match = matches[row["player_id"]]
        for column, value in match.items():
            players.loc[index, column] = value
        players.loc[index, "resolution_method"] = "exact_english_label_and_birth_year"

    if wikipedia_fallback:
        unresolved = players[~players["resolution_status"].eq("resolved")].copy()
        wikipedia_matches = _wikipedia_title_fallback(client, unresolved, force=force)
        for index, row in players[players["player_id"].isin(wikipedia_matches)].iterrows():
            for column, value in wikipedia_matches[row["player_id"]].items():
                players.loc[index, column] = value
            players.loc[index, "resolution_method"] = "wikipedia_title_and_birth_year"

    if search_fallback:
        unresolved = players[~players["resolution_status"].eq("resolved")].copy()
        fallback_matches = _search_fallback(client, unresolved, force=force)
        for index, row in players[players["player_id"].isin(fallback_matches)].iterrows():
            for column, value in fallback_matches[row["player_id"]].items():
                players.loc[index, column] = value
            players.loc[index, "resolution_method"] = "wikidata_search_and_birth_year"

    accepted = players["resolution_status"].eq("resolved")
    place_qids = players.loc[accepted & players["birth_place_qid"].notna(), "birth_place_qid"].astype(str).tolist()
    places = _fetch_entities(client, place_qids, "top5_place_batches", batch_size=30, force=force)
    players["birthplace_wikidata"] = players["birth_place_qid"].map(
        lambda qid: entity_label(places.get(qid, {})) if pd.notna(qid) else None
    )
    coordinates = players["birth_place_qid"].map(
        lambda qid: claim_coordinates(places.get(qid, {})) if pd.notna(qid) else (None, None)
    )
    players["birth_lat"] = [value[0] for value in coordinates]
    players["birth_lon"] = [value[1] for value in coordinates]
    players["birth_country_qid"] = players["birth_place_qid"].map(
        lambda qid: claim_entity(places.get(qid, {}), "P17") if pd.notna(qid) else None
    )
    country_qids = players.loc[accepted & players["birth_country_qid"].notna(), "birth_country_qid"].astype(str).tolist()
    countries = _fetch_entities(client, country_qids, "top5_country_batches", batch_size=30, force=force)
    players["birth_country"] = players["birth_country_qid"].map(
        lambda qid: entity_label(countries.get(qid, {})) if pd.notna(qid) else None
    )
    missing_coordinates = accepted & players[["birth_lat", "birth_lon"]].isna().any(axis=1)
    players.loc[missing_coordinates, "resolution_status"] = "birthplace_coordinates_missing"
    players["resolution_confidence"] = players["resolution_status"].eq("resolved").astype(float)
    players.loc[~players["resolution_status"].eq("resolved"), ["birth_lat", "birth_lon", "birth_country"]] = pd.NA
    players = players.drop(columns=["_normal_name"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    players.to_parquet(output_path, index=False)
    unresolved = players[~players["resolution_status"].eq("resolved")].copy()
    unresolved[[
        "player_id", "player_name", "birth_year", "nationality_source", "clubs", "leagues",
        "wikidata_qid", "birth_place_qid", "resolution_status",
    ]].to_csv(QA / "top5_wikidata_resolution_queue.csv", index=False)
    print(
        f"Resolved {len(players) - len(unresolved):,}/{len(players):,} players; "
        f"queued {len(unresolved):,} for QA"
    )
    return players


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Big Five player birthplaces via Wikidata")
    parser.add_argument("--players", type=Path, default=PROCESSED / "top5_players_source.parquet")
    parser.add_argument("--output", type=Path, default=PROCESSED / "top5_players_enriched.parquet")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-wikipedia-fallback", action="store_true")
    parser.add_argument("--search-fallback", action="store_true")
    args = parser.parse_args()
    run(
        args.players,
        args.output,
        batch_size=args.batch_size,
        delay=args.delay,
        force=args.force,
        wikipedia_fallback=not args.no_wikipedia_fallback,
        search_fallback=args.search_fallback,
    )


if __name__ == "__main__":
    main()
