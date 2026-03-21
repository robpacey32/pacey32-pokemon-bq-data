import streamlit as st


def apply_umbreon_theme():
    st.markdown(
        """
        <style>
        :root {
            --bg: #020303;
            --panel: #111417;
            --panel-2: #1a2024;
            --muted: #4A575D;
            --muted-2: #566574;
            --gold: #F4D995;
            --gold-2: #e9ca78;
            --gold-3: #f7e4aa;
            --ember: #E07451;
            --text: #F7F7F5;
            --soft-border: rgba(244, 217, 149, 0.18);
        }

        .stApp {
            background: linear-gradient(180deg, #020303 0%, #06090b 100%);
            color: var(--text);
        }

        h1, h2, h3, h4, h5, h6, p, label, span, div {
            color: var(--text);
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1180px;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(74,87,93,0.22), rgba(86,101,116,0.14));
            border: 1px solid var(--soft-border);
            border-radius: 18px;
            padding: 12px 16px;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--soft-border);
            border-radius: 18px;
            overflow: hidden;
        }

        div[data-testid="stVerticalBlock"] div[data-testid="stForm"] {
            background: linear-gradient(180deg, rgba(74,87,93,0.18), rgba(86,101,116,0.10));
            border: 1px solid var(--soft-border);
            border-radius: 18px;
            padding: 18px 18px 8px 18px;
        }

        .card-shell {
            background: linear-gradient(180deg, rgba(74,87,93,0.16), rgba(86,101,116,0.08));
            border: 1px solid var(--soft-border);
            border-radius: 22px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: 0 8px 22px rgba(0,0,0,0.25);
        }

        .section-shell {
            background: linear-gradient(180deg, rgba(74,87,93,0.16), rgba(86,101,116,0.08));
            border: 1px solid var(--soft-border);
            border-radius: 22px;
            padding: 18px;
            margin-bottom: 16px;
        }

        .account-kv {
            font-size: 0.96rem;
            line-height: 1.8;
        }

        .help-box {
            background: rgba(224,116,81,0.10);
            border: 1px solid rgba(224,116,81,0.28);
            border-radius: 16px;
            padding: 12px 14px;
        }

        /* Primary app buttons */
        .stButton > button,
        .stFormSubmitButton > button,
        button[kind="primary"] {
            background: linear-gradient(180deg, var(--gold), var(--gold-2)) !important;
            color: #111 !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        button[kind="primary"]:hover {
            background: linear-gradient(180deg, var(--gold-3), var(--gold)) !important;
            color: #111 !important;
        }

        .stButton > button *,
        .stFormSubmitButton > button *,
        button[kind="primary"] * {
            color: #111 !important;
            fill: #111 !important;
        }

        /* Secondary buttons */
        button[kind="secondary"] {
            border-radius: 12px !important;
            border: 1px solid var(--soft-border) !important;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #090d10 0%, #11161b 100%);
            border-right: 1px solid var(--soft-border);
        }

        hr {
            border-color: rgba(244, 217, 149, 0.15);
        }

        /* Remove text input helper text */
        div[data-testid="stTextInput"] small,
        div[data-testid="stTextInput"] [aria-live="polite"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }

        div[data-testid="stTextInput"] [data-testid="InputInstructions"] {
            display: none !important;
        }

        div[data-testid="stTextInput"] div[style*="justify-content: space-between"] {
            display: none !important;
        }

        /* Header / hamburger / menu icons */
        header button,
        [data-testid="collapsedControl"] button,
        [data-testid="stBaseButton-headerNoPadding"] {
            color: var(--gold) !important;
            background: transparent !important;
            border: none !important;
        }

        header button svg,
        [data-testid="collapsedControl"] button svg,
        [data-testid="stBaseButton-headerNoPadding"] svg {
            color: var(--gold) !important;
            fill: var(--gold) !important;
        }

        header button:hover,
        [data-testid="collapsedControl"] button:hover,
        [data-testid="stBaseButton-headerNoPadding"]:hover {
            background: rgba(244, 217, 149, 0.10) !important;
            border-radius: 10px !important;
        }

        /* Tabs - good for Sign in / Sign up */
        button[role="tab"] {
            background: linear-gradient(180deg, var(--gold), var(--gold-2)) !important;
            color: #111 !important;
            border: none !important;
            border-radius: 999px !important;
            font-weight: 700 !important;
            padding: 0.45rem 1rem !important;
            margin-right: 0.35rem !important;
        }

        button[role="tab"] * {
            color: #111 !important;
            fill: #111 !important;
        }

        button[role="tab"][aria-selected="true"] {
            background: linear-gradient(180deg, var(--gold-3), var(--gold)) !important;
            color: #111 !important;
            box-shadow: 0 0 0 1px rgba(244, 217, 149, 0.25) inset !important;
        }

        /* Keep tab row clean */
        [data-baseweb="tab-list"] {
            gap: 0.25rem;
        }

        /* Links */
        a {
            color: var(--gold) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )