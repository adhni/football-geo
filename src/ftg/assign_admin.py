from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
QA = ROOT / "data" / "qa"


def normalize_boundaries(frame: gpd.GeoDataFrame, level: str) -> gpd.GeoDataFrame:
    level = level.lower()
    code = f"{level}_code"
    name = f"{level}_name"
    aliases = {
        code: [code, "shapeID", "shape_id", "GID_1" if level == "adm1" else "GID_2"],
        name: [name, "shapeName", "shape_name", "NAME_1" if level == "adm1" else "NAME_2"],
        "adm0_code": ["adm0_code", "shapeGroup", "shape_group", "GID_0"],
    }
    selected: dict[str, str] = {}
    for target, candidates in aliases.items():
        source = next((candidate for candidate in candidates if candidate in frame.columns), None)
        if source is None and target != "adm0_code":
            raise ValueError(f"Could not identify {target}; available columns: {', '.join(frame.columns)}")
        if source is not None:
            selected[source] = target
    columns = list(selected) + ["geometry"]
    output = frame[columns].rename(columns=selected).copy()
    if "adm0_code" not in output.columns:
        output["adm0_code"] = pd.NA
    if output[code].isna().any() or output[code].duplicated().any():
        raise ValueError(f"{level.upper()} boundaries require unique, non-null area codes")
    return output.to_crs("EPSG:4326")


def _join_level(points: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame, level: str) -> tuple[pd.DataFrame, set[str]]:
    code = f"{level}_code"
    name = f"{level}_name"
    joined = gpd.sjoin(points, boundaries[["adm0_code", code, name, "geometry"]], how="left", predicate="within")
    matched = joined[joined[code].notna()]
    ambiguous = set(matched.loc[matched["player_id"].duplicated(keep=False), "player_id"].astype(str))
    assignments = joined.drop_duplicates("player_id")[["player_id", "adm0_code", code, name]].copy()
    if ambiguous:
        assignments.loc[assignments["player_id"].astype(str).isin(ambiguous), ["adm0_code", code, name]] = pd.NA
    return assignments, ambiguous


def assign(
    points_path: Path,
    adm1_path: Path,
    adm2_path: Path,
    output_path: Path = PROCESSED / "player_geography.parquet",
    qa_dir: Path = QA,
) -> pd.DataFrame:
    players = pd.read_parquet(points_path)
    required = {"player_id", "birth_lon", "birth_lat"}
    if missing := required - set(players.columns):
        raise ValueError(f"Player points are missing columns: {', '.join(sorted(missing))}")
    if players["player_id"].duplicated().any():
        raise ValueError("Player points must contain one row per player_id")

    with_coords = players.dropna(subset=["birth_lon", "birth_lat"]).copy()
    points = gpd.GeoDataFrame(
        with_coords[["player_id"]],
        geometry=gpd.points_from_xy(with_coords.birth_lon, with_coords.birth_lat),
        crs="EPSG:4326",
    )
    adm1 = normalize_boundaries(gpd.read_file(adm1_path), "adm1")
    adm2 = normalize_boundaries(gpd.read_file(adm2_path), "adm2")
    assignment1, ambiguous1 = _join_level(points, adm1, "adm1")
    assignment2, ambiguous2 = _join_level(points, adm2, "adm2")
    assignment2 = assignment2.rename(columns={"adm0_code": "adm0_code_adm2"})

    result = players[["player_id"]].merge(assignment1, on="player_id", how="left").merge(
        assignment2, on="player_id", how="left"
    )
    result["adm0_code"] = result["adm0_code"].fillna(result["adm0_code_adm2"])
    country_mismatch = (
        result["adm0_code"].notna()
        & result["adm0_code_adm2"].notna()
        & result["adm0_code"].ne(result["adm0_code_adm2"])
    )
    result = result.drop(columns="adm0_code_adm2")
    result.loc[
        country_mismatch,
        ["adm0_code", "adm1_code", "adm1_name", "adm2_code", "adm2_name"],
    ] = pd.NA
    result["admin_source"] = "geoBoundaries"

    issues: list[dict] = []
    missing_coords = players[players[["birth_lon", "birth_lat"]].isna().any(axis=1)]["player_id"]
    issues.extend({"player_id": player_id, "issue": "missing_coordinates"} for player_id in missing_coords)
    issues.extend({"player_id": player_id, "issue": "ambiguous_adm1_overlap"} for player_id in ambiguous1)
    issues.extend({"player_id": player_id, "issue": "ambiguous_adm2_overlap"} for player_id in ambiguous2)
    issues.extend(
        {"player_id": player_id, "issue": "adm_country_mismatch"}
        for player_id in result.loc[country_mismatch, "player_id"]
    )
    for level in ("adm1", "adm2"):
        missing = result[result[level + "_code"].isna() & ~result["player_id"].isin(missing_coords)]["player_id"]
        issues.extend({"player_id": player_id, "issue": f"unresolved_{level}"} for player_id in missing)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)
    pd.DataFrame(issues, columns=["player_id", "issue"]).drop_duplicates().to_csv(
        qa_dir / "admin_assignment_issues.csv", index=False
    )
    print(f"Wrote {len(result):,} player geography rows to {output_path}")
    print(f"Flagged {len(issues):,} administrative assignment issues")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=Path, default=PROCESSED / "players_enriched.parquet")
    parser.add_argument("--adm1", type=Path, required=True)
    parser.add_argument("--adm2", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=PROCESSED / "player_geography.parquet")
    parser.add_argument("--qa-dir", type=Path, default=QA)
    args = parser.parse_args()
    assign(args.points, args.adm1, args.adm2, args.output, args.qa_dir)


if __name__ == "__main__":
    main()
