import pandas as pd

from src.ftg.export_static_site import build_payload


def test_build_payload_exports_mapped_and_unresolved_records():
    data = pd.DataFrame(
        {
            "player_id": ["a", "b"],
            "player_name": ["A", "B"],
            "team": ["Italy", "Spain"],
            "season_end_year": [2006, 2010],
            "starts": [5, 2],
            "sub_appearances": [0, 1],
            "dob": ["1980-01-01", "1981-02-02"],
            "pob_mapped": [True, False],
            "resolution_status": ["resolved", "dob_mismatch"],
            "birthplace_wikidata": ["Rome", None],
            "birth_country": ["Italy", None],
            "birth_lat": [41.9, None],
            "birth_lon": [12.5, None],
            "birth_place_qid": ["Q1", None],
        }
    )
    unresolved = pd.DataFrame(
        {"player_name": ["B"], "resolution_status": ["dob_mismatch"]}
    )
    payload = build_payload(data, unresolved)
    assert payload["summary"]["players"] == 2
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["mapped_starts"] == 5
    assert payload["records"][0]["place"] == "Rome"
    assert payload["records"][1]["lat"] is None
    assert payload["unresolved"] == [{"name": "B", "status": "dob mismatch"}]
