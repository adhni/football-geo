from __future__ import annotations

import numpy as np
import pandas as pd


def area_metrics(
    starts: pd.DataFrame,
    player_geo: pd.DataFrame,
    population: pd.DataFrame | None = None,
    geo_level: str = "ADM1",
) -> pd.DataFrame:
    level = geo_level.upper()
    if level not in {"ADM1", "ADM2"}:
        raise ValueError("geo_level must be ADM1 or ADM2")
    code_col = "adm1_code" if level == "ADM1" else "adm2_code"
    name_col = "adm1_name" if level == "ADM1" else "adm2_name"
    required_starts = {"team", "player_id", "starts", "sub_appearances"}
    required_geo = {"player_id", code_col, name_col}
    if missing := required_starts - set(starts.columns):
        raise ValueError(f"starts is missing columns: {', '.join(sorted(missing))}")
    if missing := required_geo - set(player_geo.columns):
        raise ValueError(f"player_geo is missing columns: {', '.join(sorted(missing))}")
    if player_geo["player_id"].duplicated().any():
        raise ValueError("player_geo must contain one row per player_id")

    merged = starts.merge(player_geo[["player_id", code_col, name_col]], on="player_id", how="left")
    merged["starter_player_id"] = merged["player_id"].where(merged["starts"].gt(0))
    grouped = (
        merged.dropna(subset=[code_col])
        .groupby(["team", code_col, name_col], as_index=False)
        .agg(
            unique_starters=("starter_player_id", "nunique"),
            starts=("starts", "sum"),
            sub_appearances=("sub_appearances", "sum"),
        )
    )
    grouped["geo_level"] = level
    grouped = grouped.rename(columns={code_col: "geo_code", name_col: "geo_name"})
    if population is not None:
        required_population = {"geo_level", "geo_code", "population"}
        if missing := required_population - set(population.columns):
            raise ValueError(f"population is missing columns: {', '.join(sorted(missing))}")
        pop = population[population["geo_level"].str.upper().eq(level)].copy()
        if "year" in pop.columns and (pop["year"] == 2025).any():
            pop = pop[pop["year"] == 2025]
        if pop["geo_code"].duplicated().any():
            raise ValueError(f"population contains duplicate {level} geo_code rows for the selected epoch")
        pop.loc[pop["population"].le(0), "population"] = np.nan
        grouped = grouped.merge(pop[["geo_code", "population"]], on="geo_code", how="left")
        grouped["starts_per_million"] = grouped["starts"] / grouped["population"] * 1_000_000
        grouped["starters_per_million"] = grouped["unique_starters"] / grouped["population"] * 1_000_000
    return grouped


def hhi_by_team(area_metrics_df: pd.DataFrame, weight_col: str = "starts") -> pd.DataFrame:
    if weight_col not in area_metrics_df.columns:
        raise ValueError(f"Unknown weight column: {weight_col}")
    frame = area_metrics_df.copy()
    totals = frame.groupby("team")[weight_col].transform("sum")
    frame["share"] = np.where(totals > 0, frame[weight_col] / totals, 0)
    return frame.groupby("team", as_index=False).agg(hhi=("share", lambda values: float((values**2).sum())))
