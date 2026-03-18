import streamlit as st
from auth import change_password
from styles import apply_umbreon_theme
from ui_auth import render_login_portal

st.set_page_config(page_title="Account", layout="wide")
apply_umbreon_theme()

if "user" not in st.session_state:
    st.session_state.user = None

if "display_currency" not in st.session_state:
    st.session_state.display_currency = "GBP"

if st.session_state.user is None:
    render_login_portal(show_title=True)
else:
    st.title("Account")

    user = st.session_state.user

    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.markdown('<div class="section-shell">', unsafe_allow_html=True)
        st.markdown("### Account details")
        created_at = user.get("created_at")
        last_login_at = user.get("last_login_at")

        st.markdown(
            f"""
            <div class="account-kv">
                <b>Username:</b> {user['username']}<br>
                <b>Email:</b> {user['email']}<br>
                <b>Display currency:</b> {st.session_state.display_currency}<br>
                <b>Created:</b> {created_at if created_at else 'N/A'}<br>
                <b>Last login:</b> {last_login_at if last_login_at else 'N/A'}<br>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
                ok, msg = change_password(user["username"], current_password, new_password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)