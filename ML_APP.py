"""
India Healthcare Facilities Dashboard
Run:  streamlit run app.py
Needs: national_all_years_merged.csv in the same folder as this file.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------- STEP 1: config
st.set_page_config(page_title="India Healthcare Facilities", layout="wide")

CSV_PATH = "national_all_years_merged.csv"

# column name in CSV -> friendly label shown to users
FACILITY_COLS = {
    "sub_centres": "Sub Centres",
    "phcs": "Primary Health Centres (PHC)",
    "chcs": "Community Health Centres (CHC)",
    "sub_divisional_hospital": "Sub-Divisional Hospitals",
    "district_hospital": "District Hospitals",
}


# ---------------------------------------------------------------- STEP 2: load + clean
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(Path(__file__).parent / "national_all_years_merged.csv")

    # tidy text columns (extra spaces, inconsistent casing)
    for c in ["state", "district"]:
        df[c] = df[c].astype(str).str.strip()
    df["state"] = df["state"].str.title().str.replace(" And ", " & ", regex=False)
    df["state"] = df["state"].replace(
        {"The Dadra & Nagar Haveli & Daman & Diu": "Dadra & Nagar Haveli and Daman & Diu"}
    )

    # one combined number for "how many facilities in total"
    cols = list(FACILITY_COLS)
    df["total_facilities"] = df[cols].sum(axis=1)

    # population is Census-2011 and missing for newer districts -> per-lakh is NaN there
    pop_lakh = df["population"] / 100_000
    for c in cols + ["total_facilities"]:
        df[f"{c}_per_lakh"] = df[c] / pop_lakh
    return df


df = load_data()

# ---------------------------------------------------------------- STEP 3: sidebar filters
st.sidebar.header("Filters")
years = sorted(df["year"].unique())
year = st.sidebar.selectbox("Year", years, index=len(years) - 1)

all_states = sorted(df["state"].unique())
picked_states = st.sidebar.multiselect("States (empty = all)", all_states)

d = df[df["year"] == year]
if picked_states:
    d = d[d["state"].isin(picked_states)]

st.title("India Healthcare Facilities Dashboard")
st.caption(
    "Source: district-wise facility counts. Population = Census 2011, so per-lakh "
    "figures are indicative, and districts created after 2011 have no population."
)

tab_over, tab_state, tab_dist, tab_trend, tab_data = st.tabs(
    ["Overview", "State comparison", "District drill-down", "Trends over years", "Data table"]
)

# ---------------------------------------------------------------- STEP 4: overview
with tab_over:
    c = st.columns(6)
    c[0].metric("Districts", f"{d['district'].nunique():,}")
    for col, (key, label) in zip(c[1:], FACILITY_COLS.items()):
        col.metric(label.split(" (")[0], f"{int(d[key].sum()):,}")

    left, right = st.columns(2)
    totals = (
        d[list(FACILITY_COLS)].sum().rename(index=FACILITY_COLS).reset_index()
    )
    totals.columns = ["Facility type", "Count"]
    left.plotly_chart(
        px.pie(totals, names="Facility type", values="Count", hole=0.45,
               title="Share of facility types"),
        width="stretch",
    )

    mix = d.groupby("state")[list(FACILITY_COLS)].sum().rename(columns=FACILITY_COLS)
    mix = mix.loc[mix.sum(axis=1).sort_values().index]
    right.plotly_chart(
        px.bar(mix, orientation="h", barmode="stack",
               title="Facility mix by state", labels={"value": "Facilities", "state": ""}),
        width="stretch",
    )

# ---------------------------------------------------------------- STEP 5: state comparison
with tab_state:
    c1, c2 = st.columns(2)
    metric_label = c1.selectbox("Facility type", ["All facilities"] + list(FACILITY_COLS.values()))
    mode = c2.radio("Measure", ["Total count", "Per 1 lakh population"], horizontal=True)

    key = "total_facilities" if metric_label == "All facilities" else \
        {v: k for k, v in FACILITY_COLS.items()}[metric_label]

    if mode == "Total count":
        s = d.groupby("state")[key].sum()
        axis = "Facilities"
    else:
        # only districts that have population, otherwise the ratio is wrong
        dp = d.dropna(subset=["population"])
        s = dp.groupby("state")[key].sum() / (dp.groupby("state")["population"].sum() / 100_000)
        axis = "Facilities per lakh people"

    s = s.sort_values(ascending=False).reset_index()
    s.columns = ["State", axis]
    fig = px.bar(s, x="State", y=axis, title=f"{metric_label}: {mode.lower()} ({year})")
    fig.update_layout(xaxis_tickangle=-60, height=550)
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- STEP 6: district drill-down
with tab_dist:
    state_sel = st.selectbox("Choose a state", sorted(d["state"].unique()))
    ds = d[d["state"] == state_sel]

    c1, c2 = st.columns(2)
    dist_metric = c1.selectbox(
        "Facility type ", ["All facilities"] + list(FACILITY_COLS.values()), key="dm"
    )
    dist_mode = c2.radio("Measure ", ["Total count", "Per 1 lakh population"],
                         horizontal=True, key="dmode")
    k = "total_facilities" if dist_metric == "All facilities" else \
        {v: kk for kk, v in FACILITY_COLS.items()}[dist_metric]
    col = k if dist_mode == "Total count" else f"{k}_per_lakh"

    ds = ds.dropna(subset=[col]).sort_values(col, ascending=False)
    if ds.empty:
        st.info("No data for this selection (population missing for these districts).")
    else:
        n = st.slider("Districts to show", 5, min(50, len(ds)), min(15, len(ds))) \
            if len(ds) > 5 else len(ds)
        top, bottom = st.columns(2)
        top.plotly_chart(
            px.bar(ds.head(n), x=col, y="district", orientation="h",
                   title=f"Highest {n}").update_yaxes(autorange="reversed"),
            width="stretch",
        )
        bottom.plotly_chart(
            px.bar(ds.tail(n).sort_values(col), x=col, y="district", orientation="h",
                   title=f"Lowest {n} (possible gaps)", color_discrete_sequence=["#d62728"]),
            width="stretch",
        )

# ---------------------------------------------------------------- STEP 7: trends
with tab_trend:
    base = df if not picked_states else df[df["state"].isin(picked_states)]
    t_label = st.selectbox("Facility type  ", ["All facilities"] + list(FACILITY_COLS.values()),
                           key="tl")
    tk = "total_facilities" if t_label == "All facilities" else \
        {v: kk for kk, v in FACILITY_COLS.items()}[t_label]

    nat = base.groupby("year")[tk].sum().reset_index()
    st.plotly_chart(px.line(nat, x="year", y=tk, markers=True,
                            title=f"{t_label}: total across selected states",
                            labels={tk: "Facilities"}), width="stretch")

    by_state = base.groupby(["state", "year"])[tk].sum().reset_index()
    st.plotly_chart(px.line(by_state, x="year", y=tk, color="state", markers=True,
                            title="By state", labels={tk: "Facilities"}).update_layout(height=550),
                    width="stretch")
    st.caption("Note: a few districts appear/disappear between years (new districts, "
               "reorganisation), so small changes can come from boundaries, not real growth.")

# ---------------------------------------------------------------- STEP 8: table + download
with tab_data:
    show = d.rename(columns=FACILITY_COLS).drop(
        columns=[c for c in d.columns if c.endswith("_per_lakh")] +
                ["lgd_matched_name", "district_census2011_code", "match_type"],
        errors="ignore",
    )
    q = st.text_input("Search district")
    if q:
        show = show[show["district"].str.contains(q, case=False, na=False)]
    st.dataframe(show, width="stretch", height=500)
    st.download_button("Download filtered data (CSV)", show.to_csv(index=False).encode(),
                       "filtered_healthcare_data.csv", "text/csv")

    #python -m streamlit run ML_APP.py