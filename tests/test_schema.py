import pandas as pd
import pytest

from src.ftg.import_data import DataValidationError, coverage_reports, run
from src.ftg.schema import normalize_player_seasons, parse_season_end_year


def cohort():
    return pd.DataFrame(
        {
            "team": ["Italy", "Spain"],
            "fifa_code": ["ITA", "ESP"],
        }
    )


def test_normalize_aliases_and_preserve_source_columns():
    incoming = pd.DataFrame(
        {
            "country": ["Italy"],
            "season": ["2005/06"],
            "player": ["Gianluigi Buffon"],
            "A": [10],
            "S": [0],
            "profile_url": ["https://example.test/buffon"],
        }
    )
    result = normalize_player_seasons(incoming, cohort())
    assert not result.has_errors
    row = result.data.iloc[0]
    assert row.team == "Italy"
    assert row.fifa_code == "ITA"
    assert row.season_end_year == 2006
    assert row.starts == 10
    assert len(row.player_id) == 16
    assert row["A"] == 10
    assert row["country"] == "Italy"


def test_validation_reports_bad_rows_without_silently_dropping_them():
    incoming = pd.DataFrame(
        {
            "team": ["Italy", "Italy", "Atlantis"],
            "season_end_year": [2006, 2006, 2030],
            "player_name": ["A", "A", "B"],
            "starts": [1, -2, 1],
            "sub_appearances": [0, 0, 0],
        }
    )
    result = normalize_player_seasons(incoming, cohort())
    assert len(result.data) == 3
    assert result.has_errors
    assert {"duplicate_team_season_player", "negative_count", "unknown_team", "season_out_of_scope"}.issubset(
        set(result.issues.code)
    )


def test_season_parsing_and_coverage_grid():
    assert parse_season_end_year("1999-00") == 2000
    assert parse_season_end_year("2005/06") == 2006
    assert parse_season_end_year("bad") is None
    normalized = normalize_player_seasons(
        pd.DataFrame(
            {
                "team": ["Italy"],
                "season_end_year": [2006],
                "player_name": ["A"],
                "starts": [11],
                "sub_appearances": [0],
                "expected_matches": [1],
            }
        ),
        cohort(),
    ).data
    seasons, teams = coverage_reports(normalized, cohort())
    italy_2006 = seasons[(seasons.team == "Italy") & (seasons.season_end_year == 2006)].iloc[0]
    assert italy_2006.covered
    assert italy_2006.expected_lineup_starts == 11
    assert italy_2006.starts_difference == 0
    assert len(seasons) == 2 * 27
    assert teams.loc[teams.team == "Italy", "seasons_covered"].iloc[0] == 1


def test_team_names_are_normalized_case_insensitively():
    result = normalize_player_seasons(
        pd.DataFrame(
            {
                "team": ["italy"],
                "season_end_year": [2006],
                "player_name": ["A"],
                "starts": [1],
                "sub_appearances": [0],
            }
        ),
        cohort(),
    )
    assert not result.has_errors
    assert result.data.loc[0, "team"] == "Italy"
    assert result.data.loc[0, "team_source"] == "italy"


def test_import_writes_qa_before_stopping_on_missing_columns(tmp_path):
    source = tmp_path / "bad.csv"
    pd.DataFrame(
        {
            "team": ["Italy"],
            "season_end_year": [2006],
            "player_name": ["A"],
            "sub_appearances": [0],
        }
    ).to_csv(source, index=False)
    qa_dir = tmp_path / "qa"
    with pytest.raises(DataValidationError):
        run(source, tmp_path / "output.parquet", qa_dir)
    issues = pd.read_csv(qa_dir / "ingest_issues.csv")
    assert "missing_column" in set(issues.code)
    assert (qa_dir / "coverage_team_season.csv").exists()
    assert not (tmp_path / "output.parquet").exists()


def test_aliases_fill_canonical_gaps_across_split_file_shapes():
    incoming = pd.DataFrame(
        {
            "team": ["Italy", "Spain"],
            "season_end_year": [2006, 2006],
            "player_name": ["A", "B"],
            "starts": [1, None],
            "A": [None, 2],
            "sub_appearances": [0, None],
            "S": [None, 1],
        }
    )
    result = normalize_player_seasons(incoming, cohort())
    assert not result.has_errors
    assert list(result.data.starts) == [1, 2]
    assert list(result.data.sub_appearances) == [0, 1]
