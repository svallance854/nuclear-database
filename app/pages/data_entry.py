"""Data Entry Forms — add/edit companies, contracts, and notes."""
import streamlit as st
from components.db import query_df, execute


def render():
    st.title("Data Entry")

    tab1, tab2, tab3 = st.tabs(["Company", "Contract", "Note"])

    with tab1:
        _company_form()

    with tab2:
        _contract_form()

    with tab3:
        _note_form()


def _company_form():
    st.subheader("Add / Edit Company")

    # Edit existing?
    existing = query_df("SELECT id, name FROM companies ORDER BY name")
    edit_opts = ["New Company"] + [f"{r['id']}: {r['name']}" for _, r in existing.iterrows()] if not existing.empty else ["New Company"]
    selection = st.selectbox("Select", edit_opts, key="co_select")

    editing_id = None
    defaults = {}
    if selection != "New Company":
        editing_id = int(selection.split(":")[0])
        row = query_df("SELECT * FROM companies WHERE id = ?", (editing_id,))
        if not row.empty:
            defaults = row.iloc[0].to_dict()

    name = st.text_input("Company Name*", value=defaults.get("name", ""), key="co_name")
    company_type = st.selectbox(
        "Type*",
        ["utility", "developer", "contractor", "vendor", "consultant", "government", "investor", "other"],
        index=["utility", "developer", "contractor", "vendor", "consultant", "government", "investor", "other"].index(
            defaults.get("company_type", "other")
        ),
        key="co_type",
    )
    ticker = st.text_input("Ticker", value=defaults.get("ticker", "") or "", key="co_ticker")
    website = st.text_input("Website", value=defaults.get("website", "") or "", key="co_web")
    hq_state = st.text_input("HQ State", value=defaults.get("headquarters_state", "") or "", key="co_hq")
    publicly_traded = st.checkbox("Publicly Traded", value=bool(defaults.get("publicly_traded", False)), key="co_public")
    description = st.text_area("Description", value=defaults.get("description", "") or "", key="co_desc")

    if st.button("Save Company", key="save_co"):
        if not name:
            st.error("Company name is required")
            return
        if editing_id:
            execute(
                """UPDATE companies SET name=?, company_type=?, ticker=?, website=?,
                   headquarters_state=?, publicly_traded=?, description=? WHERE id=?""",
                (name, company_type, ticker or None, website or None,
                 hq_state or None, int(publicly_traded), description or None, editing_id),
            )
            st.success(f"Company '{name}' updated")
        else:
            execute(
                """INSERT INTO companies (name, company_type, ticker, website,
                   headquarters_state, publicly_traded, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, company_type, ticker or None, website or None,
                 hq_state or None, int(publicly_traded), description or None),
            )
            st.success(f"Company '{name}' created")
        st.rerun()


def _contract_form():
    st.subheader("Add Contract")

    companies = query_df("SELECT id, name FROM companies ORDER BY name")
    sites = query_df("SELECT id, name FROM sites ORDER BY name")

    if companies.empty or sites.empty:
        st.warning("Add companies and sites before creating contracts.")
        return

    company_opts = {f"{r['id']}: {r['name']}": r["id"] for _, r in companies.iterrows()}
    site_opts = {f"{r['id']}: {r['name']}": r["id"] for _, r in sites.iterrows()}

    selected_co = st.selectbox("Company*", list(company_opts.keys()), key="ct_company")
    selected_site = st.selectbox("Site*", list(site_opts.keys()), key="ct_site")
    contract_type = st.selectbox(
        "Contract Type",
        ["construction", "operations", "maintenance", "fuel", "decommissioning", "consulting", "licensing", "other"],
        key="ct_type",
    )
    status = st.selectbox(
        "Status",
        ["proposed", "negotiating", "active", "completed", "terminated", "expired"],
        index=2,
        key="ct_status",
    )
    value = st.number_input("Value ($)", min_value=0.0, step=1000.0, key="ct_value")
    start_date = st.date_input("Start Date", value=None, key="ct_start")
    end_date = st.date_input("End Date", value=None, key="ct_end")
    description = st.text_area("Description", key="ct_desc")
    source_url = st.text_input("Source URL", key="ct_url")

    if st.button("Save Contract", key="save_ct"):
        execute(
            """INSERT INTO contracts
               (company_id, site_id, contract_type, status, value,
                start_date, end_date, description, source_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                company_opts[selected_co],
                site_opts[selected_site],
                contract_type,
                status,
                value if value > 0 else None,
                str(start_date) if start_date else None,
                str(end_date) if end_date else None,
                description or None,
                source_url or None,
            ),
        )
        st.success("Contract saved")


def _note_form():
    st.subheader("Add Note to Any Entity")

    entity_type = st.selectbox(
        "Entity Type",
        ["site", "reactor", "company", "contract", "regulatory_event", "market_event"],
        key="note_etype",
    )

    # Show available entities for the selected type
    table_map = {
        "site": ("sites", "name"),
        "reactor": ("reactors", "name"),
        "company": ("companies", "name"),
        "contract": ("contracts", "description"),
        "regulatory_event": ("regulatory_events", "title"),
        "market_event": ("market_events", "title"),
    }
    table, label_col = table_map[entity_type]
    entities = query_df(f"SELECT id, {label_col} as label FROM {table} ORDER BY {label_col} LIMIT 200")

    if entities.empty:
        st.warning(f"No {entity_type} records found.")
        return

    entity_opts = {f"{r['id']}: {r['label'] or '(no name)'}": r["id"] for _, r in entities.iterrows()}
    selected = st.selectbox("Entity", list(entity_opts.keys()), key="note_entity")

    title = st.text_input("Note Title", key="note_title")
    content = st.text_area("Content*", key="note_content")

    if st.button("Save Note", key="save_note"):
        if not content:
            st.error("Content is required")
            return
        execute(
            "INSERT INTO notes (entity_type, entity_id, title, content) VALUES (?, ?, ?, ?)",
            (entity_type, entity_opts[selected], title or None, content),
        )
        st.success("Note saved")
