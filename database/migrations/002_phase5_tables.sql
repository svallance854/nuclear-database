-- Migration 002: Phase 5 tables — commodity prices, SMR projects, deal pipeline, company financials

-- Commodity prices (uranium, SWU, etc.)
CREATE TABLE IF NOT EXISTS commodity_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commodity TEXT NOT NULL CHECK (commodity IN ('U3O8', 'UF6', 'SWU', 'enriched_uranium', 'other')),
    price REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    unit TEXT NOT NULL DEFAULT 'lb',
    price_date TEXT NOT NULL,
    source TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_commodity_prices_date ON commodity_prices(commodity, price_date);

-- SMR projects with milestone tracking
CREATE TABLE IF NOT EXISTS smr_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    developer_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    site_id INTEGER REFERENCES sites(id) ON DELETE SET NULL,
    reactor_design TEXT,
    capacity_mw REAL,
    num_modules INTEGER,
    status TEXT NOT NULL DEFAULT 'announced' CHECK (status IN ('announced', 'pre-application', 'under-review', 'approved', 'under-construction', 'operating', 'cancelled', 'suspended')),
    target_operation_date TEXT,
    estimated_cost REAL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS smr_milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES smr_projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    milestone_type TEXT NOT NULL CHECK (milestone_type IN ('regulatory', 'construction', 'financial', 'technical', 'other')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in-progress', 'completed', 'delayed', 'cancelled')),
    target_date TEXT,
    actual_date TEXT,
    description TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Deal pipeline
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    deal_type TEXT NOT NULL CHECK (deal_type IN ('acquisition', 'investment', 'ppa', 'joint-venture', 'licensing', 'development', 'other')),
    stage TEXT NOT NULL DEFAULT 'identified' CHECK (stage IN ('identified', 'preliminary', 'due-diligence', 'negotiation', 'closed', 'dead')),
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    site_id INTEGER REFERENCES sites(id) ON DELETE SET NULL,
    smr_project_id INTEGER REFERENCES smr_projects(id) ON DELETE SET NULL,
    estimated_value REAL,
    currency TEXT DEFAULT 'USD',
    probability_pct INTEGER CHECK (probability_pct BETWEEN 0 AND 100),
    lead_contact TEXT,
    next_step TEXT,
    next_step_date TEXT,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Company financials
CREATE TABLE IF NOT EXISTS company_financials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER CHECK (fiscal_quarter IN (1, 2, 3, 4)),
    revenue REAL,
    net_income REAL,
    total_assets REAL,
    total_debt REAL,
    market_cap REAL,
    employees INTEGER,
    source TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(company_id, fiscal_year, fiscal_quarter)
);

-- NRC ADAMS documents
CREATE TABLE IF NOT EXISTS adams_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accession_number TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    document_date TEXT,
    docket_number TEXT,
    document_type TEXT,
    site_id INTEGER REFERENCES sites(id) ON DELETE SET NULL,
    reactor_id INTEGER REFERENCES reactors(id) ON DELETE SET NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    adams_url TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_adams_accession ON adams_documents(accession_number);
CREATE INDEX IF NOT EXISTS idx_adams_docket ON adams_documents(docket_number);

-- Triggers
CREATE TRIGGER IF NOT EXISTS smr_projects_updated_at AFTER UPDATE ON smr_projects
BEGIN UPDATE smr_projects SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS smr_milestones_updated_at AFTER UPDATE ON smr_milestones
BEGIN UPDATE smr_milestones SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS deals_updated_at AFTER UPDATE ON deals
BEGIN UPDATE deals SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;
