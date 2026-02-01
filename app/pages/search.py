"""Global Search — search across sites, reactors, companies, and notes."""
import streamlit as st
from components.db import query_df


def render():
    st.title("Search")

    query = st.text_input("Search across all entities", placeholder="e.g. Vogtle, Holtec, PWR, decommissioning...")

    if not query:
        st.info("Enter a search term to find sites, reactors, companies, and notes.")
        return

    term = f"%{query}%"

    # Sites
    sites = query_df(
        """SELECT id, name, state, site_type, owner
           FROM sites WHERE name LIKE ? OR owner LIKE ? OR operator LIKE ? OR notes LIKE ?
           ORDER BY name LIMIT 50""",
        (term, term, term, term),
    )
    if not sites.empty:
        st.subheader(f"Sites ({len(sites)})")
        st.dataframe(sites, use_container_width=True, hide_index=True)

    # Reactors
    reactors = query_df(
        """SELECT r.id, r.name, r.reactor_type, r.status, r.nrc_docket_number,
                  s.name as site_name
           FROM reactors r JOIN sites s ON r.site_id = s.id
           WHERE r.name LIKE ? OR r.nrc_docket_number LIKE ? OR r.vendor LIKE ? OR r.model LIKE ?
           ORDER BY r.name LIMIT 50""",
        (term, term, term, term),
    )
    if not reactors.empty:
        st.subheader(f"Reactors ({len(reactors)})")
        st.dataframe(reactors, use_container_width=True, hide_index=True)

    # Companies
    companies = query_df(
        """SELECT id, name, company_type, ticker, headquarters_state
           FROM companies WHERE name LIKE ? OR description LIKE ? OR ticker LIKE ?
           ORDER BY name LIMIT 50""",
        (term, term, term),
    )
    if not companies.empty:
        st.subheader(f"Companies ({len(companies)})")
        st.dataframe(companies, use_container_width=True, hide_index=True)

    # Regulatory events
    reg = query_df(
        """SELECT title, event_type, event_date, source_url
           FROM regulatory_events WHERE title LIKE ? OR description LIKE ?
           ORDER BY event_date DESC LIMIT 20""",
        (term, term),
    )
    if not reg.empty:
        st.subheader(f"Regulatory Events ({len(reg)})")
        st.dataframe(reg, use_container_width=True, hide_index=True)

    # Market events
    mkt = query_df(
        """SELECT title, event_type, event_date, financial_value
           FROM market_events WHERE title LIKE ? OR description LIKE ?
           ORDER BY event_date DESC LIMIT 20""",
        (term, term),
    )
    if not mkt.empty:
        st.subheader(f"Market Events ({len(mkt)})")
        st.dataframe(mkt, use_container_width=True, hide_index=True)

    # Notes
    notes = query_df(
        """SELECT entity_type, entity_id, title, content, created_at
           FROM notes WHERE title LIKE ? OR content LIKE ?
           ORDER BY created_at DESC LIMIT 20""",
        (term, term),
    )
    if not notes.empty:
        st.subheader(f"Notes ({len(notes)})")
        st.dataframe(notes, use_container_width=True, hide_index=True)

    if sites.empty and reactors.empty and companies.empty and reg.empty and mkt.empty and notes.empty:
        st.warning(f'No results found for "{query}"')
