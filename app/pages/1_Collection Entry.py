import streamlit as st
import pandas as pd
import plotly.express as px
from ui_auth import render_login_portal, restore_login_from_storage

from db_bigquery import (
    get_series_list,
    get_set_list,
    get_card_master,
    get_card_detail_by_id,
    get_card_price_history,
    get_card_latest_variant_prices,
    get_card_latest_variant_prices_bulk,
)
from db_mongo import get_user_card_variants, upsert_user_card_variants
from styles import apply_umbreon_theme

st.set_page_config(page_title="Collection Entry", layout="wide")
apply_umbreon_theme()
restore_login_from_storage()

if "user" not in st.session_state or st.session_state.user is None:
    render_login_portal(show_title=True)
    st.stop()

if "display_currency" not in st.session_state:
    st.session_state.display_currency = "GBP"

if "selected_card_id" not in st.session_state:
    st.session_state.selected_card_id = None

if "page_number" not in st.session_state:
    st.session_state.page_number = 1

if "last_filter_key" not in st.session_state:
    st.session_state.last_filter_key = None

if "show_card_images" not in st.session_state:
    st.session_state.show_card_images = True

user_id = st.session_state.user["user_id"]

st.title("Collection Entry")
st.write(f"Logged in as **{st.session_state.user['username']}**")

st.toggle(
    "Show pictures",
    key="show_card_images",
    help="Turn card pictures on or off to make the list more compact.",
)


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


def get_card_owned_value(row, owned_map):
    total = 0.0

    if owned_map.get("owned_normal", False):
        normal_val = row.get("display_normal_price_display")
        if pd.notnull(normal_val):
            total += float(normal_val)

    if owned_map.get("owned_holo", False):
        holo_val = row.get("display_holofoil_price_display")
        if pd.notnull(holo_val):
            total += float(holo_val)

    if owned_map.get("owned_reverse", False):
        reverse_val = row.get("display_reverse_holofoil_price_display")
        if pd.notnull(reverse_val):
            total += float(reverse_val)

    if owned_map.get("owned_first_edition", False):
        fallback_vals = []
        for col in [
            "display_normal_price_display",
            "display_holofoil_price_display",
            "display_reverse_holofoil_price_display",
        ]:
            val = row.get(col)
            if pd.notnull(val):
                fallback_vals.append(float(val))
        if fallback_vals:
            total += max(fallback_vals)

    if owned_map.get("owned_w_promo", False):
        fallback_vals = []
        for col in [
            "display_normal_price_display",
            "display_holofoil_price_display",
            "display_reverse_holofoil_price_display",
        ]:
            val = row.get(col)
            if pd.notnull(val):
                fallback_vals.append(float(val))
        if fallback_vals:
            total += max(fallback_vals)

    return total


def get_card_max_tcgplayer_price(row):
    candidates = []

    if row.get("variant_normal"):
        val = row.get("display_normal_price_display")
        if pd.notnull(val):
            candidates.append(float(val))

    if row.get("variant_holo"):
        val = row.get("display_holofoil_price_display")
        if pd.notnull(val):
            candidates.append(float(val))

    if row.get("variant_reverse"):
        val = row.get("display_reverse_holofoil_price_display")
        if pd.notnull(val):
            candidates.append(float(val))

    if not candidates:
        return None

    return max(candidates)


def render_card_detail_content(card_id, display_currency, symbol):
    detail_df = get_card_detail_by_id(card_id)
    history_df = get_card_price_history(card_id)
    latest_variant_df = get_card_latest_variant_prices(card_id)

    if detail_df.empty:
        st.warning("No detail found for this card.")
        return

    row = detail_df.iloc[0]

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

    st.markdown("### Latest Variant Prices")
    if latest_variant_df.empty:
        st.info("No variant pricing found.")
    else:
        v = latest_variant_df.iloc[0]
        variant_rows = []

        if row.get("variant_normal"):
            variant_rows.append([
                "Normal",
                format_money(v.get("display_normal_price_display"), symbol),
                v.get("display_normal_source") or "N/A",
            ])

        if row.get("variant_holo"):
            variant_rows.append([
                "Holofoil",
                format_money(v.get("display_holofoil_price_display"), symbol),
                v.get("display_holofoil_source") or "N/A",
            ])

        if row.get("variant_reverse"):
            variant_rows.append([
                "Reverse Holofoil",
                format_money(v.get("display_reverse_holofoil_price_display"), symbol),
                v.get("display_reverse_holofoil_source") or "N/A",
            ])

        if not variant_rows:
            variant_rows = [["Price", "N/A", "N/A"]]

        variant_df = pd.DataFrame(variant_rows, columns=["Variant", "Value", "Source"])
        st.dataframe(variant_df, use_container_width=True, hide_index=True)

    st.markdown("### Historic Pricing")
    if history_df.empty:
        st.info("No historic pricing available yet.")
    else:
        chart_cols = [
            "display_normal_price_display",
            "display_holofoil_price_display",
            "display_reverse_holofoil_price_display",
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
                "display_normal_price_display": "Normal",
                "display_holofoil_price_display": "Holofoil",
                "display_reverse_holofoil_price_display": "Reverse Holofoil",
            }
            chart_long["price_type"] = chart_long["price_type"].map(label_map)
            chart_long["snapshot_date"] = pd.to_datetime(
                chart_long["snapshot_timestamp"]
            ).dt.date

            fig = px.line(
                chart_long,
                x="snapshot_date",
                y="price_value",
                color="price_type",
                title=f"Historic Prices ({display_currency})",
                markers=True,
            )
            fig.update_traces(
                hovertemplate="%{y:.2f}<extra></extra>"
            )
            fig.update_layout(
                xaxis_title="Snapshot Date",
                yaxis_title=f"Price ({display_currency})",
                legend_title_text="Key",
                margin=dict(l=20, r=20, t=50, b=20),
            )
            fig.update_xaxes(type="category")
            st.plotly_chart(fig, use_container_width=True)


@st.dialog("Card Detail", width="large")
def show_card_detail_dialog(card_id, display_currency, symbol):
    render_card_detail_content(card_id, display_currency, symbol)

    if st.button("Close", key="close_card_detail_dialog"):
        st.session_state.selected_card_id = None
        st.rerun()


with st.sidebar:
    st.subheader("Filters")

    series_options = ["All"] + get_series_list()
    selected_series = st.selectbox("Series", series_options)

    set_options = ["All"] + get_set_list(selected_series)
    selected_set = st.selectbox("Set", set_options)

    card_name_search = st.text_input("Search cards")
    row_limit = st.selectbox("Rows per page", [25, 50, 100, 250, 500], index=1)

    filter_key = (
        f"{selected_series}_{selected_set}_{card_name_search}_{row_limit}_{st.session_state.show_card_images}"
    )
    if st.session_state.last_filter_key != filter_key:
        st.session_state.page_number = 1
        st.session_state.last_filter_key = filter_key

display_currency = st.session_state.display_currency

currency_symbols = {
    "GBP": "£",
    "EUR": "€",
    "USD": "$"
}
symbol = currency_symbols.get(display_currency, display_currency)

offset = (st.session_state.page_number - 1) * row_limit

df = get_card_master(
    series_name=selected_series,
    set_name=selected_set,
    card_name_search=card_name_search,
    limit=row_limit,
    offset=offset,
    display_currency=display_currency,
)

if not df.empty:
    latest_variant_all_df = get_card_latest_variant_prices_bulk(df["card_id"].tolist())

    if not latest_variant_all_df.empty:
        df = df.merge(
            latest_variant_all_df[
                [
                    "card_id",
                    "display_normal_price_display",
                    "display_normal_source",
                    "display_holofoil_price_display",
                    "display_holofoil_source",
                    "display_reverse_holofoil_price_display",
                    "display_reverse_holofoil_source",
                ]
            ],
            on="card_id",
            how="left",
        )

user_variant_map = get_user_card_variants(user_id)

start_row = offset + 1 if len(df) > 0 else 0
end_row = offset + len(df)

nav1, nav2, nav3 = st.columns([1, 2, 1])

with nav1:
    if st.button("◀ Prev", key="prev_page_main"):
        if st.session_state.page_number > 1:
            st.session_state.page_number -= 1
            st.rerun()

with nav2:
    st.markdown(
        f"<div style='text-align:center; font-size: 1.5rem; font-weight: 700;'>Showing cards {start_row}–{end_row}</div>"
        f"<div style='text-align:center;'>Page {st.session_state.page_number}</div>",
        unsafe_allow_html=True
    )

with nav3:
    if st.button("Next ▶", key="next_page_main"):
        if len(df) == row_limit:
            st.session_state.page_number += 1
            st.rerun()

show_card_images = st.session_state.show_card_images

for _, row in df.iterrows():
    card_id = row["card_id"]
    is_selected = card_id == st.session_state.selected_card_id

    current_variants = user_variant_map.get(
        card_id,
        {
            "owned_normal": False,
            "owned_holo": False,
            "owned_reverse": False,
            "owned_first_edition": False,
            "owned_w_promo": False,
        }
    )

    owned_value = get_card_owned_value(row, current_variants)
    max_tcgplayer_price = get_card_max_tcgplayer_price(row)

    if owned_value > 0:
        value_text = f"Price: {symbol}{owned_value:,.2f}"
    elif max_tcgplayer_price is not None:
        value_text = f"Price: {symbol}{max_tcgplayer_price:,.2f}"
    else:
        value_text = "Price: N/A"

    if is_selected:
        st.markdown(
            '<div class="card-shell" style="border: 2px solid #F4D995;">',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="card-shell">', unsafe_allow_html=True)

    if show_card_images:
        col1, col2, col3, col4 = st.columns([1.1, 4.2, 1.6, 1.2])

        with col1:
            final_image_url = build_card_image_url(row["image_url"])
            if final_image_url:
                st.image(final_image_url, width=110)
            else:
                st.write("No image")

        with col2:
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

        with col3:
            variant_updates = current_variants.copy()

            if row.get("variant_normal"):
                variant_updates["owned_normal"] = st.checkbox(
                    "Normal",
                    value=current_variants["owned_normal"],
                    key=f"normal_{card_id}"
                )

            if row.get("variant_holo"):
                variant_updates["owned_holo"] = st.checkbox(
                    "Holo",
                    value=current_variants["owned_holo"],
                    key=f"holo_{card_id}"
                )

            if row.get("variant_reverse"):
                variant_updates["owned_reverse"] = st.checkbox(
                    "Reverse",
                    value=current_variants["owned_reverse"],
                    key=f"reverse_{card_id}"
                )

            if row.get("variant_first_edition"):
                variant_updates["owned_first_edition"] = st.checkbox(
                    "1st Ed",
                    value=current_variants["owned_first_edition"],
                    key=f"firsted_{card_id}"
                )

            if row.get("variant_w_promo"):
                variant_updates["owned_w_promo"] = st.checkbox(
                    "Promo",
                    value=current_variants["owned_w_promo"],
                    key=f"wpromo_{card_id}"
                )

            if variant_updates != current_variants:
                upsert_user_card_variants(user_id, card_id, variant_updates)
                st.rerun()

        with col4:
            if st.button("View details", key=f"detail_{card_id}"):
                st.session_state.selected_card_id = card_id
                st.rerun()

    else:
        col2, col3, col4 = st.columns([5.4, 1.8, 1.3])

        with col2:
            series_text = row["series_name"] if row["series_name"] else "Unknown Series"
            set_text = row["set_name"] if row["set_name"] else "Unknown Set"
            st.markdown(
                f"""
                <div style="font-size: 1.00rem; line-height: 1.7;">
                    <div style="font-size: 1.25rem; font-weight: 700;">{row['name']}</div>
                    <div>{series_text} | {set_text} | #{row['local_id']}</div>
                    <div>Rarity: {row['rarity']} | {value_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            variant_updates = current_variants.copy()

            if row.get("variant_normal"):
                variant_updates["owned_normal"] = st.checkbox(
                    "Normal",
                    value=current_variants["owned_normal"],
                    key=f"normal_{card_id}"
                )

            if row.get("variant_holo"):
                variant_updates["owned_holo"] = st.checkbox(
                    "Holo",
                    value=current_variants["owned_holo"],
                    key=f"holo_{card_id}"
                )

            if row.get("variant_reverse"):
                variant_updates["owned_reverse"] = st.checkbox(
                    "Reverse",
                    value=current_variants["owned_reverse"],
                    key=f"reverse_{card_id}"
                )

            if row.get("variant_first_edition"):
                variant_updates["owned_first_edition"] = st.checkbox(
                    "1st Ed",
                    value=current_variants["owned_first_edition"],
                    key=f"firsted_{card_id}"
                )

            if row.get("variant_w_promo"):
                variant_updates["owned_w_promo"] = st.checkbox(
                    "Promo",
                    value=current_variants["owned_w_promo"],
                    key=f"wpromo_{card_id}"
                )

            if variant_updates != current_variants:
                upsert_user_card_variants(user_id, card_id, variant_updates)
                st.rerun()

        with col4:
            if st.button("View details", key=f"detail_{card_id}"):
                st.session_state.selected_card_id = card_id
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.selected_card_id:
    show_card_detail_dialog(
        st.session_state.selected_card_id,
        display_currency,
        symbol,
    )