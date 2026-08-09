import pandas as pd

from src.ftg.build_metrics import run


def test_build_metrics_writes_outputs_and_qa(tmp_path):
    starts = pd.DataFrame(
        {
            "team": ["Italy", "Italy"],
            "player_id": ["a", "b"],
            "player_name": ["A", "B"],
            "starts": [5, 2],
            "sub_appearances": [0, 1],
            "season_end_year": [2006, 2006],
        }
    )
    geography = pd.DataFrame(
        {
            "player_id": ["a", "b"],
            "adm1_code": ["IT-A", None],
            "adm1_name": ["A", None],
            "adm2_code": ["IT-A1", None],
            "adm2_name": ["A1", None],
        }
    )
    population = pd.DataFrame(
        {
            "geo_level": ["ADM1", "ADM2"],
            "geo_code": ["IT-A", "IT-A1"],
            "year": [2025, 2025],
            "population": [1_000_000, 500_000],
        }
    )
    starts_path = tmp_path / "starts.parquet"
    geography_path = tmp_path / "geography.parquet"
    population_path = tmp_path / "population.csv"
    output_path = tmp_path / "metrics.parquet"
    starts.to_parquet(starts_path, index=False)
    geography.to_parquet(geography_path, index=False)
    population.to_csv(population_path, index=False)

    output = run(starts_path, geography_path, population_path, output_path, tmp_path / "qa")

    assert set(output.geo_level) == {"ADM1", "ADM2"}
    assert output.period_start.min() == 2006
    assert output_path.exists()
    unresolved = pd.read_csv(tmp_path / "qa" / "unresolved_player_geography.csv")
    assert set(unresolved.geo_level) == {"ADM1", "ADM2"}
    assert set(unresolved.player_name) == {"B"}
