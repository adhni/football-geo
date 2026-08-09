from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
OUT = ROOT / "data" / "processed"

st.set_page_config(page_title="Football Talent Geography", layout="wide")
st.title("Football Talent Geography")
st.caption("Seed demo — the production pipeline is designed for the frozen FIFA top 20, 1999-00 to 2025-26.")

final = pd.read_csv(SEED / "italy_2006_final_starters.csv")
squad = pd.read_csv(SEED / "italy_2005_06_11v11.csv")

c1, c2, c3 = st.columns(3)
c1.metric("2006 final starters", len(final))
c2.metric("Born in Italy", int((final.birth_country == "Italy").sum()))
c3.metric("2005-06 Italy starts in source", int(squad.starts.sum()))

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
st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip={"text": "{player}\n{birth_city}, {birth_country}"}))

st.subheader("Seed source: Italy 2005-06 starts")
st.dataframe(squad.sort_values("starts", ascending=False), use_container_width=True, hide_index=True)

st.info("After full ingestion this page becomes the Country Explorer with ADM1/ADM2 choropleths, raw/per-capita toggles, period filters and player drill-down.")
