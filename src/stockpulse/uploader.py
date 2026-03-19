"""
Notion Data Uploader — Uploads stock data to Notion databases.

Handles rate limiting, batching, and maps DataFrame rows to Notion page properties.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime

import pandas as pd
from notion_client import Client

from stockpulse.notion_setup import (
    get_client,
    load_db_ids,
    _rate_limit_pause,
    ensure_all_db_schemas,
)

logger = logging.getLogger(__name__)


def _resolve_data_source_id(key: str) -> str:
    """Return data_source_id for a logical DB key after ensuring schemas."""
    ds_ids = ensure_all_db_schemas()
    ds_id = ds_ids.get(key)
    if not ds_id:
        raise ValueError(f"{key} data source ID not found. Run setup first.")
    return ds_id


def _safe_float(val) -> float | None:
    """Convert to float, return None if not possible."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    if isinstance(val, str) and val.strip() in ("NIL", "", "-"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_str(val) -> str:
    """Convert to string safely."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    return str(val).strip()


def _number_prop(val) -> dict | None:
    """Create a Notion number property."""
    v = _safe_float(val)
    if v is None:
        return None
    return {"number": v}


def _pct_prop(val) -> dict | None:
    """Create a Notion number property for percentage (store as decimal)."""
    v = _safe_float(val)
    if v is None:
        return None
    return {"number": round(v / 100, 4)}


def _date_prop(val) -> dict | None:
    """Create a Notion date property."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return {"date": {"start": val.strftime("%Y-%m-%d")}}
    if isinstance(val, pd.Timestamp):
        return {"date": {"start": val.strftime("%Y-%m-%d")}}
    if isinstance(val, str):
        return {"date": {"start": val[:10]}}
    return None


def _title_prop(val) -> dict:
    """Create a Notion title property."""
    return {"title": [{"text": {"content": _safe_str(val)[:100]}}]}


def _rich_text_prop(val) -> dict:
    """Create a Notion rich_text property."""
    text = _safe_str(val)[:2000]
    return {"rich_text": [{"text": {"content": text}}]} if text else {"rich_text": []}


def _select_prop(val) -> dict | None:
    """Create a Notion select property."""
    v = _safe_str(val)
    if not v:
        return None
    return {"select": {"name": v[:100]}}


def _checkbox_prop(val) -> dict:
    """Create a Notion checkbox property."""
    return {"checkbox": bool(val)}


def _relation_prop(page_id: str) -> dict:
    """Create a Notion relation property."""
    return {"relation": [{"id": page_id}]}


# ---------------------------------------------------------------------------
# Upload Stocks Master
# ---------------------------------------------------------------------------

def upload_stocks_master(
    df: pd.DataFrame,
    screen_results: pd.DataFrame | None = None,
) -> dict[str, str]:
    """Upload stocks master data to Notion.

    Returns a mapping of symbol → Notion page_id for relation linking.
    """
    client = get_client()
    data_source_id = _resolve_data_source_id("stocks_master")

    # Merge screening results if provided
    if screen_results is not None and not screen_results.empty:
        screen_results = screen_results.drop_duplicates(subset=["symbol"], keep="first")
        df = df.merge(
            screen_results[["symbol", "passes_screen", "score", "conditions_met"]],
            on="symbol",
            how="left",
        )

    symbol_to_page = {}
    total = len(df)
    logger.info("Uploading %d stocks to Stocks Master ...", total)

    for idx, (_, row) in enumerate(df.iterrows()):
        symbol = _safe_str(row.get("symbol") or row.get("bse_id", ""))
        if not symbol:
            continue

        props = {"Symbol": _title_prop(symbol)}

        # Map DataFrame columns to Notion properties
        field_map = {
            "BSE Code": ("bse_code", _number_prop),
            "ISIN": ("isin", _rich_text_prop),
            "Industry": ("industry", _select_prop),
            "Group": ("group", _select_prop),
            "CMP": ("cmp", _number_prop),
            "Market Cap (Cr)": ("market_cap_cr", _number_prop),
            "PE": ("pe", _number_prop),
            "EPS": ("eps", _number_prop),
            "Sales Qrt (Cr)": ("sales_qrt", _number_prop),
            "NP Qrt (Cr)": ("np_qrt", _number_prop),
            "Sales Var %": ("sales_var_pct", _pct_prop),
            "Profit Var %": ("profit_var_pct", _pct_prop),
            "Debt/Equity": ("debt_eq_ratio", _number_prop),
            "Current Ratio": ("current_ratio", _number_prop),
            "ROCE %": ("roce_pct", _pct_prop),
            "ROE %": ("roe_pct", _pct_prop),
            "Promoter Hold %": ("promoter_hold_pct", _pct_prop),
            "Pledged %": ("pledged_pct", _pct_prop),
            "Unpledged Promo %": ("unpledged_promo_pct", _pct_prop),
            "Ch Promo Hold %": ("ch_promo_hold_pct", _pct_prop),
            "FII Hold %": ("fii_hold_pct", _pct_prop),
            "DII Hold %": ("dii_hold_pct", _pct_prop),
            "Piotroski Score": ("piotroski_score", _number_prop),
        }

        for notion_key, (df_col, converter) in field_map.items():
            val = row.get(df_col)
            converted = converter(val)
            if converted is not None:
                props[notion_key] = converted

        # Screening results
        if "passes_screen" in row:
            props["Passes Screen"] = _checkbox_prop(row.get("passes_screen", False))
        if "score" in row:
            score_val = _number_prop(row.get("score"))
            if score_val:
                props["Screen Score"] = score_val

        # Last Updated
        props["Last Updated"] = {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}

        try:
            page = client.pages.create(
                parent={"data_source_id": data_source_id},
                properties=props,
            )
            symbol_to_page[symbol] = page["id"]

            if (idx + 1) % 50 == 0:
                logger.info("  Uploaded %d/%d stocks", idx + 1, total)
            _rate_limit_pause()

        except Exception as e:
            logger.error("Failed to upload %s: %s", symbol, e)

    logger.info("Uploaded %d/%d stocks to Notion", len(symbol_to_page), total)
    return symbol_to_page


# ---------------------------------------------------------------------------
# Upload Daily Prices
# ---------------------------------------------------------------------------

def upload_daily_prices(
    df: pd.DataFrame,
    symbol_to_page: dict[str, str],
) -> int:
    """Upload daily price data to Notion.

    Returns count of successfully uploaded rows.
    """
    client = get_client()
    data_source_id = _resolve_data_source_id("daily_prices")

    uploaded = 0
    total = len(df)
    logger.info("Uploading %d price rows to Daily Prices ...", total)

    for idx, (_, row) in enumerate(df.iterrows()):
        symbol = _safe_str(row.get("symbol", ""))
        date_val = row.get("date")
        if not symbol or date_val is None:
            continue

        date_str = (
            date_val.strftime("%Y-%m-%d")
            if hasattr(date_val, "strftime")
            else str(date_val)[:10]
        )
        entry_name = f"{symbol}-{date_str}"

        props = {
            "Entry": _title_prop(entry_name),
            "Date": {"date": {"start": date_str}},
        }

        # Link to stock if we have the page ID
        stock_page_id = symbol_to_page.get(symbol)
        if stock_page_id:
            props["Stock"] = _relation_prop(stock_page_id)

        price_map = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Prev Close": "prev_close",
            "Volume": "volume",
            "Delivery Qty": "delivery_qty",
            "Turnover (Cr)": "turnover_cr",
            "Total Trades": "total_trades",
        }

        for notion_key, df_col in price_map.items():
            val = _number_prop(row.get(df_col))
            if val:
                props[notion_key] = val

        # Delivery %
        deli_pct = _pct_prop(row.get("delivery_pct"))
        if deli_pct:
            props["Delivery %"] = deli_pct

        try:
            client.pages.create(
                parent={"data_source_id": data_source_id},
                properties=props,
            )
            uploaded += 1

            if (idx + 1) % 100 == 0:
                logger.info("  Uploaded %d/%d price rows", idx + 1, total)
            _rate_limit_pause()

        except Exception as e:
            logger.error("Failed to upload price %s: %s", entry_name, e)

    logger.info("Uploaded %d/%d price rows to Notion", uploaded, total)
    return uploaded


# ---------------------------------------------------------------------------
# Upload Screener Results
# ---------------------------------------------------------------------------

def upload_screener_results(
    results_df: pd.DataFrame,
    symbol_to_page: dict[str, str],
) -> int:
    """Upload screening results to Notion."""
    client = get_client()
    data_source_id = _resolve_data_source_id("screener")

    uploaded = 0
    today = datetime.now().strftime("%Y-%m-%d")
    logger.info("Uploading %d screener results ...", len(results_df))

    for _, row in results_df.iterrows():
        symbol = _safe_str(row.get("symbol", ""))
        if not symbol:
            continue

        props = {
            "Stock": _title_prop(symbol),
            "Screen Date": {"date": {"start": today}},
            "Conditions Met": {"number": row.get("conditions_met", 0)},
            "Score": {"number": row.get("score", 0)},
            "Passes": _checkbox_prop(row.get("passes_screen", False)),
            "Failed Conditions": _rich_text_prop(
                ", ".join(row.get("failed", []))
            ),
        }

        stock_page_id = symbol_to_page.get(symbol)
        if stock_page_id:
            props["Stock Link"] = _relation_prop(stock_page_id)

        try:
            client.pages.create(
                parent={"data_source_id": data_source_id},
                properties=props,
            )
            uploaded += 1
            _rate_limit_pause()
        except Exception as e:
            logger.error("Failed to upload screener result %s: %s", symbol, e)

    logger.info("Uploaded %d screener results", uploaded)
    return uploaded
