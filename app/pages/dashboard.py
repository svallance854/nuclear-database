"""Dashboard Home — key metrics and recent activity."""
import streamlit as st
from components.db import query_df


def render():
    st.title("Nuclear Asset Database")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    sites = query_df("SELECT site_type, COUNT(*) as cnt FROM sites GROUP BY site_type")
    total_sites = sites["cnt"].sum() if not sites.empty else 0
    col1.metric("Total Sites", total_sites)

    operating = query_df("SELECT COUNT(*) as cnt FROM reactors WHERE status = 'operating'")
    col2.metric("Operating Reactors", operating.iloc[0]["cnt"] if not operating.empty else 0)

    decom = query_df(
        "SELECT COUNT(*) as cnt FROM sites WHERE site_type IN ('decommissioning', 'decommissioned')"
    )
    col3.metric("Decom Sites", decom.iloc[0]["cnt"] if not decom.empty else 0)

    companies_count = query_df("SELECT COUNT(*) as cnt FROM companies")
    col4.metric("Companies", companies_count.iloc[0]["cnt"] if not companies_count.empty else 0)

    st.divider()

    # Sites by status
    left, right = st.columns(2)
    with left:
        st.subheader("Sites by Type")
        if not sites.empty:
            st.bar_chart(sites.set_index("site_type"))
        else:
            st.info("No site data yet. Run ingestion scripts first.")

    # Upcoming license expirations
    with right:
        st.subheader("Upcoming License Expirations")
        expiring = query_df(
            """SELECT r.name, r.license_expiration_date, s.name as site_name
               FROM reactors r JOIN sites s ON r.site_id = s.id
               WHERE r.license_expiration_date IS NOT NULL
               ORDER BY r.license_expiration_date ASC LIMIT 10"""
        )
        if not expiring.empty:
            st.dataframe(expiring, use_container_width=True, hide_index=True)
        else:
            st.info("No license expiration data available.")

    st.divider()

    # Recent market events
    st.subheader("Recent Market Events")
    events = query_df(
        """SELECT title, event_type, event_date, financial_value, source_url
           FROM market_events ORDER BY event_date DESC LIMIT 10"""
    )
    if not events.empty:
        st.dataframe(events, use_container_width=True, hide_index=True)
    else:
        st.info("No market events yet.")

    # Recent regulatory events
    st.subheader("Recent Regulatory Events")
    reg = query_df(
        """SELECT title, event_type, event_date, source_url
           FROM regulatory_events ORDER BY event_date DESC LIMIT 10"""
    )
    if not reg.empty:
        st.dataframe(reg, use_container_width=True, hide_index=True)
    else:
        st.info("No regulatory events yet.")
