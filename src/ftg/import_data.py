from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .schema import MAX_SEASON_END_YEAR, MIN_SEASON_END_YEAR, normalize_player_seasons

ROOT = Path(__file__).resolve().parents[2]
COHORT_PATH = ROOT / "config" / "top20_fifa_2026-07-20.csv"
DEFAULT_INPUT = ROOT / "data" / "incoming"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "player_season_starts.parquet"
DEFAULT_QA = ROOT / "data" / "qa"


class DataValidationError(RuntimeError):
    pass


def read_tables(path: Path) -> pd.DataFrame:
    paths: list[Path]
    if path.is_dir():
        paths = sorted(item for item in path.rglob("*") if item.suffix.lower() in {".csv", ".parquet"})
    else:
        paths = [path]
    if not paths:
        raise FileNotFoundError(f"No CSV or Parquet files found at {path}")

    frames: list[pd.DataFrame] = []
    for item in paths:
        if item.suffix.lower() == ".csv":
            frame = pd.read_csv(item)
        elif item.suffix.lower() == ".parquet":
            frame = pd.read_parquet(item)
        else:
            continue
        frame["source_input_file"] = str(item)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def coverage_reports(data: pd.DataFrame, cohort: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    years = range(MIN_SEASON_END_YEAR, MAX_SEASON_END_YEAR + 1)
    grid = pd.MultiIndex.from_product(
        [cohort["team"].tolist(), years], names=["team", "season_end_year"]
    ).to_frame(index=False)
    if data.empty or not {"team", "season_end_year"}.issubset(data.columns):
        observed = pd.DataFrame(columns=["team", "season_end_year"])
    else:
        usable = data.dropna(subset=["team", "season_end_year"]).copy()
        usable["season_end_year"] = usable["season_end_year"].astype(int)
        for column in ("starts", "sub_appearances"):
            if column not in usable.columns:
                usable[column] = 0
        aggregations = {
            "record_count": ("team", "size"),
            "unique_players": ("player_id", "nunique"),
            "starts": ("starts", "sum"),
            "sub_appearances": ("sub_appearances", "sum"),
        }
        if "expected_matches" in usable.columns:
            aggregations["expected_matches"] = ("expected_matches", "max")
        observed = usable.groupby(["team", "season_end_year"], as_index=False).agg(**aggregations)
    seasons = grid.merge(observed, on=["team", "season_end_year"], how="left")
    for column in ("record_count", "unique_players", "starts", "sub_appearances"):
        if column not in seasons.columns:
            seasons[column] = 0
        else:
            seasons[column] = seasons[column].fillna(0).astype(int)
    seasons["covered"] = seasons["record_count"].gt(0)
    if "expected_matches" in seasons.columns:
        seasons["expected_lineup_starts"] = seasons["expected_matches"] * 11
        seasons["starts_difference"] = seasons["starts"] - seasons["expected_lineup_starts"]
    else:
        seasons["expected_lineup_starts"] = pd.NA
        seasons["starts_difference"] = pd.NA

    team_summary = seasons.groupby("team", as_index=False).agg(
        seasons_covered=("covered", "sum"),
        seasons_expected=("season_end_year", "size"),
        total_records=("record_count", "sum"),
        unique_player_seasons=("unique_players", "sum"),
        starts=("starts", "sum"),
        sub_appearances=("sub_appearances", "sum"),
    )
    team_summary["coverage_pct"] = team_summary["seasons_covered"] / team_summary["seasons_expected"] * 100
    return seasons, team_summary


def run(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    qa_dir: Path = DEFAULT_QA,
) -> pd.DataFrame:
    incoming = read_tables(input_path)
    cohort = pd.read_csv(COHORT_PATH)
    result = normalize_player_seasons(incoming, cohort)
    qa_dir.mkdir(parents=True, exist_ok=True)
    result.issues.to_csv(qa_dir / "ingest_issues.csv", index=False)
    season_coverage, team_coverage = coverage_reports(result.data, cohort)
    season_coverage.to_csv(qa_dir / "coverage_team_season.csv", index=False)
    team_coverage.to_csv(qa_dir / "coverage_team.csv", index=False)

    if result.has_errors:
        error_count = int((result.issues["severity"] == "error").sum())
        raise DataValidationError(
            f"Import stopped with {error_count} validation errors; review {qa_dir / 'ingest_issues.csv'}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.data.to_parquet(output_path, index=False)
    print(f"Wrote {len(result.data):,} validated rows to {output_path}")
    print(f"Wrote coverage and validation reports to {qa_dir}")
    return result.data


def main() -> None:
    parser = argparse.ArgumentParser(description="Import and validate player-season source data")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="CSV/Parquet file or directory")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--qa-dir", type=Path, default=DEFAULT_QA)
    args = parser.parse_args()
    try:
        run(args.input, args.output, args.qa_dir)
    except (DataValidationError, FileNotFoundError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
