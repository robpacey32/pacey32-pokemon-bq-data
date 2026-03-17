import streamlit as st
from db_bigquery import get_series_list, get_set_list, get_card_master
from db_mongo import get_user_owned_card_ids, upsert_user_card

st.set_page_config(page_title="Collection", layout="wide")

# -------------------------
# AUTH CHECK
# -------------------------
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in first from the main page.")
    st.stop()

user_id = st.session_state.user["user_id"]

# -------------------------
# HEADER
# -------------------------
st.title("Collection")
st.write(f"Logged in as **{st.session_state.user['username']}**")

# -------------------------
# FILTERS
# -------------------------
with st.sidebar:
    st.subheader("Filters")

    series_options = ["All"] + get_series_list()
    selected_series = st.selectbox("Series", series_options)

    set_options = ["All"] + get_set_list(selected_series)
    selected_set = st.selectbox("Set", set_options)

    card_name_search = st.text_input("Card name contains")
    row_limit = st.selectbox("Rows to show", [50, 100, 250, 500], index=1)

# -------------------------
# LOAD DATA
# -------------------------
df = get_card_master(
    series_name=selected_series,
    set_name=selected_set,
    card_name_search=card_name_search,
    limit=row_limit,
)

owned_ids = get_user_owned_card_ids(user_id)

st.write(f"Showing **{len(df)}** cards")

# -------------------------
# DISPLAY CARDS
# -------------------------
for _, row in df.iterrows():

    card_id = row["card_id"]
    current_owned = card_id in owned_ids

    col1, col2 = st.columns([1, 5])

    # ---- Checkbox ----
    with col1:
        new_owned = st.checkbox(
            "Owned",
            value=current_owned,
            key=f"owned_{card_id}",
            label_visibility="collapsed"
        )

        # If changed → update Mongo and refresh
        if new_owned != current_owned:
            upsert_user_card(user_id, card_id, new_owned)
            st.rerun()

    # ---- Card details ----
    with col2:
        st.write(
            f"**{row['name']}**  \n"
            f"{row['series_name']} | {row['set_name']} | #{row['local_id']}  \n"
            f"Rarity: {row['rarity']} | CardMarket Trend: {row['cardmarket_trend']}"
        )

    st.divider()