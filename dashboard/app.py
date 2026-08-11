from pathlib import Path

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
OUT = ROOT / "data" / "processed"
QA = ROOT / "data" / "qa"
WORLD_CUP_DATA = OUT / "worldcup_player_starts.parquet"
WORLD_CUP_POB_DATA = OUT / "player_starts_with_birthplace.parquet"

st.set_page_config(page_title="Football Talent Geography", layout="wide")
st.title("Football Talent Geography")


def world_cup_dashboard() -> None:
    data = pd.read_parquet(
        WORLD_CUP_POB_DATA if WORLD_CUP_POB_DATA.exists() else WORLD_CUP_DATA
    )
    st.caption("Available dataset — frozen FIFA top 20 at 20 July 2026")
    st.warning(
        "Current coverage is FIFA Men's World Cup finals only (2002–2022), not all national-team matches. "
        "Norway has no rows because it did not qualify during this window."
    )

    years = sorted(int(year) for year in data["season_end_year"].unique())
    teams = sorted(data["team"].unique())
    selected_years = st.sidebar.multiselect("World Cups", years, default=years)
    selected_teams = st.sidebar.multiselect("Teams", teams, default=teams)
    filtered = data[
        data["season_end_year"].isin(selected_years) & data["team"].isin(selected_teams)
    ].copy()

    team_period = filtered.groupby(["team", "season_end_year"], as_index=False).agg(
        matches=("expected_matches", "first"), starts=("starts", "sum")
    )
    columns = st.columns(5)
    columns[0].metric("Teams represented", filtered["team"].nunique())
    columns[1].metric("Unique players", filtered["player_id"].nunique())
    columns[2].metric("Team-match appearances", int(team_period["matches"].sum()))
    columns[3].metric("Recorded starts", int(filtered["starts"].sum()))
    if "pob_mapped" in filtered.columns and len(filtered):
        mapped_players = filtered.loc[filtered["pob_mapped"], "player_id"].nunique()
        coverage = mapped_players / filtered["player_id"].nunique() * 100
        columns[4].metric("POB coverage", f"{coverage:.1f}%")
    else:
        columns[4].metric("POB coverage", "Pending")

    overview, birthplace_tab, players_tab, quality = st.tabs(
        ["Overview", "Birthplace map", "Players", "Coverage & QA"]
    )
    with overview:
        team_summary = filtered.groupby("team", as_index=False).agg(
            starts=("starts", "sum"),
            unique_starters=("player_id", lambda values: values[filtered.loc[values.index, "starts"].gt(0)].nunique()),
            tournaments=("season_end_year", "nunique"),
        )
        chart = px.bar(
            team_summary.sort_values("starts", ascending=True),
            x="starts",
            y="team",
            orientation="h",
            hover_data=["unique_starters", "tournaments"],
            title="World Cup starts by represented team",
        )
        st.plotly_chart(chart, width="stretch")

        timeline = filtered.groupby(["season_end_year", "team"], as_index=False)["starts"].sum()
        st.plotly_chart(
            px.line(
                timeline,
                x="season_end_year",
                y="starts",
                color="team",
                markers=True,
                title="Starts by tournament",
            ),
            width="stretch",
        )

    with birthplace_tab:
        if "pob_mapped" not in filtered.columns:
            st.info("Run `python -m src.ftg.build_birthplaces` after Wikidata enrichment.")
        else:
            mapped = filtered[filtered["pob_mapped"]].copy()
            mapped["starter_player_id"] = mapped["player_id"].where(mapped["starts"].gt(0))
            birthplace_summary = mapped.groupby(
                [
                    "birth_place_qid",
                    "birthplace_wikidata",
                    "birth_country",
                    "birth_lat",
                    "birth_lon",
                ],
                as_index=False,
                dropna=False,
            ).agg(
                players=("player_id", "nunique"),
                unique_starters=("starter_player_id", "nunique"),
                starts=("starts", "sum"),
                teams=("team", lambda values: ", ".join(sorted(set(values)))),
            )
            metric = st.radio(
                "Map metric",
                ["starts", "unique_starters", "players"],
                horizontal=True,
                format_func=lambda value: value.replace("_", " ").title(),
            )
            birthplace_summary["map_value"] = birthplace_summary[metric]
            birthplace_summary["radius"] = 20_000 + birthplace_summary["map_value"].pow(0.5) * 28_000
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=birthplace_summary,
                get_position="[birth_lon, birth_lat]",
                get_radius="radius",
                get_fill_color=[224, 72, 56, 185],
                pickable=True,
                radius_min_pixels=3,
                radius_max_pixels=32,
            )
            st.pydeck_chart(
                pdk.Deck(
                    layers=[layer],
                    initial_view_state=pdk.ViewState(latitude=18, longitude=5, zoom=0.7),
                    tooltip={
                        "html": "<b>{birthplace_wikidata}, {birth_country}</b><br/>"
                        "Starts: {starts}<br/>Unique starters: {unique_starters}<br/>"
                        "Players: {players}<br/>Teams: {teams}"
                    },
                ),
                height=620,
            )
            st.dataframe(
                birthplace_summary.sort_values(metric, ascending=False)[
                    [
                        "birthplace_wikidata",
                        "birth_country",
                        "starts",
                        "unique_starters",
                        "players",
                        "teams",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )

    with players_tab:
        player_summary = filtered.groupby(["player_id", "player_name"], as_index=False).agg(
            teams=("team", lambda values: ", ".join(sorted(set(values)))),
            tournaments=("season_end_year", "nunique"),
            starts=("starts", "sum"),
            sub_appearances=("sub_appearances", "sum"),
            dob=("dob", "first"),
            birthplace=("birthplace_wikidata", "first") if "birthplace_wikidata" in filtered else ("dob", lambda values: None),
            birth_country=("birth_country", "first") if "birth_country" in filtered else ("dob", lambda values: None),
        )
        st.dataframe(
            player_summary.sort_values(["starts", "player_name"], ascending=[False, True]),
            width="stretch",
            hide_index=True,
        )

    with quality:
        st.write(
            "All available team-tournament totals passed the lineup check: "
            "recorded starts equal 11 × matches."
        )
        coverage_path = QA / "worldcup_team_tournament_coverage.csv"
        if coverage_path.exists():
            st.dataframe(pd.read_csv(coverage_path), width="stretch", hide_index=True)
        pob_coverage_path = QA / "birthplace_coverage_by_team.csv"
        if pob_coverage_path.exists():
            st.subheader("Validated birthplace coverage")
            st.dataframe(pd.read_csv(pob_coverage_path), width="stretch", hide_index=True)
        unresolved_path = QA / "wikidata_resolution_queue.csv"
        if unresolved_path.exists():
            st.subheader("Unresolved player QA")
            st.dataframe(pd.read_csv(unresolved_path), width="stretch", hide_index=True)


def seed_dashboard() -> None:
    st.caption(
        "Seed demo — the production pipeline is designed for the frozen FIFA top 20, "
        "1999-00 to 2025-26."
    )
    final = pd.read_csv(SEED / "italy_2006_final_starters.csv")
    squad = pd.read_csv(SEED / "italy_2005_06_11v11.csv")

    columns = st.columns(3)
    columns[0].metric("2006 final starters", len(final))
    columns[1].metric("Born in Italy", int((final.birth_country == "Italy").sum()))
    columns[2].metric("2005-06 Italy starts in source", int(squad.starts.sum()))

    st.subheader("2006 World Cup Final XI — birthplaces")
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=final,
        get_position="[lon, lat]",
        get_radius=35000,
        pickable=True,
        opacity=0.75,
    )
    view = pdk.ViewState(latitude=42.5, longitude=12.5, zoom=3.2)
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={"text": "{player}\n{birth_city}, {birth_country}"},
        )
    )
    st.dataframe(
        squad.sort_values("starts", ascending=False), width="stretch", hide_index=True
    )


if WORLD_CUP_DATA.exists():
    world_cup_dashboard()
else:
    seed_dashboard()
