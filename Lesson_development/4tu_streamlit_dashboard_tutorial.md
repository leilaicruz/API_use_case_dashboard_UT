# Build a simple dashboard for 4TU.ResearchData API data with Python and Streamlit

This tutorial shows how to build a small Streamlit dashboard on top of data retrieved from the 4TU.ResearchData API. The goal is not to build a production application immediately, but to create a clean, teachable foundation that other people can run, extend, and publish.

This is part of a series of tutorials on different ways of using the API of 4TU.ResearchData relevant for researchers and support staff at technical universities.

## Goal of the tutorial

You will create a small web app that:

- fetches metadata from the 4TU.ResearchData API,
- transforms the API response into a tabular structure with `pandas`,
- presents the result in Streamlit,
- adds a text search filter,
- adds a simple visualization,
- and can be deployed online with Streamlit Community Cloud.



## The main workflow

A dashboard is easier to explain and maintain when you separate it into three layers:

### 1. Data access layer
This layer is responsible for talking to the API.

Typical responsibilities:

- define the API endpoint,
- send HTTP requests,
- pass authentication headers when needed,
- handle errors,
- return raw JSON.

In Python, this is usually implemented with `requests`.

### 2. Data transformation layer
This layer converts the raw JSON into a structure that is easier to use in the UI.

Typical responsibilities:

- extract the list of records from the API response,
- flatten nested JSON,
- rename columns,
- clean missing values,
- derive helper columns such as year, author string, or record URL.

In Python, this is typically done with `pandas`.

### 3. Data presentation layer
This layer renders the dashboard.

Typical responsibilities:

- page title and introduction,
- controls such as filters and search boxes,
- metrics and tables,
- charts,
- links back to the original records.

In this tutorial, this layer is built with Streamlit.

That gives you a simple mental model:

```text
4TU.ResearchData API -> Python request -> pandas cleanup -> Streamlit dashboard
```

This separation is worth emphasizing in the tutorial because it makes later extensions much easier. For example, if the API response changes, you usually only update the access or transformation code, not the whole dashboard.


## Installation


Before starting, complete the environment setup described in [the workshop materials repo](https://github.com/4TUResearchData-Carpentries/API_use_case_dashboard_UT/blob/main/Lesson_development/installations_instructions.md).

At minimum, make sure you have:
- Python 3.10+
- streamlit
- pandas
- requests


## Recommended repository structure

A simple structure for this lesson is:

```text
project/
├── minimal_dashboard.py
├── requirements.txt
├── installation.md
└── tutorial_dashboard.md
```



## Coding the web app

- The original python scripts lives in the [workshop materials repo](https://github.com/4TUResearchData-Carpentries/API_use_case_dashboard_UT/blob/main/Lesson_development/minimal_dashboard.py)

- repository file: `minimal_dashboard.py`
- tutorial section: “Full minimal example” with the full code
- follow-up subsections: “How it works” and “Extensions”

### Full code

```python
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
st.dataframe(filtered_df, use_container_width=True)

# Optional CSV download
csv_data = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download filtered data as CSV",
    data=csv_data,
    file_name="filtered_datasets.csv",
    mime="text/csv",
)
```

## Running the app locally

From the project directory, run:

```bash
streamlit run minimal_dashboard.py
```

Streamlit will start a local development server and open the app in your browser.

## How the web app script works

The minimal dashboard code is organized as a short end-to-end pipeline: it configures the Streamlit page, requests data from the 4TU.ResearchData API, converts the JSON response into a pandas table, applies a couple of filters, and then presents the results in the browser. 

### 1. Import the main libraries

The script starts by importing three libraries:

* `requests` to communicate with the API
* `pandas` to organize the returned JSON into a table
* `streamlit` to build the dashboard interface

This reflects the three core parts of the workflow:
**data access** (`requests`), **data transformation** (`pandas`), and **data presentation** (`streamlit`). 

### 2. Configure the Streamlit page

Next, the script defines some basic interface elements:

* the browser tab title with `st.set_page_config(...)`
* the main page title with `st.title(...)`
* a short introductory text with `st.write(...)`

This is the first visible part of the dashboard and helps users immediately understand what the application does. 

### 3. Define the API endpoints

The script then stores the base URL of 4TU.ResearchData and builds two endpoint URLs:

* `/v2/articles` to retrieve dataset records
* `/v3/groups` to retrieve institutional group information

Using separate variables for these endpoints makes the code easier to read and easier to modify later. 

### 4. Create a helper function for API requests

The function `get_json()` wraps the `requests.get()` call. It sends a request to a given URL, optionally includes query parameters, waits up to 30 seconds, checks whether the request succeeded, and returns the JSON response.

This is a good teaching pattern because it avoids repeating the same request logic throughout the script. Instead of writing `requests.get(...)` multiple times, the dashboard can reuse one small function. 

### 5. Load group information first

Before loading datasets, the script requests the institutional groups from the groups endpoint. It stores them in a dictionary called `group_map`, where the key is the group ID and the value is the group name.

This matters because dataset records contain a `group_id`, which is not very meaningful to a human reader on its own. By creating this lookup table first, the dashboard can later translate group IDs into readable institution names. If this request fails, the script does not stop completely; instead, it shows a warning in the app. 

### 6. Load a batch of datasets

The script then requests dataset metadata from the articles endpoint, using two parameters:

* `limit=500`
* `offset=0`

This means the app loads the first 500 dataset records. For a workshop, this is a practical choice: it keeps the example fast and simple while still providing enough data to explore. If the dataset request fails, the script shows an error and stops execution with `st.stop()`. 

### 7. Transform the JSON into a simpler table

Once the dataset JSON is loaded, the script loops through the returned records and extracts only a small set of fields:

* `id`
* `title`
* `published_date`
* `institution`

For the institution field, it uses the earlier `group_map` dictionary to convert `group_id` into a readable group name. If no match is found, it labels it as an unknown group.

Each simplified record is added to a list called `rows`, and at the end that list is converted into a pandas DataFrame. This is the main transformation step: a nested JSON response becomes a flat table that is much easier to filter and display. 

### 8. Clean the date column

After creating the DataFrame, the script converts the `published_date` column into pandas datetime format using `pd.to_datetime(...)`.

This is an important preparation step because date filters work much better when dates are stored as actual datetime values instead of plain text strings. The option `errors="coerce"` ensures that invalid date values are converted safely rather than crashing the app. 

### 9. Build the sidebar filters

The dashboard then creates a sidebar with two filters:

* an **institution filter**
* a **date range filter**

For the institution filter, the script collects the unique institution names from the DataFrame, sorts them, and adds them to a `selectbox`, with `"All"` as the default option.

For the date filter, the script calculates the minimum and maximum publication dates present in the data and uses them as the default values in two `date_input` widgets. If no valid dates are available, the app shows an informational message instead. 

### 10. Apply the filters to the DataFrame

The script creates a copy of the original DataFrame called `filtered_df` and then applies the selected filters step by step.

* If the user selects a specific institution, the table is restricted to rows from that institution.
* If the user selects a start and end date, the table is further restricted to rows whose publication date falls within that range.

This is a clear and useful pattern for teaching dashboard logic: start with the full table, then progressively narrow it down according to user choices. 

### 11. Display summary metrics and the filtered table

Finally, the dashboard presents the filtered results in three ways:

* a metric showing the total number of loaded datasets
* a metric showing how many datasets remain after filtering
* a table displaying the filtered records

The metrics are placed side by side using `st.columns(2)`, which gives the app a slightly more dashboard-like layout. Then `st.dataframe(...)` shows the filtered dataset table in an interactive format. 

### 12. Offer a CSV download

As a final convenience, the script converts the filtered DataFrame to CSV and adds a `Download filtered data as CSV` button.

This is a small but very useful feature: it allows users not only to explore the data in the browser, but also to export the current filtered results for reuse in another tool. 


## Two incremental improvements

### Exercise 1: add a text search filter

Now, make a modification to the code such as **it allows users to search datasets by title. Add a search box  so, users can filter datasets containing a word in the title**


#### What to add
Add the following code bellow the section 10 *"Applying the filters"* of the main web app code:

```python
# ============================================================
# 10. Apply the filters
# ============================================================
filtered_df = df.copy()

```
Add this below, 

```python
    # ---- Text search title filter ----
search_term = st.sidebar.text_input("Search in title") #Streamlit widgets return Python variables.

if search_term:
    filtered_df = filtered_df[
        filtered_df["title"].str.contains(search_term, case=False, na=False)
    ]
```

### Exercise 2:  add a small visualization

Now, make another modification such there is chart showing the number of datasets per institution. 



#### What to add

Insert this block  in the last module of the main web app code:

```python
# Plotting 

st.subheader("Datasets per institution")

institution_counts = filtered_df["institution"].value_counts()

st.bar_chart(institution_counts)
```



## How to serve it online with Streamlit Community Cloud

The easiest way to publish this dashboard for other people is Streamlit Community Cloud.

### 1. Put the project in a GitHub repository
Your repository should contain at least:

- `minimal_dashboard.py`
- `requirements.txt`

A minimal `requirements.txt` could be:

```txt
streamlit
pandas
requests
```

If you use extra libraries, add them there as well.

### 2. Push the repository to GitHub
Make sure the app script is committed and pushed.

### 3. Sign in to Streamlit Community Cloud
Go to Streamlit Community Cloud and connect your GitHub account.

### 4. Create a new app
Choose:

- the GitHub repository,
- the branch,
- and the main file, for example `minimal_dashboard.py`.

### 5. Deploy
Click **Deploy**. Streamlit will install dependencies and launch the app.

### 6. Share the URL
Once deployment succeeds, you will get a public app URL ending in `streamlit.app`.



## Notes for API keys or secrets

If your 4TU.ResearchData API workflow requires a token or other secret, do not hard-code it in the Python file.

For local development, use Streamlit secrets or environment variables.
For deployment, add the secret in the Streamlit Community Cloud app settings.

In Streamlit, you would typically read a secret like this:

```python
api_token = st.secrets["API_TOKEN"]
```

And then pass it in the request headers.

Example:

```python
headers = {"Authorization": f"Bearer {api_token}"}
response = requests.get(API_URL, headers=headers, timeout=TIMEOUT)
```


