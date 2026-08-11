from __future__ import annotations

import argparse
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "top5_2025_26"
PROCESSED = ROOT / "data" / "processed"
QA = ROOT / "data" / "qa"

DATASET_VERSION = 36
SOURCE_PAGE = "https://www.kaggle.com/datasets/hubertsidorowicz/football-players-stats-2025-2026"
SOURCE_FILE = "players_data_light-2025_2026.csv"
SOURCE_DOWNLOAD = (
    "https://www.kaggle.com/api/v1/datasets/download/"
    f"hubertsidorowicz/football-players-stats-2025-2026/{SOURCE_FILE}"
)
SOURCE_LICENSE = "MIT"
SOURCE_SCOPE = "2025-26 Big Five domestic leagues; players with at least one league appearance"

LEAGUES = {
    "eng Premier League": ("Premier League", "England", 20, 38),
    "es La Liga": ("La Liga", "Spain", 20, 38),
    "de Bundesliga": ("Bundesliga", "Germany", 18, 34),
    "it Serie A": ("Serie A", "Italy", 20, 38),
    "fr Ligue 1": ("Ligue 1", "France", 18, 34),
}


def _slug(value: object) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")


def _player_id(name: object, born: object, nation: object) -> str:
    year = str(int(float(born))) if pd.notna(born) else f"unknown-{_slug(nation)}"
    return f"top5:{_slug(name)}:{year}"


def _nation(value: object) -> str | None:
    if pd.isna(value):
        return None
    parts = str(value).strip().split()
    return parts[-1] if parts else None


def transform(source: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = {"Player", "Nation", "Pos", "Squad", "Comp", "Born", "MP", "Starts", "Min", "Gls", "Ast"}
    if missing := required - set(source.columns):
        raise ValueError(f"Top-five source is missing columns: {', '.join(sorted(missing))}")
    unknown = set(source["Comp"].dropna()) - set(LEAGUES)
    if unknown:
        raise ValueError(f"Unexpected competitions: {', '.join(sorted(unknown))}")

    data = source.copy()
    data = data[pd.to_numeric(data["MP"], errors="coerce").fillna(0).gt(0)].copy()
    data["league"] = data["Comp"].map(lambda value: LEAGUES[value][0])
    data["league_country"] = data["Comp"].map(lambda value: LEAGUES[value][1])
    data["expected_teams"] = data["Comp"].map(lambda value: LEAGUES[value][2])
    data["expected_matches"] = data["Comp"].map(lambda value: LEAGUES[value][3])
    data["team"] = data["Squad"].astype(str).str.strip()
    data["player_name"] = data["Player"].astype(str).str.strip()
    data["birth_year"] = pd.to_numeric(data["Born"], errors="coerce").astype("Int64")
    data["nationality_source"] = data["Nation"].map(_nation)
    data["player_id"] = [
        _player_id(name, born, nation)
        for name, born, nation in zip(data["player_name"], data["birth_year"], data["nationality_source"])
    ]
    data["source_player_id"] = data["player_id"]
    data["season"] = "2025-26"
    data["season_end_year"] = 2026
    data["starts"] = pd.to_numeric(data["Starts"], errors="raise").astype(int)
    data["appearances"] = pd.to_numeric(data["MP"], errors="raise").astype(int)
    data["sub_appearances"] = data["appearances"] - data["starts"]
    data["minutes"] = pd.to_numeric(data["Min"], errors="coerce").fillna(0).astype(int)
    data["goals"] = pd.to_numeric(data["Gls"], errors="coerce").fillna(0).astype(int)
    data["assists"] = pd.to_numeric(data["Ast"], errors="coerce").fillna(0).astype(int)
    data["position_source"] = data["Pos"].astype(str)
    data["dob"] = pd.NaT
    data["player_url"] = pd.NA
    data["source_url"] = SOURCE_PAGE
    data["source_version"] = DATASET_VERSION
    data["source_license"] = SOURCE_LICENSE
    data["dataset_scope"] = SOURCE_SCOPE
    data["retrieved_at"] = datetime.now(timezone.utc).isoformat()

    output_columns = [
        "league", "league_country", "team", "season", "season_end_year", "player_id",
        "source_player_id", "player_name", "birth_year", "dob", "nationality_source",
        "position_source", "appearances", "starts", "sub_appearances", "minutes", "goals",
        "assists", "expected_matches", "player_url", "source_url", "source_version",
        "source_license", "dataset_scope", "retrieved_at",
    ]
    starts = data[output_columns].sort_values(["league", "team", "player_name"]).reset_index(drop=True)
    if starts.duplicated(["league", "team", "player_id"]).any():
        raise ValueError("Duplicate league-team-player rows found")
    if (starts["sub_appearances"] < 0).any():
        raise ValueError("Found starts greater than appearances")

    team_qa = starts.groupby(["league", "team", "expected_matches"], as_index=False).agg(
        players=("player_id", "nunique"), starts=("starts", "sum"), appearances=("appearances", "sum")
    )
    team_qa["expected_starts"] = team_qa["expected_matches"] * 11
    team_qa["starts_difference"] = team_qa["starts"] - team_qa["expected_starts"]
    league_qa = starts.groupby("league", as_index=False).agg(
        teams=("team", "nunique"), player_rows=("player_id", "size"), players=("player_id", "nunique"),
        starts=("starts", "sum"), appearances=("appearances", "sum"),
    )
    expected_teams = {details[0]: details[2] for details in LEAGUES.values()}
    league_qa["expected_teams"] = league_qa["league"].map(expected_teams)
    if team_qa["starts_difference"].ne(0).any():
        bad = team_qa.loc[team_qa["starts_difference"].ne(0), "team"].tolist()
        raise ValueError(f"Start totals do not equal 11 × matches for: {', '.join(bad)}")
    if league_qa["teams"].ne(league_qa["expected_teams"]).any():
        raise ValueError("League team counts do not match the completed 2025-26 season")

    profiles = starts.groupby("player_id", as_index=False).agg(
        player_name=("player_name", "first"), birth_year=("birth_year", "first"),
        nationality_source=("nationality_source", "first"), position_source=("position_source", "first"),
        clubs=("team", lambda values: "; ".join(sorted(set(values)))),
        leagues=("league", lambda values: "; ".join(sorted(set(values)))),
        source_url=("source_url", "first"), source_version=("source_version", "first"),
        source_license=("source_license", "first"), dataset_scope=("dataset_scope", "first"),
    )
    profiles["dob"] = pd.NaT
    profiles["player_url"] = pd.NA
    return starts, profiles, team_qa.merge(league_qa.add_prefix("league_"), left_on="league", right_on="league_league")


def download(path: Path = RAW / SOURCE_FILE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(
        SOURCE_DOWNLOAD,
        headers={"User-Agent": "football-geo/1.0 (github.com/adhni/football-geo)"},
        timeout=60,
    )
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def run(source_path: Path | None = None, output_dir: Path = PROCESSED, qa_dir: Path = QA) -> pd.DataFrame:
    source_path = source_path or download()
    starts, profiles, qa = transform(pd.read_csv(source_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    starts.to_parquet(output_dir / "top5_player_seasons.parquet", index=False)
    profiles.to_parquet(output_dir / "top5_players_source.parquet", index=False)
    qa.to_csv(qa_dir / "top5_team_coverage.csv", index=False)
    print(
        f"Wrote {len(starts):,} club-player rows for {starts['player_id'].nunique():,} players, "
        f"{starts['team'].nunique()} clubs and {starts['league'].nunique()} leagues"
    )
    return starts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import 2025-26 Big Five league player statistics")
    parser.add_argument("--source", type=Path, help="Existing source CSV; otherwise download the pinned dataset")
    parser.add_argument("--output-dir", type=Path, default=PROCESSED)
    parser.add_argument("--qa-dir", type=Path, default=QA)
    args = parser.parse_args()
    run(args.source, args.output_dir, args.qa_dir)


if __name__ == "__main__":
    main()
