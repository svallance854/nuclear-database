"""Deal Pipeline — track and manage deals through stages."""
import streamlit as st
from components.db import query_df, execute

STAGES = ["identified", "preliminary", "due-diligence", "negotiation", "closed", "dead"]
DEAL_TYPES = ["acquisition", "investment", "ppa", "joint-venture", "licensing", "development", "other"]


def render():
    st.title("Deal Pipeline")

    tab1, tab2 = st.tabs(["Pipeline", "Add / Edit Deal"])

    with tab1:
        _pipeline_view()
    with tab2:
        _deal_form()


def _pipeline_view():
    deals = query_df(
        """SELECT d.id, d.title, d.deal_type, d.stage, d.estimated_value,
                  d.probability_pct, d.lead_contact, d.next_step, d.next_step_date,
                  c.name as company, s.name as site
           FROM deals d
           LEFT JOIN companies c ON d.company_id = c.id
           LEFT JOIN sites s ON d.site_id = s.id
           ORDER BY d.stage, d.title"""
    )
    if deals.empty:
        st.info("No deals in the pipeline. Use the Add Deal tab to get started.")
        return

    # Summary by stage
    summary = deals.groupby("stage").agg(
        count=("id", "count"),
        total_value=("estimated_value", "sum"),
    ).reindex(STAGES).fillna(0)
    summary["count"] = summary["count"].astype(int)

    cols = st.columns(len(STAGES))
    for i, stage in enumerate(STAGES):
        if stage in summary.index:
            row = summary.loc[stage]
            cols[i].metric(stage.title(), f"{int(row['count'])} deals",
                          f"${row['total_value']:,.0f}" if row['total_value'] > 0 else None)

    st.divider()

    # Filter by stage
    selected_stage = st.selectbox("Filter by Stage", ["All"] + STAGES, key="deal_stage_filter")
    if selected_stage != "All":
        deals = deals[deals["stage"] == selected_stage]

    st.dataframe(
        deals, use_container_width=True, hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "estimated_value": st.column_config.NumberColumn("Value ($)", format="$%.0f"),
            "probability_pct": st.column_config.ProgressColumn("Probability", max_value=100),
        },
    )


def _deal_form():
    existing = query_df("SELECT id, title FROM deals ORDER BY title")
    edit_opts = ["New Deal"] + [f"{r['id']}: {r['title']}" for _, r in existing.iterrows()] if not existing.empty else ["New Deal"]
    selection = st.selectbox("Select", edit_opts, key="deal_select")

    editing_id = None
    defaults = {}
    if selection != "New Deal":
        editing_id = int(selection.split(":")[0])
        row = query_df("SELECT * FROM deals WHERE id = ?", (editing_id,))
        if not row.empty:
            defaults = row.iloc[0].to_dict()

    title = st.text_input("Deal Title*", value=defaults.get("title", ""), key="deal_title")
    deal_type = st.selectbox("Deal Type", DEAL_TYPES,
                              index=DEAL_TYPES.index(defaults["deal_type"]) if defaults.get("deal_type") in DEAL_TYPES else 0,
                              key="deal_type")
    stage = st.selectbox("Stage", STAGES,
                          index=STAGES.index(defaults["stage"]) if defaults.get("stage") in STAGES else 0,
                          key="deal_stage")

    companies = query_df("SELECT id, name FROM companies ORDER BY name")
    sites = query_df("SELECT id, name FROM sites ORDER BY name")

    co_opts = {"None": None}
    if not companies.empty:
        co_opts.update({f"{r['id']}: {r['name']}": r["id"] for _, r in companies.iterrows()})
    default_co = "None"
    if defaults.get("company_id"):
        for k, v in co_opts.items():
            if v == defaults["company_id"]:
                default_co = k
                break
    company = st.selectbox("Company", list(co_opts.keys()),
                           index=list(co_opts.keys()).index(default_co), key="deal_co")

    site_opts = {"None": None}
    if not sites.empty:
        site_opts.update({f"{r['id']}: {r['name']}": r["id"] for _, r in sites.iterrows()})
    default_site = "None"
    if defaults.get("site_id"):
        for k, v in site_opts.items():
            if v == defaults["site_id"]:
                default_site = k
                break
    site = st.selectbox("Site", list(site_opts.keys()),
                        index=list(site_opts.keys()).index(default_site), key="deal_site")

    col1, col2 = st.columns(2)
    estimated_value = col1.number_input("Estimated Value ($)", min_value=0.0, step=1e5,
                                         value=float(defaults.get("estimated_value") or 0), key="deal_val")
    probability = col2.slider("Probability %", 0, 100,
                               value=int(defaults.get("probability_pct") or 50), key="deal_prob")

    lead_contact = st.text_input("Lead Contact", value=defaults.get("lead_contact", "") or "", key="deal_lead")
    next_step = st.text_input("Next Step", value=defaults.get("next_step", "") or "", key="deal_next")
    next_step_date = st.text_input("Next Step Date (YYYY-MM-DD)",
                                    value=defaults.get("next_step_date", "") or "", key="deal_next_date")
    description = st.text_area("Description", value=defaults.get("description", "") or "", key="deal_desc")

    if st.button("Save Deal", key="save_deal"):
        if not title:
            st.error("Deal title is required")
            return
        params = (title, deal_type, stage, co_opts[company], site_opts[site],
                  estimated_value or None, probability, lead_contact or None,
                  next_step or None, next_step_date or None, description or None)
        if editing_id:
            execute(
                """UPDATE deals SET title=?, deal_type=?, stage=?, company_id=?, site_id=?,
                   estimated_value=?, probability_pct=?, lead_contact=?, next_step=?,
                   next_step_date=?, description=? WHERE id=?""",
                params + (editing_id,),
            )
            st.success(f"Deal '{title}' updated")
        else:
            execute(
                """INSERT INTO deals (title, deal_type, stage, company_id, site_id,
                   estimated_value, probability_pct, lead_contact, next_step,
                   next_step_date, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                params,
            )
            st.success(f"Deal '{title}' created")
        st.rerun()
