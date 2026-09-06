import json
from collections import Counter
from pathlib import Path

import pytest

from src.ftg.build_padel_site import build_payload, parse_profile, parse_ranking, resolve_place


ROOT = Path(__file__).resolve().parents[1]


def _ranking(count=100):
    return [
        {
            "player_id": f"P{rank:06d}", "name": "Player", "surname": str(rank),
            "rank": rank, "points": 10001 - rank,
            "url": f"https://www.padelfip.com/player/player-{rank}/", "country_name": "ESP",
        }
        for rank in range(1, count + 1)
    ]


@pytest.mark.parametrize("division", ["Men", "Women"])
def test_parse_ranking_requires_exact_top_100(division):
    rows = parse_ranking(_ranking(), division)

    assert len(rows) == 100
    assert rows[0]["rank"] == 1
    assert rows[-1]["rank"] == 100
    assert rows[0]["points"] == 10000


def test_parse_ranking_rejects_incomplete_cohort():
    with pytest.raises(ValueError, match="Expected 100"):
        parse_ranking(_ranking(99), "Men")


def test_parse_profile_uses_official_json_ld():
    profile_html = '''
    <div class="summary__player playerID-P000010"></div>
    <script type="application/ld+json" class="yoast-schema-graph">
    {"@graph":[{"@type":"Person","name":"Arturo Coello","gender":"Male",
    "nationality":{"@type":"Country","name":"ESP"},"birthDate":"2002-03-08",
    "birthPlace":{"@type":"Place","name":"Valladolid"},"height":"1.90",
    "description":"Playing Position: Right;"}]}
    </script>'''

    profile = parse_profile(profile_html, "Arturo Coello", "P000010")

    assert profile["dob"] == "2002-03-08"
    assert profile["birth_place"] == "Valladolid"
    assert profile["height_cm"] == 190
    assert profile["playing_position"] == "Right"


def test_resolve_place_rejects_ambiguous_equal_candidates():
    cities = {"springfield": [
        {"name": "Springfield", "lat": 1, "lon": 2, "country_code": "US", "population": 100000, "geonames_id": "1"},
        {"name": "Springfield", "lat": 3, "lon": 4, "country_code": "CA", "population": 50000, "geonames_id": "2"},
    ]}

    assert resolve_place("P1", "Springfield", cities, {"US": "United States", "CA": "Canada"}) is None


def test_payload_reconciles_players_and_point_coverage():
    cohort = parse_ranking(_ranking(), "Men")[:2]
    profiles = {
        "P000001": {"dob": "2002-03-08", "birth_place": "Valladolid", "height_cm": 190, "playing_position": "Right"},
        "P000002": {"dob": "2000-01-01", "birth_place": None, "height_cm": None, "playing_position": None},
    }
    cities = {"valladolid": [{
        "name": "Valladolid", "lat": 41.65, "lon": -4.72, "country_code": "ES",
        "population": 300000, "geonames_id": "3106672",
    }]}

    payload = build_payload(cohort, profiles, cities, {"ES": "Spain"}, {}, generated_at="2026-09-06T00:00:00+00:00")

    assert payload["summary"]["players"] == 2
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["points"] == 19999
    assert payload["summary"]["mapped_points"] == 10000
    assert payload["records"][0]["locationType"] == "birthplace"


def test_published_padel_snapshot_reconciles_exact_top_100_cohorts():
    payload = json.loads(
        (ROOT / "docs" / "padel" / "data" / "dashboard.json").read_text(encoding="utf-8")
    )
    records = payload["records"]
    mapped = [record for record in records if record["mapped"]]

    assert payload["meta"]["sport"] == "padel"
    assert len(records) == 200
    assert Counter(record["conference"] for record in records) == {"Men": 100, "Women": 100}
    assert len({record["id"] for record in records}) == 200
    assert payload["summary"]["players"] == len(records)
    assert payload["summary"]["mapped_players"] == len(mapped)
    assert payload["summary"]["points"] == sum(record["points"] for record in records)
    assert payload["summary"]["mapped_points"] == sum(record["points"] for record in mapped)
