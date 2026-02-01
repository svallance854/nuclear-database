-- Nuclear Asset Database Schema (SQLite)
PRAGMA foreign_keys = ON;

-- 1. Sites
CREATE TABLE sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    county TEXT,
    latitude REAL,
    longitude REAL,
    site_type TEXT NOT NULL DEFAULT 'operating' CHECK (site_type IN ('operating', 'decommissioning', 'decommissioned', 'proposed', 'cancelled')),
    owner TEXT,
    operator TEXT,
    nrc_site_id TEXT UNIQUE,
    grid_connection TEXT,
    total_capacity_mw REAL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_sites_name ON sites(name);

-- 2. Reactors
CREATE TABLE reactors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    unit_number INTEGER,
    reactor_type TEXT CHECK (reactor_type IN ('PWR', 'BWR', 'SMR', 'HTGR', 'MSR', 'FBR', 'Other')),
    vendor TEXT,
    model TEXT,
    capacity_mw REAL,
    construction_start_date TEXT,
    operating_license_date TEXT,
    commercial_operation_date TEXT,
    license_expiration_date TEXT,
    permanent_shutdown_date TEXT,
    nrc_docket_number TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'operating' CHECK (status IN ('pre-construction', 'under-construction', 'operating', 'extended-outage', 'permanently-shutdown', 'decommissioning', 'decommissioned', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_reactors_nrc_docket ON reactors(nrc_docket_number);

-- 3. Companies
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ticker TEXT,
    company_type TEXT NOT NULL DEFAULT 'other' CHECK (company_type IN ('utility', 'developer', 'contractor', 'vendor', 'consultant', 'government', 'investor', 'other')),
    website TEXT,
    headquarters_state TEXT,
    headquarters_country TEXT DEFAULT 'US',
    description TEXT,
    publicly_traded INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_companies_name ON companies(name);

-- 4. Service Categories
CREATE TABLE service_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES service_categories(id) ON DELETE SET NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- 5. Company Services
CREATE TABLE company_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES service_categories(id) ON DELETE CASCADE,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(company_id, category_id)
);

-- 6. Contracts
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    reactor_id INTEGER REFERENCES reactors(id) ON DELETE SET NULL,
    category_id INTEGER REFERENCES service_categories(id) ON DELETE SET NULL,
    contract_type TEXT CHECK (contract_type IN ('construction', 'operations', 'maintenance', 'fuel', 'decommissioning', 'consulting', 'licensing', 'other')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('proposed', 'negotiating', 'active', 'completed', 'terminated', 'expired')),
    value REAL,
    currency TEXT DEFAULT 'USD',
    start_date TEXT,
    end_date TEXT,
    description TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_contracts_company ON contracts(company_id);
CREATE INDEX idx_contracts_site ON contracts(site_id);

-- 7. Decommissioning Trust Funds
CREATE TABLE decommissioning_trust_funds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    reactor_id INTEGER REFERENCES reactors(id) ON DELETE SET NULL,
    fund_balance REAL,
    estimated_cost REAL,
    report_date TEXT,
    source TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- 8. Regulatory Events
CREATE TABLE regulatory_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER REFERENCES sites(id) ON DELETE SET NULL,
    reactor_id INTEGER REFERENCES reactors(id) ON DELETE SET NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('license-renewal', 'license-amendment', 'inspection', 'enforcement', 'exemption', 'rulemaking', 'hearing', 'other')),
    title TEXT NOT NULL,
    description TEXT,
    event_date TEXT,
    nrc_document_id TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- 9. Market Events
CREATE TABLE market_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('ppa', 'acquisition', 'investment', 'ipo', 'policy', 'legislation', 'market-report', 'other')),
    description TEXT,
    event_date TEXT,
    site_id INTEGER REFERENCES sites(id) ON DELETE SET NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    financial_value REAL,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- 10. Notes
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('site', 'reactor', 'company', 'contract', 'regulatory_event', 'market_event')),
    entity_id INTEGER NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Updated_at triggers
CREATE TRIGGER sites_updated_at AFTER UPDATE ON sites
BEGIN UPDATE sites SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER reactors_updated_at AFTER UPDATE ON reactors
BEGIN UPDATE reactors SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER companies_updated_at AFTER UPDATE ON companies
BEGIN UPDATE companies SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER service_categories_updated_at AFTER UPDATE ON service_categories
BEGIN UPDATE service_categories SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER contracts_updated_at AFTER UPDATE ON contracts
BEGIN UPDATE contracts SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER decommissioning_trust_funds_updated_at AFTER UPDATE ON decommissioning_trust_funds
BEGIN UPDATE decommissioning_trust_funds SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER regulatory_events_updated_at AFTER UPDATE ON regulatory_events
BEGIN UPDATE regulatory_events SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER market_events_updated_at AFTER UPDATE ON market_events
BEGIN UPDATE market_events SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;

CREATE TRIGGER notes_updated_at AFTER UPDATE ON notes
BEGIN UPDATE notes SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = NEW.id; END;
