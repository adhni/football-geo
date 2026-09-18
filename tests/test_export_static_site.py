import json

import pandas as pd
import pytest

from src.ftg import export_static_site as exporter
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


@pytest.fixture
def top5_data():
    data = pd.DataFrame(
        {
            "player_id": ["p1"], "player_name": ["Player"], "team": ["Arsenal"],
            "league": ["Premier League"], "season_end_year": [2026], "starts": [4],
            "sub_appearances": [2], "appearances": [6], "minutes": [400], "goals": [1],
            "assists": [2], "position_source": ["MF"], "nationality_source": ["ENG"],
            "birth_year": [2000], "dob": ["2000-02-03"], "pob_mapped": [True],
            "resolution_status": ["resolved"], "birthplace_wikidata": ["London"],
            "birth_country": ["United Kingdom"], "birth_lat": [51.5], "birth_lon": [-0.1],
            "birth_place_qid": ["Q84"],
        }
    )
    return data


def test_build_payload_exports_top5_metadata_and_stats(top5_data):
    payload = build_payload(top5_data)
    assert payload["meta"]["scope"] == "2025–26 Big Five European domestic leagues"
    assert payload["meta"]["leagues"] == ["Premier League"]
    assert payload["summary"]["appearances"] == 6
    assert payload["records"][0]["birthYear"] == 2000


def test_cli_defaults_export_big_five_and_matching_qa(tmp_path, monkeypatch, top5_data):
    inputs = []
    qa_inputs = []

    def read_parquet(path):
        inputs.append(path)
        return top5_data

    qa = tmp_path / "top5-qa.csv"
    qa.touch()
    monkeypatch.setattr(exporter, "DEFAULT_UNRESOLVED", qa)
    monkeypatch.setattr(exporter.pd, "read_parquet", read_parquet)
    monkeypatch.setattr(exporter.pd, "read_csv", lambda path: qa_inputs.append(path) or pd.DataFrame())
    output = tmp_path / "dashboard.json"
    monkeypatch.setattr("sys.argv", ["export_static_site", "--output", str(output)])
    exporter.main()
    assert inputs == [exporter.DEFAULT_INPUT]
    assert inputs[0].name == "top5_players_with_birthplace.parquet"
    assert qa_inputs == [qa]
    assert json.loads(output.read_text())["meta"]["leagues"] == ["Premier League"]


@pytest.mark.parametrize("invalid", ["worldcup", "season", "league", "empty"])
def test_live_export_rejects_wrong_cohort_without_changing_existing_file(tmp_path, monkeypatch, top5_data, invalid):
    data = top5_data.copy()
    if invalid == "worldcup":
        data = data.drop(columns="league")
    elif invalid == "season":
        data["season_end_year"] = 2025
    elif invalid == "league":
        data["league"] = "Other league"
    else:
        data = data.iloc[:0]
    output = tmp_path / "dashboard.json"
    output.write_text("existing dashboard")
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT", output)
    source = tmp_path / "input.parquet"
    data.to_parquet(source)
    with pytest.raises(ValueError, match="reserved"):
        exporter.run(source, tmp_path / "missing.csv", output)
    assert output.read_text() == "existing dashboard"


def test_historical_export_requires_separate_destination(tmp_path, top5_data):
    data = top5_data.drop(columns="league")
    data["season_end_year"] = 2022
    source = tmp_path / "worldcup.parquet"
    data.to_parquet(source)
    output = tmp_path / "historical" / "dashboard.json"
    exporter.run(source, tmp_path / "missing.csv", output)
    assert json.loads(output.read_text())["meta"]["scope"] == "FIFA Men's World Cup finals only"
