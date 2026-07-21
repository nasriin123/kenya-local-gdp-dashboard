from pathlib import Path
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Kenya Local GDP Explorer",
    page_icon="🇰🇪",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ADM1_CSV_PATH = DATA_DIR / "kenya_adm1_county_year.csv"
BOUNDARIES_PATH = DATA_DIR / "kenya_county_boundaries.geojson"
ADM0_PATH = DATA_DIR / "kenya_adm0_national_year.csv"
VERIFY_PATH = DATA_DIR / "verification_totals.csv"

VARIABLES = {
    "Total predicted GDP (constant 2017 PPP, billion)": "gdp_county",
    "Population": "pop_county",
    "GDP per capita (constant 2017 PPP dollars)": "gdppc_county",
    "Log GDP per capita": "ln_gdppc_county",
}


@st.cache_data(show_spinner=False)
def load_data():
    # Read county boundaries separately
    county_boundaries = gpd.read_file(
        BOUNDARIES_PATH
    ).to_crs("EPSG:4326")

    # Read county-year panel
    county_panel = pd.read_csv(ADM1_CSV_PATH)

    # Avoid duplicate county-name columns during the merge
    county_panel = county_panel.drop(
        columns=["NAME_1"],
        errors="ignore"
    )

    # Merge geometry with the county-year panel
    adm1 = county_boundaries[
        ["GID_1", "NAME_1", "geometry"]
    ].drop_duplicates("GID_1").merge(
        county_panel,
        on="GID_1",
        how="left",
        validate="one_to_many"
    )

    adm1 = gpd.GeoDataFrame(
        adm1,
        geometry="geometry",
        crs=county_boundaries.crs
    )

    adm0 = pd.read_csv(ADM0_PATH)
    verification = pd.read_csv(VERIFY_PATH)

    adm1["year"] = pd.to_numeric(
        adm1["year"],
        errors="coerce"
    ).astype("Int64")

    adm0["year"] = pd.to_numeric(
        adm0["year"],
        errors="coerce"
    ).astype("Int64")

    verification["year"] = pd.to_numeric(
        verification["year"],
        errors="coerce"
    ).astype("Int64")

    return adm1, adm0, verification


adm1, adm0, verification = load_data()
years = sorted(adm1["year"].dropna().astype(int).unique().tolist())
county_count = int(adm1["GID_1"].nunique())

st.title("🇰🇪 Kenya Local GDP Explorer")
st.caption(
    f"Spatial and temporal exploration of 0.5° gridded local-GDP estimates "
    f"aggregated to Kenyan counties, {min(years)}–{max(years)}."
)

with st.sidebar:
    st.header("Explore")
    selected_year = st.select_slider("Year", options=years, value=max(years))
    selected_label = st.selectbox("Map variable", list(VARIABLES.keys()), index=2)
    selected_var = VARIABLES[selected_label]
    log_color = st.checkbox(
        "Use log colour scale",
        value=selected_var in {"gdp_county", "pop_county"},
    )

    st.divider()
    st.subheader("Dataset status")
    st.write(f"**Counties retained:** {county_count}")
    st.write(f"**County-year rows:** {len(adm1):,}")
    st.write(f"**Years:** {min(years)}–{max(years)}")
    st.write(
        f"**County-year rows with no grid estimate:** "
        f"{int(adm1['gdp_county'].isna().sum()):,}"
    )

selected = adm1.loc[adm1["year"] == selected_year].copy().reset_index(drop=True)
selected["map_value"] = selected[selected_var]
if log_color:
    selected["map_value"] = np.log1p(selected[selected_var].clip(lower=0))

national_row = adm0.loc[adm0["year"] == selected_year].iloc[0]
previous = adm0.loc[adm0["year"] == selected_year - 1]
prev_gdp = previous["national_gdp"].iloc[0] if not previous.empty else None
prev_pc = previous["national_gdppc"].iloc[0] if not previous.empty else None

gdp_delta = None if prev_gdp is None else 100 * (national_row["national_gdp"] / prev_gdp - 1)
pc_delta = None if prev_pc is None else 100 * (national_row["national_gdppc"] / prev_pc - 1)

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "National predicted GDP",
    f"{national_row['national_gdp']:.1f} bn",
    None if gdp_delta is None else f"{gdp_delta:.1f}% YoY",
)
c2.metric("National population", f"{national_row['national_pop'] / 1e6:.1f} million")
c3.metric(
    "National GDP per capita",
    f"${national_row['national_gdppc']:,.0f}",
    None if pc_delta is None else f"{pc_delta:.1f}% YoY",
)
c4.metric(
    "Counties with estimates",
    f"{selected[selected_var].notna().sum()} / {county_count}",
)

st.subheader(f"County map — {selected_label}, {selected_year}")
geojson = json.loads(selected.to_json())

valid = selected[selected["map_value"].notna()].copy()
missing = selected[selected["map_value"].isna()].copy()

fig_map = go.Figure()

if not valid.empty:
    fig_map.add_trace(
        go.Choroplethmapbox(
            geojson=geojson,
            locations=valid["GID_1"],
            z=valid["map_value"],
            featureidkey="properties.GID_1",
            colorscale="Viridis",
            marker_opacity=0.78,
            marker_line_width=0.7,
            customdata=np.stack(
                [
                    valid["NAME_1"],
                    valid["gdp_county"],
                    valid["pop_county"],
                    valid["gdppc_county"],
                    valid["ln_gdppc_county"],
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "GDP: %{customdata[1]:.3f} bn<br>"
                "Population: %{customdata[2]:,.0f}<br>"
                "GDP per capita: $%{customdata[3]:,.0f}<br>"
                "Log GDP per capita: %{customdata[4]:.2f}<extra></extra>"
            ),
            colorbar_title="log(1+x)" if log_color else selected_label,
            name="Estimated",
        )
    )

if not missing.empty:
    fig_map.add_trace(
        go.Choroplethmapbox(
            geojson=geojson,
            locations=missing["GID_1"],
            z=[0] * len(missing),
            featureidkey="properties.GID_1",
            colorscale=[[0, "#d9d9d9"], [1, "#d9d9d9"]],
            showscale=False,
            marker_opacity=0.85,
            marker_line_width=0.8,
            customdata=missing[["NAME_1"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>No 0.5° grid estimate<extra></extra>",
            name="No data",
        )
    )

fig_map.update_layout(
    mapbox_style="carto-positron",
    mapbox_center={"lat": 0.2, "lon": 37.9},
    mapbox_zoom=5.4,
    margin=dict(l=0, r=0, t=0, b=0),
    height=630,
    legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01),
)
st.plotly_chart(fig_map, use_container_width=True)
st.caption(
    "Grey counties are retained in the panel but have no assigned 0.5° grid centroid; "
    "their values are missing rather than coded as zero."
)

left, right = st.columns([1.35, 1])
with left:
    st.subheader("National trends")
    trend_choice = st.radio(
        "Series",
        ["National GDP", "GDP per capita", "Population"],
        horizontal=True,
        label_visibility="collapsed",
    )
    trend_map = {
        "National GDP": ("national_gdp", "Billion, constant 2017 PPP"),
        "GDP per capita": ("national_gdppc", "Constant 2017 PPP dollars"),
        "Population": ("national_pop", "Persons"),
    }
    trend_var, y_title = trend_map[trend_choice]
    fig_trend = px.line(adm0, x="year", y=trend_var, markers=True)
    fig_trend.update_layout(
        xaxis_title="Year",
        yaxis_title=y_title,
        height=410,
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with right:
    st.subheader(f"County ranking, {selected_year}")
    ranking = (
        selected[["NAME_1", selected_var]]
        .dropna()
        .sort_values(selected_var, ascending=False)
    )
    tab_top, tab_bottom = st.tabs(["Highest", "Lowest"])
    with tab_top:
        st.dataframe(
            ranking.head(10).rename(
                columns={"NAME_1": "County", selected_var: selected_label}
            ),
            hide_index=True,
            use_container_width=True,
        )
    with tab_bottom:
        st.dataframe(
            ranking.tail(10)
            .sort_values(selected_var)
            .rename(columns={"NAME_1": "County", selected_var: selected_label}),
            hide_index=True,
            use_container_width=True,
        )

st.subheader("County trajectories")
county_options = sorted(adm1["NAME_1"].dropna().unique().tolist())
default_counties = [
    county
    for county in ["Nairobi", "Turkana", "Kisumu", "Nakuru"]
    if county in county_options
]
chosen_counties = st.multiselect(
    "Choose counties",
    county_options,
    default=default_counties,
)
if chosen_counties:
    county_trend = adm1.loc[adm1["NAME_1"].isin(chosen_counties)]
    fig_county = px.line(
        county_trend,
        x="year",
        y=selected_var,
        color="NAME_1",
        markers=True,
    )
    fig_county.update_layout(
        xaxis_title="Year",
        yaxis_title=selected_label,
        legend_title="County",
        height=450,
    )
    st.plotly_chart(fig_county, use_container_width=True)
else:
    st.info("Select at least one county to display its trajectory.")

with st.expander("Methodology and caveats"):
    st.markdown(
        """
**Construction.** Global 0.5° local-GDP cells were filtered to Kenya and merged with the official grid geometry. Cell locations were assigned to GADM ADM1 county boundaries using spatial containment, with a nearest-county fallback for unmatched cells. GDP and population were then summed by county and year.

**Interpretation.** These are model-predicted local-GDP estimates, not official KNBS Gross County Product. The current series uses constant 2017 PPP measures from the source file.

**Coverage.** All 47 counties are retained. Six counties receive no 0.5° grid centroid and therefore have missing estimates for all years. Missing values are not replaced with zero.

**Limitations.** A 0.5° grid is coarse relative to small and urban counties. Centroid assignment can be imperfect around borders and the coast. Validation against official county GDP is a separate next step.
        """
    )

with st.expander("Verification"):
    st.dataframe(verification, hide_index=True, use_container_width=True)
    max_gdp_diff = verification["gdp_difference"].abs().max()
    max_pop_diff = verification["population_difference"].abs().max()
    st.write(f"Maximum absolute GDP aggregation difference: **{max_gdp_diff:.3e}**")
    st.write(f"Maximum absolute population aggregation difference: **{max_pop_diff:.3e}**")

st.caption(
    "Source: Local GDP Estimates Around the World; county boundaries: GADM. "
    "Prepared as an exploratory seminar dashboard."
)
