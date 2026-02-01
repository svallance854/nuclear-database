"""Commodity Prices — uranium and SWU price tracking and charts."""
import streamlit as st
from components.db import query_df


def render():
    st.title("Commodity Prices")

    prices = query_df(
        "SELECT * FROM commodity_prices ORDER BY price_date DESC"
    )
    if prices.empty:
        st.info("No price data yet. Run `python scripts/ingest_uranium_prices.py` to fetch prices.")
        return

    # Latest prices
    commodities = prices["commodity"].unique()
    cols = st.columns(len(commodities))
    for i, c in enumerate(commodities):
        latest = prices[prices["commodity"] == c].iloc[0]
        cols[i].metric(
            c,
            f"${latest['price']:.2f}/{latest['unit']}",
            f"as of {latest['price_date']}",
        )

    st.divider()

    # Filter
    selected = st.multiselect("Commodities", commodities.tolist(), default=commodities.tolist())
    filtered = prices[prices["commodity"].isin(selected)]

    # Chart
    if not filtered.empty:
        st.subheader("Price History")
        pivot = filtered.pivot_table(index="price_date", columns="commodity", values="price")
        pivot = pivot.sort_index()
        st.line_chart(pivot)

    # Table
    st.subheader("All Records")
    st.dataframe(filtered, use_container_width=True, hide_index=True,
                 column_config={"price": st.column_config.NumberColumn("Price", format="$%.2f")})
