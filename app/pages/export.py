"""Excel Export page — generate and download Excel workbook from the dashboard."""
import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def render():
    st.title("Export to Excel")
    st.write("Generate an Excel workbook with all database tables for deal memos and reporting.")

    from scripts.export_excel import EXPORTABLE_TABLES

    available = list(EXPORTABLE_TABLES.keys())
    selected = st.multiselect("Tables to export", available, default=available)

    if st.button("Generate Excel Export"):
        if not selected:
            st.warning("Select at least one table.")
            return

        with st.spinner("Generating..."):
            from scripts.export_excel import export
            tmp = tempfile.mktemp(suffix=".xlsx")
            export(tables=selected, output=tmp)

            with open(tmp, "rb") as f:
                data = f.read()

            import os
            os.unlink(tmp)

        st.download_button(
            label="Download nuclear_export.xlsx",
            data=data,
            file_name="nuclear_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
