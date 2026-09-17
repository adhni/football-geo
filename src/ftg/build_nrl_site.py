from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

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
SEASON_END = date(2025, 9, 7)
DEFAULT_COMPETITION_ID = 12755
DEFAULT_OUTPUT = ROOT / "docs" / "nrl" / "data" / "dashboard.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "nrl_2025"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "nrl_wikidata_2025.json"
FIXTURE_URL = "https://mc.championdata.com/data/{competition_id}/fixture.json"
MATCH_URL = "https://mc.championdata.com/data/{competition_id}/{match_id}.json"
RUGBY_LEAGUE_QIDS = {"Q10962", "Q14373094"}


def _integer(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def parse_fixture(payload: dict[str, Any]) -> list[dict[str, Any]]:
    fixture = payload.get("fixture") or {}
    matches = [row for row in fixture.get("match", []) if row.get("matchStatus") == "complete"]
    if len(matches) != 204 or _integer(fixture.get("totalMatches")) != 204:
        raise ValueError(f"Expected 204 completed NRL matches, found {len(matches)}")
    teams = {
        str(row[key])
        for row in matches
        for key in ("homeSquadName", "awaySquadName")
        if row.get(key)
    }
    if len(teams) != 17:
        raise ValueError(f"Expected 17 NRL clubs, found {len(teams)}")
    return sorted(matches, key=lambda row: _integer(row.get("matchId")))


MEANINGFUL_STATS = (
    "points", "tries", "runMetres", "tackles", "runs", "passes", "kickMetres",
    "tackleds", "possessions", "errors", "penaltiesConceded", "sinBins", "sentOffs",
)


def parse_match(fixture: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    stats = payload.get("matchStats") or {}
    info = {str(row.get("playerId")): row for row in (stats.get("playerInfo") or {}).get("player", [])}
    squad_meta = {
        str(fixture.get("homeSquadId")): (fixture.get("homeSquadName"), fixture.get("homeSquadCode")),
        str(fixture.get("awaySquadId")): (fixture.get("awaySquadName"), fixture.get("awaySquadCode")),
    }
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in (stats.get("playerStats") or {}).get("player", []):
        player_id = str(row.get("playerId") or "")
        if not player_id or player_id in seen:
            continue
        seen.add(player_id)
        if not any(_integer(row.get(field)) for field in MEANINGFUL_STATS):
            continue
        player = info.get(player_id, {})
        team, team_code = squad_meta.get(str(row.get("squadId")), (None, None))
        name = " ".join(str(player.get(field) or "").strip() for field in ("firstname", "surname")).strip()
        if not name or not team:
            continue
        output.append({
            "match_id": str(fixture["matchId"]), "player_id": player_id, "name": name,
            "team": str(team), "team_code": str(team_code or row.get("squadId")),
            "position": str(row.get("position") or "") or None,
            "points": _integer(row.get("points")), "tries": _integer(row.get("tries")),
            "run_metres": _integer(row.get("runMetres") or row.get("metresGained")),
            "tackles": _integer(row.get("tackles")),
        })
    return output


def aggregate_matches(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_player: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_player.setdefault(row["player_id"], []).append(row)
    output: list[dict[str, Any]] = []
    for player_id, player_rows in by_player.items():
        names = Counter(row["name"] for row in player_rows)
        positions = Counter(row["position"] for row in player_rows if row.get("position"))
        splits = []
        for team in sorted({row["team"] for row in player_rows}):
            team_rows = [row for row in player_rows if row["team"] == team]
            splits.append({
                "team": team, "team_code": team_rows[0]["team_code"], "games": len(team_rows),
                "points": sum(row["points"] for row in team_rows),
                "tries": sum(row["tries"] for row in team_rows),
                "run_metres": sum(row["run_metres"] for row in team_rows),
                "tackles": sum(row["tackles"] for row in team_rows),
            })
        splits.sort(key=lambda split: (-split["games"], split["team"]))
        output.append({
            "player_id": player_id, "name": names.most_common(1)[0][0],
            "position": positions.most_common(1)[0][0] if positions else None,
            "team_splits": splits, "games": sum(split["games"] for split in splits),
            "points": sum(split["points"] for split in splits),
            "tries": sum(split["tries"] for split in splits),
            "run_metres": sum(split["run_metres"] for split in splits),
            "tackles": sum(split["tackles"] for split in splits),
        })
    return sorted(output, key=lambda row: (row["team_splits"][0]["team"], row["name"]))


def _fetch_json(url: str, path: Path, *, force: bool = False) -> tuple[dict[str, Any], str]:
    session = requests.Session()
    session.headers.update({"User-Agent": "football-geo/1.0 (research; github.com/adhni/football-geo)"})
    result = CachedHttpClient(session, delay=0, retries=3, timeout=90).fetch_text(url, path, force=force)
    return json.loads(result.text), result.retrieved_at


def fetch_competition(
    competition_id: int, cache_dir: Path = DEFAULT_CACHE, *, workers: int = 8, force: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fixture_payload, retrieved_at = _fetch_json(
        FIXTURE_URL.format(competition_id=competition_id), cache_dir / "fixture.json", force=force,
    )
    fixtures = parse_fixture(fixture_payload)
    rows: list[dict[str, Any]] = []

    def fetch_one(fixture: dict[str, Any]) -> list[dict[str, Any]]:
        match_id = str(fixture["matchId"])
        payload, _ = _fetch_json(
            MATCH_URL.format(competition_id=competition_id, match_id=match_id),
            cache_dir / "matches" / f"{match_id}.json", force=force,
        )
        return parse_match(fixture, payload)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(fetch_one, fixture): fixture for fixture in fixtures}
        for index, future in enumerate(as_completed(futures), start=1):
            rows.extend(future.result())
            if index % 25 == 0 or index == len(futures):
                print(f"  fetched {index}/{len(futures)} NRL matches", flush=True)
    return aggregate_matches(rows), {
        "competition_id": competition_id, "fixture_retrieved_at": retrieved_at,
        "matches": len(fixtures), "raw_player_match_rows": len(rows),
    }


def _claim_ids(entity: dict[str, Any], property_id: str) -> set[str]:
    output = set()
    for claim in entity.get("claims", {}).get(property_id, []):
        value = (claim.get("mainsnak", {}).get("datavalue") or {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            output.add(value["id"])
    return output


def _rugby_league_identity(entity: dict[str, Any], expected_name: str) -> bool:
    if normalize(entity_label(entity)) != normalize(expected_name):
        return False
    return bool(
        _claim_ids(entity, "P106") & RUGBY_LEAGUE_QIDS
        or _claim_ids(entity, "P641") & RUGBY_LEAGUE_QIDS
    )


def fetch_birthplaces(
    players: list[dict[str, Any]], cache_path: Path = DEFAULT_WIKIDATA_CACHE, *, force: bool = False,
) -> dict[str, dict[str, Any]]:
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": "football-geo/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.15, retries=3, timeout=90)
    titles_by_id = {
        player["player_id"]: [
            player["name"], f"{player['name']} (rugby league)",
            f"{player['name']} (rugby league player)",
            f"{player['name']} (Australian rugby league)",
            f"{player['name']} (New Zealand rugby league)",
        ] for player in players
    }
    qids_by_title = _fetch_title_qids(
        client, [title for titles in titles_by_id.values() for title in titles], batch_size=40, force=force,
    )
    people = _fetch_entities(
        client, [qid for qid in qids_by_title.values() if qid], "nrl_person_batches",
        batch_size=30, force=force,
    )
    selected: dict[str, str] = {}
    for player in players:
        qids = {qids_by_title.get(title) for title in titles_by_id[player["player_id"]]} - {None}
        matches = {qid for qid in qids if _rugby_league_identity(people.get(qid, {}), player["name"])}
        if len(matches) == 1:
            selected[player["player_id"]] = matches.pop()
    place_by_player = {
        player_id: claim_entity(people.get(person_qid, {}), "P19")
        for player_id, person_qid in selected.items()
    }
    places = _fetch_entities(
        client, [qid for qid in place_by_player.values() if qid], "nrl_place_batches",
        batch_size=30, force=force,
    )
    countries = _fetch_entities(
        client, [qid for entity in places.values() if (qid := claim_entity(entity, "P17"))],
        "nrl_country_batches", batch_size=30, force=force,
    )
    output: dict[str, dict[str, Any]] = {"_meta": {"schema_version": 1, "source": "Wikidata"}}
    for player_id, person_qid in selected.items():
        place_qid = place_by_player[player_id]
        entity = places.get(place_qid, {})
        lat, lon = claim_coordinates(entity)
        if lat is None or lon is None:
            continue
        country_qid = claim_entity(entity, "P17")
        output[player_id] = {
            "wikidata_qid": person_qid, "birth_place_qid": place_qid,
            "dob": claim_date(people.get(person_qid, {})), "place": entity_label(entity),
            "country": entity_label(countries.get(country_qid, {})), "lat": lat, "lon": lon,
            "resolution_source": "Wikidata rugby-league identity",
        }
    _write_json(cache_path, output, pretty=True)
    return output


def age_on(dob: str | None) -> int | None:
    return _age_on(dob, SEASON_END)


def build_payload(
    cohort: list[dict[str, Any]], places: dict[str, dict[str, Any]], source_meta: dict[str, Any],
    *, generated_at: str | None = None,
) -> dict[str, Any]:
    records, unresolved = [], []
    for player in cohort:
        place = places.get(player["player_id"], {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        splits = [{
            "team": split["team"], "teamCode": split["team_code"], "conference": "League-wide",
            "games": split["games"], "points": split["points"], "tries": split["tries"],
            "runMetres": split["run_metres"], "tackles": split["tackles"],
        } for split in player["team_splits"]]
        primary = splits[0]
        status = "verified birthplace" if mapped else "Wikidata birthplace unresolved"
        record = {
            "id": f"nrl:{player['player_id']}", "championDataId": player["player_id"],
            "name": player["name"], "team": primary["team"], "teamCode": primary["teamCode"],
            "teams": [split["team"] for split in splits], "teamSplits": splits,
            "conference": "League-wide", "year": SEASON, "games": player["games"],
            "points": player["points"], "tries": player["tries"], "runMetres": player["run_metres"],
            "tackles": player["tackles"], "position": player["position"],
            "dob": place.get("dob"), "age": age_on(place.get("dob")), "nationality": None,
            "place": place.get("place") if mapped else None, "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None, "lon": place.get("lon") if mapped else None,
            "mapped": mapped, "status": status, "locationType": "birthplace" if mapped else None,
            "wikidataQid": place.get("wikidata_qid"), "birthPlaceQid": place.get("birth_place_qid"),
            "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": record["name"], "status": status})
    records.sort(key=lambda row: (row["team"], row["name"]))
    mapped_records = [row for row in records if row["mapped"]]
    games = sum(row["games"] for row in records)
    mapped_games = sum(row["games"] for row in mapped_records)
    teams = sorted({split["team"] for row in records for split in row["teamSplits"]})
    return {
        "meta": {
            "title": "NRL Talent Geography", "sport": "nrl", "scope": "2025 NRL regular season",
            "season": "2025", "year": 2025, "teams": teams, "conferences": ["League-wide"],
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "stats_source_name": "Champion Data Match Centre", "stats_source_url": FIXTURE_URL.format(competition_id=source_meta["competition_id"]),
            "stats_retrieved_at": source_meta.get("fixture_retrieved_at"),
            "birthplace_source_name": "Wikidata", "birthplace_source_url": "https://www.wikidata.org/",
            "matches": source_meta["matches"],
        },
        "summary": {
            "teams": len(teams), "players": len(records), "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "games": games, "mapped_games": mapped_games,
            "game_coverage_pct": round(mapped_games / games * 100, 1) if games else 0,
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped_records}),
            "birth_countries": len({row["country"] for row in mapped_records}),
            "unresolved_players": len(unresolved),
        },
        "records": records, "unresolved": unresolved,
    }


def run(
    competition_id: int = DEFAULT_COMPETITION_ID, output_path: Path = DEFAULT_OUTPUT,
    *, workers: int = 8, force: bool = False,
) -> dict[str, Any]:
    cohort, source_meta = fetch_competition(competition_id, workers=workers, force=force)
    payload = build_payload(cohort, fetch_birthplaces(cohort, force=force), source_meta)
    if payload["summary"]["teams"] != 17 or payload["meta"]["matches"] != 204:
        raise ValueError("NRL reconciliation failed")
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']} NRL players from 204 matches with "
        f"{payload['summary']['player_coverage_pct']}% birthplace coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the 2025 NRL talent geography dataset")
    parser.add_argument("--competition-id", type=int, default=DEFAULT_COMPETITION_ID)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(args.competition_id, args.output, workers=args.workers, force=args.force)


if __name__ == "__main__":
    main()
