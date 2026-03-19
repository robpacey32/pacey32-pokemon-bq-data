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

        /* Buttons */
        .stButton > button, .stFormSubmitButton > button {
            background: linear-gradient(180deg, var(--gold), #e9ca78);
            color: #111 !important;
            border: none;
            border-radius: 12px;
            font-weight: 700;
        }

        .stButton > button:hover, .stFormSubmitButton > button:hover {
            background: linear-gradient(180deg, #f7e4aa, var(--gold));
            color: #111 !important;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #090d10 0%, #11161b 100%);
            border-right: 1px solid var(--soft-border);
        }

        hr {
            border-color: rgba(244, 217, 149, 0.15);
        }

        /* === REMOVE "Press Enter to submit form" === */

        /* Standard helper text */
        div[data-testid="stTextInput"] small,
        div[data-testid="stTextInput"] [aria-live="polite"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }

        /* Newer Streamlit versions */
        div[data-testid="stTextInput"] [data-testid="InputInstructions"] {
            display: none !important;
        }

        /* Aggressive fallback: removes right-side hint inside input */
        div[data-testid="stTextInput"] div[style*="justify-content: space-between"] {
            display: none !important;
        }

        /* Ensure button text is always visible */
        button, button * {
            color: #020303 !important;
            fill: #020303 !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )