"""Sites Explorer — browse, filter, and view site details."""
import streamlit as st
from components.db import query_df, execute


def render():
    st.title("Sites Explorer")

    # Check if viewing a specific site
    if "selected_site_id" in st.session_state and st.session_state.selected_site_id:
        _render_site_detail(st.session_state.selected_site_id)
        if st.button("← Back to Sites"):
            st.session_state.selected_site_id = None
            st.rerun()
        return

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    site_types = query_df("SELECT DISTINCT site_type FROM sites ORDER BY site_type")
    type_options = ["All"] + site_types["site_type"].tolist() if not site_types.empty else ["All"]
    selected_type = col1.selectbox("Site Type", type_options)

    states = query_df("SELECT DISTINCT state FROM sites ORDER BY state")
    state_options = ["All"] + states["state"].tolist() if not states.empty else ["All"]
    selected_state = col2.selectbox("State", state_options)

    owners = query_df("SELECT DISTINCT owner FROM sites WHERE owner IS NOT NULL ORDER BY owner")
    owner_options = ["All"] + owners["owner"].tolist() if not owners.empty else ["All"]
    selected_owner = col3.selectbox("Owner", owner_options)

    search_term = col4.text_input("Search name")

    # Build query
    conditions = []
    params = []
    if selected_type != "All":
        conditions.append("site_type = ?")
        params.append(selected_type)
    if selected_state != "All":
        conditions.append("state = ?")
        params.append(selected_state)
    if selected_owner != "All":
        conditions.append("owner = ?")
        params.append(selected_owner)
    if search_term:
        conditions.append("name LIKE ?")
        params.append(f"%{search_term}%")

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    sites_df = query_df(
        f"""SELECT id, name, state, site_type, owner, operator, total_capacity_mw
            FROM sites{where} ORDER BY name""",
        tuple(params),
    )

    st.write(f"**{len(sites_df)} sites**")

    if sites_df.empty:
        st.info("No sites found. Run ingestion scripts to populate data.")
        return

    # Display as interactive table
    st.dataframe(
        sites_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "total_capacity_mw": st.column_config.NumberColumn("Capacity (MW)", format="%.0f"),
        },
    )

    # Site selection
    site_id = st.number_input("Enter Site ID to view details", min_value=0, step=1, value=0)
    if site_id and st.button("View Site"):
        st.session_state.selected_site_id = site_id
        st.rerun()


def _render_site_detail(site_id: int):
    """Render the detail page for a single site."""
    site = query_df("SELECT * FROM sites WHERE id = ?", (site_id,))
    if site.empty:
        st.error("Site not found")
        return

    s = site.iloc[0]
    st.header(s["name"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("State", s["state"])
    col2.metric("Type", s["site_type"])
    col3.metric("Capacity (MW)", f"{s['total_capacity_mw']:.0f}" if s["total_capacity_mw"] else "N/A")
    col4.metric("Owner", s["owner"] or "N/A")

    if s["operator"]:
        st.write(f"**Operator:** {s['operator']}")
    if s["nrc_site_id"]:
        st.write(f"**NRC Site ID:** {s['nrc_site_id']}")

    st.divider()

    # Reactors at this site
    st.subheader("Reactors")
    reactors = query_df(
        """SELECT name, unit_number, reactor_type, capacity_mw, status,
                  nrc_docket_number, commercial_operation_date, license_expiration_date,
                  permanent_shutdown_date
           FROM reactors WHERE site_id = ? ORDER BY unit_number""",
        (site_id,),
    )
    if not reactors.empty:
        st.dataframe(reactors, use_container_width=True, hide_index=True)
    else:
        st.info("No reactors recorded for this site.")

    # Service providers (contracts)
    st.subheader("Service Providers")
    contracts = query_df(
        """SELECT c.name as company, ct.contract_type, ct.status, ct.value,
                  ct.start_date, ct.end_date, ct.description
           FROM contracts ct
           JOIN companies c ON ct.company_id = c.id
           WHERE ct.site_id = ? ORDER BY ct.start_date DESC""",
        (site_id,),
    )
    if not contracts.empty:
        st.dataframe(contracts, use_container_width=True, hide_index=True)
    else:
        st.info("No contracts recorded for this site.")

    # Decommissioning trust fund
    trust = query_df(
        """SELECT fund_balance, estimated_cost, report_date, source, source_url
           FROM decommissioning_trust_funds WHERE site_id = ?""",
        (site_id,),
    )
    if not trust.empty:
        st.subheader("Decommissioning Trust Fund")
        t = trust.iloc[0]
        tc1, tc2 = st.columns(2)
        tc1.metric("Fund Balance", f"${t['fund_balance']:,.0f}" if t["fund_balance"] else "N/A")
        tc2.metric("Estimated Cost", f"${t['estimated_cost']:,.0f}" if t["estimated_cost"] else "N/A")
        if t["report_date"]:
            st.caption(f"As of {t['report_date']} — Source: {t['source'] or 'NRC'}")

    # Regulatory events
    st.subheader("Regulatory Events")
    reg = query_df(
        """SELECT title, event_type, event_date, source_url
           FROM regulatory_events WHERE site_id = ? ORDER BY event_date DESC""",
        (site_id,),
    )
    if not reg.empty:
        st.dataframe(reg, use_container_width=True, hide_index=True)
    else:
        st.info("No regulatory events for this site.")

    # Notes
    st.subheader("Notes")
    notes = query_df(
        "SELECT title, content, created_at FROM notes WHERE entity_type = 'site' AND entity_id = ? ORDER BY created_at DESC",
        (site_id,),
    )
    if not notes.empty:
        for _, n in notes.iterrows():
            with st.expander(n["title"] or "Note"):
                st.write(n["content"])
                st.caption(f"Created: {n['created_at']}")

    # Add note
    with st.expander("Add Note"):
        note_title = st.text_input("Title", key="site_note_title")
        note_content = st.text_area("Content", key="site_note_content")
        if st.button("Save Note", key="save_site_note"):
            if note_content:
                execute(
                    "INSERT INTO notes (entity_type, entity_id, title, content) VALUES ('site', ?, ?, ?)",
                    (site_id, note_title, note_content),
                )
                st.success("Note saved")
                st.rerun()
            else:
                st.warning("Note content is required")
