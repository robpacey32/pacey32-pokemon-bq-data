import streamlit as st
from db_bigquery import get_series_list, get_set_list, get_card_master, get_fx_rate
from db_mongo import get_user_owned_card_ids, upsert_user_card
from styles import apply_umbreon_theme
from ui_auth import render_login_portal

st.set_page_config(page_title="Collection Entry", layout="wide")
apply_umbreon_theme()

if "user" not in st.session_state or st.session_state.user is None:
    render_login_portal(show_title=True)
    st.stop()

if "display_currency" not in st.session_state:
    st.session_state.display_currency = "GBP"

user_id = st.session_state.user["user_id"]

st.title("Collection Entry")
st.write(f"Logged in as **{st.session_state.user['username']}**")

with st.sidebar:
    st.subheader("Filters")

    currency_options = ["GBP", "EUR", "USD"]
    selected_currency = st.selectbox(
        "Display currency",
        currency_options,
        index=currency_options.index(st.session_state.get("display_currency", "GBP"))
    )
    st.session_state.display_currency = selected_currency

    series_options = ["All"] + get_series_list()
    selected_series = st.selectbox("Series", series_options)

    set_options = ["All"] + get_set_list(selected_series)
    selected_set = st.selectbox("Set", set_options)

    card_name_search = st.text_input("Card name contains")
    row_limit = st.selectbox("Rows to show", [50, 100, 250, 500], index=1)

df = get_card_master(
    series_name=selected_series,
    set_name=selected_set,
    card_name_search=card_name_search,
    limit=row_limit,
)

owned_ids = get_user_owned_card_ids(user_id)
display_currency = st.session_state.get("display_currency", "GBP")
eur_to_display = get_fx_rate("EUR", display_currency)

currency_symbols = {
    "GBP": "£",
    "EUR": "€",
    "USD": "$"
}
symbol = currency_symbols.get(display_currency, display_currency)

st.markdown(f"### Showing {len(df)} cards")


def build_card_image_url(image_url):
    if not image_url:
        return None
    image_url = str(image_url).strip().rstrip("/")
    if image_url.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return image_url
    return f"{image_url}/low.webp"


for _, row in df.iterrows():
    card_id = row["card_id"]
    current_owned = card_id in owned_ids

    trend_value_display = None
    if row["cardmarket_trend"] is not None:
        try:
            trend_value_display = float(row["cardmarket_trend"]) * eur_to_display
        except Exception:
            trend_value_display = None

    value_text = f"CardMarket Price: {symbol}{trend_value_display:,.2f}" if trend_value_display is not None else "CardMarket Price: N/A"

    st.markdown('<div class="card-shell">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([0.7, 1.1, 5])

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

    st.markdown("</div>", unsafe_allow_html=True)