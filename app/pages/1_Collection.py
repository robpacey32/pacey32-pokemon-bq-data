import streamlit as st
from db_bigquery import get_series_list, get_set_list, get_card_master
from db_mongo import get_user_owned_card_ids, upsert_user_card

st.set_page_config(page_title="Collection", layout="wide")

if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in first from the main page.")
    st.stop()

user_id = st.session_state.user["user_id"]

st.title("Collection")
st.write(f"Logged in as **{st.session_state.user['username']}**")

with st.sidebar:
    st.subheader("Filters")

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
df["owned"] = df["card_id"].isin(owned_ids)

st.write(f"Showing **{len(df)}** cards")

for _, row in df.iterrows():
    col1, col2 = st.columns([1, 5])

    with col1:
        owned_value = st.checkbox(
            "Owned",
            value=bool(row["owned"]),
            key=f"owned_{row['card_id']}",
            label_visibility="collapsed"
        )

        if owned_value != bool(row["owned"]):
            upsert_user_card(user_id, row["card_id"], owned_value)
            st.rerun()

    with col2:
        st.write(
            f"**{row['name']}**  \n"
            f"{row['series_name']} | {row['set_name']} | #{row['local_id']}  \n"
            f"Rarity: {row['rarity']} | CardMarket Trend: {row['cardmarket_trend']}"
        )

    st.divider()