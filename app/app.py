import streamlit as st
from auth import register_user, login_user

st.set_page_config(page_title="Pokemon Collection App", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

st.title("Pokemon Collection App")

if st.session_state.user is None:
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            user = login_user(username, password)
            if user:
                st.session_state.user = {
                    "username": user["username"],
                    "email": user["email"],
                    "user_id": str(user["_id"]),
                }
                st.success("Logged in")
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        username = st.text_input("New username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("New password", type="password", key="reg_password")

        if st.button("Register"):
            ok, msg = register_user(username, email, password)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

else:
    st.write(f"Logged in as **{st.session_state.user['username']}**")

    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()