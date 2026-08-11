from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
QA = ROOT / "data" / "qa"


def build(
    starts: pd.DataFrame,
    players: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required_starts = {"team", "player_id", "player_name", "starts", "sub_appearances"}
    required_players = {
        "player_id",
        "resolution_status",
        "birth_place_qid",
        "birthplace_wikidata",
        "birth_country",
        "birth_lat",
        "birth_lon",
    }
    if missing := required_starts - set(starts.columns):
        raise ValueError(f"Starts data is missing columns: {', '.join(sorted(missing))}")
    if missing := required_players - set(players.columns):
        raise ValueError(f"Player data is missing columns: {', '.join(sorted(missing))}")
    if players["player_id"].duplicated().any():
        raise ValueError("Player enrichment must contain one row per player_id")

    coordinates_valid = (
        players["resolution_status"].eq("resolved")
        & players["birth_lat"].between(-90, 90)
        & players["birth_lon"].between(-180, 180)
    )
    player_geo = players[
        [
            "player_id",
            "wikidata_qid",
            "birth_place_qid",
            "birthplace_wikidata",
            "birth_country_qid",
            "birth_country",
            "birth_lat",
            "birth_lon",
            "resolution_status",
        ]
    ].copy()
    player_geo["pob_mapped"] = coordinates_valid
    combined = starts.merge(player_geo, on="player_id", how="left", validate="many_to_one")

    mapped = combined[combined["pob_mapped"].fillna(False)].copy()
    mapped["starter_player_id"] = mapped["player_id"].where(mapped["starts"].gt(0))
    summary = mapped.groupby(
        [
            "birth_place_qid",
            "birthplace_wikidata",
            "birth_country_qid",
            "birth_country",
            "birth_lat",
            "birth_lon",
        ],
        as_index=False,
        dropna=False,
    ).agg(
        unique_players=("player_id", "nunique"),
        unique_starters=("starter_player_id", "nunique"),
        starts=("starts", "sum"),
        sub_appearances=("sub_appearances", "sum"),
        represented_teams=("team", lambda values: ", ".join(sorted(set(values)))),
        tournaments=("season_end_year", "nunique"),
    )

    player_team = combined.groupby(["team", "player_id"], as_index=False).agg(
        pob_mapped=("pob_mapped", "max"),
        starts=("starts", "sum"),
    )
    coverage = player_team.groupby("team", as_index=False).agg(
        players=("player_id", "nunique"),
        mapped_players=("pob_mapped", "sum"),
        starts=("starts", "sum"),
        mapped_starts=("starts", lambda values: values[player_team.loc[values.index, "pob_mapped"]].sum()),
    )
    coverage["player_coverage_pct"] = coverage["mapped_players"] / coverage["players"] * 100
    coverage["start_coverage_pct"] = coverage["mapped_starts"] / coverage["starts"] * 100
    return combined, summary, coverage


def run(
    starts_path: Path = PROCESSED / "worldcup_player_starts.parquet",
    players_path: Path = PROCESSED / "players_enriched.parquet",
    output_dir: Path = PROCESSED,
    qa_dir: Path = QA,
) -> pd.DataFrame:
    starts = pd.read_parquet(starts_path)
    players = pd.read_parquet(players_path)
    combined, summary, coverage = build(starts, players)
    output_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output_dir / "player_starts_with_birthplace.parquet", index=False)
    summary.to_parquet(output_dir / "birthplace_summary.parquet", index=False)
    summary.to_csv(output_dir / "birthplace_summary.csv", index=False)
    coverage.to_csv(qa_dir / "birthplace_coverage_by_team.csv", index=False)
    unresolved = combined[~combined["pob_mapped"].fillna(False)][
        ["team", "season_end_year", "player_id", "player_name", "starts", "resolution_status"]
    ].drop_duplicates()
    unresolved.to_csv(qa_dir / "unresolved_birthplace_contributions.csv", index=False)
    print(
        f"Mapped {int(combined['pob_mapped'].fillna(False).sum()):,}/{len(combined):,} "
        f"player-tournament rows to {len(summary):,} birthplaces"
    )
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Build validated birthplace map inputs")
    parser.add_argument("--starts", type=Path, default=PROCESSED / "worldcup_player_starts.parquet")
    parser.add_argument("--players", type=Path, default=PROCESSED / "players_enriched.parquet")
    parser.add_argument("--output-dir", type=Path, default=PROCESSED)
    parser.add_argument("--qa-dir", type=Path, default=QA)
    args = parser.parse_args()
    run(args.starts, args.players, args.output_dir, args.qa_dir)


if __name__ == "__main__":
    main()
