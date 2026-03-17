import streamlit as st
import pandas as pd
from db_bigquery import get_card_master
from db_mongo import get_user_cards_df

st.set_page_config(page_title="Stats", layout="wide")

if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in first.")
    st.stop()

user_id = st.session_state.user["user_id"]

st.title("Collection Stats")

# Load data
cards_df = get_card_master(limit=5000)
user_df = get_user_cards_df(user_id)

if user_df.empty:
    st.warning("No cards owned yet.")
    st.stop()

# Merge
df = cards_df.merge(
    user_df,
    on="card_id",
    how="left"
)

df["owned"] = df["owned"].fillna(False)

# Choose price (CardMarket first)
df["value"] = df["cardmarket_trend"]

# Owned vs missing
owned_df = df[df["owned"] == True]
missing_df = df[df["owned"] == False]

# ---- Metrics ----

total_cards = len(df)
owned_cards = len(owned_df)
pct_complete = owned_cards / total_cards * 100

total_value = owned_df["value"].fillna(0).sum()
missing_value = missing_df["value"].fillna(0).sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Cards Owned", owned_cards)
col2.metric("Completion %", f"{pct_complete:.1f}%")
col3.metric("Collection Value", f"£{total_value:,.2f}")
col4.metric("Cost to Complete", f"£{missing_value:,.2f}")

st.divider()

# ---- Completion by set ----

set_stats = (
    df.groupby("set_name")
    .agg(
        total_cards=("card_id", "count"),
        owned_cards=("owned", "sum"),
        total_value=("value", "sum"),
    )
    .reset_index()
)

set_stats["pct_complete"] = (
    set_stats["owned_cards"] / set_stats["total_cards"] * 100
)

st.subheader("Completion by Set")
st.dataframe(set_stats.sort_values("pct_complete", ascending=False), use_container_width=True)

st.divider()

# ---- Top owned cards ----

st.subheader("Top Owned Cards")

top_owned = owned_df.sort_values("value", ascending=False).head(20)

st.dataframe(
    top_owned[[
        "name",
        "set_name",
        "cardmarket_trend"
    ]],
    use_container_width=True
)

st.divider()

# ---- Most valuable missing cards ----

st.subheader("Most Valuable Missing Cards")

top_missing = missing_df.sort_values("value", ascending=False).head(20)

st.dataframe(
    top_missing[[
        "name",
        "set_name",
        "cardmarket_trend"
    ]],
    use_container_width=True
)