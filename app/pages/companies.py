"""Companies Explorer — browse, filter, and view company details."""
import streamlit as st
from components.db import query_df, execute


def render():
    st.title("Companies Explorer")

    if "selected_company_id" in st.session_state and st.session_state.selected_company_id:
        _render_company_detail(st.session_state.selected_company_id)
        if st.button("← Back to Companies"):
            st.session_state.selected_company_id = None
            st.rerun()
        return

    # Filters
    col1, col2, col3 = st.columns(3)

    types = query_df("SELECT DISTINCT company_type FROM companies ORDER BY company_type")
    type_opts = ["All"] + types["company_type"].tolist() if not types.empty else ["All"]
    selected_type = col1.selectbox("Company Type", type_opts)

    categories = query_df(
        """SELECT DISTINCT sc.name FROM service_categories sc
           JOIN company_services cs ON cs.category_id = sc.id
           ORDER BY sc.name"""
    )
    cat_opts = ["All"] + categories["name"].tolist() if not categories.empty else ["All"]
    selected_cat = col2.selectbox("Service Category", cat_opts)

    search_term = col3.text_input("Search name")

    # Build query
    conditions = []
    params = []
    joins = ""
    if selected_type != "All":
        conditions.append("c.company_type = ?")
        params.append(selected_type)
    if selected_cat != "All":
        joins = " JOIN company_services cs ON cs.company_id = c.id JOIN service_categories sc ON sc.id = cs.category_id"
        conditions.append("sc.name = ?")
        params.append(selected_cat)
    if search_term:
        conditions.append("c.name LIKE ?")
        params.append(f"%{search_term}%")

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    companies_df = query_df(
        f"""SELECT DISTINCT c.id, c.name, c.company_type, c.ticker, c.headquarters_state,
                   c.publicly_traded, c.website
            FROM companies c{joins}{where} ORDER BY c.name""",
        tuple(params),
    )

    st.write(f"**{len(companies_df)} companies**")

    if companies_df.empty:
        st.info("No companies found. Run ingestion scripts or add companies manually.")
        return

    st.dataframe(
        companies_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "publicly_traded": st.column_config.CheckboxColumn("Public"),
            "website": st.column_config.LinkColumn("Website"),
        },
    )

    company_id = st.number_input("Enter Company ID to view details", min_value=0, step=1, value=0)
    if company_id and st.button("View Company"):
        st.session_state.selected_company_id = company_id
        st.rerun()


def _render_company_detail(company_id: int):
    """Render detail page for a single company."""
    company = query_df("SELECT * FROM companies WHERE id = ?", (company_id,))
    if company.empty:
        st.error("Company not found")
        return

    c = company.iloc[0]
    st.header(c["name"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Type", c["company_type"])
    col2.metric("Ticker", c["ticker"] or "N/A")
    col3.metric("HQ State", c["headquarters_state"] or "N/A")
    col4.metric("Public", "Yes" if c["publicly_traded"] else "No")

    if c["website"]:
        st.write(f"**Website:** {c['website']}")
    if c["description"]:
        st.write(c["description"])

    st.divider()

    # Service categories
    st.subheader("Service Categories")
    services = query_df(
        """SELECT sc.name as category, cs.details
           FROM company_services cs
           JOIN service_categories sc ON sc.id = cs.category_id
           WHERE cs.company_id = ?""",
        (company_id,),
    )
    if not services.empty:
        st.dataframe(services, use_container_width=True, hide_index=True)
    else:
        st.info("No service categories assigned.")

    # Sites served
    st.subheader("Sites Served")
    sites_served = query_df(
        """SELECT s.name as site, ct.contract_type, ct.status, ct.value,
                  ct.start_date, ct.end_date
           FROM contracts ct
           JOIN sites s ON ct.site_id = s.id
           WHERE ct.company_id = ? ORDER BY ct.start_date DESC""",
        (company_id,),
    )
    if not sites_served.empty:
        st.dataframe(sites_served, use_container_width=True, hide_index=True)
    else:
        st.info("No contracts recorded.")

    # Government contracts (market events)
    st.subheader("Government Contracts")
    gov = query_df(
        """SELECT title, event_date, financial_value, source_url
           FROM market_events WHERE company_id = ? ORDER BY event_date DESC""",
        (company_id,),
    )
    if not gov.empty:
        st.dataframe(gov, use_container_width=True, hide_index=True)
    else:
        st.info("No government contracts recorded.")

    # Notes
    st.subheader("Notes")
    notes = query_df(
        "SELECT title, content, created_at FROM notes WHERE entity_type = 'company' AND entity_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    if not notes.empty:
        for _, n in notes.iterrows():
            with st.expander(n["title"] or "Note"):
                st.write(n["content"])
                st.caption(f"Created: {n['created_at']}")

    with st.expander("Add Note"):
        note_title = st.text_input("Title", key="co_note_title")
        note_content = st.text_area("Content", key="co_note_content")
        if st.button("Save Note", key="save_co_note"):
            if note_content:
                execute(
                    "INSERT INTO notes (entity_type, entity_id, title, content) VALUES ('company', ?, ?, ?)",
                    (company_id, note_title, note_content),
                )
                st.success("Note saved")
                st.rerun()
            else:
                st.warning("Note content is required")
