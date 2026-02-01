"""Nuclear Asset Database — Streamlit Dashboard."""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.db_utils import init_db

# Initialize DB on first run
init_db()

st.set_page_config(
    page_title="Nuclear Asset Database",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Basic auth
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    with st.form("login"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        import os
        correct = os.getenv("APP_PASSWORD", "nuclear2024")
        if password == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False


if not check_password():
    st.stop()

# Navigation
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Sites Explorer", "Companies Explorer", "SMR Projects",
     "Deal Pipeline", "Commodity Prices", "Search", "Data Entry", "Export"],
)

if page == "Dashboard":
    from pages import dashboard
    dashboard.render()
elif page == "Sites Explorer":
    from pages import sites
    sites.render()
elif page == "Companies Explorer":
    from pages import companies
    companies.render()
elif page == "SMR Projects":
    from pages import smr_projects
    smr_projects.render()
elif page == "Deal Pipeline":
    from pages import deals
    deals.render()
elif page == "Commodity Prices":
    from pages import commodities
    commodities.render()
elif page == "Search":
    from pages import search
    search.render()
elif page == "Data Entry":
    from pages import data_entry
    data_entry.render()
elif page == "Export":
    from pages import export
    export.render()
