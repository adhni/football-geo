import pandas as pd

from src.ftg.metrics import area_metrics, hhi_by_team


def test_area_metrics_and_hhi():
    starts = pd.DataFrame({
        "team": ["Italy", "Italy", "Italy"],
        "player_id": ["a", "b", "a"],
        "starts": [10, 5, 2],
        "sub_appearances": [1, 1, 0],
    })
    geo = pd.DataFrame({
        "player_id": ["a", "b"],
        "adm1_code": ["IT-A", "IT-B"],
        "adm1_name": ["A", "B"],
    })
    pop = pd.DataFrame({
        "geo_level": ["ADM1", "ADM1"],
        "geo_code": ["IT-A", "IT-B"],
        "year": [2025, 2025],
        "population": [2_000_000, 1_000_000],
    })
    out = area_metrics(starts, geo, pop, "ADM1")
    a = out[out.geo_code == "IT-A"].iloc[0]
    assert a.starts == 12
    assert a.unique_starters == 1
    assert a.starts_per_million == 6
    hhi = hhi_by_team(out).iloc[0].hhi
    assert 0 < hhi <= 1
