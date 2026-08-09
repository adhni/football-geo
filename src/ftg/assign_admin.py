from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def assign(points_path: Path, adm1_path: Path, adm2_path: Path) -> pd.DataFrame:
    players = pd.read_parquet(points_path)
    pts = players.dropna(subset=["birth_lon", "birth_lat"]).copy()
    gpts = gpd.GeoDataFrame(
        pts,
        geometry=gpd.points_from_xy(pts.birth_lon, pts.birth_lat),
        crs="EPSG:4326",
    )
    a1 = gpd.read_file(adm1_path).to_crs("EPSG:4326")
    a2 = gpd.read_file(adm2_path).to_crs("EPSG:4326")
    # Keep all source columns; rename the desired display/code fields in a country-specific
    # normalisation step before using this function if necessary.
    j1 = gpd.sjoin(gpts, a1, how="left", predicate="within", rsuffix="adm1")
    j2 = gpd.sjoin(gpts, a2, how="left", predicate="within", rsuffix="adm2")
    # Persist full joins for QA; Codex should add a normalised canonical admin schema.
    j1.drop(columns="geometry").to_parquet(PROCESSED / "player_adm1_raw.parquet", index=False)
    j2.drop(columns="geometry").to_parquet(PROCESSED / "player_adm2_raw.parquet", index=False)
    return pts


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--points", type=Path, default=PROCESSED / "players_enriched.parquet")
    p.add_argument("--adm1", type=Path, required=True)
    p.add_argument("--adm2", type=Path, required=True)
    a = p.parse_args()
    assign(a.points, a.adm1, a.adm2)


if __name__ == "__main__":
    main()
