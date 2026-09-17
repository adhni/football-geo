from src.ftg.enrich_wikidata import (
    claim_coordinates,
    claim_date,
    claim_entity,
    entity_label,
    title_qid_map,
    wikipedia_title,
)


def test_unsupported_11v11_flow_fails_before_requests_or_output(tmp_path, monkeypatch):
    import pandas as pd
    import pytest
    from src.ftg import enrich_wikidata

    source = tmp_path / "players.parquet"
    pd.DataFrame([{
        "player_id": "p1", "player_url": "https://www.11v11.com/players/example-1/",
        "dob": "2000-01-01",
    }]).to_parquet(source)
    output = tmp_path / "enriched.parquet"
    output.write_bytes(b"existing output")
    monkeypatch.setattr(enrich_wikidata.requests, "Session", lambda: pytest.fail("Unexpected request setup"))
    with pytest.raises(ValueError, match="English Wikipedia"):
        enrich_wikidata.run(source, output)
    assert output.read_bytes() == b"existing output"


def test_wikipedia_title_and_redirect_qid_mapping():
    assert wikipedia_title("https://en.wikipedia.org/wiki/Gianluigi_Buffon") == "Gianluigi Buffon"
    response = {
        "query": {
            "redirects": [{"from": "Old Name", "to": "Current Name"}],
            "pages": {"1": {"title": "Current Name", "pageprops": {"wikibase_item": "Q1"}}},
        }
    }
    assert title_qid_map(response, ["Old Name"])["Old Name"] == "Q1"


def test_claim_parsers():
    entity = {
        "claims": {
            "P569": [
                {
                    "rank": "normal",
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"value": {"time": "+1978-01-28T00:00:00Z"}},
                    },
                }
            ],
            "P19": [
                {
                    "rank": "normal",
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"value": {"id": "Q123"}},
                    },
                }
            ],
            "P625": [
                {
                    "rank": "normal",
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"value": {"latitude": 44.1, "longitude": 10.1}},
                    },
                }
            ],
        }
    }
    assert claim_date(entity) == "1978-01-28"
    assert claim_entity(entity, "P19") == "Q123"
    assert claim_coordinates(entity) == (44.1, 10.1)
    assert entity_label({"labels": {"it": {"value": "Firenze"}}}) == "Firenze"
