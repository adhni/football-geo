from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlencode, urlparse

import pandas as pd
import requests

from .http_cache import CachedHttpClient

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
CACHE = ROOT / "data" / "raw" / "wikidata"
QA = ROOT / "data" / "qa"
API = "https://www.wikidata.org/w/api.php"
ENWIKI_API = "https://en.wikipedia.org/w/api.php"


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def wikipedia_title(url: object) -> str | None:
    if url is None or pd.isna(url):
        return None
    parsed = urlparse(str(url))
    marker = "/wiki/"
    if parsed.hostname not in {"en.wikipedia.org", "www.en.wikipedia.org"} or marker not in parsed.path:
        return None
    return unquote(parsed.path.split(marker, 1)[1]).replace("_", " ").strip() or None


def _claim_value(entity: dict, property_id: str) -> object | None:
    claims = entity.get("claims", {}).get(property_id, [])
    if not claims:
        return None
    ranked = sorted(claims, key=lambda claim: claim.get("rank") == "preferred", reverse=True)
    snak = ranked[0].get("mainsnak", {})
    if snak.get("snaktype") != "value":
        return None
    return snak.get("datavalue", {}).get("value")


def claim_entity(entity: dict, property_id: str) -> str | None:
    value = _claim_value(entity, property_id)
    return value.get("id") if isinstance(value, dict) else None


def claim_date(entity: dict, property_id: str = "P569") -> str | None:
    value = _claim_value(entity, property_id)
    if not isinstance(value, dict) or not value.get("time"):
        return None
    raw = str(value["time"]).lstrip("+")
    return raw[:10] if len(raw) >= 10 else None


def claim_coordinates(entity: dict) -> tuple[float | None, float | None]:
    value = _claim_value(entity, "P625")
    if not isinstance(value, dict):
        return None, None
    latitude = value.get("latitude")
    longitude = value.get("longitude")
    return (
        float(latitude) if latitude is not None else None,
        float(longitude) if longitude is not None else None,
    )


def entity_label(entity: dict) -> str | None:
    labels = entity.get("labels", {})
    if "en" in labels:
        return labels["en"].get("value")
    return next(
        (label.get("value") for label in labels.values() if label.get("value")),
        None,
    )


def title_qid_map(query_response: dict, requested_titles: list[str]) -> dict[str, str | None]:
    query = query_response.get("query", {})
    aliases: dict[str, str] = {}
    for item in query.get("normalized", []):
        aliases[item["from"].replace("_", " ")] = item["to"]
    for item in query.get("redirects", []):
        aliases[item["from"].replace("_", " ")] = item["to"]
    pages = query.get("pages", {})
    page_qids = {
        page.get("title", ""): page.get("pageprops", {}).get("wikibase_item")
        for page in pages.values()
    }

    output: dict[str, str | None] = {}
    for requested in requested_titles:
        title = requested.replace("_", " ")
        visited: set[str] = set()
        while title in aliases and title not in visited:
            visited.add(title)
            title = aliases[title]
        output[requested] = page_qids.get(title)
    return output


def _request_url(base_url: str, params: dict[str, str]) -> str:
    return f"{base_url}?{urlencode(params)}"


def _cached_json(
    client: CachedHttpClient,
    params: dict[str, str],
    cache_group: str,
    cache_keys: list[str],
    *,
    force: bool,
    base_url: str = API,
) -> dict:
    digest = hashlib.sha1("|".join(cache_keys).encode("utf-8")).hexdigest()[:16]
    path = CACHE / cache_group / f"{digest}.json"
    result = client.fetch_text(_request_url(base_url, params), path, force=force)
    return json.loads(result.text)


def _fetch_title_qids(
    client: CachedHttpClient,
    titles: list[str],
    *,
    batch_size: int,
    force: bool,
) -> dict[str, str | None]:
    output: dict[str, str | None] = {}
    for batch in chunks(sorted(set(titles)), batch_size):
        response = _cached_json(
            client,
            {
                "action": "query",
                "prop": "pageprops",
                "ppprop": "wikibase_item",
                "redirects": "1",
                "titles": "|".join(batch),
                "format": "json",
            },
            "enwiki_title_batches",
            batch,
            force=force,
            base_url=ENWIKI_API,
        )
        output.update(title_qid_map(response, batch))
    return output


def _fetch_entities(
    client: CachedHttpClient,
    qids: list[str],
    cache_group: str,
    *,
    batch_size: int,
    force: bool,
    languages: str = "en",
) -> dict[str, dict]:
    output: dict[str, dict] = {}
    for batch in chunks(sorted(set(qids)), batch_size):
        response = _cached_json(
            client,
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "claims|labels",
                "languages": languages,
                "format": "json",
            },
            cache_group,
            batch,
            force=force,
        )
        output.update(response.get("entities", {}))
    return output


def run(
    players_path: Path = PROCESSED / "players_source.parquet",
    output_path: Path = PROCESSED / "players_enriched.parquet",
    *,
    delay: float = 0.5,
    retries: int = 3,
    batch_size: int = 30,
    force: bool = False,
) -> pd.DataFrame:
    players = pd.read_parquet(players_path).copy()
    if players["player_id"].duplicated().any():
        raise ValueError("players_source must contain one row per player_id")
    players["wikipedia_title"] = players["player_url"].map(wikipedia_title)
    if not players.empty and players["wikipedia_title"].isna().all():
        raise ValueError(
            "This resolver requires English Wikipedia player URLs and source DOBs. "
            "Use worldcup_players_source.parquet for the World Cup flow; "
            "11v11 profiles require a separate identity-resolution step."
        )

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "football-talent-geography/0.2 (research; contact via GitHub adhni/football-geo)"}
    )
    client = CachedHttpClient(session, delay=delay, retries=retries)
    titles = players["wikipedia_title"].dropna().astype(str).tolist()
    qids_by_title = _fetch_title_qids(
        client, titles, batch_size=batch_size, force=force
    )
    players["wikidata_qid"] = players["wikipedia_title"].map(qids_by_title)

    person_qids = players["wikidata_qid"].dropna().astype(str).tolist()
    people = _fetch_entities(
        client,
        person_qids,
        "person_batches",
        batch_size=batch_size,
        force=force,
    )
    source_dob = pd.to_datetime(players["dob"], errors="coerce").dt.strftime("%Y-%m-%d")
    players["wikidata_dob"] = players["wikidata_qid"].map(
        lambda qid: claim_date(people.get(qid, {})) if pd.notna(qid) else None
    )
    players["birth_place_qid"] = players["wikidata_qid"].map(
        lambda qid: claim_entity(people.get(qid, {}), "P19") if pd.notna(qid) else None
    )
    players["resolution_status"] = "resolved"
    players.loc[players["wikipedia_title"].isna(), "resolution_status"] = "missing_wikipedia_link"
    players.loc[
        players["wikipedia_title"].notna() & players["wikidata_qid"].isna(),
        "resolution_status",
    ] = "wikipedia_not_linked_to_wikidata"
    players.loc[
        players["wikidata_qid"].notna() & source_dob.isna(),
        "resolution_status",
    ] = "source_dob_missing"
    players.loc[
        players["wikidata_qid"].notna()
        & source_dob.notna()
        & players["wikidata_dob"].isna(),
        "resolution_status",
    ] = "wikidata_dob_missing"
    players.loc[
        players["wikidata_dob"].notna() & source_dob.notna() & players["wikidata_dob"].ne(source_dob),
        "resolution_status",
    ] = "dob_mismatch"
    players.loc[
        players["resolution_status"].eq("resolved") & players["birth_place_qid"].isna(),
        "resolution_status",
    ] = "birthplace_missing"

    accepted = players["resolution_status"].eq("resolved")
    place_qids = players.loc[accepted, "birth_place_qid"].dropna().astype(str).tolist()
    places = _fetch_entities(
        client,
        place_qids,
        "place_batches",
        batch_size=batch_size,
        force=force,
    )
    missing_place_labels = [qid for qid in place_qids if not entity_label(places.get(qid, {}))]
    if missing_place_labels:
        places.update(
            _fetch_entities(
                client,
                missing_place_labels,
                "place_label_fallback_batches",
                batch_size=batch_size,
                force=force,
                languages="en|fr|es|pt|de|it|nl|hr|ja",
            )
        )
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

    country_qids = players.loc[accepted, "birth_country_qid"].dropna().astype(str).tolist()
    countries = _fetch_entities(
        client,
        country_qids,
        "country_batches",
        batch_size=batch_size,
        force=force,
    )
    missing_country_labels = [qid for qid in country_qids if not entity_label(countries.get(qid, {}))]
    if missing_country_labels:
        countries.update(
            _fetch_entities(
                client,
                missing_country_labels,
                "country_label_fallback_batches",
                batch_size=batch_size,
                force=force,
                languages="en|fr|es|pt|de|it|nl|hr|ja",
            )
        )
    players["birth_country"] = players["birth_country_qid"].map(
        lambda qid: entity_label(countries.get(qid, {})) if pd.notna(qid) else None
    )
    players["resolution_confidence"] = accepted.astype(float)
    players.loc[~accepted, ["birth_lat", "birth_lon", "birth_country"]] = pd.NA
    missing_coordinates = accepted & players[["birth_lat", "birth_lon"]].isna().any(axis=1)
    players.loc[missing_coordinates, "resolution_status"] = "birthplace_coordinates_missing"
    players.loc[missing_coordinates, "resolution_confidence"] = 0.0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    players.to_parquet(output_path, index=False)
    unresolved = players[~players["resolution_status"].eq("resolved")].copy()
    unresolved[
        [
            "player_id",
            "player_name",
            "dob",
            "player_url",
            "wikidata_qid",
            "wikidata_dob",
            "birth_place_qid",
            "resolution_status",
        ]
    ].to_csv(QA / "wikidata_resolution_queue.csv", index=False)
    print(
        f"Resolved {len(players) - len(unresolved):,}/{len(players):,} players "
        f"with DOB-validated Wikidata birth coordinates"
    )
    print(f"Queued {len(unresolved):,} unresolved players for QA")
    return players


def main() -> None:
    parser = argparse.ArgumentParser(description="DOB-validated batched Wikidata enrichment")
    parser.add_argument("--players", type=Path, default=PROCESSED / "players_source.parquet")
    parser.add_argument("--output", type=Path, default=PROCESSED / "players_enriched.parquet")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(
        args.players,
        args.output,
        delay=args.delay,
        retries=args.retries,
        batch_size=args.batch_size,
        force=args.force,
    )


if __name__ == "__main__":
    main()
