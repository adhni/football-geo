import pandas as pd

from src.ftg.import_worldcup import build_player_starts


def test_build_worldcup_starts_maps_teams_and_validates_lineups():
    appearances = pd.DataFrame(
        {
            "tournament_id": ["WC-2022"] * 4,
            "tournament_name": ["2022 FIFA Men's World Cup"] * 4,
            "match_id": ["M1"] * 4,
            "team_name": ["United States"] * 3 + ["Not Selected"],
            "team_code": ["USA"] * 3 + ["XXX"],
            "player_id": ["P1", "P2", "P1", "P3"],
            "given_name": ["Tim", "Matt", "Tim", "X"],
            "family_name": ["One", "Two", "One", "Three"],
            "starter": [1, 1, 0, 1],
            "substitute": [0, 0, 1, 0],
            "position_name": ["goal keeper", "defender", "goal keeper", "forward"],
        }
    )
    players = pd.DataFrame(
        {
            "player_id": ["P1", "P2", "P3"],
            "birth_date": ["1990-01-01", "1991-01-01", "1992-01-01"],
            "player_wikipedia_link": ["https://example/P1", "https://example/P2", "https://example/P3"],
        }
    )
    cohort = pd.DataFrame({"team": ["USA"], "fifa_code": ["USA"]})
    starts, profiles, coverage = build_player_starts(appearances, players, cohort)
    assert set(starts.team) == {"USA"}
    assert set(starts.player_id) == {"fwc:P1", "fwc:P2"}
    p1 = starts[starts.player_id.eq("fwc:P1")].iloc[0]
    assert p1.starts == 1
    assert p1.sub_appearances == 1
    assert p1.player_name == "Tim One"
    assert len(profiles) == 2
    assert coverage.iloc[0].starts_difference == -9
