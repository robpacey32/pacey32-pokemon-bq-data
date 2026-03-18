import streamlit as st
from auth import register_user, login_user
from styles import apply_umbreon_theme


def render_login_portal(show_title: bool = True):
    apply_umbreon_theme()

    if "user" not in st.session_state:
        st.session_state.user = None

    if "display_currency" not in st.session_state:
        st.session_state.display_currency = "GBP"

    if show_title:
        st.title("Account")

    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown("### Sign in")
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
                    "created_at": user.get("created_at"),
                    "last_login_at": user.get("last_login_at"),
                }
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

    st.markdown(
        """
        <div class="help-box">
            Need help? Contact <b>info@pacey32.com</b>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)