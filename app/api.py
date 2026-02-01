"""REST API for programmatic access to the Nuclear Asset Database.

Usage:
    python app/api.py

Endpoints:
    GET  /api/sites                  — list sites (supports ?state=, ?site_type=, ?q=)
    GET  /api/sites/<id>             — site detail with reactors
    GET  /api/reactors               — list reactors (supports ?status=, ?reactor_type=, ?q=)
    GET  /api/companies              — list companies (supports ?company_type=, ?q=)
    GET  /api/companies/<id>         — company detail with services and contracts
    GET  /api/contracts              — list contracts (supports ?company_id=, ?site_id=, ?status=)
    GET  /api/regulatory-events      — list events (supports ?site_id=, ?event_type=)
    GET  /api/market-events          — list events (supports ?event_type=, ?company_id=)
    GET  /api/smr-projects           — list SMR projects
    GET  /api/deals                  — list deals (supports ?stage=)
    GET  /api/commodity-prices       — list prices (supports ?commodity=)
    GET  /api/export                 — download Excel export
"""
import os
import sys
import sqlite3
import tempfile
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATABASE_PATH, API_HOST, API_PORT, API_KEY
from scripts.db_utils import init_db

app = Flask(__name__)
CORS(app)


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if API_KEY:
            key = request.headers.get("X-API-Key") or request.args.get("api_key")
            if key != API_KEY:
                abort(401, description="Invalid or missing API key")
        return f(*args, **kwargs)
    return decorated


def paginate(query: str, params: tuple, conn):
    """Add LIMIT/OFFSET pagination to a query."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 100, type=int), 500)
    offset = (page - 1) * per_page

    rows = conn.execute(f"{query} LIMIT ? OFFSET ?", params + (per_page, offset)).fetchall()
    total = conn.execute(
        f"SELECT COUNT(*) FROM ({query})", params
    ).fetchone()[0]

    return {
        "data": rows_to_dicts(rows),
        "page": page,
        "per_page": per_page,
        "total": total,
    }


# --- Sites ---

@app.route("/api/sites")
@require_api_key
def list_sites():
    conn = get_db()
    conditions, params = [], []
    if q := request.args.get("q"):
        conditions.append("name LIKE ?")
        params.append(f"%{q}%")
    if v := request.args.get("state"):
        conditions.append("state = ?")
        params.append(v)
    if v := request.args.get("site_type"):
        conditions.append("site_type = ?")
        params.append(v)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    result = paginate(f"SELECT * FROM sites{where} ORDER BY name", tuple(params), conn)
    conn.close()
    return jsonify(result)


@app.route("/api/sites/<int:site_id>")
@require_api_key
def get_site(site_id):
    conn = get_db()
    site = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
    if not site:
        abort(404)
    reactors = conn.execute("SELECT * FROM reactors WHERE site_id = ?", (site_id,)).fetchall()
    conn.close()
    data = dict(site)
    data["reactors"] = rows_to_dicts(reactors)
    return jsonify(data)


# --- Reactors ---

@app.route("/api/reactors")
@require_api_key
def list_reactors():
    conn = get_db()
    conditions, params = [], []
    if q := request.args.get("q"):
        conditions.append("r.name LIKE ?")
        params.append(f"%{q}%")
    if v := request.args.get("status"):
        conditions.append("r.status = ?")
        params.append(v)
    if v := request.args.get("reactor_type"):
        conditions.append("r.reactor_type = ?")
        params.append(v)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"SELECT r.*, s.name as site_name FROM reactors r JOIN sites s ON r.site_id = s.id{where} ORDER BY s.name, r.unit_number"
    result = paginate(query, tuple(params), conn)
    conn.close()
    return jsonify(result)


# --- Companies ---

@app.route("/api/companies")
@require_api_key
def list_companies():
    conn = get_db()
    conditions, params = [], []
    if q := request.args.get("q"):
        conditions.append("name LIKE ?")
        params.append(f"%{q}%")
    if v := request.args.get("company_type"):
        conditions.append("company_type = ?")
        params.append(v)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    result = paginate(f"SELECT * FROM companies{where} ORDER BY name", tuple(params), conn)
    conn.close()
    return jsonify(result)


@app.route("/api/companies/<int:company_id>")
@require_api_key
def get_company(company_id):
    conn = get_db()
    company = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    if not company:
        abort(404)
    services = conn.execute(
        """SELECT sc.name as category, cs.details
           FROM company_services cs JOIN service_categories sc ON sc.id = cs.category_id
           WHERE cs.company_id = ?""", (company_id,)
    ).fetchall()
    contracts = conn.execute(
        """SELECT ct.*, s.name as site_name FROM contracts ct
           JOIN sites s ON ct.site_id = s.id WHERE ct.company_id = ?""", (company_id,)
    ).fetchall()
    conn.close()
    data = dict(company)
    data["services"] = rows_to_dicts(services)
    data["contracts"] = rows_to_dicts(contracts)
    return jsonify(data)


# --- Contracts ---

@app.route("/api/contracts")
@require_api_key
def list_contracts():
    conn = get_db()
    conditions, params = [], []
    if v := request.args.get("company_id"):
        conditions.append("ct.company_id = ?")
        params.append(int(v))
    if v := request.args.get("site_id"):
        conditions.append("ct.site_id = ?")
        params.append(int(v))
    if v := request.args.get("status"):
        conditions.append("ct.status = ?")
        params.append(v)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""SELECT ct.*, c.name as company_name, s.name as site_name
                FROM contracts ct
                JOIN companies c ON ct.company_id = c.id
                JOIN sites s ON ct.site_id = s.id{where}
                ORDER BY ct.start_date DESC"""
    result = paginate(query, tuple(params), conn)
    conn.close()
    return jsonify(result)


# --- Events ---

@app.route("/api/regulatory-events")
@require_api_key
def list_regulatory_events():
    conn = get_db()
    conditions, params = [], []
    if v := request.args.get("site_id"):
        conditions.append("site_id = ?")
        params.append(int(v))
    if v := request.args.get("event_type"):
        conditions.append("event_type = ?")
        params.append(v)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    result = paginate(f"SELECT * FROM regulatory_events{where} ORDER BY event_date DESC", tuple(params), conn)
    conn.close()
    return jsonify(result)


@app.route("/api/market-events")
@require_api_key
def list_market_events():
    conn = get_db()
    conditions, params = [], []
    if v := request.args.get("event_type"):
        conditions.append("event_type = ?")
        params.append(v)
    if v := request.args.get("company_id"):
        conditions.append("company_id = ?")
        params.append(int(v))

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    result = paginate(f"SELECT * FROM market_events{where} ORDER BY event_date DESC", tuple(params), conn)
    conn.close()
    return jsonify(result)


# --- SMR Projects ---

@app.route("/api/smr-projects")
@require_api_key
def list_smr_projects():
    conn = get_db()
    query = """SELECT p.*, c.name as developer_name
               FROM smr_projects p LEFT JOIN companies c ON p.developer_id = c.id
               ORDER BY p.name"""
    result = paginate(query, (), conn)
    conn.close()
    return jsonify(result)


# --- Deals ---

@app.route("/api/deals")
@require_api_key
def list_deals():
    conn = get_db()
    conditions, params = [], []
    if v := request.args.get("stage"):
        conditions.append("d.stage = ?")
        params.append(v)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""SELECT d.*, c.name as company_name, s.name as site_name
                FROM deals d
                LEFT JOIN companies c ON d.company_id = c.id
                LEFT JOIN sites s ON d.site_id = s.id{where}
                ORDER BY d.stage, d.title"""
    result = paginate(query, tuple(params), conn)
    conn.close()
    return jsonify(result)


# --- Commodity Prices ---

@app.route("/api/commodity-prices")
@require_api_key
def list_commodity_prices():
    conn = get_db()
    conditions, params = [], []
    if v := request.args.get("commodity"):
        conditions.append("commodity = ?")
        params.append(v)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    result = paginate(f"SELECT * FROM commodity_prices{where} ORDER BY price_date DESC", tuple(params), conn)
    conn.close()
    return jsonify(result)


# --- Excel Export ---

@app.route("/api/export")
@require_api_key
def export_excel():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from export_excel import export

    tmp = tempfile.mktemp(suffix=".xlsx")
    export(output=tmp)
    return send_file(tmp, as_attachment=True, download_name="nuclear_export.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    init_db()
    app.run(host=API_HOST, port=API_PORT, debug=True)
