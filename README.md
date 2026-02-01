# Nuclear Asset Database

A proprietary database and dashboard for tracking US nuclear power sites, reactors, service companies, contracts, regulatory events, and market activity.

## Features

- **SQLite database** with 19 tables covering sites, reactors, companies, contracts, decommissioning trust funds, regulatory/market events, SMR projects, deal pipeline, commodity prices, and more
- **Data ingestion scripts** pulling from NRC, USAspending.gov, NRC ADAMS, and uranium price sources
- **Streamlit dashboard** with 9 pages: home dashboard, sites explorer, companies explorer, SMR project tracker, deal pipeline, commodity prices, global search, data entry forms, and Excel export
- **REST API** (Flask) with 12 endpoints, pagination, filtering, and optional API key auth
- **Automated scheduler** with weekly ingestion, diff detection, and email/Slack/log notifications
- **Excel export** for deal memos and reporting

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database (auto-creates on first run)
python scripts/ingest_nrc_reactors.py

# Launch dashboard
cd app && streamlit run streamlit_app.py

# Launch REST API
python app/api.py
```

## Project Structure

```
nuclear-database/
├── database/
│   ├── schema.sql              # Core schema (10 tables)
│   ├── seed_data.sql           # Service categories (53 entries)
│   └── migrations/             # Incremental migrations
├── scripts/
│   ├── ingest_nrc_reactors.py  # NRC operating reactor data
│   ├── ingest_decommissioning.py # NRC decommissioning sites
│   ├── ingest_usaspending.py   # Federal nuclear contracts
│   ├── ingest_trust_funds.py   # Decommissioning trust fund data
│   ├── ingest_nrc_events.py    # NRC press releases / RSS
│   ├── ingest_uranium_prices.py # U3O8/SWU spot prices
│   ├── ingest_adams.py         # NRC ADAMS document search
│   ├── export_excel.py         # Excel workbook export
│   ├── scheduler.py            # Automated ingestion runner
│   ├── diff_detector.py        # Change detection
│   ├── notifier.py             # Email/Slack/log alerts
│   ├── run_logger.py           # Script execution logging
│   └── db_utils.py             # Shared DB utilities
├── app/
│   ├── streamlit_app.py        # Dashboard entry point
│   ├── api.py                  # REST API (Flask)
│   ├── pages/                  # Streamlit pages
│   └── components/             # Shared UI helpers
├── config/
│   └── settings.py             # Centralized configuration
├── requirements.txt
├── .env.example
└── .gitignore
```

## Ingestion Scripts

Each script runs independently and supports upsert (duplicate handling):

```bash
python scripts/ingest_nrc_reactors.py    # Operating reactors
python scripts/ingest_decommissioning.py # Decommissioning sites
python scripts/ingest_usaspending.py     # Federal contracts
python scripts/ingest_trust_funds.py     # Trust fund balances
python scripts/ingest_nrc_events.py      # Regulatory events
python scripts/ingest_uranium_prices.py  # Commodity prices
python scripts/ingest_adams.py           # ADAMS documents
```

Run all scripts at once with change detection:

```bash
python scripts/scheduler.py              # Run once
python scripts/scheduler.py --daemon     # Run on weekly schedule
```

## REST API

```bash
python app/api.py  # Starts on http://localhost:5000
```

| Endpoint | Description |
|---|---|
| `GET /api/sites` | List sites (?state=, ?site_type=, ?q=) |
| `GET /api/sites/<id>` | Site detail with reactors |
| `GET /api/reactors` | List reactors (?status=, ?reactor_type=) |
| `GET /api/companies` | List companies (?company_type=, ?q=) |
| `GET /api/companies/<id>` | Company detail with services/contracts |
| `GET /api/contracts` | List contracts (?company_id=, ?site_id=) |
| `GET /api/regulatory-events` | Regulatory events (?site_id=, ?event_type=) |
| `GET /api/market-events` | Market events (?event_type=, ?company_id=) |
| `GET /api/smr-projects` | SMR projects |
| `GET /api/deals` | Deal pipeline (?stage=) |
| `GET /api/commodity-prices` | Commodity prices (?commodity=) |
| `GET /api/export` | Download Excel workbook |

All endpoints support `?page=` and `?per_page=` pagination. Set `API_KEY` in `.env` to require `X-API-Key` header.

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings: database path, app password, scheduler interval, notification method (log/email/Slack), API key.

## License

Proprietary. All rights reserved.
