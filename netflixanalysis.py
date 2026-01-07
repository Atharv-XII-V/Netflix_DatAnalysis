# ============================================================
# Netflix Deep Analysis Dashboard
# Step 11 - Full Analytics App
# ============================================================

import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="Netflix Deep Analysis",
    layout="wide"
)

st.title("📺 Netflix Deep Analysis Dashboard")
st.markdown("""
End-to-end analysis using **Linux + SQLite + SQL + Streamlit + Plotly**  
Dataset: Netflix Movies & TV Shows
""")

# ------------------------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------------------------
DB_PATH = "netflix.db"

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH)

# ------------------------------------------------------------
# DATA LOADING (CACHED)
# ------------------------------------------------------------
@st.cache_data
def load_movies():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM movies", conn)
    return df

@st.cache_data
def load_tvshows():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM tvshows", conn)
    return df

@st.cache_data
def load_movie_genres():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT genre, COUNT(*) AS total
        FROM movie_genres
        GROUP BY genre
        ORDER BY total DESC
    """, conn)
    return df

@st.cache_data
def load_tv_genres():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT genre, COUNT(*) AS total
        FROM tvshow_genres
        GROUP BY genre
        ORDER BY total DESC
    """, conn)
    return df

@st.cache_data
def load_movie_countries():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT country, COUNT(*) AS total
        FROM movie_countries
        GROUP BY country
        ORDER BY total DESC
    """, conn)
    return df

@st.cache_data
def load_tv_countries():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT country, COUNT(*) AS total
        FROM tvshows_countries
        GROUP BY country
        ORDER BY total DESC
    """, conn)
    return df

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
movies = load_movies()
tvshows = load_tvshows()
movie_genres = load_movie_genres()
tv_genres = load_tv_genres()
movie_countries = load_movie_countries()
tv_countries = load_tv_countries()

# ------------------------------------------------------------
# DATA CLEANING
# ------------------------------------------------------------
movies = movies[movies["release_year"].astype(str).str.isnumeric()]
tvshows = tvshows[tvshows["release_year"].astype(str).str.isnumeric()]

movies["release_year"] = movies["release_year"].astype(int)
tvshows["release_year"] = tvshows["release_year"].astype(int)

# ------------------------------------------------------------
# YEAR BOUNDS
# ------------------------------------------------------------
min_year = min(movies["release_year"].min(), tvshows["release_year"].min())
max_year = max(movies["release_year"].max(), tvshows["release_year"].max())


# ============================================================
# FILTER MASTER VALUES
# ============================================================
all_movie_genres = sorted(movie_genres["genre"].dropna().unique())
all_tv_genres = sorted(tv_genres["genre"].dropna().unique())

all_movie_countries = sorted(movie_countries["country"].dropna().unique())
all_tv_countries = sorted(tv_countries["country"].dropna().unique())

all_movie_ratings = sorted(movies["rating"].dropna().unique())
all_tv_ratings = sorted(tvshows["rating"].dropna().unique())

# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------
st.sidebar.header("🔎 Advanced Filters")

year_range = st.sidebar.slider(
    "Release Year Range",
    min_year,
    max_year,
    (2010, max_year)
)

content_type = st.sidebar.radio(
    "Content Type",
    ["Both", "Movies", "TV Shows"],
    index=0
)

genre_filter = st.sidebar.multiselect(
    "Genre",
    options=sorted(set(all_movie_genres + all_tv_genres)),
    default=[]
)

country_filter = st.sidebar.multiselect(
    "Country",
    options=sorted(set(all_movie_countries + all_tv_countries)),
    default=[]
)

rating_filter = st.sidebar.multiselect(
    "Rating",
    options=sorted(set(all_movie_ratings + all_tv_ratings)),
    default=[]
)

# ------------------------------------------------------------
# APPLY FILTERS
# ------------------------------------------------------------
movies_f = movies[movies["release_year"].between(*year_range)]
tvshows_f = tvshows[tvshows["release_year"].between(*year_range)]

# Rating filter
if rating_filter:
    movies_f = movies_f[movies_f["rating"].isin(rating_filter)]
    tvshows_f = tvshows_f[tvshows_f["rating"].isin(rating_filter)]

# Content type filter
if content_type == "Movies":
    tvshows_f = tvshows_f.iloc[0:0]
elif content_type == "TV Shows":
    movies_f = movies_f.iloc[0:0]
movies_f = movies_f.reset_index(drop=True)
tvshows_f = tvshows_f.reset_index(drop=True)

# ------------------------------------------------------------
# GENRE FILTER (via normalized tables)
# ------------------------------------------------------------
if genre_filter:
    conn = sqlite3.connect(DB_PATH)

    movie_ids = pd.read_sql(
        f"""
        SELECT DISTINCT rowid
        FROM movie_genres
        WHERE genre IN ({','.join('?' for _ in genre_filter)})
        """,
        conn,
        params=genre_filter
    )["rowid"].tolist()

    tv_ids = pd.read_sql(
        f"""
        SELECT DISTINCT rowid
        FROM tvshow_genres
        WHERE genre IN ({','.join('?' for _ in genre_filter)})
        """,
        conn,
        params=genre_filter
    )["rowid"].tolist()

    conn.close()

    movies_f = (
        movies_f[movies_f.index.isin(movie_ids)]
        if movie_ids else movies_f.iloc[0:0]
    )

    tvshows_f = (
        tvshows_f[tvshows_f.index.isin(tv_ids)]
        if tv_ids else tvshows_f.iloc[0:0]
    )



# ------------------------------------------------------------
# KPI METRICS
# ------------------------------------------------------------
st.subheader("📌 Key Metrics")

k1, k2, k3 = st.columns(3)
k1.metric("🎬 Movies", len(movies_f))
k2.metric("📺 TV Shows", len(tvshows_f))
k3.metric("🍿 Total Content", len(movies_f) + len(tvshows_f))

# ------------------------------------------------------------
# CONTENT MIX PIE CHART
# ------------------------------------------------------------
st.subheader("🍿 Content Mix")

pie_df = pd.DataFrame({
    "Type": ["Movies", "TV Shows"],
    "Count": [len(movies_f), len(tvshows_f)]
})

fig_pie = px.pie(
    pie_df,
    names="Type",
    values="Count",
    color_discrete_sequence=["#E50914", "#221F1F"],
    hole=0.4
)

st.plotly_chart(fig_pie, use_container_width=True)

# ------------------------------------------------------------
# YEAR-WISE TRENDS
# ------------------------------------------------------------
st.subheader("📈 Content Growth Over Time")

movies_year = movies_f.groupby("release_year").size().reset_index(name="Movies")
tv_year = tvshows_f.groupby("release_year").size().reset_index(name="TV Shows")

trend_df = pd.merge(
    movies_year,
    tv_year,
    on="release_year",
    how="outer"
).fillna(0)

fig_trend = px.line(
    trend_df,
    x="release_year",
    y=["Movies", "TV Shows"],
    markers=True,
    color_discrete_sequence=["#E50914", "#221F1F"],
)

st.plotly_chart(fig_trend, use_container_width=True)

# ------------------------------------------------------------
# RATING ANALYSIS
# ------------------------------------------------------------
st.subheader("🎯 Rating Distribution")

r1, r2 = st.columns(2)

with r1:
    fig_movie_rating = px.bar(
        movies_f.groupby("rating").size().reset_index(name="total"),
        x="rating",
        y="total",
        title="Movie Ratings",
        color_discrete_sequence=["#E50914"]
    )
    st.plotly_chart(fig_movie_rating, use_container_width=True)

with r2:
    fig_tv_rating = px.bar(
        tvshows_f.groupby("rating").size().reset_index(name="total"),
        x="rating",
        y="total",
        title="TV Show Ratings",
        color_discrete_sequence=["#221F1F"]
    )
    st.plotly_chart(fig_tv_rating, use_container_width=True)

# ------------------------------------------------------------
# DURATION & SEASONS ANALYSIS
# ------------------------------------------------------------
st.subheader("⏱ Duration & Seasons Analysis")

d1, d2 = st.columns(2)

with d1:
    fig_duration = px.histogram(
        movies_f,
        x="duration_minutes",
        nbins=20,
        title="Movie Duration Distribution (Minutes)",
        color_discrete_sequence=["#E50914"]
    )
    st.plotly_chart(fig_duration, use_container_width=True)

with d2:
    fig_seasons = px.bar(
        tvshows_f.groupby("seasons").size().reset_index(name="total"),
        x="seasons",
        y="total",
        title="TV Shows by Seasons",
        color_discrete_sequence=["#221F1F"]
    )
    st.plotly_chart(fig_seasons, use_container_width=True)

# ------------------------------------------------------------
# GENRE ANALYSIS
# ------------------------------------------------------------
st.subheader("🎭 Genre Popularity")

g1, g2 = st.columns(2)

with g1:
    fig_movie_genre = px.bar(
        movie_genres.head(10),
        x="total",
        y="genre",
        orientation="h",
        title="Top Movie Genres",
        color_discrete_sequence=["#B20710"]
    )
    fig_movie_genre.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_movie_genre, use_container_width=True)

with g2:
    fig_tv_genre = px.bar(
        tv_genres.head(10),
        x="total",
        y="genre",
        orientation="h",
        title="Top TV Genres",
        color_discrete_sequence=["#141414"]
    )
    fig_tv_genre.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_tv_genre, use_container_width=True)

# ------------------------------------------------------------
# COUNTRY ANALYSIS
# ------------------------------------------------------------
st.subheader("🌍 Country-wise Content")

c1, c2 = st.columns(2)

with c1:
    fig_movie_country = px.bar(
        movie_countries.head(10),
        x="total",
        y="country",
        orientation="h",
        title="Top Movie Producing Countries",
        color_discrete_sequence=["#E50914"]
    )
    fig_movie_country.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_movie_country, use_container_width=True)

with c2:
    fig_tv_country = px.bar(
        tv_countries.head(10),
        x="total",
        y="country",
        orientation="h",
        title="Top TV Producing Countries",
        color_discrete_sequence=["#221F1F"]
    )
    fig_tv_country.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_tv_country, use_container_width=True)

# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------
st.markdown("---")
st.markdown("""
### 📌 Project Summary
- Cleaned using Linux (awk, sed, csvkit)
- Stored in SQLite
- Analyzed using SQL
- Visualized with Streamlit + Plotly

**Author:** Atharv Saswade
""")





