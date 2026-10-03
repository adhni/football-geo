"""Import an explicitly sourced ITTF singles ranking pilot without guessing birthplaces."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.ftg.build_edition_catalog import validate_dashboard
from src.ftg.utils import age_on, write_json

EVENTS = {"MS": "Men", "WS": "Women"}
EDITION = {"id": "table-tennis", "workloadField": "points"}


def parse_rankings(text: str, *, ranking_date: str, limit: int = 100) -> list[dict[str, Any]]:
    date.fromisoformat(ranking_date)
    if limit < 1:
        raise ValueError("Ranking limit must be positive")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    required = {"event", "rank", "player_id", "name", "represented_country", "points", "ranking_date"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError(f"Ranking CSV requires columns: {', '.join(sorted(required))}")
    rows = []
    for source in reader:
        if source["ranking_date"] != ranking_date:
            continue
        if source["event"] not in EVENTS:
            raise ValueError("The pilot supports MS and WS singles only; doubles need pair contribution rules")
        rank = int(source["rank"])
        if not 1 <= rank <= limit:
            continue
        identifier = source["player_id"].strip()
        points = int(source["points"].replace(",", ""))
        if not identifier.isascii() or not identifier.isdigit() or not source["name"].strip() or points < 0 or not source["represented_country"].strip():
            raise ValueError("Each ranking requires a numeric WTT player ID, name, represented country and nonnegative points")
        dob = source.get("dob", "").strip() or None
        if dob:
            date.fromisoformat(dob)
        rows.append({
            "event": source["event"], "rank": rank, "sourcePlayerId": identifier,
            "name": source["name"].strip(), "representedCountry": source["represented_country"].strip(),
            "points": points, "rankingDate": ranking_date, "dob": dob,
        })
    for event in EVENTS:
        selected = [row for row in rows if row["event"] == event]
        if sorted(row["rank"] for row in selected) != list(range(1, limit + 1)):
            raise ValueError(f"Expected exact {event} ranks 1–{limit} on {ranking_date}")
    if len({row["sourcePlayerId"] for row in rows}) != len(rows):
        raise ValueError("Duplicate WTT player identity in singles cohort")
    return sorted(rows, key=lambda row: (row["event"], row["rank"]))


def build_payload(rows: list[dict[str, Any]], places: dict[str, dict[str, Any]], *, ranking_date: str, limit: int, source_url: str, source_hash: str, generated_at: str | None = None) -> dict[str, Any]:
    snapshot = date.fromisoformat(ranking_date)
    records, unresolved = [], []
    for row in rows:
        place = places.get(row["sourcePlayerId"], {})
        identity_verified = place.get("source_player_id") == row["sourcePlayerId"] and bool(place.get("wikidata_qid")) and bool(place.get("source_url"))
        dob_matches = not row["dob"] or place.get("dob") == row["dob"]
        lat, lon = place.get("lat"), place.get("lon")
        coordinates_valid = isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and -90 <= lat <= 90 and -180 <= lon <= 180
        mapped = identity_verified and dob_matches and coordinates_valid and bool(place.get("place")) and bool(place.get("country"))
        dob = row["dob"] or (place.get("dob") if identity_verified else None)
        status = "verified birthplace" if mapped else "birthplace or verified WTT identity unresolved"
        gender = EVENTS[row["event"]]
        record = {
            **row, "id": f"table-tennis:wtt:{row['sourcePlayerId']}", "year": snapshot.year,
            "team": gender, "teamCode": row["event"], "teams": [gender], "conference": gender, "gender": gender,
            "position": f"{gender}’s singles", "games": 1, "dob": dob, "age": age_on(dob, snapshot),
            "nationality": row["representedCountry"], "mapped": mapped, "status": status,
            "locationType": "birthplace" if mapped else None,
            "place": place.get("place") if mapped else None, "country": place.get("country") if mapped else None,
            "lat": lat if mapped else None, "lon": lon if mapped else None,
            "wikidataQid": place.get("wikidata_qid") if identity_verified else None,
            "birthPlaceQid": place.get("birth_place_qid") if mapped else None,
            "birthplaceSource": place.get("source_url") if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": row["name"], "sourcePlayerId": row["sourcePlayerId"], "status": status})
    mapped_rows = [row for row in records if row["mapped"]]
    points = sum(row["points"] for row in records)
    mapped_points = sum(row["points"] for row in mapped_rows)
    payload = {
        "meta": {
            "title": "Table Tennis Talent Geography", "sport": "table-tennis", "status": "pilot",
            "scope": f"ITTF men's and women's singles top {limit} on {ranking_date}",
            "season": ranking_date, "year": snapshot.year, "ranking_date": ranking_date, "cohort_limit": limit,
            "teams": list(EVENTS.values()), "conferences": list(EVENTS.values()),
            "ranking_source_name": "ITTF world singles rankings", "ranking_source_url": source_url,
            "ranking_source_sha256": source_hash, "birthplace_source_name": "Verified WTT identities and recorded birthplaces",
            "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
        "summary": {
            "teams": 2, "players": len(records), "mapped_players": len(mapped_rows), "unresolved_players": len(unresolved),
            "player_coverage_pct": round(len(mapped_rows) / len(records) * 100, 1) if records else 0,
            "points": points, "mapped_points": mapped_points, "point_coverage_pct": round(mapped_points / points * 100, 1) if points else 0,
            "birthplaces": len({(row["lat"], row["lon"]) for row in mapped_rows}), "birth_countries": len({row["country"] for row in mapped_rows}),
        },
        "records": records, "unresolved": unresolved,
    }
    validate_dashboard(payload, EDITION)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rankings-input", type=Path, required=True)
    parser.add_argument("--birthplaces-input", type=Path, help="Verified identity/location JSON keyed by WTT player ID")
    parser.add_argument("--ranking-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--source-url", required=True, help="Exact URL of the imported official ranking")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    content = args.rankings_input.read_bytes()
    rows = parse_rankings(content.decode("utf-8-sig"), ranking_date=args.ranking_date, limit=args.limit)
    places = json.loads(args.birthplaces_input.read_text(encoding="utf-8")) if args.birthplaces_input else {}
    payload = build_payload(rows, places, ranking_date=args.ranking_date, limit=args.limit, source_url=args.source_url, source_hash=hashlib.sha256(content).hexdigest())
    write_json(args.output, payload)
    print(f"Wrote {len(rows)} table-tennis players; {payload['summary']['player_coverage_pct']}% verified birthplace coverage")


if __name__ == "__main__":
    main()
