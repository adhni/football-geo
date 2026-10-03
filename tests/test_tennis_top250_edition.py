import csv
import json
from collections import Counter
from pathlib import Path

import h3
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/tennis-250/data"


def test_published_top250_is_an_exact_expansion_with_public_coverage_gaps():
    payload = json.loads((DATA / "dashboard.json").read_text())
    records = payload["records"]
    old = json.loads((ROOT / "docs/tennis/data/dashboard.json").read_text())
    expanded = {row["id"]: row for row in records}
    assert len(expanded) == len(records) == 500
    for tour in ("ATP", "WTA"):
        assert sorted(row["rank"] for row in records if row["tour"] == tour) == list(range(1, 251))
    for row in old["records"]:
        current = expanded[row["id"]]
        assert (current["name"], current["rank"], current["points"]) == (row["name"], row["rank"], row["points"])
        if row["mapped"]:
            assert current["mapped"]
    assert payload["meta"]["ranking_dates"] == {"ATP": "20251117", "WTA": "20251110"}
    assert payload["meta"]["cohort_limit"] == 250
    assert payload["summary"]["mapped_players"] == 462
    assert payload["summary"]["unresolved_players"] == 38
    assert payload["summary"]["points"] == sum(row["points"] for row in records)
    assert payload["summary"]["mapped_points"] == sum(row["points"] for row in records if row["mapped"])
    with (DATA / "birthplace_qa.csv").open() as handle:
        qa = list(csv.DictReader(handle))
    assert {row["id"] for row in qa} == {row["id"] for row in records if not row["mapped"]}
    for row in records:
        assert row["age"] is not None
        if row["mapped"]:
            assert row["locationType"] == "birthplace"
            assert row["birthPlaceQid"] and row["place"] and row["country"]
            assert row["wikidataQid"] or "Official tour profile" in row["birthplaceSource"]
        else:
            assert row["lat"] is None and row["lon"] is None


@pytest.mark.parametrize("resolution", [1, 2, 3])
def test_population_membership_is_rebuilt_from_the_expanded_birthplaces(resolution):
    payload = json.loads((DATA / "dashboard.json").read_text())
    layer = json.loads((DATA / f"population_hexes_r{resolution}.geojson").read_text())
    expected = {row["id"]: h3.latlng_to_cell(row["lat"], row["lon"], resolution) for row in payload["records"] if row["mapped"]}
    seen = Counter()
    for feature in layer["features"]:
        properties = feature["properties"]
        assert properties["all_players"] == len(properties["player_ids"])
        assert properties["reference_cell"] == (len(properties["player_ids"]) == 0)
        for identifier in properties["player_ids"]:
            assert expected[identifier] == properties["hex_id"]
            seen[identifier] += 1
    assert seen == Counter({identifier: 1 for identifier in expected})
    assert layer["metadata"]["mapped_players"] == len(expected)
    assert layer["metadata"]["h3_resolution"] == resolution
    assert layer["metadata"]["population_method"] == "official_country_rasters"
    assert layer["metadata"]["reference_cells"] > 0
