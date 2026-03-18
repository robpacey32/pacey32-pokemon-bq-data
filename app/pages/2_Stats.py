import streamlit as st
import pandas as pd
from db_bigquery import get_card_master, get_fx_rate
from db_mongo import get_user_cards_df
from styles import apply_umbreon_theme
from ui_auth import render_login_portal

st.set_page_config(page_title="Stats", layout="wide")
apply_umbreon_theme()

if "user" not in st.session_state or st.session_state.user is None:
    render_login_portal(show_title=True)
    st.stop()

if "display_currency" not in st.session_state:
    st.session_state.display_currency = "GBP"

user_id = st.session_state.user["user_id"]
display_currency = st.session_state.get("display_currency", "GBP")
eur_to_display = get_fx_rate("EUR", display_currency)

st.title("Stats")

cards_df = get_card_master(limit=5000)
user_df = get_user_cards_df(user_id)

if user_df.empty:
    st.warning("No cards owned yet.")
    st.stop()

df = cards_df.merge(user_df, on="card_id", how="left")
df["owned"] = df["owned"].fillna(False)
df["value_eur"] = pd.to_numeric(df["cardmarket_trend"], errors="coerce")
df["value"] = df["value_eur"] * eur_to_display

owned_df = df[df["owned"] == True].copy()
missing_df = df[df["owned"] == False].copy()

total_cards = len(df)
owned_cards = len(owned_df)
pct_complete = (owned_cards / total_cards * 100) if total_cards > 0 else 0
total_value = owned_df["value"].fillna(0).sum()
missing_value = missing_df["value"].fillna(0).sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Cards Owned", owned_cards)
col2.metric("Completion %", f"{pct_complete:.1f}%")
col3.metric("Collection Value", f"{display_currency} {total_value:,.2f}")
col4.metric("Cost to Complete", f"{display_currency} {missing_value:,.2f}")

st.markdown("---")

set_stats = (
    df.groupby("set_name")
    .agg(
        total_cards=("card_id", "count"),
        owned_cards=("owned", "sum"),
        total_value=("value", "sum"),
    )
    .reset_index()
)
set_stats["pct_complete"] = set_stats["owned_cards"] / set_stats["total_cards"] * 100

series_stats = (
    df.groupby("series_name")
    .agg(
        total_cards=("card_id", "count"),
        owned_cards=("owned", "sum"),
        total_value=("value", "sum"),
    )
    .reset_index()
)
series_stats["pct_complete"] = series_stats["owned_cards"] / series_stats["total_cards"] * 100

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### Completion by Set")
    st.dataframe(
        set_stats.sort_values("pct_complete", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

with col_b:
    st.markdown("### Completion by Series")
    st.dataframe(
        series_stats.sort_values("pct_complete", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")

col_c, col_d = st.columns(2)

with col_c:
    st.markdown("### Top Owned Cards")
    top_owned = owned_df.sort_values("value", ascending=False).head(20).copy()
    top_owned["display_value"] = top_owned["value"].fillna(0)
    st.dataframe(
        top_owned[["name", "set_name", "series_name", "display_value"]].rename(
            columns={"display_value": f"value_{display_currency.lower()}"}
        ),
        use_container_width=True,
        hide_index=True,
    )

with col_d:
    st.markdown("### Most Valuable Missing Cards")
    top_missing = missing_df.sort_values("value", ascending=False).head(20).copy()
    top_missing["display_value"] = top_missing["value"].fillna(0)
    st.dataframe(
        top_missing[["name", "set_name", "series_name", "display_value"]].rename(
            columns={"display_value": f"value_{display_currency.lower()}"}
        ),
        use_container_width=True,
        hide_index=True,
    )