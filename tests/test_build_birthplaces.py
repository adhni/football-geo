import pandas as pd

from src.ftg.build_birthplaces import build


def test_build_birthplaces_preserves_unresolved_rows_and_reports_coverage():
    starts = pd.DataFrame(
        {
            "team": ["Italy", "Italy", "Spain"],
            "season_end_year": [2006, 2006, 2010],
            "player_id": ["a", "b", "a"],
            "player_name": ["A", "B", "A"],
            "starts": [5, 2, 3],
            "sub_appearances": [0, 1, 0],
        }
    )
    players = pd.DataFrame(
        {
            "player_id": ["a", "b"],
            "wikidata_qid": ["Q1", "Q2"],
            "birth_place_qid": ["Q10", "Q20"],
            "birthplace_wikidata": ["Rome", "Unknown"],
            "birth_country_qid": ["Q38", None],
            "birth_country": ["Italy", None],
            "birth_lat": [41.9, None],
            "birth_lon": [12.5, None],
            "resolution_status": ["resolved", "birthplace_coordinates_missing"],
        }
    )
    combined, summary, coverage = build(starts, players)
    assert len(combined) == 3
    assert combined.pob_mapped.sum() == 2
    assert len(summary) == 1
    assert summary.iloc[0].starts == 8
    italy = coverage[coverage.team.eq("Italy")].iloc[0]
    assert italy.players == 2
    assert italy.mapped_players == 1
    assert italy.mapped_starts == 5
