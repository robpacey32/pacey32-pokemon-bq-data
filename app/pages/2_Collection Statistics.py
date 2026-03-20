import streamlit as st
import pandas as pd
import plotly.express as px
from db_bigquery import get_card_master, get_fx_rate
from db_mongo import get_user_cards_df
from styles import apply_umbreon_theme
from ui_auth import render_login_portal, restore_login_from_cookie

st.set_page_config(page_title="Collection Statistics", layout="wide")
apply_umbreon_theme()
restore_login_from_cookie()

if "user" not in st.session_state or st.session_state.user is None:
    render_login_portal(show_title=True)
    st.stop()

if "display_currency" not in st.session_state:
    st.session_state.display_currency = "GBP"

user_id = st.session_state.user["user_id"]

st.title("Collection Statistics")

#with st.sidebar:
#    st.subheader("Display")

display_currency = st.session_state.display_currency
eur_to_display = get_fx_rate("EUR", display_currency)

currency_symbols = {
    "GBP": "£",
    "EUR": "€",
    "USD": "$"
}
symbol = currency_symbols.get(display_currency, display_currency)


@st.cache_data(ttl=300, show_spinner=False)
def build_stats_base(cards_df: pd.DataFrame, user_df: pd.DataFrame, eur_to_display: float) -> pd.DataFrame:
    df = cards_df.merge(user_df, on="card_id", how="left")
    df["owned"] = df["owned"].fillna(False)

    for col in [
        "owned_normal",
        "owned_holo",
        "owned_reverse",
        "owned_first_edition",
        "owned_w_promo",
    ]:
        if col not in df.columns:
            df[col] = False
        df[col] = df[col].fillna(False)

    df["owned"] = (
        df["owned_normal"] |
        df["owned_holo"] |
        df["owned_reverse"] |
        df["owned_first_edition"] |
        df["owned_w_promo"]
    )

    def calc_total_possible_value(row):
        vals = []

        if row.get("variant_normal") and pd.notnull(row.get("tcgplayer_normal_market_price_display")):
            vals.append(float(row["tcgplayer_normal_market_price_display"]))

        if row.get("variant_holo") and pd.notnull(row.get("tcgplayer_holofoil_market_price_display")):
            vals.append(float(row["tcgplayer_holofoil_market_price_display"]))

        if row.get("variant_reverse") and pd.notnull(row.get("tcgplayer_reverse_holofoil_market_price_display")):
            vals.append(float(row["tcgplayer_reverse_holofoil_market_price_display"]))

        return sum(vals)

    def calc_owned_value(row):
        total = 0.0

        if row.get("owned_normal") and pd.notnull(row.get("tcgplayer_normal_market_price_display")):
            total += float(row["tcgplayer_normal_market_price_display"])

        if row.get("owned_holo") and pd.notnull(row.get("tcgplayer_holofoil_market_price_display")):
            total += float(row["tcgplayer_holofoil_market_price_display"])

        if row.get("owned_reverse") and pd.notnull(row.get("tcgplayer_reverse_holofoil_market_price_display")):
            total += float(row["tcgplayer_reverse_holofoil_market_price_display"])

        if row.get("owned_first_edition") or row.get("owned_w_promo"):
            promo_vals = []
            for col in [
                "tcgplayer_normal_market_price_display",
                "tcgplayer_holofoil_market_price_display",
                "tcgplayer_reverse_holofoil_market_price_display",
            ]:
                val = row.get(col)
                if pd.notnull(val):
                    promo_vals.append(float(val))
            if promo_vals:
                total += max(promo_vals)

        return total

    df["value"] = df.apply(calc_total_possible_value, axis=1)
    df["owned_value"] = df.apply(calc_owned_value, axis=1)

    return df


@st.cache_data(ttl=300, show_spinner=False)
def build_series_stats(df: pd.DataFrame) -> pd.DataFrame:
    series_stats = (
        df.groupby("series_name", dropna=False)
        .agg(
            total_cards=("card_id", "count"),
            owned_cards=("owned", "sum"),
            total_value=("value", "sum"),
            owned_value=("owned_value", "sum"),
        )
        .reset_index()
    )

    series_stats["series_name"] = series_stats["series_name"].fillna("Unknown Series")
    series_stats["pct_cards_completion"] = (
        series_stats["owned_cards"] / series_stats["total_cards"] * 100
    ).fillna(0)

    series_stats["pct_value_completion"] = (
        series_stats["owned_value"] / series_stats["total_value"].replace(0, pd.NA) * 100
    ).fillna(0)

    return series_stats


@st.cache_data(ttl=300, show_spinner=False)
def build_set_stats(df: pd.DataFrame, selected_series: str) -> pd.DataFrame:
    drill_df = df[df["series_name"].fillna("Unknown Series") == selected_series].copy()

    set_stats = (
        drill_df.groupby("set_name", dropna=False)
        .agg(
            total_cards=("card_id", "count"),
            owned_cards=("owned", "sum"),
            total_value=("value", "sum"),
            owned_value=("owned_value", "sum"),
            release_date=("release_date", "min"),
        )
        .reset_index()
    )

    set_stats["set_name"] = set_stats["set_name"].fillna("Unknown Set")
    set_stats["pct_cards_completion"] = (
        set_stats["owned_cards"] / set_stats["total_cards"] * 100
    ).fillna(0)

    set_stats["pct_value_completion"] = (
        set_stats["owned_value"] / set_stats["total_value"].replace(0, pd.NA) * 100
    ).fillna(0)

    return set_stats


@st.cache_data(ttl=300, show_spinner=False)
def build_top_owned_table(owned_df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    top_owned = owned_df.sort_values("value", ascending=False).head(10).copy()
    top_owned["formatted_value"] = top_owned["value"].apply(
        lambda x: f"{symbol}{x:,.2f}" if pd.notnull(x) else f"{symbol}0.00"
    )

    display_df = top_owned.rename(
        columns={
            "name": "Name",
            "series_name": "Series",
            "set_name": "Set",
            "card_id": "Card ID",
        }
    )[["Name", "Series", "Set", "Card ID", "formatted_value"]]

    return display_df.rename(columns={"formatted_value": "Value"})


# -------------------------
# LOAD DATA
# -------------------------
cards_df = get_card_master(display_currency=display_currency)
user_df = get_user_cards_df(user_id)

if user_df.empty:
    user_df = pd.DataFrame(columns=["card_id", "owned"])

df = build_stats_base(cards_df, user_df, eur_to_display)

# -------------------------
# TOP METRICS
# -------------------------
total_cards = len(df)
owned_cards = int(df["owned"].sum())
pct_complete = (owned_cards / total_cards * 100) if total_cards > 0 else 0
collection_value = df.loc[df["owned"] == True, "value"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Cards Owned", f"{owned_cards:,}")
col2.metric("Completion %", f"{pct_complete:.1f}%")
col3.metric("Collection Value", f"{symbol}{collection_value:,.0f}")

st.markdown("---")

# -------------------------
# VIEW MODE
# -------------------------
view_mode = st.selectbox(
    "Chart view",
    ["% cards completion", "% value completion"],
    index=0,
    key="stats_view_mode"
)

# -------------------------
# SERIES SUMMARY
# -------------------------
series_stats = build_series_stats(df)

if view_mode == "% cards completion":
    chart_col = "pct_cards_completion"
    chart_title = "Series completion by cards"
else:
    chart_col = "pct_value_completion"
    chart_title = "Series completion by value"

series_stats = series_stats.sort_values(chart_col, ascending=True)

# Optional: cap to top 30 series for faster chart rendering
series_chart_df = series_stats.tail(30).copy()

fig_series = px.bar(
    series_chart_df,
    x=chart_col,
    y="series_name",
    orientation="h",
    text=series_chart_df[chart_col].round(1).astype(str) + "%",
    custom_data=["series_name"],
)

fig_series.update_traces(
    textposition="outside",
    hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
)
fig_series.update_layout(
    title=chart_title,
    xaxis_title="Completion %",
    yaxis_title="Series",
    height=min(900, max(450, len(series_chart_df) * 24)),
    margin=dict(l=20, r=20, t=50, b=20),
)

st.markdown("### Series overview")
series_event = st.plotly_chart(
    fig_series,
    use_container_width=True,
    key="series_completion_chart",
    on_select="rerun",
    config={"displayModeBar": False},
)

selected_series = st.session_state.get("selected_series_for_stats")

if series_event and getattr(series_event, "selection", None):
    points = series_event.selection.get("points", [])
    if points:
        selected_series = points[0].get("y")
        st.session_state["selected_series_for_stats"] = selected_series

col_a, col_b = st.columns([4, 1])
with col_a:
    if selected_series:
        st.info(f"Drilldown series: {selected_series}")
    else:
        st.caption("Click a series bar to drill into its sets.")
with col_b:
    if st.button("Clear selection"):
        st.session_state["selected_series_for_stats"] = None
        st.rerun()

# -------------------------
# SET DRILLDOWN
# -------------------------
if selected_series:
    set_stats = build_set_stats(df, selected_series)

    set_stats = set_stats.sort_values(
        by=["release_date", "set_name"],
        ascending=[True, True],
        na_position="last"
    )

    if view_mode == "% cards completion":
        drill_col = "pct_cards_completion"
        drill_title = f"Set drilldown for {selected_series} by cards"
    else:
        drill_col = "pct_value_completion"
        drill_title = f"Set drilldown for {selected_series} by value"

    set_chart_df = set_stats.sort_values(drill_col, ascending=True).copy()

    fig_sets = px.bar(
        set_chart_df,
        x=drill_col,
        y="set_name",
        orientation="h",
        text=set_chart_df[drill_col].round(1).astype(str) + "%",
    )

    fig_sets.update_traces(
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
    )
    fig_sets.update_layout(
        title=drill_title,
        xaxis_title="Completion %",
        yaxis_title="Set",
        height=min(800, max(350, len(set_chart_df) * 24)),
        margin=dict(l=20, r=20, t=50, b=20),
    )

    st.markdown("### Set drilldown")
    st.plotly_chart(
        fig_sets,
        use_container_width=True,
        config={"displayModeBar": False},
    )

st.markdown("---")

# -------------------------
# TOP 10 OWNED CARDS
# -------------------------
st.markdown("### Top 10 owned cards")

owned_df = df[df["owned"] == True].copy()

if owned_df.empty:
    st.info("You do not have any owned cards yet.")
else:
    display_df = build_top_owned_table(owned_df, symbol)
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )