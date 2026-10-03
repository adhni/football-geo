import pytest

from src.ftg.build_table_tennis_site import parse_rankings, build_payload


def rankings():
    return "ranking_date,event,rank,player_id,name,represented_country,points,dob\n2025-12-23,MS,1,100001,Example Man,AAA,1000,2000-01-01\n2025-12-23,WS,1,100002,Example Woman,BBB,900,2001-01-01\n"


def test_pilot_preserves_ranking_scales_and_unresolved_participants():
    rows = parse_rankings(rankings(), ranking_date="2025-12-23", limit=1)
    places = {"100001": {"source_player_id": "100001", "wikidata_qid": "Q1", "source_url": "https://www.wikidata.org/wiki/Q1", "dob": "2000-01-01", "place": "Example City", "country": "Example Country", "lat": 1, "lon": 2}}
    payload = build_payload(rows, places, ranking_date="2025-12-23", limit=1, source_url="https://www.ittf.com/2025-ittf-table-tennis-world-ranking/", source_hash="example")
    assert payload["summary"]["players"] == 2
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["points"] == 1900
    assert payload["summary"]["mapped_points"] == 1000
    assert len(payload["unresolved"]) == 1
    assert payload["meta"]["status"] == "pilot"


@pytest.mark.parametrize("change", [{"source_player_id": "wrong"}, {"dob": "2000-02-01"}, {"lat": float("nan")}, {"lon": 181}])
def test_pilot_rejects_unverified_identity_dob_mismatch_and_invalid_coordinates(change):
    rows = parse_rankings(rankings(), ranking_date="2025-12-23", limit=1)
    place = {"source_player_id": "100001", "wikidata_qid": "Q1", "source_url": "https://www.wikidata.org/wiki/Q1", "dob": "2000-01-01", "place": "Example City", "country": "Example Country", "lat": 1, "lon": 2, **change}
    payload = build_payload(rows, {"100001": place}, ranking_date="2025-12-23", limit=1, source_url="https://www.ittf.com/", source_hash="example")
    assert payload["summary"]["mapped_players"] == 0
    assert all(row["lat"] is None for row in payload["records"])


def test_pilot_does_not_accept_partial_or_mixed_date_rankings():
    with pytest.raises(ValueError, match="exact WS"):
        parse_rankings(rankings().replace("2025-12-23,WS", "2025-12-16,WS"), ranking_date="2025-12-23", limit=1)
    with pytest.raises(ValueError, match="Duplicate"):
        parse_rankings(rankings().replace("100002", "100001"), ranking_date="2025-12-23", limit=1)
