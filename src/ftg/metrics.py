from __future__ import annotations

import numpy as np
import pandas as pd


def area_metrics(
    starts: pd.DataFrame,
    player_geo: pd.DataFrame,
    population: pd.DataFrame | None = None,
    geo_level: str = "ADM1",
) -> pd.DataFrame:
    code_col = "adm1_code" if geo_level.upper() == "ADM1" else "adm2_code"
    name_col = "adm1_name" if geo_level.upper() == "ADM1" else "adm2_name"
    merged = starts.merge(player_geo[["player_id", code_col, name_col]], on="player_id", how="left")
    grouped = (
        merged.dropna(subset=[code_col])
        .groupby(["team", code_col, name_col], as_index=False)
        .agg(
            unique_starters=("player_id", lambda s: s[merged.loc[s.index, "starts"].gt(0)].nunique()),
            starts=("starts", "sum"),
            sub_appearances=("sub_appearances", "sum"),
        )
    )
    grouped["geo_level"] = geo_level.upper()
    grouped = grouped.rename(columns={code_col: "geo_code", name_col: "geo_name"})
    if population is not None:
        pop = population[population["geo_level"].str.upper().eq(geo_level.upper())].copy()
        # Headline v1 comparison defaults to 2025 unless caller prefilters otherwise.
        if "year" in pop.columns and (pop["year"] == 2025).any():
            pop = pop[pop["year"] == 2025]
        grouped = grouped.merge(pop[["geo_code", "population"]], on="geo_code", how="left")
        grouped["starts_per_million"] = grouped["starts"] / grouped["population"] * 1_000_000
        grouped["starters_per_million"] = grouped["unique_starters"] / grouped["population"] * 1_000_000
    return grouped


def hhi_by_team(area_metrics_df: pd.DataFrame, weight_col: str = "starts") -> pd.DataFrame:
    df = area_metrics_df.copy()
    totals = df.groupby("team")[weight_col].transform("sum")
    df["share"] = np.where(totals > 0, df[weight_col] / totals, 0)
    return df.groupby("team", as_index=False).agg(hhi=("share", lambda s: float((s**2).sum())))
