from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

# ------------------------------------------------------------
# 0) Configuration
# ------------------------------------------------------------
load_dotenv()  # reads .env if present

BASE_URL = os.getenv("FOURTU_BASE_URL", "https://data.4tu.nl").rstrip("/")
TIMEOUT = int(os.getenv("FOURTU_TIMEOUT", "30"))
TOKEN = os.getenv("FOURTU_TOKEN", "").strip()  # optional for public monitoring

DEFAULT_PUBLISHED_SINCE = os.getenv("UC01_PUBLISHED_SINCE", "2025-01-01")
DEFAULT_PAGE_SIZE = int(os.getenv("UC01_PAGE_SIZE", "11687"))
DEFAULT_MAX_PAGES = int(os.getenv("UC01_MAX_PAGES", "3"))


def headers() -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if TOKEN:
        h["Authorization"] = f"token {TOKEN}"
    return h


# ------------------------------------------------------------
# 1) "Client" functions (keep them tiny and readable)
# ------------------------------------------------------------
def get_groups() -> List[Dict[str, Any]]:
    """GET /v3/groups"""
    url = f"{BASE_URL}/v3/groups"
    r = requests.get(url, headers=headers(), timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def get_articles_page(
    *,
    item_type: int,
    published_since: str,
    limit: int,
    offset: int,
) -> List[Dict[str, Any]]:
    """GET /v2/articles (paged)"""
    url = f"{BASE_URL}/v2/articles"
    params = {
        "item_type": item_type,
        "published_since": published_since,
        "limit": limit,
        "offset": offset,
    }
    r = requests.get(url, headers=headers(), params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def get_recent_articles(
    *,
    item_type: int,
    published_since: str,
    page_size: int,
    max_pages: int,
) -> List[Dict[str, Any]]:
    """Fetch up to max_pages of articles using limit/offset."""
    all_items: List[Dict[str, Any]] = []
    for page in range(max_pages):
        offset = page * page_size
        batch = get_articles_page(
            item_type=item_type,
            published_since=published_since,
            limit=page_size,
            offset=offset,
        )
        all_items.extend(batch)
        if len(batch) < page_size:
            break
    return all_items


# ------------------------------------------------------------
# 2) Transformations
# ------------------------------------------------------------
def build_group_map(groups: List[Dict[str, Any]]) -> Dict[int, str]:
    """Map group id -> name."""
    out: Dict[int, str] = {}
    for g in groups:
        gid = g.get("id")
        name = g.get("name")
        if isinstance(gid, int) and isinstance(name, str):
            out[gid] = name
    return out


def to_dataframe(
    articles: List[Dict[str, Any]],
    group_map: Dict[int, str],
) -> pd.DataFrame:
    """Extract minimal columns needed for dashboard."""
    rows = []
    for a in articles:
        gid = a.get("group_id")
        rows.append(
            {
                "id": a.get("id"),
                "title": a.get("title"),
                "published_date": a.get("published_date"),
                "group_id": gid,
                "group_name": group_map.get(gid, "Unknown"),
                "doi": a.get("doi"),
                "uuid": a.get("uuid"),
                "url": a.get("url"),
            }
        )
    df = pd.DataFrame(rows)
    if "published_date" in df.columns:
        df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")
    return df


# ------------------------------------------------------------
# 3) Streamlit app
# ------------------------------------------------------------
st.set_page_config(page_title="4TU Monitoring MVP", layout="wide")
st.title("4TU Dataset/Software Monitoring Dashboard (MVP)")
st.caption(f"Source: {BASE_URL}")

with st.sidebar:
    st.header("Data source")
    use_cache = st.checkbox("Use Streamlit cache", value=True)

    refresh = st.button("Refresh now")

    st.header("Query")
    item_type_label = st.selectbox("Item type", ["Dataset (3)", "Software (9)"], index=0)
    item_type = 3 if item_type_label.startswith("Dataset") else 9

    published_since = st.text_input("published_since (YYYY-MM-DD)", value=DEFAULT_PUBLISHED_SINCE)
    page_size = st.number_input("page_size", min_value=10, max_value=11687, value=DEFAULT_PAGE_SIZE, step=10)
    max_pages = st.number_input("max_pages", min_value=1, max_value=50, value=DEFAULT_MAX_PAGES, step=1)

    st.caption(f"Effective item_type = {item_type}")


# Caching: keyed by function args (item_type, published_since, etc.)
@st.cache_data(show_spinner=True)
def load_data_cached(
    *,
    item_type: int,
    published_since: str,
    page_size: int,
    max_pages: int,
) -> pd.DataFrame:
    groups = get_groups()
    group_map = build_group_map(groups)
    articles = get_recent_articles(
        item_type=item_type,
        published_since=published_since,
        page_size=page_size,
        max_pages=max_pages,
    )
    return to_dataframe(articles, group_map)


if refresh:
    load_data_cached.clear()

if use_cache:
    df = load_data_cached(
        item_type=item_type,
        published_since=published_since,
        page_size=int(page_size),
        max_pages=int(max_pages),
    )
else:
    # No cache path: call the same logic directly
    groups = get_groups()
    group_map = build_group_map(groups)
    articles = get_recent_articles(
        item_type=item_type,
        published_since=published_since,
        page_size=int(page_size),
        max_pages=int(max_pages),
    )
    df = to_dataframe(articles, group_map)

if df.empty:
    st.warning("No results returned. Try a different published_since or increase max_pages.")
    st.stop()


# ------------------------------------------------------------
# 4) Filters
# ------------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    group_options = sorted([g for g in df["group_name"].dropna().unique().tolist() if isinstance(g, str)])
    group_choice = st.selectbox("Affiliation (group)", ["All"] + group_options)

    date_series = df["published_date"].dropna()
    if not date_series.empty:
        min_d = date_series.min().date()
        max_d = date_series.max().date()
        start_d, end_d = st.date_input("Publication date range", value=(min_d, max_d))
    else:
        start_d = end_d = None
        st.info("No published_date found to filter on.")

    keyword = st.text_input("Keyword in title", value="").strip()

filtered = df.copy()

if group_choice != "All":
    filtered = filtered[filtered["group_name"] == group_choice]

if start_d and end_d and filtered["published_date"].notna().any():
    filtered = filtered[
        (filtered["published_date"].dt.date >= start_d)
        & (filtered["published_date"].dt.date <= end_d)
    ]

if keyword:
    filtered = filtered[filtered["title"].fillna("").str.contains(keyword, case=False, na=False)]


# ------------------------------------------------------------
# 5) Output
# ------------------------------------------------------------
col1, col2 = st.columns([1, 3])

with col1:
    st.metric("Results", int(len(filtered)))
    st.download_button(
        "Download CSV",
        data=filtered.drop(columns=["group_id"], errors="ignore").to_csv(index=False),
        file_name=f"4tu_monitoring_item_type_{item_type}.csv",
        mime="text/csv",
    )

with col2:
    st.dataframe(
        filtered.drop(columns=["group_id"], errors="ignore"),
        width="stretch",
        hide_index=True,
    )

with st.expander("Diagnostics"):
    st.write("Loaded rows:", len(df))
    st.write("Columns:", list(df.columns))

# ------------------------------------------------------------
# 6) Plotting
# ------------------------------------------------------------
st.subheader("Quick plot")

plot_choice = st.selectbox(
    "Choose a plot",
    [
        "Items per group",
        "Items per publication date",
    ],
)

if plot_choice == "Items per group":
    plot_df = (
        filtered["group_name"]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("group_name")
        .reset_index(name="count")
    )

    st.write("Number of items per affiliation/group")
    st.bar_chart(plot_df.set_index("group_name"))

elif plot_choice == "Items per publication date":
    date_plot_df = filtered.dropna(subset=["published_date"]).copy()

    if date_plot_df.empty:
        st.info("No publication dates available for plotting.")
    else:
        date_plot_df["published_day"] = date_plot_df["published_date"].dt.date

        counts_by_day = (
            date_plot_df["published_day"]
            .value_counts()
            .sort_index()
            .rename_axis("published_day")
            .reset_index(name="count")
        )

        st.write("Number of items per publication date")
        st.bar_chart(counts_by_day.set_index("published_day"))