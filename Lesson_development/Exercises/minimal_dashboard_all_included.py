from __future__ import annotations

# ============================================================
# 1. Import the libraries we need
# ============================================================
import pandas as pd
import requests
import streamlit as st

# ============================================================
# 2. Basic page setup
# ============================================================
st.set_page_config(page_title="4TU Dataset Dashboard", layout="wide")
st.title("4TU.ResearchData Minimal Dashboard")
st.write("A simple Streamlit dashboard that reads dataset metadata from the 4TU.ResearchData API.")

# ============================================================
# 3. API settings
# ============================================================
BASE_URL = "https://data.4tu.nl"
ARTICLES_ENDPOINT = f"{BASE_URL}/v2/articles"
GROUPS_ENDPOINT = f"{BASE_URL}/v3/groups"

# ============================================================
# 4. Small helper function to request JSON from an endpoint
# ============================================================
def get_json(url: str, params: dict | None = None) -> list | dict:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

# ============================================================
# 5. Load institutional groups
#    We use this to translate group IDs into group names
# ============================================================
group_map = {}

try:
    groups_data = get_json(GROUPS_ENDPOINT)

    if isinstance(groups_data, list):
        for group in groups_data:
            group_id = group.get("id")
            group_name = group.get("name")

            if group_id is not None and group_name:
                group_map[group_id] = group_name

except requests.RequestException as e:
    st.warning(f"Could not load groups from the API: {e}")

# ============================================================
# 6. Load a small batch of datasets
#    We keep the number small to make the workshop faster
# ============================================================
try:
    articles_data = get_json(
        ARTICLES_ENDPOINT,
        params={
            "limit": 500,
            "offset": 0,
        },
    )
except requests.RequestException as e:
    st.error(f"Could not load datasets from the API: {e}")
    st.stop()

# ============================================================
# 7. Turn the JSON into a simpler table
#    We only keep a few fields for the workshop
# ============================================================
rows = []

if isinstance(articles_data, list):
    for article in articles_data:
        article_id = article.get("id")
        title = article.get("title", "No title")
        published_date = article.get("published_date")
        group_id = article.get("group_id")
        institution = group_map.get(group_id, f"Unknown group ({group_id})")

        rows.append(
            {
                "id": article_id,
                "title": title,
                "published_date": published_date,
                "institution": institution,
            }
        )

df = pd.DataFrame(rows)

# ============================================================
# 8. Clean the date column
#    We convert text dates into pandas datetime values
# ============================================================
if not df.empty:
    df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")
    df = df[df["published_date"].dt.year >= 2020]

# ============================================================
# 9. Sidebar filters
# ============================================================
st.sidebar.header("Filters")

# ---- Institution filter ----
institution_options = ["All"]

if not df.empty and "institution" in df.columns:
    unique_institutions = sorted(df["institution"].dropna().unique().tolist())
    institution_options.extend(unique_institutions)

selected_institution = st.sidebar.selectbox(
    "Institution",
    institution_options,
)

# ---- Date filter ----
min_date = None
max_date = None

if not df.empty and df["published_date"].notna().any():
    min_date = df["published_date"].min().date()
    max_date = df["published_date"].max().date()

selected_start_date = None
selected_end_date = None

if min_date and max_date:
    selected_start_date = st.sidebar.date_input("Start date", value=min_date)
    selected_end_date = st.sidebar.date_input("End date", value=max_date)
else:
    st.sidebar.info("No valid dates available for filtering.")

# ============================================================
# 10. Apply the filters
# ============================================================
filtered_df = df.copy()

# ---- Text search title filter ----
search_term = st.sidebar.text_input("Search in title") #Streamlit widgets return Python variables.

if search_term:
    filtered_df = filtered_df[
        filtered_df["title"].str.contains(search_term, case=False, na=False)
    ]

if selected_institution != "All":
    filtered_df = filtered_df[filtered_df["institution"] == selected_institution]

if selected_start_date and selected_end_date:
    filtered_df = filtered_df[
        (filtered_df["published_date"].dt.date >= selected_start_date)
        & (filtered_df["published_date"].dt.date <= selected_end_date)
    ]

# ============================================================
# 11. Show a few simple dashboard elements
# ============================================================
col1, col2 = st.columns(2)

with col1:
    st.metric("Datasets loaded", len(df))

with col2:
    st.metric("Datasets after filtering", len(filtered_df))

st.subheader("Filtered datasets")
st.dataframe(filtered_df, width="stretch")

# Plotting 

st.subheader("Datasets per institution")

institution_counts = filtered_df["institution"].value_counts()

st.bar_chart(institution_counts)

# Optional CSV download
csv_data = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download filtered data as CSV",
    data=csv_data,
    file_name="filtered_datasets.csv",
    mime="text/csv",
)