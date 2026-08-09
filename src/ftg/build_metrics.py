from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .metrics import area_metrics

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
QA = ROOT / "data" / "qa"


def run(
    starts_path: Path,
    geography_path: Path,
    population_path: Path,
    output_path: Path,
    qa_dir: Path = QA,
) -> pd.DataFrame:
    starts = pd.read_parquet(starts_path)
    geography = pd.read_parquet(geography_path)
    population = (
        pd.read_parquet(population_path)
        if population_path.suffix.lower() == ".parquet"
        else pd.read_csv(population_path)
    )
    required_starts = {"team", "player_id", "player_name", "starts", "sub_appearances"}
    required_geography = {
        "player_id",
        "adm1_code",
        "adm1_name",
        "adm2_code",
        "adm2_name",
    }
    if missing := required_starts - set(starts.columns):
        raise ValueError(f"Starts data is missing columns: {', '.join(sorted(missing))}")
    if missing := required_geography - set(geography.columns):
        raise ValueError(f"Geography data is missing columns: {', '.join(sorted(missing))}")
    qa_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[pd.DataFrame] = []
    unresolved: list[pd.DataFrame] = []
    population_failures: list[pd.DataFrame] = []
    for level in ("ADM1", "ADM2"):
        code_column = f"{level.lower()}_code"
        joined = starts[["team", "player_id", "player_name", "starts"]].merge(
            geography[["player_id", code_column]], on="player_id", how="left"
        )
        missing_geo = joined[joined["starts"].gt(0) & joined[code_column].isna()].copy()
        if not missing_geo.empty:
            missing_geo["geo_level"] = level
            unresolved.append(missing_geo)

        metrics = area_metrics(starts, geography, population, level)
        if "season_end_year" in starts.columns and not starts.empty:
            metrics["period_start"] = int(starts["season_end_year"].min())
            metrics["period_end"] = int(starts["season_end_year"].max())
        if "population" in metrics.columns:
            failed = metrics[metrics["population"].isna()][["team", "geo_level", "geo_code", "geo_name"]].copy()
            if not failed.empty:
                population_failures.append(failed)
        outputs.append(metrics)

    result = pd.concat(outputs, ignore_index=True, sort=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)
    result.to_csv(output_path.with_suffix(".csv"), index=False)
    unresolved_output = (
        pd.concat(unresolved, ignore_index=True).drop_duplicates()
        if unresolved
        else pd.DataFrame(columns=["team", "player_id", "player_name", "starts", "geo_level"])
    )
    unresolved_output.to_csv(qa_dir / "unresolved_player_geography.csv", index=False)
    population_output = (
        pd.concat(population_failures, ignore_index=True).drop_duplicates()
        if population_failures
        else pd.DataFrame(columns=["team", "geo_level", "geo_code", "geo_name"])
    )
    population_output.to_csv(qa_dir / "population_join_failures.csv", index=False)
    print(f"Wrote {len(result):,} area metric rows to {output_path}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ADM1/ADM2 football production metrics")
    parser.add_argument("--starts", type=Path, default=PROCESSED / "player_season_starts.parquet")
    parser.add_argument("--geography", type=Path, default=PROCESSED / "player_geography.parquet")
    parser.add_argument("--population", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=PROCESSED / "area_metrics.parquet")
    parser.add_argument("--qa-dir", type=Path, default=QA)
    args = parser.parse_args()
    run(args.starts, args.geography, args.population, args.output, args.qa_dir)


if __name__ == "__main__":
    main()
