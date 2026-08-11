from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .build_birthplaces import build

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
QA = ROOT / "data" / "qa"


def run(
    starts_path: Path = PROCESSED / "top5_player_seasons.parquet",
    players_path: Path = PROCESSED / "top5_players_enriched.parquet",
    output_dir: Path = PROCESSED,
    qa_dir: Path = QA,
) -> pd.DataFrame:
    starts = pd.read_parquet(starts_path)
    players = pd.read_parquet(players_path)
    combined, summary, coverage = build(starts, players)
    dob_by_player = players.set_index("player_id")["wikidata_dob"]
    combined["dob"] = combined["player_id"].map(dob_by_player).combine_first(combined["dob"])

    output_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output_dir / "top5_players_with_birthplace.parquet", index=False)
    summary.to_parquet(output_dir / "top5_birthplace_summary.parquet", index=False)
    coverage.to_csv(qa_dir / "top5_birthplace_coverage_by_club.csv", index=False)
    unresolved = combined[~combined["pob_mapped"].fillna(False)][
        ["league", "team", "player_id", "player_name", "birth_year", "starts", "resolution_status"]
    ].drop_duplicates()
    unresolved.to_csv(qa_dir / "top5_unresolved_birthplace_contributions.csv", index=False)
    print(
        f"Mapped {combined.loc[combined['pob_mapped'], 'player_id'].nunique():,}/"
        f"{combined['player_id'].nunique():,} players across {combined['team'].nunique()} clubs"
    )
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 2025-26 Big Five birthplace map inputs")
    parser.add_argument("--starts", type=Path, default=PROCESSED / "top5_player_seasons.parquet")
    parser.add_argument("--players", type=Path, default=PROCESSED / "top5_players_enriched.parquet")
    parser.add_argument("--output-dir", type=Path, default=PROCESSED)
    parser.add_argument("--qa-dir", type=Path, default=QA)
    args = parser.parse_args()
    run(args.starts, args.players, args.output_dir, args.qa_dir)


if __name__ == "__main__":
    main()
