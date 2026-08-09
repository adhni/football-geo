from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .import_data import coverage_reports
from .schema import normalize_player_seasons, season_label

ROOT = Path(__file__).resolve().parents[2]
COHORT_PATH = ROOT / "config" / "top20_fifa_2026-07-20.csv"
PROCESSED = ROOT / "data" / "processed"
QA = ROOT / "data" / "qa"

WORLD_CUP_YEARS = (2002, 2006, 2010, 2014, 2018, 2022)
SOURCE_COMMIT = "35a8667f518b07469182ae16d35574dd0e7a00fb"
SOURCE_URL = f"https://github.com/jfjelstul/worldcup/tree/{SOURCE_COMMIT}"
SOURCE_SCOPE = "FIFA Men's World Cup finals only"
SOURCE_LICENSE = "CC-BY-SA 4.0"
TEAM_ALIASES = {"United States": "USA"}


def _full_name(given_name: object, family_name: object) -> str:
    given = "" if pd.isna(given_name) else str(given_name).strip()
    family = "" if pd.isna(family_name) else str(family_name).strip()
    if given.casefold() == "not applicable":
        given = ""
    return " ".join(part for part in (given, family) if part)


def build_player_starts(
    appearances: pd.DataFrame,
    players: pd.DataFrame,
    cohort: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tournament_ids = {f"WC-{year}" for year in WORLD_CUP_YEARS}
    selected = appearances[appearances["tournament_id"].isin(tournament_ids)].copy()
    selected["team"] = selected["team_name"].replace(TEAM_ALIASES)
    selected = selected[selected["team"].isin(cohort["team"])].copy()
    selected["season_end_year"] = selected["tournament_id"].str.removeprefix("WC-").astype(int)

    player_fields = players[
        ["player_id", "birth_date", "player_wikipedia_link"]
    ].drop_duplicates("player_id")
    selected = selected.merge(player_fields, on="player_id", how="left", validate="many_to_one")
    selected["player_name"] = [
        _full_name(given, family)
        for given, family in zip(selected["given_name"], selected["family_name"])
    ]
    code_by_team = cohort.set_index("team")["fifa_code"]
    selected["fifa_code"] = selected["team"].map(code_by_team)
    matches_by_team = selected.groupby(["team", "season_end_year"])["match_id"].nunique()

    grouped = selected.groupby(
        [
            "team",
            "fifa_code",
            "season_end_year",
            "tournament_id",
            "tournament_name",
            "player_id",
            "player_name",
        ],
        as_index=False,
    ).agg(
        starts=("starter", "sum"),
        sub_appearances=("substitute", "sum"),
        goals=("starter", lambda values: 0),
        position_source=("position_name", "first"),
        source_positions=("position_name", lambda values: ";".join(sorted(set(values.dropna())))),
        dob=("birth_date", "first"),
        player_url=("player_wikipedia_link", "first"),
    )
    grouped["source_player_id"] = grouped["player_id"]
    grouped["player_id"] = "fwc:" + grouped["player_id"].astype(str)
    grouped["season"] = grouped["season_end_year"].map(season_label)
    grouped["expected_matches"] = [
        matches_by_team.loc[(team, year)]
        for team, year in zip(grouped["team"], grouped["season_end_year"])
    ]
    grouped["source_url"] = SOURCE_URL
    grouped["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    grouped["dataset_scope"] = SOURCE_SCOPE
    grouped["source_license"] = SOURCE_LICENSE
    grouped["source_commit"] = SOURCE_COMMIT
    grouped["competitive_starts"] = grouped["starts"]

    validation = normalize_player_seasons(grouped, cohort)
    if validation.has_errors:
        raise ValueError("World Cup transformation failed canonical validation")

    team_tournament = selected.groupby(
        ["team", "fifa_code", "season_end_year", "tournament_id", "tournament_name"],
        as_index=False,
    ).agg(matches=("match_id", "nunique"), starts=("starter", "sum"))
    team_tournament["expected_starts"] = team_tournament["matches"] * 11
    team_tournament["starts_difference"] = (
        team_tournament["starts"] - team_tournament["expected_starts"]
    )

    profile_columns = [
        "player_id",
        "player_name",
        "player_url",
        "dob",
        "source_player_id",
    ]
    player_profiles = validation.data[profile_columns].drop_duplicates("player_id").copy()
    player_profiles["dob_source"] = player_profiles["dob"]
    player_profiles["birthplace_text"] = pd.NA
    player_profiles["nationality_source"] = pd.NA
    player_profiles["source_url"] = SOURCE_URL
    player_profiles["dataset_scope"] = SOURCE_SCOPE
    return validation.data, player_profiles, team_tournament


def run(
    source_dir: Path,
    output_dir: Path = PROCESSED,
    qa_dir: Path = QA,
    make_default: bool = True,
) -> pd.DataFrame:
    appearances = pd.read_csv(source_dir / "player_appearances.csv", low_memory=False)
    players = pd.read_csv(source_dir / "players.csv", low_memory=False)
    cohort = pd.read_csv(COHORT_PATH)
    starts, profiles, team_tournament = build_player_starts(appearances, players, cohort)
    output_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)

    starts.to_parquet(output_dir / "worldcup_player_starts.parquet", index=False)
    profiles.to_parquet(output_dir / "worldcup_players_source.parquet", index=False)
    team_tournament.to_csv(qa_dir / "worldcup_team_tournament_coverage.csv", index=False)
    season_coverage, team_coverage = coverage_reports(starts, cohort)
    season_coverage.to_csv(qa_dir / "worldcup_coverage_team_period.csv", index=False)
    team_coverage.to_csv(qa_dir / "worldcup_coverage_team.csv", index=False)
    if make_default:
        starts.to_parquet(output_dir / "player_season_starts.parquet", index=False)
        profiles.to_parquet(output_dir / "players_source.parquet", index=False)

    mismatches = int(team_tournament["starts_difference"].ne(0).sum())
    if mismatches:
        raise ValueError(f"Found {mismatches} team-tournaments where starts != 11 * matches")
    print(
        f"Wrote {len(starts):,} player-tournament rows for "
        f"{starts['team'].nunique()} teams and {starts['player_id'].nunique():,} players"
    )
    print(f"Scope: {SOURCE_SCOPE}, {WORLD_CUP_YEARS[0]}-{WORLD_CUP_YEARS[-1]}")
    return starts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the Fjelstul World Cup database")
    parser.add_argument("--source-dir", type=Path, required=True, help="Path to its data-csv directory")
    parser.add_argument("--output-dir", type=Path, default=PROCESSED)
    parser.add_argument("--qa-dir", type=Path, default=QA)
    parser.add_argument("--no-default", action="store_true", help="Do not replace the canonical processed inputs")
    args = parser.parse_args()
    run(args.source_dir, args.output_dir, args.qa_dir, make_default=not args.no_default)


if __name__ == "__main__":
    main()
