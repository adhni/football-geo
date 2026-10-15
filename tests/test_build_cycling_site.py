import json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import h3
import pytest

from src.ftg.build_cycling_site import (
    EVENTS, aggregate_results, build_payload, display_name, resolve_identities,
    search_identity_bindings,
)
from src.ftg.http_cache import FetchResult

ROOT = Path(__file__).resolve().parents[1]


def result(identifier="10000000001", name="RIDER First", nation="BEL", *, status="Finished", rank=1):
    return {
        "rider": {"uciRiderId": identifier, "name": name, "nation": nation, "bib": 1},
        "resultType": "Time" if status == "Finished" else "IRM", "rank": rank if status == "Finished" else 0,
        "value": "1:00:00" if status == "Finished" else status, "time": "1:00:00" if status == "Finished" else status,
    }


def pages(road, itt):
    return {key: {"event": {"number": spec["number"], "name": spec["source_name"]}, "results": rows}
            for (key, spec), rows in zip(EVENTS.items(), (road, itt))}


def binding(qid="Q1", name="First Rider", dob="2000-01-01", coord="Point(4 50)"):
    return {key: {"value": value} for key, value in {
        "lookup": name, "personLabel": name, "person": f"http://www.wikidata.org/entity/{qid}",
        "dob": dob + "T00:00:00Z", "birthplace": "http://www.wikidata.org/entity/Q2",
        "birthplaceLabel": "City", "countryLabel": "Belgium", "coord": coord,
    }.items()}


def test_actual_starters_are_deduplicated_across_events_and_dns_is_excluded():
    data = pages([result(status="DNF"), result("10000000002", status="DNS")], [result()])
    riders = aggregate_results(data, {"10000000001": "2000-01-01"}, {"BEL": "Belgium"}, validate_counts=False)
    payload = build_payload(riders, {}, {})
    assert len(riders) == 1
    assert payload["summary"]["starts"] == 2
    assert payload["summary"]["finishes"] == 1
    assert payload["summary"]["gold"] == 1
    row = payload["records"][0]
    assert [split["starts"] for split in row["teamSplits"]] == [1, 1]
    assert [split["finishes"] for split in row["teamSplits"]] == [0, 1]
    assert row["eventNames"] == ["Road race", "Individual time trial"]
    assert row["age"] == 25
    assert row["mapped"] is False
    assert payload["summary"]["unresolved_players"] == 1


@pytest.mark.parametrize("status", ["DNF", "OTL", "DSQ"])
def test_non_finishing_results_still_count_as_starts(status):
    riders = aggregate_results(pages([result(status=status)], []), {}, {"BEL": "Belgium"}, validate_counts=False)
    assert len(riders[0]["eventLog"]) == 1
    assert riders[0]["eventLog"][0]["position"] is None
    assert riders[0]["eventLog"][0]["medal"] is None


def test_cohort_rejects_duplicate_id_wrong_event_and_incomplete_source():
    with pytest.raises(ValueError, match="duplicate UCI"):
        aggregate_results(pages([result(), result()], []), {}, {"BEL": "Belgium"}, validate_counts=False)
    data = pages([result()], [])
    data["road"]["event"]["name"] = "Women Elite Road Race"
    with pytest.raises(ValueError, match="Wrong event"):
        aggregate_results(data, {}, {"BEL": "Belgium"}, validate_counts=False)
    with pytest.raises(ValueError, match="Incomplete"):
        aggregate_results(pages([result()], []), {}, {"BEL": "Belgium"})


def test_identity_matching_requires_unique_cyclist_and_known_official_dob():
    rider = {"sourcePlayerId": "10000000001", "name": "First Rider", "officialName": "RIDER First", "dob": "2000-01-01"}
    assert resolve_identities([rider], [binding()])[rider["sourcePlayerId"]]["place"] == "City"
    assert resolve_identities([rider], [binding(dob="2000-01-02")]) == {}
    assert resolve_identities([rider], [binding(), binding(qid="Q3")]) == {}
    # Contradictory birthplace claims retain the rider for QA without coordinates.
    identity = resolve_identities([rider], [binding(), binding(coord="Point(5 51)")])[rider["sourcePlayerId"]]
    assert "lat" not in identity


def test_invalid_birthplace_coordinates_do_not_enter_population_layers():
    rider = {"sourcePlayerId": "1", "name": "First Rider", "officialName": "RIDER First", "dob": None}
    identity = resolve_identities([rider], [binding(coord="Point(5 95)")])["1"]
    assert "lat" not in identity


def test_name_search_only_discovers_candidates_and_requires_a_documented_exact_alias(tmp_path):
    def claim(value):
        return {"rank": "normal", "mainsnak": {"snaktype": "value", "datavalue": {"value": value}}}

    entities = {
        "Q1": {"labels": {"en": {"value": "First Rider"}}, "aliases": {"en": [{"value": "First Full Rider"}]}, "claims": {
            "P31": [claim({"id": "Q5"})], "P1663": [claim("123")],
            "P569": [claim({"time": "+2000-01-01T00:00:00Z"})], "P19": [claim({"id": "Q2"})],
        }},
        "Q2": {"labels": {"en": {"value": "City"}}, "claims": {
            "P625": [claim({"latitude": 50, "longitude": 4})], "P17": [claim({"id": "Q3"})],
        }},
        "Q3": {"labels": {"en": {"value": "Belgium"}}, "claims": {}},
    }

    class Client:
        def fetch_text(self, url, path, *, force=False):
            params = parse_qs(urlparse(url).query)
            if params["action"] == ["wbsearchentities"]:
                data = {"search": [{"id": "Q1"}]}
            else:
                data = {"entities": {qid: entities[qid] for qid in params["ids"][0].split("|")}}
            return FetchResult(json.dumps(data), "2026-10-16T00:00:00Z", 200, True)

    rider = {"sourcePlayerId": "1", "name": "First Full Rider", "officialName": "FULL RIDER First", "dob": "2000-01-01"}
    bindings = search_identity_bindings([rider], Client(), tmp_path, [])
    assert resolve_identities([rider], bindings)["1"]["place"] == "City"
    # A search result alone does not establish a different source identity.
    wrong = {**rider, "name": "Second Rider", "officialName": "RIDER Second"}
    assert search_identity_bindings([wrong], Client(), tmp_path, []) == []
    wrong_dob = {**rider, "dob": "2001-01-01"}
    assert search_identity_bindings([wrong_dob], Client(), tmp_path, []) == []


@pytest.mark.parametrize(("raw", "expected"), [("POGAČAR Tadej", "Tadej Pogačar"), ("van WILDER Ilan", "Ilan van Wilder"), ("del TORO ROMERO Isaac", "Isaac del Toro Romero")])
def test_timing_names_keep_given_names_and_surname_particles(raw, expected):
    assert display_name(raw) == expected


def test_committed_cycling_cohort_reconciles_official_mens_results():
    payload = json.loads((ROOT / "docs/cycling/data/dashboard.json").read_text())
    rows, summary = payload["records"], payload["summary"]
    assert len(rows) == summary["players"] == 182
    assert len({row["sourcePlayerId"] for row in rows}) == 182
    assert {row["gender"] for row in rows} == {"Men"}
    assert sum(row["starts"] for row in rows) == summary["starts"] == 218
    assert sum(row["finishes"] for row in rows) == summary["finishes"] == 84
    assert sum(row["medals"] for row in rows) == summary["medals"] == 6
    assert Counter(event["event"] for row in rows for event in row["eventLog"]) == {"Road race": 164, "Individual time trial": 54}
    assert sum(row["mapped"] for row in rows) == summary["mapped_players"]
    assert summary["mapped_players"] + summary["unresolved_players"] == 182
    assert all(row["team"] != "Uci World Cycling Centre" for row in rows)
    for row in rows:
        assert sum(split["starts"] for split in row["teamSplits"]) == row["starts"]
        assert sum(split["medals"] for split in row["teamSplits"]) == row["medals"]
        assert all(event["status"] != "DNS" for event in row["eventLog"])
    assert {row["name"] for row in rows if row["gold"]} == {"Tadej Pogačar", "Remco Evenepoel"}


@pytest.mark.parametrize("resolution", [1, 2, 3])
def test_cycling_population_layers_use_current_birthplace_membership(resolution):
    payload = json.loads((ROOT / "docs/cycling/data/dashboard.json").read_text())
    geo = json.loads((ROOT / f"docs/cycling/data/population_hexes_r{resolution}.geojson").read_text())
    cells = {feature["properties"]["hex_id"]: feature["properties"] for feature in geo["features"]}
    ids = [identifier for cell in cells.values() for identifier in cell["player_ids"]]
    mapped = [row for row in payload["records"] if row["mapped"]]
    assert len(ids) == len(set(ids)) == len(mapped)
    assert set(ids) == {row["id"] for row in mapped}
    for row in mapped:
        assert row["id"] in cells[h3.latlng_to_cell(row["lat"], row["lon"], resolution)]["player_ids"]
    assert geo["metadata"]["reference_cells"] > 0
    assert geo["metadata"]["population_year"] == 2025
