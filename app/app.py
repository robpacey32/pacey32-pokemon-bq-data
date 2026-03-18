import streamlit as st
from auth import register_user, login_user

st.set_page_config(page_title="Pokemon Collection App", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

if "display_currency" not in st.session_state:
    st.session_state.display_currency = "GBP"

st.title("Pokemon Collection App")

if st.session_state.user is None:
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            login_submitted = st.form_submit_button("Login")

        if login_submitted:
            user = login_user(username, password)
            if user:
                st.session_state.user = {
                    "username": user["username"],
                    "email": user["email"],
                    "user_id": user["username"],
                }
                st.session_state.display_currency = st.session_state.get("display_currency", "GBP")
                st.success("Logged in")
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        with st.form("register_form"):
            username = st.text_input("New username", key="reg_username")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("New password", type="password", key="reg_password")
            register_submitted = st.form_submit_button("Register")

        if register_submitted:
            ok, msg = register_user(username, email, password)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

else:
    st.write(f"Logged in as **{st.session_state.user['username']}**")
    st.write(f"Display currency: **{st.session_state.display_currency}**")

    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()