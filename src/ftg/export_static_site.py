from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
QA = ROOT / "data" / "qa"
DEFAULT_OUTPUT = ROOT / "docs" / "data" / "dashboard.json"


def _date_string(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else str(value)


def build_payload(
    data: pd.DataFrame,
    unresolved: pd.DataFrame | None = None,
) -> dict:
    required = {
        "player_id",
        "player_name",
        "team",
        "season_end_year",
        "starts",
        "sub_appearances",
        "dob",
        "pob_mapped",
        "resolution_status",
    }
    if missing := required - set(data.columns):
        raise ValueError(f"Static export is missing columns: {', '.join(sorted(missing))}")

    records: list[dict] = []
    for row in data.sort_values(["season_end_year", "team", "player_name"]).itertuples(index=False):
        mapped = bool(row.pob_mapped)
        records.append(
            {
                "id": str(row.player_id),
                "name": str(row.player_name),
                "team": str(row.team),
                "year": int(row.season_end_year),
                "starts": int(row.starts),
                "subs": int(row.sub_appearances),
                "dob": _date_string(row.dob),
                "place": str(row.birthplace_wikidata) if mapped and pd.notna(row.birthplace_wikidata) else None,
                "country": str(row.birth_country) if mapped and pd.notna(row.birth_country) else None,
                "lat": round(float(row.birth_lat), 6) if mapped else None,
                "lon": round(float(row.birth_lon), 6) if mapped else None,
                "mapped": mapped,
                "status": str(row.resolution_status) if pd.notna(row.resolution_status) else "unresolved",
            }
        )

    unique_players = data.drop_duplicates("player_id")
    mapped_players = unique_players[unique_players["pob_mapped"]]
    total_starts = int(data["starts"].sum())
    mapped_starts = int(data.loc[data["pob_mapped"], "starts"].sum())
    unresolved_rows: list[dict] = []
    if unresolved is not None and not unresolved.empty:
        for row in unresolved.itertuples(index=False):
            unresolved_rows.append(
                {
                    "name": str(row.player_name),
                    "status": str(row.resolution_status).replace("_", " "),
                }
            )

    return {
        "meta": {
            "title": "Football Talent Geography",
            "scope": "FIFA Men's World Cup finals only",
            "years": sorted(int(year) for year in data["season_end_year"].unique()),
            "teams": sorted(str(team) for team in data["team"].unique()),
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source_name": "Fjelstul World Cup Database",
            "source_url": "https://github.com/jfjelstul/worldcup",
            "source_commit": "35a8667f518b07469182ae16d35574dd0e7a00fb",
            "license": "CC BY-SA 4.0",
            "missing_team": "Norway",
        },
        "summary": {
            "teams": int(data["team"].nunique()),
            "players": int(unique_players["player_id"].nunique()),
            "mapped_players": int(mapped_players["player_id"].nunique()),
            "player_coverage_pct": round(len(mapped_players) / len(unique_players) * 100, 1),
            "starts": total_starts,
            "mapped_starts": mapped_starts,
            "start_coverage_pct": round(mapped_starts / total_starts * 100, 1),
            "birthplaces": int(mapped_players["birth_place_qid"].nunique()),
            "unresolved_players": int(len(unique_players) - len(mapped_players)),
        },
        "records": records,
        "unresolved": unresolved_rows,
    }


def run(
    input_path: Path = PROCESSED / "player_starts_with_birthplace.parquet",
    unresolved_path: Path = QA / "wikidata_resolution_queue.csv",
    output_path: Path = DEFAULT_OUTPUT,
) -> dict:
    data = pd.read_parquet(input_path)
    unresolved = pd.read_csv(unresolved_path) if unresolved_path.exists() else None
    payload = build_payload(data, unresolved)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(payload['records']):,} records and "
        f"{payload['summary']['birthplaces']:,} birthplaces to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the static GitHub Pages dataset")
    parser.add_argument("--input", type=Path, default=PROCESSED / "player_starts_with_birthplace.parquet")
    parser.add_argument("--unresolved", type=Path, default=QA / "wikidata_resolution_queue.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.input, args.unresolved, args.output)


if __name__ == "__main__":
    main()
