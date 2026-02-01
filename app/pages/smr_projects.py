"""SMR Project Tracker — browse and manage SMR projects with milestone tracking."""
import streamlit as st
from components.db import query_df, execute


def render():
    st.title("SMR Project Tracker")

    tab1, tab2, tab3 = st.tabs(["Projects", "Add Project", "Add Milestone"])

    with tab1:
        _list_projects()
    with tab2:
        _add_project_form()
    with tab3:
        _add_milestone_form()


def _list_projects():
    projects = query_df(
        """SELECT p.id, p.name, c.name as developer, p.reactor_design, p.capacity_mw,
                  p.num_modules, p.status, p.target_operation_date, p.estimated_cost
           FROM smr_projects p
           LEFT JOIN companies c ON p.developer_id = c.id
           ORDER BY p.name"""
    )
    if projects.empty:
        st.info("No SMR projects tracked yet. Use the Add Project tab to create one.")
        return

    st.dataframe(
        projects, use_container_width=True, hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "estimated_cost": st.column_config.NumberColumn("Est. Cost ($)", format="$%.0f"),
            "capacity_mw": st.column_config.NumberColumn("MW"),
        },
    )

    # Detail view
    project_id = st.number_input("Project ID for milestones", min_value=0, step=1, value=0)
    if project_id:
        milestones = query_df(
            """SELECT title, milestone_type, status, target_date, actual_date, description
               FROM smr_milestones WHERE project_id = ? ORDER BY target_date""",
            (project_id,),
        )
        if not milestones.empty:
            st.subheader("Milestones")
            st.dataframe(milestones, use_container_width=True, hide_index=True)
        else:
            st.info("No milestones for this project.")


def _add_project_form():
    companies = query_df("SELECT id, name FROM companies ORDER BY name")
    sites = query_df("SELECT id, name FROM sites ORDER BY name")

    name = st.text_input("Project Name*", key="smr_name")
    developer_opts = {"None": None}
    if not companies.empty:
        developer_opts.update({f"{r['id']}: {r['name']}": r["id"] for _, r in companies.iterrows()})
    developer = st.selectbox("Developer", list(developer_opts.keys()), key="smr_dev")

    site_opts = {"None": None}
    if not sites.empty:
        site_opts.update({f"{r['id']}: {r['name']}": r["id"] for _, r in sites.iterrows()})
    site = st.selectbox("Site", list(site_opts.keys()), key="smr_site")

    reactor_design = st.text_input("Reactor Design", key="smr_design")
    col1, col2 = st.columns(2)
    capacity = col1.number_input("Capacity (MW)", min_value=0.0, key="smr_cap")
    num_modules = col2.number_input("Modules", min_value=0, step=1, key="smr_mod")
    status = st.selectbox("Status", ["announced", "pre-application", "under-review", "approved",
                                      "under-construction", "operating", "cancelled", "suspended"], key="smr_status")
    target_date = st.text_input("Target Operation Date (YYYY-MM-DD)", key="smr_target")
    estimated_cost = st.number_input("Estimated Cost ($)", min_value=0.0, step=1e6, key="smr_cost")
    description = st.text_area("Description", key="smr_desc")

    if st.button("Save Project", key="save_smr"):
        if not name:
            st.error("Project name is required")
            return
        execute(
            """INSERT INTO smr_projects (name, developer_id, site_id, reactor_design, capacity_mw,
               num_modules, status, target_operation_date, estimated_cost, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, developer_opts[developer], site_opts[site], reactor_design or None,
             capacity or None, num_modules or None, status, target_date or None,
             estimated_cost or None, description or None),
        )
        st.success(f"Project '{name}' created")
        st.rerun()


def _add_milestone_form():
    projects = query_df("SELECT id, name FROM smr_projects ORDER BY name")
    if projects.empty:
        st.warning("Create an SMR project first.")
        return

    proj_opts = {f"{r['id']}: {r['name']}": r["id"] for _, r in projects.iterrows()}
    project = st.selectbox("Project*", list(proj_opts.keys()), key="ms_proj")
    title = st.text_input("Milestone Title*", key="ms_title")
    milestone_type = st.selectbox("Type", ["regulatory", "construction", "financial", "technical", "other"], key="ms_type")
    status = st.selectbox("Status", ["pending", "in-progress", "completed", "delayed", "cancelled"], key="ms_status")
    target_date = st.text_input("Target Date (YYYY-MM-DD)", key="ms_target")
    actual_date = st.text_input("Actual Date (YYYY-MM-DD)", key="ms_actual")
    description = st.text_area("Description", key="ms_desc")
    source_url = st.text_input("Source URL", key="ms_url")

    if st.button("Save Milestone", key="save_ms"):
        if not title:
            st.error("Milestone title is required")
            return
        execute(
            """INSERT INTO smr_milestones (project_id, title, milestone_type, status,
               target_date, actual_date, description, source_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (proj_opts[project], title, milestone_type, status,
             target_date or None, actual_date or None, description or None, source_url or None),
        )
        st.success("Milestone saved")
        st.rerun()
