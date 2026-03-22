import streamlit as st
from datetime import datetime

from auth import (
    change_password,
    verify_email_token,
    reset_password_with_token,
)
from db_mongo import get_user_by_username, update_user_display_currency
from styles import apply_umbreon_theme
from ui_auth import render_login_portal, restore_login_from_storage, logout

st.set_page_config(page_title="Account", layout="wide")
apply_umbreon_theme()
restore_login_from_storage()

# Show one-time success messages after redirect/rerun
if "password_reset_success" in st.session_state:
    st.success(st.session_state.pop("password_reset_success"))
    st.info("You can now log in with your new password.")

if "email_verify_success" in st.session_state:
    st.success(st.session_state.pop("email_verify_success"))
    st.info("You can now log in.")

params = st.query_params

# -------------------------
# EMAIL VERIFICATION HANDLER
# -------------------------
if "verify_token" in params:
    token = params["verify_token"]
    ok, msg = verify_email_token(token)

    st.title("Verify Email")

    if ok:
        st.session_state["email_verify_success"] = msg
        st.query_params.clear()
        st.rerun()
    else:
        st.error(msg)

    st.stop()

# -------------------------
# PASSWORD RESET HANDLER
# -------------------------
if "reset_token" in params:
    token = params["reset_token"]

    st.title("Reset Password")

    with st.form("reset_password_form"):
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Reset password")

    if submitted:
        if new_password != confirm_password:
            st.error("Passwords do not match")
        elif len(new_password) < 6:
            st.error("Password must be at least 6 characters")
        else:
            ok, msg = reset_password_with_token(token, new_password)

            if ok:
                st.session_state["password_reset_success"] = msg
                st.query_params.clear()
                st.rerun()
            else:
                st.error(msg)

    st.stop()

if "user" not in st.session_state or st.session_state.user is None:
    render_login_portal(show_title=True)
    st.stop()

if "display_currency" not in st.session_state:
    st.session_state.display_currency = "GBP"


def format_dt(value):
    if not value:
        return "N/A"

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)


user = get_user_by_username(st.session_state.user["username"])

# Safety fallback
if not user:
    st.session_state.user = None
    st.warning("Your session could not be loaded. Please log in again.")
    st.rerun()

st.session_state.display_currency = user.get(
    "display_currency",
    st.session_state.get("display_currency", "GBP")
)

st.title("Account")

created_at_fmt = format_dt(user.get("created_at"))
last_login_at_fmt = format_dt(user.get("last_login_at"))

col1, col2 = st.columns([1.6, 1])

with col1:
    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown("### Account details")
    st.markdown(
        f"""
        <div class="account-kv">
            <b>Username:</b> {user.get('username', 'N/A')}<br>
            <b>Email:</b> {user.get('email', 'N/A')}<br>
            <b>Email verified:</b> {"Yes" if user.get("email_verified", False) else "No"}<br>
            <b>Created:</b> {created_at_fmt}<br>
            <b>Last login:</b> {last_login_at_fmt}<br>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown("### Preferences")

    currency_options = ["GBP", "EUR", "USD"]
    current_currency = user.get(
        "display_currency",
        st.session_state.get("display_currency", "GBP")
    )

    selected_currency = st.selectbox(
        "Default currency",
        currency_options,
        index=currency_options.index(current_currency),
        key="account_default_currency"
    )

    if st.button("Save currency preference"):
        update_user_display_currency(user["username"], selected_currency)
        st.session_state.display_currency = selected_currency
        st.session_state.user["display_currency"] = selected_currency
        st.success("Default currency updated")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown("### Help")
    st.markdown(
        """
        <div class="help-box">
            For support, account issues, or collection questions, contact
            <a href="mailto:info@pacey32.com" style="color:#F4D995; text-decoration:none; font-weight:700;">
                info@pacey32.com
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown("### Change password")

    with st.form("change_password_form"):
        current_password = st.text_input("Current password", type="password")
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Update password")

    if submitted:
        if new_password != confirm_password:
            st.error("New passwords do not match")
        elif len(new_password) < 6:
            st.error("New password must be at least 6 characters")
        else:
            ok, msg = change_password(
                user["username"],
                current_password,
                new_password
            )
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.markdown("---")

    st.markdown(
        f"""
        <div class="account-kv">
            <b>Current default currency:</b> {st.session_state.display_currency}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    if st.button("Logout", use_container_width=True):
        logout()
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)