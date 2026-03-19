"""
Notion Database Setup — Creates all StockPulse databases in Notion.

Uses the official notion-client SDK to programmatically create the
5 databases with proper schemas, then stores their IDs for later use.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from notion_client import Client

from stockpulse.config import (
    NOTION_TOKEN,
    NOTION_PARENT_PAGE_ID,
    PROJECT_ROOT,
    DB_STOCKS_MASTER,
    DB_DAILY_PRICES,
    DB_SCREENER,
    DB_WATCHLIST,
    DB_REPORTS,
)

logger = logging.getLogger(__name__)

DB_IDS_FILE = PROJECT_ROOT / "notion_db_ids.json"


# Title property name + non-title property schema per data source.
SCHEMAS: dict[str, dict[str, Any]] = {
    "stocks_master": {
        "title": "Symbol",
        "properties": {
            "BSE Code": {"number": {"format": "number"}},
            "ISIN": {"rich_text": {}},
            "Industry": {"select": {"options": []}},
            "Group": {"select": {"options": [
                {"name": "A", "color": "green"},
                {"name": "B", "color": "blue"},
                {"name": "T", "color": "orange"},
            ]}},
            "CMP": {"number": {"format": "rupee"}},
            "Market Cap (Cr)": {"number": {"format": "number"}},
            "PE": {"number": {"format": "number"}},
            "EPS": {"number": {"format": "number"}},
            "Sales Qrt (Cr)": {"number": {"format": "number"}},
            "NP Qrt (Cr)": {"number": {"format": "number"}},
            "Sales Var %": {"number": {"format": "percent"}},
            "Profit Var %": {"number": {"format": "percent"}},
            "Debt/Equity": {"number": {"format": "number"}},
            "Current Ratio": {"number": {"format": "number"}},
            "ROCE %": {"number": {"format": "percent"}},
            "ROE %": {"number": {"format": "percent"}},
            "Promoter Hold %": {"number": {"format": "percent"}},
            "Pledged %": {"number": {"format": "percent"}},
            "Unpledged Promo %": {"number": {"format": "percent"}},
            "Ch Promo Hold %": {"number": {"format": "percent"}},
            "FII Hold %": {"number": {"format": "percent"}},
            "DII Hold %": {"number": {"format": "percent"}},
            "Piotroski Score": {"number": {"format": "number"}},
            "Passes Screen": {"checkbox": {}},
            "Screen Score": {"number": {"format": "number"}},
            "AI Rating": {"select": {"options": [
                {"name": "Strong Buy", "color": "green"},
                {"name": "Buy", "color": "blue"},
                {"name": "Hold", "color": "yellow"},
                {"name": "Avoid", "color": "red"},
            ]}},
            "Last Updated": {"date": {}},
        },
    },
    "daily_prices": {
        "title": "Entry",
        "properties": {
            "Date": {"date": {}},
            "Open": {"number": {"format": "rupee"}},
            "High": {"number": {"format": "rupee"}},
            "Low": {"number": {"format": "rupee"}},
            "Close": {"number": {"format": "rupee"}},
            "Prev Close": {"number": {"format": "rupee"}},
            "Volume": {"number": {"format": "number"}},
            "Delivery Qty": {"number": {"format": "number"}},
            "Delivery %": {"number": {"format": "percent"}},
            "Turnover (Cr)": {"number": {"format": "number"}},
            "Total Trades": {"number": {"format": "number"}},
            "Stock": {"relation": {"data_source_id": "<stocks_master_data_source_id>", "single_property": {}}},
        },
    },
    "screener": {
        "title": "Stock",
        "properties": {
            "Stock Link": {"relation": {"data_source_id": "<stocks_master_data_source_id>", "single_property": {}}},
            "Screen Date": {"date": {}},
            "Conditions Met": {"number": {"format": "number"}},
            "Score": {"number": {"format": "number"}},
            "Passes": {"checkbox": {}},
            "Failed Conditions": {"rich_text": {}},
            "AI Commentary": {"rich_text": {}},
        },
    },
    "watchlist": {
        "title": "Stock",
        "properties": {
            "Stock Link": {"relation": {"data_source_id": "<stocks_master_data_source_id>", "single_property": {}}},
            "Added Date": {"date": {}},
            "User Notes": {"rich_text": {}},
            "AI Alerts": {"rich_text": {}},
            "Status": {"select": {"options": [
                {"name": "Watching", "color": "blue"},
                {"name": "Entered", "color": "green"},
                {"name": "Exited", "color": "gray"},
                {"name": "Alerted", "color": "red"},
            ]}},
        },
    },
    "reports": {
        "title": "Title",
        "properties": {
            "Report Type": {"select": {"options": [
                {"name": "Stock Analysis", "color": "blue"},
                {"name": "Weekly Summary", "color": "green"},
                {"name": "Sector Report", "color": "purple"},
                {"name": "Anomaly Alert", "color": "red"},
                {"name": "Screener Report", "color": "yellow"},
            ]}},
            "Date": {"date": {}},
            "Symbols Covered": {"rich_text": {}},
        },
    },
}


def get_client() -> Client:
    """Create and return a Notion client."""
    if not NOTION_TOKEN:
        raise ValueError(
            "NOTION_TOKEN not set. Create an integration at "
            "https://www.notion.so/my-integrations and add the token to .env"
        )
    return Client(auth=NOTION_TOKEN)


def _rate_limit_pause():
    """Pause to respect Notion's 3 req/sec rate limit."""
    time.sleep(0.4)


def save_db_ids(db_ids: dict):
    """Save database IDs to a JSON file for later use."""
    DB_IDS_FILE.write_text(json.dumps(db_ids, indent=2))
    logger.info("Database IDs saved to %s", DB_IDS_FILE)


def load_db_ids() -> dict:
    """Load saved database IDs."""
    if DB_IDS_FILE.exists():
        return json.loads(DB_IDS_FILE.read_text())
    return {}


def create_stocks_master_db(client: Client, parent_id: str) -> str:
    """Create the Stocks Master database."""
    logger.info("Creating database: %s", DB_STOCKS_MASTER)

    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_id},
        title=[{"type": "text", "text": {"content": DB_STOCKS_MASTER}}],
        properties={
            "Symbol": {"title": {}},
            "BSE Code": {"number": {"format": "number"}},
            "ISIN": {"rich_text": {}},
            "Industry": {"select": {"options": []}},
            "Group": {"select": {"options": [
                {"name": "A", "color": "green"},
                {"name": "B", "color": "blue"},
                {"name": "T", "color": "orange"},
            ]}},
            "CMP": {"number": {"format": "rupee"}},
            "Market Cap (Cr)": {"number": {"format": "number"}},
            "PE": {"number": {"format": "number"}},
            "EPS": {"number": {"format": "number"}},
            "Sales Qrt (Cr)": {"number": {"format": "number"}},
            "NP Qrt (Cr)": {"number": {"format": "number"}},
            "Sales Var %": {"number": {"format": "percent"}},
            "Profit Var %": {"number": {"format": "percent"}},
            "Debt/Equity": {"number": {"format": "number"}},
            "Current Ratio": {"number": {"format": "number"}},
            "ROCE %": {"number": {"format": "percent"}},
            "ROE %": {"number": {"format": "percent"}},
            "Promoter Hold %": {"number": {"format": "percent"}},
            "Pledged %": {"number": {"format": "percent"}},
            "Unpledged Promo %": {"number": {"format": "percent"}},
            "Ch Promo Hold %": {"number": {"format": "percent"}},
            "FII Hold %": {"number": {"format": "percent"}},
            "DII Hold %": {"number": {"format": "percent"}},
            "Piotroski Score": {"number": {"format": "number"}},
            "Passes Screen": {"checkbox": {}},
            "Screen Score": {"number": {"format": "number"}},
            "AI Rating": {"select": {"options": [
                {"name": "Strong Buy", "color": "green"},
                {"name": "Buy", "color": "blue"},
                {"name": "Hold", "color": "yellow"},
                {"name": "Avoid", "color": "red"},
            ]}},
            "Last Updated": {"date": {}},
        },
    )
    logger.info("Created %s → %s", DB_STOCKS_MASTER, db["id"])
    return db["id"]


def create_daily_prices_db(
    client: Client, parent_id: str, stocks_db_id: str
) -> str:
    """Create the Daily Prices database."""
    logger.info("Creating database: %s", DB_DAILY_PRICES)

    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_id},
        title=[{"type": "text", "text": {"content": DB_DAILY_PRICES}}],
        properties={
            "Entry": {"title": {}},
            "Stock": {"relation": {"database_id": stocks_db_id, "single_property": {}}},
            "Date": {"date": {}},
            "Open": {"number": {"format": "rupee"}},
            "High": {"number": {"format": "rupee"}},
            "Low": {"number": {"format": "rupee"}},
            "Close": {"number": {"format": "rupee"}},
            "Prev Close": {"number": {"format": "rupee"}},
            "Volume": {"number": {"format": "number"}},
            "Delivery Qty": {"number": {"format": "number"}},
            "Delivery %": {"number": {"format": "percent"}},
            "Turnover (Cr)": {"number": {"format": "number"}},
            "Total Trades": {"number": {"format": "number"}},
        },
    )
    logger.info("Created %s → %s", DB_DAILY_PRICES, db["id"])
    return db["id"]


def create_screener_db(
    client: Client, parent_id: str, stocks_db_id: str
) -> str:
    """Create the Screener Results database."""
    logger.info("Creating database: %s", DB_SCREENER)

    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_id},
        title=[{"type": "text", "text": {"content": DB_SCREENER}}],
        properties={
            "Stock": {"title": {}},
            "Stock Link": {"relation": {"database_id": stocks_db_id, "single_property": {}}},
            "Screen Date": {"date": {}},
            "Conditions Met": {"number": {"format": "number"}},
            "Score": {"number": {"format": "number"}},
            "Passes": {"checkbox": {}},
            "Failed Conditions": {"rich_text": {}},
            "AI Commentary": {"rich_text": {}},
        },
    )
    logger.info("Created %s → %s", DB_SCREENER, db["id"])
    return db["id"]


def create_watchlist_db(
    client: Client, parent_id: str, stocks_db_id: str
) -> str:
    """Create the Watchlist database."""
    logger.info("Creating database: %s", DB_WATCHLIST)

    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_id},
        title=[{"type": "text", "text": {"content": DB_WATCHLIST}}],
        properties={
            "Stock": {"title": {}},
            "Stock Link": {"relation": {"database_id": stocks_db_id, "single_property": {}}},
            "Added Date": {"date": {}},
            "User Notes": {"rich_text": {}},
            "AI Alerts": {"rich_text": {}},
            "Status": {"select": {"options": [
                {"name": "Watching", "color": "blue"},
                {"name": "Entered", "color": "green"},
                {"name": "Exited", "color": "gray"},
                {"name": "Alerted", "color": "red"},
            ]}},
        },
    )
    logger.info("Created %s → %s", DB_WATCHLIST, db["id"])
    return db["id"]


def create_reports_db(client: Client, parent_id: str) -> str:
    """Create the AI Reports database."""
    logger.info("Creating database: %s", DB_REPORTS)

    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_id},
        title=[{"type": "text", "text": {"content": DB_REPORTS}}],
        properties={
            "Title": {"title": {}},
            "Report Type": {"select": {"options": [
                {"name": "Stock Analysis", "color": "blue"},
                {"name": "Weekly Summary", "color": "green"},
                {"name": "Sector Report", "color": "purple"},
                {"name": "Anomaly Alert", "color": "red"},
                {"name": "Screener Report", "color": "yellow"},
            ]}},
            "Date": {"date": {}},
            "Symbols Covered": {"rich_text": {}},
        },
    )
    logger.info("Created %s → %s", DB_REPORTS, db["id"])
    return db["id"]


def setup_all_databases() -> dict:
    """Create all 5 databases and return their IDs.

    Returns dict like:
        {
            "stocks_master": "xxx",
            "daily_prices": "xxx",
            "screener": "xxx",
            "watchlist": "xxx",
            "reports": "xxx",
        }
    """
    client = get_client()
    parent_id = NOTION_PARENT_PAGE_ID

    if not parent_id:
        raise ValueError(
            "NOTION_PARENT_PAGE_ID not set. Create a page in Notion, "
            "copy its ID from the URL, and add it to .env"
        )

    # Create in order (some depend on stocks_master)
    stocks_id = create_stocks_master_db(client, parent_id)
    _rate_limit_pause()

    prices_id = create_daily_prices_db(client, parent_id, stocks_id)
    _rate_limit_pause()

    screener_id = create_screener_db(client, parent_id, stocks_id)
    _rate_limit_pause()

    watchlist_id = create_watchlist_db(client, parent_id, stocks_id)
    _rate_limit_pause()

    reports_id = create_reports_db(client, parent_id)

    db_ids = {
        "stocks_master": stocks_id,
        "daily_prices": prices_id,
        "screener": screener_id,
        "watchlist": watchlist_id,
        "reports": reports_id,
    }

    ensure_all_db_schemas(db_ids)

    save_db_ids(db_ids)
    return db_ids


def _get_data_source_id(client: Client, database_id: str) -> str:
    """Resolve database ID to its primary data source ID."""
    db = client.databases.retrieve(database_id=database_id)
    ds = db.get("data_sources", [])
    if not ds:
        raise ValueError(f"No data source attached to database {database_id}")
    return ds[0]["id"]


def _ensure_title_name(client: Client, data_source_id: str, title_name: str):
    """Ensure the title property exists with the requested name."""
    ds = client.data_sources.retrieve(data_source_id=data_source_id)
    props = ds.get("properties", {}) or {}
    if title_name in props and props[title_name].get("type") == "title":
        return

    existing_title = None
    for name, meta in props.items():
        if meta.get("type") == "title":
            existing_title = name
            break

    # New data sources start with a default "Name" title prop.
    rename_from = existing_title or "Name"
    client.data_sources.update(
        data_source_id=data_source_id,
        properties={rename_from: {"name": title_name}},
    )
    _rate_limit_pause()


def _ensure_non_title_properties(
    client: Client,
    data_source_id: str,
    properties: dict[str, Any],
):
    """Create missing non-title properties on a data source."""
    ds = client.data_sources.retrieve(data_source_id=data_source_id)
    existing = set((ds.get("properties") or {}).keys())
    missing = {k: v for k, v in properties.items() if k not in existing}
    if not missing:
        return

    # Notion handles multiple creates in one update call.
    client.data_sources.update(data_source_id=data_source_id, properties=missing)
    _rate_limit_pause()


def ensure_all_db_schemas(db_ids: dict | None = None) -> dict[str, str]:
    """Ensure all data source schemas match expected StockPulse properties.

    Returns mapping of db-key -> data_source_id.
    """
    client = get_client()
    db_ids = db_ids or load_db_ids()
    if not db_ids:
        raise ValueError("No database IDs found. Run setup first.")

    stocks_db_id = db_ids.get("stocks_master")
    if not stocks_db_id:
        raise ValueError("stocks_master database ID missing.")

    stocks_data_source_id = _get_data_source_id(client, stocks_db_id)

    data_source_ids: dict[str, str] = {}

    for key, schema in SCHEMAS.items():
        db_id = db_ids.get(key)
        if not db_id:
            continue

        ds_id = _get_data_source_id(client, db_id)
        data_source_ids[key] = ds_id

        title_name = schema["title"]
        non_title_props = dict(schema["properties"])

        # Resolve relation targets for non-master DBs at runtime.
        for prop_name, spec in list(non_title_props.items()):
            relation = spec.get("relation") if isinstance(spec, dict) else None
            if relation and relation.get("data_source_id") == "<stocks_master_data_source_id>":
                relation["data_source_id"] = stocks_data_source_id

        _ensure_title_name(client, ds_id, title_name)
        _ensure_non_title_properties(client, ds_id, non_title_props)
        logger.info("Schema ensured for %s (data_source_id=%s)", key, ds_id)

    return data_source_ids
