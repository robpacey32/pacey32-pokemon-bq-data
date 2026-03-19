import os
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

from auth import register_user, login_user
from styles import apply_umbreon_theme

cookies = EncryptedCookieManager(
    prefix="poketcg_app",
    password=os.environ.get("COOKIE_PASSWORD", "local-dev-cookie-password"),
)


def cookies_ready() -> bool:
    try:
        return cookies.ready()
    except Exception:
        return False


def restore_login_from_cookie():
    if "user" not in st.session_state:
        st.session_state.user = None

    if "display_currency" not in st.session_state:
        st.session_state.display_currency = "GBP"

    if not cookies_ready():
        return

    username = cookies.get("user_username")
    if st.session_state.user is None and username:
        st.session_state.user = {
            "username": username,
            "email": cookies.get("user_email"),
            "user_id": cookies.get("user_id"),
            "created_at": cookies.get("created_at"),
            "last_login_at": cookies.get("last_login_at"),
            "display_currency": cookies.get("display_currency", "GBP"),
        }
        st.session_state.display_currency = cookies.get("display_currency", "GBP")


def save_login_cookie(user: dict):
    if not cookies_ready():
        return

    cookies["user_username"] = user.get("username", "")
    cookies["user_email"] = user.get("email", "")
    cookies["user_id"] = user.get("user_id", "")
    cookies["created_at"] = str(user.get("created_at", "")) if user.get("created_at") else ""
    cookies["last_login_at"] = str(user.get("last_login_at", "")) if user.get("last_login_at") else ""
    cookies["display_currency"] = user.get("display_currency", "GBP")
    cookies.save()


def clear_login_cookie():
    if not cookies_ready():
        return

    for key in [
        "user_username",
        "user_email",
        "user_id",
        "created_at",
        "last_login_at",
        "display_currency",
    ]:
        if key in cookies:
            del cookies[key]
    cookies.save()


def render_login_portal(show_title: bool = True):
    apply_umbreon_theme()
    restore_login_from_cookie()

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
                session_user = {
                    "username": user["username"],
                    "email": user["email"],
                    "user_id": user["username"],
                    "created_at": user.get("created_at"),
                    "last_login_at": user.get("last_login_at"),
                    "display_currency": user.get("display_currency", "GBP"),
                }

                st.session_state.user = session_user
                st.session_state.display_currency = user.get("display_currency", "GBP")
                save_login_cookie(session_user)
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
            Need help? Contact
            <a href="mailto:info@pacey32.com" style="color:#F4D995; text-decoration:none; font-weight:700;">
                info@pacey32.com
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)