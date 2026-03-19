import streamlit as st
import pandas as pd
import plotly.express as px
from ui_auth import render_login_portal, restore_login_from_cookie

from db_bigquery import (
    get_series_list,
    get_set_list,
    get_card_master,
    get_fx_rate,
    get_card_detail_by_id,
    get_card_price_history,
    get_card_latest_variant_prices,
)
from db_mongo import get_user_owned_card_ids, upsert_user_card
from styles import apply_umbreon_theme

st.set_page_config(page_title="Collection Entry", layout="wide")
apply_umbreon_theme()
restore_login_from_cookie()

if "user" not in st.session_state or st.session_state.user is None:
    render_login_portal(show_title=True)
    st.stop()

if "display_currency" not in st.session_state:
    st.session_state.display_currency = "GBP"

if "selected_card_id" not in st.session_state:
    st.session_state.selected_card_id = None

user_id = st.session_state.user["user_id"]

st.title("Collection Entry")
st.write(f"Logged in as **{st.session_state.user['username']}**")


def build_card_image_url(image_url):
    if not image_url:
        return None
    image_url = str(image_url).strip().rstrip("/")
    if image_url.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return image_url
    return f"{image_url}/low.webp"


def format_money(value, symbol):
    if pd.isna(value):
        return "N/A"
    return f"{symbol}{float(value):,.2f}"


def render_card_detail_panel(card_id, display_currency, symbol):
    detail_df = get_card_detail_by_id(card_id)
    history_df = get_card_price_history(card_id)
    latest_variant_df = get_card_latest_variant_prices(card_id)

    if detail_df.empty:
        st.warning("No detail found for this card.")
        return

    row = detail_df.iloc[0]

    st.markdown("## Card Detail")
    st.markdown('<div class="section-shell">', unsafe_allow_html=True)

    col1, col2 = st.columns([1.2, 3])

    with col1:
        image_url = build_card_image_url(row.get("image_url"))
        if image_url:
            st.image(image_url, width=220)

    with col2:
        st.markdown(f"### {row['name']}")
        st.write(f"**Card ID:** {row['card_id']}")
        st.write(f"**Set:** {row.get('set_name')}")
        st.write(f"**Series:** {row.get('series_name')}")
        st.write(f"**Release date:** {row.get('release_date')}")
        st.write(f"**Rarity:** {row.get('rarity')}")
        st.write(f"**Category:** {row.get('category')}")
        st.write(f"**HP:** {row.get('hp')}")
        st.write(f"**Illustrator:** {row.get('illustrator')}")
        st.write(f"**Stage:** {row.get('stage')}")
        st.write(f"**Level:** {row.get('level')}")
        st.write(f"**Trainer type:** {row.get('trainer_type')}")
        st.write(f"**Regulation mark:** {row.get('regulation_mark')}")
        if pd.notnull(row.get("description")):
            st.write(f"**Description:** {row.get('description')}")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Latest Variant Prices")
    if latest_variant_df.empty:
        st.info("No variant pricing found.")
    else:
        v = latest_variant_df.iloc[0]

        variant_rows = [
            ["CardMarket Avg", format_money(v.get("cardmarket_avg_display"), symbol)],
            ["CardMarket Low", format_money(v.get("cardmarket_low_display"), symbol)],
            ["CardMarket Trend", format_money(v.get("cardmarket_trend_display"), symbol)],
            ["CardMarket Holo Avg", format_money(v.get("cardmarket_avg_holo_display"), symbol)],
            ["CardMarket Holo Low", format_money(v.get("cardmarket_low_holo_display"), symbol)],
            ["CardMarket Holo Trend", format_money(v.get("cardmarket_trend_holo_display"), symbol)],
            ["TCGPlayer Normal", format_money(v.get("tcgplayer_normal_market_price_display"), symbol)],
            ["TCGPlayer Holofoil", format_money(v.get("tcgplayer_holofoil_market_price_display"), symbol)],
            ["TCGPlayer Reverse Holofoil", format_money(v.get("tcgplayer_reverse_holofoil_market_price_display"), symbol)],
        ]

        variant_df = pd.DataFrame(variant_rows, columns=["Variant", "Value"])
        st.dataframe(variant_df, use_container_width=True, hide_index=True)

    st.markdown("### Historic Pricing")
    if history_df.empty:
        st.info("No historic pricing available yet.")
    else:
        chart_cols = [
            "cardmarket_avg_display",
            "cardmarket_low_display",
            "cardmarket_trend_display",
            "cardmarket_avg_holo_display",
            "cardmarket_low_holo_display",
            "cardmarket_trend_holo_display",
            "tcgplayer_normal_market_price_display",
            "tcgplayer_holofoil_market_price_display",
            "tcgplayer_reverse_holofoil_market_price_display",
        ]

        chart_long = history_df.melt(
            id_vars=["snapshot_timestamp"],
            value_vars=[c for c in chart_cols if c in history_df.columns],
            var_name="price_type",
            value_name="price_value",
        ).dropna(subset=["price_value"])

        if chart_long.empty:
            st.info("No chartable price history available.")
        else:
            label_map = {
                "cardmarket_avg_display": "CardMarket Avg",
                "cardmarket_low_display": "CardMarket Low",
                "cardmarket_trend_display": "CardMarket Trend",
                "cardmarket_avg_holo_display": "CardMarket Holo Avg",
                "cardmarket_low_holo_display": "CardMarket Holo Low",
                "cardmarket_trend_holo_display": "CardMarket Holo Trend",
                "tcgplayer_normal_market_price_display": "TCGPlayer Normal",
                "tcgplayer_holofoil_market_price_display": "TCGPlayer Holofoil",
                "tcgplayer_reverse_holofoil_market_price_display": "TCGPlayer Reverse Holofoil",
            }
            chart_long["price_type"] = chart_long["price_type"].map(label_map)

            fig = px.line(
                chart_long,
                x="snapshot_timestamp",
                y="price_value",
                color="price_type",
                title=f"Historic Prices ({display_currency})",
            )
            fig.update_layout(
                xaxis_title="Snapshot Date",
                yaxis_title=f"Price ({display_currency})",
                margin=dict(l=20, r=20, t=50, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

with st.sidebar:
    st.subheader("Filters")

    series_options = ["All"] + get_series_list()
    selected_series = st.selectbox("Series", series_options)

    set_options = ["All"] + get_set_list(selected_series)
    selected_set = st.selectbox("Set", set_options)

    card_name_search = st.text_input("Card name contains")
    row_limit = st.selectbox("Rows to show", [50, 100, 250, 500], index=1)

display_currency = st.session_state.display_currency

currency_symbols = {
    "GBP": "£",
    "EUR": "€",
    "USD": "$"
}
symbol = currency_symbols.get(display_currency, display_currency)

if st.session_state.selected_card_id:
    render_card_detail_panel(
        st.session_state.selected_card_id,
        display_currency,
        symbol,
    )

    if st.button("Close card detail"):
        st.session_state.selected_card_id = None
        st.rerun()

    st.markdown("---")

df = get_card_master(
    series_name=selected_series,
    set_name=selected_set,
    card_name_search=card_name_search,
    limit=row_limit,
    display_currency=display_currency,
)

owned_ids = get_user_owned_card_ids(user_id)

st.markdown(f"### Showing {len(df)} cards")

for _, row in df.iterrows():
    card_id = row["card_id"]
    current_owned = card_id in owned_ids

    value_text = "CardMarket Price: N/A"
    if pd.notnull(row.get("cardmarket_trend_display")):
        value_text = f"CardMarket Price: {symbol}{float(row['cardmarket_trend_display']):,.2f}"

    st.markdown('<div class="card-shell">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([0.7, 1.1, 4.6, 1.2])

    with col1:
        new_owned = st.checkbox(
            "Owned",
            value=current_owned,
            key=f"owned_{card_id}",
            label_visibility="collapsed"
        )
        if new_owned != current_owned:
            upsert_user_card(user_id, card_id, new_owned)
            st.rerun()

    with col2:
        final_image_url = build_card_image_url(row["image_url"])
        if final_image_url:
            st.image(final_image_url, width=92)
        else:
            st.write("No image")

    with col3:
        series_text = row["series_name"] if row["series_name"] else "Unknown Series"
        set_text = row["set_name"] if row["set_name"] else "Unknown Set"
        st.markdown(
            f"""
            <div style="font-size: 1.05rem; line-height: 1.8;">
                <div style="font-size: 1.35rem; font-weight: 700;">{row['name']}</div>
                <div>{series_text} | {set_text} | #{row['local_id']}</div>
                <div>Rarity: {row['rarity']} | {value_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        if st.button("View details", key=f"detail_{card_id}"):
            st.session_state.selected_card_id = card_id
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)