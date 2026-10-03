from __future__ import annotations

import argparse
import csv
import io
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

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
SEASON_END = date(2025, 11, 17)
TOURS = {
    "ATP": {"ranking_date": "20251117", "gender": "Men"},
    "WTA": {"ranking_date": "20251110", "gender": "Women"},
}
MIRROR_ROOT = "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main"
INPUT_URLS = {
    "ATP": {
        "rankings": f"{MIRROR_ROOT}/atp/atp_rankings_20s.csv",
        "players": f"{MIRROR_ROOT}/atp/atp_players.csv",
    },
    "WTA": {
        "rankings": f"{MIRROR_ROOT}/wta/wta_rankings_20s.csv",
        "players": f"{MIRROR_ROOT}/wta/wta_players.csv",
    },
}
OFFICIAL_SOURCES = {
    "ATP": "https://www.atptour.com/en/news/year-end-pif-atp-rankings-2025-release",
    "WTA": "https://wtafiles.wtatennis.com/pdf/rankings/RankingArchive/Singles_Numeric_2025.pdf",
}
DEFAULT_OUTPUT = ROOT / "docs" / "tennis" / "data" / "dashboard.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "tennis_2025"
DEFAULT_WIKIDATA_CACHE = ROOT / "data" / "cache" / "tennis_wikidata_2025.json"
OFFICIAL_BIRTHPLACE_OVERRIDES = {
    "ATP:211663": ("Rio de Janeiro", "https://www.atptour.com/en/players/Joao-Fonseca/F0FV/overview"),
    "ATP:209098": ("Novi Pazar", "https://www.atptour.com/-/media/files/media-guide/2026/2026-atp-media-guide-player-bios-birthdays.pdf"),
    "ATP:207678": ("Buenos Aires", "https://www.atptour.com/en/players/juan%20manuel-cerundolo/c0c8/overview"),
    "ATP:209920": ("Rochester, Minnesota", "https://www.atptour.com/-/media/8f48933340da440a970b88a697f31c5e.pdf"),
    "ATP:207686": ("Rostov-on-Don", "https://www.atptour.com/en/players/alexander-shevchenko/s0h2/overview"),
    "ATP:111513": ("Senta", "https://www.atptour.com/en/players/laslo-djere/db63/overview"),
    "WTA:220367": ("Montreal", "https://www.wtatennis.com/players/326735/leylah-fernandez"),
    "WTA:221012": ("Shiyan", "https://www.wtatennis.com/players/328120/qinwen-zheng"),
    "WTA:216133": ("Shenzhen", "https://www.wtatennis.com/players/326376/xinyu-wang/"),
}


def _read_text(path: Path | None, url: str, cache_path: Path, *, force: bool) -> tuple[str, str]:
    if path is not None:
        return path.read_text(encoding="utf-8"), datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat()
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    result = CachedHttpClient(session, delay=0, retries=3, timeout=120).fetch_text(
        url, cache_path, force=force
    )
    return result.text, result.retrieved_at


def parse_cohort(rankings_text: str, players_text: str, tour: str, *, ranking_date: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    if tour not in TOURS:
        raise ValueError(f"Unsupported tour: {tour}")
    players = {row["player_id"]: row for row in csv.DictReader(io.StringIO(players_text))}
    ranking_date = ranking_date or TOURS[tour]["ranking_date"]
    datetime.strptime(ranking_date, "%Y%m%d")
    if limit < 1:
        raise ValueError("Ranking limit must be positive")
    rankings = [
        row for row in csv.DictReader(io.StringIO(rankings_text))
        if row["ranking_date"] == ranking_date and 1 <= int(row["rank"]) <= limit
    ]
    ranks = sorted(int(row["rank"]) for row in rankings)
    if ranks != list(range(1, limit + 1)):
        raise ValueError(f"Expected exact {tour} ranks 1–{limit} on {ranking_date}; found {len(rankings)} rows")
    output = []
    for ranking in rankings:
        player = players.get(ranking["player"])
        if player is None:
            raise ValueError(f"Missing {tour} player metadata for {ranking['player']}")
        name = " ".join((player.get("name_first") or "", player.get("name_last") or "")).strip()
        if not name or not ranking.get("points"):
            raise ValueError(f"Incomplete {tour} ranking row at rank {ranking['rank']}")
        dob_raw = (player.get("dob") or "").strip()
        dob = f"{dob_raw[:4]}-{dob_raw[4:6]}-{dob_raw[6:8]}" if len(dob_raw) == 8 and dob_raw != "19000000" else None
        output.append({
            "tour": tour,
            "gender": TOURS[tour]["gender"],
            "ranking_date": f"{ranking_date[:4]}-{ranking_date[4:6]}-{ranking_date[6:]}",
            "rank": int(ranking["rank"]),
            "points": int(ranking["points"]),
            "tournaments": int(ranking.get("tours") or 0) or None,
            "player_id": ranking["player"],
            "name": name,
            "dob": dob,
            "represented_country": (player.get("ioc") or "").strip() or None,
            "hand": {"R": "Right-handed", "L": "Left-handed"}.get(player.get("hand"), "Hand unavailable"),
            "height_cm": int(player["height"]) if (player.get("height") or "").isdigit() else None,
            "wikidata_qid": (player.get("wikidata_id") or "").strip() or None,
        })
    return sorted(output, key=lambda row: row["rank"])


def fetch_cohorts(
    cache_dir: Path = DEFAULT_CACHE,
    *,
    atp_rankings_input: Path | None = None,
    atp_players_input: Path | None = None,
    wta_rankings_input: Path | None = None,
    wta_players_input: Path | None = None,
    ranking_dates: dict[str, str] | None = None,
    limit: int = 100,
    force: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inputs = {
        "ATP": (atp_rankings_input, atp_players_input),
        "WTA": (wta_rankings_input, wta_players_input),
    }
    rows: list[dict[str, Any]] = []
    retrieval: dict[str, str] = {}
    for tour, (rankings_input, players_input) in inputs.items():
        rankings_text, rankings_at = _read_text(
            rankings_input, INPUT_URLS[tour]["rankings"], cache_dir / f"{tour.lower()}_rankings_20s.csv",
            force=force,
        )
        players_text, players_at = _read_text(
            players_input, INPUT_URLS[tour]["players"], cache_dir / f"{tour.lower()}_players.csv",
            force=force,
        )
        rows.extend(parse_cohort(rankings_text, players_text, tour, ranking_date=(ranking_dates or {}).get(tour), limit=limit))
        retrieval[f"{tour.lower()}_rankings_retrieved_at"] = rankings_at
        retrieval[f"{tour.lower()}_players_retrieved_at"] = players_at
    return rows, retrieval


def fetch_birthplaces(
    players: list[dict[str, Any]], cache_path: Path = DEFAULT_WIKIDATA_CACHE, *, force: bool = False,
) -> dict[str, dict[str, Any]]:
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": "TalentGeography/1.0 (research; github.com/adhni/football-geo)"})
    client = CachedHttpClient(session, delay=0.1, retries=3, timeout=90)

    titles_by_id = {
        f"{row['tour']}:{row['player_id']}": [
            row["name"], f"{row['name']} (tennis)", f"{row['name']} (tennis player)"
        ]
        for row in players if not row.get("wikidata_qid")
    }
    title_qids = _fetch_title_qids(
        client, [title for titles in titles_by_id.values() for title in titles], batch_size=40, force=force,
    ) if titles_by_id else {}
    candidate_qids = {
        qid for qid in title_qids.values() if qid
    } | {row["wikidata_qid"] for row in players if row.get("wikidata_qid")}
    people = _fetch_entities(client, list(candidate_qids), "tennis_person_batches", batch_size=30, force=force)

    selected: dict[str, str] = {}
    for row in players:
        key = f"{row['tour']}:{row['player_id']}"
        candidates = {row["wikidata_qid"]} if row.get("wikidata_qid") else {
            title_qids.get(title) for title in titles_by_id.get(key, [])
        }
        matches = set()
        for qid in candidates - {None}:
            entity = people.get(qid, {})
            same_name = normalize(entity_label(entity)) == normalize(row["name"])
            wikidata_dob = claim_date(entity)
            same_dob = not row.get("dob") or not wikidata_dob or row["dob"] == wikidata_dob
            if same_name and same_dob:
                matches.add(qid)
        if len(matches) == 1:
            selected[key] = matches.pop()

    place_by_player = {
        key: claim_entity(people.get(qid, {}), "P19") for key, qid in selected.items()
    }
    places = _fetch_entities(
        client, [qid for qid in place_by_player.values() if qid], "tennis_place_batches",
        batch_size=30, force=force,
    )
    countries = _fetch_entities(
        client, [qid for entity in places.values() if (qid := claim_entity(entity, "P17"))],
        "tennis_country_batches", batch_size=30, force=force,
    )
    output: dict[str, dict[str, Any]] = {"_meta": {"schema_version": 1, "source": "Wikidata"}}
    for key, person_qid in selected.items():
        place_qid = place_by_player.get(key)
        entity = places.get(place_qid, {})
        lat, lon = claim_coordinates(entity)
        if lat is None or lon is None:
            continue
        country_qid = claim_entity(entity, "P17")
        output[key] = {
            "wikidata_qid": person_qid,
            "birth_place_qid": place_qid,
            "dob": claim_date(people.get(person_qid, {})),
            "place": entity_label(entity),
            "country": entity_label(countries.get(country_qid, {})),
            "lat": lat,
            "lon": lon,
            "resolution_source": "Wikidata identity matched by stable ID or exact name and DOB",
        }

    unresolved_overrides = {
        key: value for key, value in OFFICIAL_BIRTHPLACE_OVERRIDES.items() if key not in output
    }
    if unresolved_overrides:
        override_qids = _fetch_title_qids(
            client, [value[0] for value in unresolved_overrides.values()], batch_size=40, force=force,
        )
        override_places = _fetch_entities(
            client, [qid for qid in override_qids.values() if qid], "tennis_official_place_batches",
            batch_size=30, force=force,
        )
        override_countries = _fetch_entities(
            client, [qid for entity in override_places.values() if (qid := claim_entity(entity, "P17"))],
            "tennis_official_country_batches", batch_size=30, force=force,
        )
        players_by_key = {f"{row['tour']}:{row['player_id']}": row for row in players}
        for key, (title, source_url) in unresolved_overrides.items():
            place_qid = override_qids.get(title)
            entity = override_places.get(place_qid, {})
            lat, lon = claim_coordinates(entity)
            country_qid = claim_entity(entity, "P17")
            country = entity_label(override_countries.get(country_qid, {}))
            if lat is None or lon is None or not country:
                continue
            output[key] = {
                "wikidata_qid": selected.get(key) or players_by_key[key].get("wikidata_qid"),
                "birth_place_qid": place_qid,
                "dob": players_by_key[key].get("dob"),
                "place": title,
                "country": country,
                "lat": lat,
                "lon": lon,
                "resolution_source": f"Official tour profile; coordinates from Wikidata ({source_url})",
            }
    _write_json(cache_path, output, pretty=True)
    return output


def age_on(dob: str | None) -> int | None:
    return _age_on(dob, SEASON_END)


def build_payload(
    cohort: list[dict[str, Any]], places: dict[str, dict[str, Any]], source_meta: dict[str, Any],
    *, generated_at: str | None = None, limit: int = 100, ranking_dates: dict[str, str] | None = None,
) -> dict[str, Any]:
    dates = ranking_dates or {tour: details["ranking_date"] for tour, details in TOURS.items()}
    years = {datetime.strptime(value, "%Y%m%d").year for value in dates.values()}
    if len(years) != 1:
        raise ValueError("ATP and WTA snapshot dates must be in the same year")
    year = years.pop()
    snapshot_date = max(datetime.strptime(value, "%Y%m%d").date() for value in dates.values())
    year_end = dates == {tour: details["ranking_date"] for tour, details in TOURS.items()}
    records, unresolved = [], []
    for player in cohort:
        source_key = f"{player['tour']}:{player['player_id']}"
        place = places.get(source_key, {})
        mapped = place.get("lat") is not None and place.get("lon") is not None
        dob = place.get("dob") or player.get("dob")
        status = "verified birthplace" if mapped else "birthplace or coordinates unresolved"
        record = {
            "id": f"tennis:{player['tour'].lower()}:{player['player_id']}",
            "sourcePlayerId": player["player_id"],
            "name": player["name"],
            "team": player["tour"],
            "teamCode": player["tour"],
            "teams": [player["tour"]],
            "conference": player["tour"],
            "tour": player["tour"],
            "gender": player["gender"],
            "year": year,
            "rankingDate": player["ranking_date"],
            "rank": player["rank"],
            "points": player["points"],
            "games": 1,
            "tournaments": player.get("tournaments"),
            "position": f"{player['gender']}’s singles · {player['hand']}",
            "hand": player["hand"],
            "heightCm": player.get("height_cm"),
            "dob": dob,
            "age": _age_on(dob, snapshot_date),
            "nationality": player.get("represented_country"),
            "representedCountry": player.get("represented_country"),
            "place": place.get("place") if mapped else None,
            "country": place.get("country") if mapped else None,
            "lat": place.get("lat") if mapped else None,
            "lon": place.get("lon") if mapped else None,
            "mapped": mapped,
            "status": status,
            "locationType": "birthplace" if mapped else None,
            "wikidataQid": place.get("wikidata_qid") or player.get("wikidata_qid"),
            "birthPlaceQid": place.get("birth_place_qid"),
            "birthplaceSource": place.get("resolution_source") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": record["name"], "tour": record["tour"], "status": status})
    records.sort(key=lambda row: (row["tour"], row["rank"]))
    mapped_records = [row for row in records if row["mapped"]]
    points = sum(row["points"] for row in records)
    mapped_points = sum(row["points"] for row in mapped_records)
    return {
        "meta": {
            "title": "Tennis Talent Geography",
            "sport": "tennis",
            "scope": f"{year}{' year-end' if year_end else ''} ATP and WTA singles top {limit}",
            "season": f"{year} {'year-end' if year_end else 'ranking snapshot'}",
            "year": year,
            "cohort_limit": limit,
            "snapshot_date": snapshot_date.isoformat(),
            "teams": ["ATP", "WTA"],
            "conferences": ["ATP", "WTA"],
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "ranking_dates": dates,
            "ranking_source_name": "Official ATP and WTA year-end singles rankings" if year_end else "Tennis Sackmann Archive singles ranking snapshot",
            "ranking_source_urls": OFFICIAL_SOURCES if year_end else {"ATP": "https://www.atptour.com/en/rankings/singles", "WTA": "https://www.wtatennis.com/rankings/singles"},
            "processed_snapshot_name": "Tennis Sackmann Archive",
            "processed_snapshot_url": "https://github.com/Aneeshers/tennis-sackmann-archive",
            "birthplace_source_name": "Wikidata",
            "birthplace_source_url": "https://www.wikidata.org/",
            **source_meta,
        },
        "summary": {
            "teams": 2,
            "players": len(records),
            "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "points": points,
            "mapped_points": mapped_points,
            "point_coverage_pct": round(mapped_points / points * 100, 1) if points else 0,
            "birthplaces": len({(row["lat"], row["lon"], row["place"]) for row in mapped_records}),
            "birth_countries": len({row["country"] for row in mapped_records}),
            "unresolved_players": len(unresolved),
        },
        "records": records,
        "unresolved": unresolved,
    }


def run(
    output_path: Path = DEFAULT_OUTPUT,
    *,
    cache_dir: Path = DEFAULT_CACHE,
    wikidata_cache: Path = DEFAULT_WIKIDATA_CACHE,
    atp_rankings_input: Path | None = None,
    atp_players_input: Path | None = None,
    wta_rankings_input: Path | None = None,
    wta_players_input: Path | None = None,
    ranking_dates: dict[str, str] | None = None,
    limit: int = 100,
    force: bool = False,
) -> dict[str, Any]:
    dates = ranking_dates or {tour: details["ranking_date"] for tour, details in TOURS.items()}
    if set(dates) != set(TOURS) or len({datetime.strptime(value, "%Y%m%d").year for value in dates.values()}) != 1 or limit < 1:
        raise ValueError("Provide valid ATP and WTA dates in one year and a positive ranking limit")
    custom = limit != 100 or dates != {tour: details["ranking_date"] for tour, details in TOURS.items()}
    if custom and output_path.resolve() == DEFAULT_OUTPUT.resolve():
        raise ValueError("Custom tennis cohorts require --output outside the published snapshot; rebuild their population layers separately")
    if custom and wikidata_cache == DEFAULT_WIKIDATA_CACHE:
        wikidata_cache = cache_dir / f"birthplaces_{dates['ATP']}_{dates['WTA']}_top{limit}.json"
    cohort, source_meta = fetch_cohorts(
        cache_dir,
        atp_rankings_input=atp_rankings_input,
        atp_players_input=atp_players_input,
        wta_rankings_input=wta_rankings_input,
        wta_players_input=wta_players_input,
        ranking_dates=dates,
        limit=limit,
        force=force,
    )
    payload = build_payload(cohort, fetch_birthplaces(cohort, wikidata_cache, force=force), source_meta, limit=limit, ranking_dates=dates)
    if len(payload["records"]) != 2 * limit or any(
        len([row for row in payload["records"] if row["tour"] == tour]) != limit for tour in TOURS
    ):
        raise ValueError(f"Tennis top-{limit} reconciliation failed")
    _write_json(output_path, payload)
    print(
        f"Wrote {limit} ATP and {limit} WTA players with {payload['summary']['player_coverage_pct']}% "
        f"birthplace coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an explicit ATP/WTA singles ranking cohort")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--wikidata-cache", type=Path, default=DEFAULT_WIKIDATA_CACHE)
    parser.add_argument("--atp-rankings-input", type=Path)
    parser.add_argument("--atp-players-input", type=Path)
    parser.add_argument("--wta-rankings-input", type=Path)
    parser.add_argument("--wta-players-input", type=Path)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--atp-ranking-date", default=TOURS["ATP"]["ranking_date"], help="YYYYMMDD")
    parser.add_argument("--wta-ranking-date", default=TOURS["WTA"]["ranking_date"], help="YYYYMMDD")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(
        args.output,
        cache_dir=args.cache_dir,
        wikidata_cache=args.wikidata_cache,
        atp_rankings_input=args.atp_rankings_input,
        atp_players_input=args.atp_players_input,
        wta_rankings_input=args.wta_rankings_input,
        wta_players_input=args.wta_players_input,
        ranking_dates={"ATP": args.atp_ranking_date, "WTA": args.wta_ranking_date},
        limit=args.limit,
        force=args.force,
    )


if __name__ == "__main__":
    main()
