import pandas as pd

from src.ftg.import_top5 import transform


def test_transform_top5_builds_appearance_rows_and_profiles():
    rows = []
    for index in range(11):
        rows.append(
            {
                "Player": f"Player {index}", "Nation": "xx XYZ", "Pos": "MF", "Squad": "Arsenal",
                "Comp": "eng Premier League", "Born": 2000 + index, "MP": 38, "Starts": 38,
                "Min": 38 * 90, "Gls": 2, "Ast": 3,
            }
        )
    source = pd.DataFrame(rows)

    # A complete season has 418 team starts; repeat a single synthetic team 20 times
    # so both the team-start and league-team QA invariants are exercised.
    source = pd.concat(
        [source.assign(Squad=f"Club {index:02d}") for index in range(20)], ignore_index=True
    )
    starts, profiles, qa = transform(source)

    assert len(starts) == 220
    assert len(profiles) == 11
    assert starts["starts"].sum() == 20 * 418
    assert starts["sub_appearances"].sum() == 0
    assert qa["starts_difference"].eq(0).all()
