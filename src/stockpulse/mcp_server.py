"""
StockPulse MCP Server — Exposes stock intelligence tools via Model Context Protocol.

This server lets an AI agent (e.g., Claude) read stock data, run screens,
generate analysis, and write reports into Notion — all through MCP.

Requires Python 3.10+ and the `mcp` package: pip install mcp
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from stockpulse.notion_setup import get_client, ensure_all_db_schemas
from stockpulse.screener import SCREEN_CONDITIONS

logger = logging.getLogger(__name__)

if HAS_MCP:
    # Create MCP server
    mcp = FastMCP("StockPulse India")
else:
    mcp = None


def _tool():
    """Decorator that registers as MCP tool if available, otherwise no-op."""
    if mcp:
        return mcp.tool()
    return lambda fn: fn


def _prompt():
    """Decorator that registers as MCP prompt if available, otherwise no-op."""
    if mcp:
        return mcp.prompt()
    return lambda fn: fn


# ---------------------------------------------------------------------------
# Helper: Query Notion database
# ---------------------------------------------------------------------------

def _query_database(db_key: str, filter_obj: dict | None = None, page_size: int = 100) -> list[dict]:
    """Query a Notion database and return pages."""
    client = get_client()
    ds_ids = ensure_all_db_schemas()
    data_source_id = ds_ids.get(db_key)
    if not data_source_id:
        return []

    kwargs = {"data_source_id": data_source_id, "page_size": min(page_size, 100)}
    if filter_obj:
        kwargs["filter"] = filter_obj

    results = []
    response = client.data_sources.query(**kwargs)
    results.extend(response.get("results", []))

    # Handle pagination
    while response.get("has_more") and len(results) < page_size:
        response = client.data_sources.query(
            data_source_id=data_source_id,
            start_cursor=response["next_cursor"],
            page_size=min(page_size - len(results), 100),
        )
        results.extend(response.get("results", []))

    return results


def _extract_property(page: dict, prop_name: str) -> str | float | bool | None:
    """Extract a property value from a Notion page."""
    props = page.get("properties", {})
    prop = props.get(prop_name)
    if not prop:
        return None

    ptype = prop.get("type")

    if ptype == "title":
        texts = prop.get("title", [])
        return texts[0]["plain_text"] if texts else None

    if ptype == "rich_text":
        texts = prop.get("rich_text", [])
        return texts[0]["plain_text"] if texts else None

    if ptype == "number":
        return prop.get("number")

    if ptype == "checkbox":
        return prop.get("checkbox")

    if ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else None

    if ptype == "date":
        d = prop.get("date")
        return d["start"] if d else None

    if ptype == "relation":
        rels = prop.get("relation", [])
        return [r["id"] for r in rels]

    return None


def _page_to_dict(page: dict, fields: list[str]) -> dict:
    """Convert a Notion page to a simple dict with given fields."""
    result = {"page_id": page["id"]}
    for field in fields:
        result[field] = _extract_property(page, field)
    return result


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

STOCK_FIELDS = [
    "Symbol", "BSE Code", "Industry", "Group", "CMP", "Market Cap (Cr)",
    "PE", "EPS", "Sales Qrt (Cr)", "NP Qrt (Cr)", "Sales Var %", "Profit Var %",
    "Debt/Equity", "Current Ratio", "ROCE %", "ROE %",
    "Promoter Hold %", "Pledged %", "Unpledged Promo %", "Ch Promo Hold %",
    "FII Hold %", "DII Hold %", "Piotroski Score",
    "Passes Screen", "Screen Score", "AI Rating",
]


@_tool()
def get_screened_stocks(
    min_score: int = 0,
    limit: int = 50,
) -> str:
    """Get stocks that pass the 12-condition fundamental screen.

    Args:
        min_score: Minimum quality score (0-100) to include.
        limit: Maximum number of stocks to return.

    Returns:
        JSON array of screened stocks with fundamentals and scores.
    """
    filter_obj = {
        "and": [
            {"property": "Passes Screen", "checkbox": {"equals": True}},
        ]
    }
    if min_score > 0:
        filter_obj["and"].append(
            {"property": "Screen Score", "number": {"greater_than_or_equal_to": min_score}}
        )

    pages = _query_database("stocks_master", filter_obj, page_size=limit)
    stocks = [_page_to_dict(p, STOCK_FIELDS) for p in pages]
    stocks.sort(key=lambda x: x.get("Screen Score") or 0, reverse=True)

    return json.dumps(stocks[:limit], indent=2, default=str)


@_tool()
def get_stock_details(symbol: str) -> str:
    """Get detailed fundamentals for a specific stock symbol.

    Args:
        symbol: The stock ticker symbol (e.g., 'HCLTECH', 'TRENT').

    Returns:
        JSON object with all fundamental data for the stock.
    """
    filter_obj = {
        "property": "Symbol",
        "title": {"equals": symbol.upper()},
    }
    pages = _query_database("stocks_master", filter_obj, page_size=1)

    if not pages:
        return json.dumps({"error": f"Stock {symbol} not found"})

    return json.dumps(_page_to_dict(pages[0], STOCK_FIELDS), indent=2, default=str)


@_tool()
def get_price_history(
    symbol: str,
    days: int = 30,
) -> str:
    """Get recent daily price and delivery data for a stock.

    Args:
        symbol: Stock ticker symbol.
        days: Number of recent trading days to fetch (max 60).

    Returns:
        JSON array of daily OHLCV + delivery data, newest first.
    """
    days = min(days, 60)
    price_fields = [
        "Entry", "Date", "Open", "High", "Low", "Close", "Prev Close",
        "Volume", "Delivery Qty", "Delivery %", "Turnover (Cr)", "Total Trades",
    ]

    # We need to search by the entry title pattern
    filter_obj = {
        "property": "Entry",
        "title": {"starts_with": symbol.upper()},
    }

    pages = _query_database("daily_prices", filter_obj, page_size=days)
    prices = [_page_to_dict(p, price_fields) for p in pages]
    prices.sort(key=lambda x: x.get("Date") or "", reverse=True)

    return json.dumps(prices[:days], indent=2, default=str)


@_tool()
def get_stocks_by_industry(industry: str) -> str:
    """Get all screened stocks in a specific industry/sector.

    Args:
        industry: Industry name (e.g., 'IT - Software', 'Pharmaceuticals').

    Returns:
        JSON array of stocks in the industry with fundamentals.
    """
    filter_obj = {
        "and": [
            {"property": "Industry", "select": {"equals": industry}},
            {"property": "Passes Screen", "checkbox": {"equals": True}},
        ]
    }
    pages = _query_database("stocks_master", filter_obj, page_size=100)
    stocks = [_page_to_dict(p, STOCK_FIELDS) for p in pages]
    return json.dumps(stocks, indent=2, default=str)


@_tool()
def list_industries() -> str:
    """List all industries/sectors with count of screened stocks.

    Returns:
        JSON object mapping industry name to stock count.
    """
    pages = _query_database("stocks_master", {
        "property": "Passes Screen",
        "checkbox": {"equals": True},
    }, page_size=500)

    industries: dict[str, int] = {}
    for p in pages:
        ind = _extract_property(p, "Industry")
        if ind:
            industries[ind] = industries.get(ind, 0) + 1

    sorted_ind = dict(sorted(industries.items(), key=lambda x: x[1], reverse=True))
    return json.dumps(sorted_ind, indent=2)


@_tool()
def get_screening_conditions() -> str:
    """Get the 12 fundamental screening conditions used to filter stocks.

    Returns:
        JSON description of all screening conditions.
    """
    conditions = []
    for name, cond in SCREEN_CONDITIONS.items():
        conditions.append({
            "name": name,
            "field": cond["field"],
            "operator": cond["op"],
            "threshold": cond["value"],
        })
    return json.dumps(conditions, indent=2)


@_tool()
def get_watchlist() -> str:
    """Get the current watchlist with user notes and AI alerts.

    Returns:
        JSON array of watchlist entries.
    """
    fields = ["Stock", "Added Date", "User Notes", "AI Alerts", "Status"]
    pages = _query_database("watchlist", page_size=100)
    items = [_page_to_dict(p, fields) for p in pages]
    return json.dumps(items, indent=2, default=str)


@_tool()
def add_to_watchlist(
    symbol: str,
    notes: str = "",
    status: str = "Watching",
) -> str:
    """Add a stock to the watchlist.

    Args:
        symbol: Stock ticker symbol to watch.
        notes: Optional notes about why you're watching this stock.
        status: One of 'Watching', 'Entered', 'Exited', 'Alerted'.

    Returns:
        Confirmation message.
    """
    client = get_client()
    ds_ids = ensure_all_db_schemas()
    data_source_id = ds_ids.get("watchlist")
    if not data_source_id:
        return json.dumps({"error": "Watchlist database not found"})

    props = {
        "Stock": {"title": [{"text": {"content": symbol.upper()}}]},
        "Added Date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        "Status": {"select": {"name": status}},
    }
    if notes:
        props["User Notes"] = {"rich_text": [{"text": {"content": notes[:2000]}}]}

    client.pages.create(parent={"data_source_id": data_source_id}, properties=props)
    return json.dumps({"success": True, "message": f"{symbol} added to watchlist"})


@_tool()
def write_analysis_report(
    title: str,
    report_type: str,
    content: str,
    symbols: str = "",
) -> str:
    """Write an AI analysis report to Notion.

    Creates a new page in the AI Reports database with the analysis content
    as the page body.

    Args:
        title: Report title (e.g., 'Weekly Market Summary - Mar 10, 2026').
        report_type: One of 'Stock Analysis', 'Weekly Summary', 'Sector Report',
                     'Anomaly Alert', 'Screener Report'.
        content: The full analysis text (Markdown). Will be added as page content.
        symbols: Comma-separated list of symbols covered in this report.

    Returns:
        Confirmation with the created page URL.
    """
    client = get_client()
    ds_ids = ensure_all_db_schemas()
    data_source_id = ds_ids.get("reports")
    if not data_source_id:
        return json.dumps({"error": "Reports database not found"})

    props = {
        "Title": {"title": [{"text": {"content": title[:100]}}]},
        "Report Type": {"select": {"name": report_type}},
        "Date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
    }
    if symbols:
        props["Symbols Covered"] = {
            "rich_text": [{"text": {"content": symbols[:2000]}}]
        }

    # Split content into blocks (Notion max 2000 chars per block)
    blocks = _text_to_blocks(content)

    page = client.pages.create(
        parent={"data_source_id": data_source_id},
        properties=props,
        children=blocks,
    )

    return json.dumps({
        "success": True,
        "page_id": page["id"],
        "url": page.get("url", ""),
        "message": f"Report '{title}' created successfully",
    })


@_tool()
def update_stock_ai_rating(
    symbol: str,
    rating: str,
) -> str:
    """Update the AI Rating for a stock in the master database.

    Args:
        symbol: Stock ticker symbol.
        rating: One of 'Strong Buy', 'Buy', 'Hold', 'Avoid'.

    Returns:
        Confirmation message.
    """
    client = get_client()

    filter_obj = {
        "property": "Symbol",
        "title": {"equals": symbol.upper()},
    }
    pages = _query_database("stocks_master", filter_obj, page_size=1)

    if not pages:
        return json.dumps({"error": f"Stock {symbol} not found"})

    page_id = pages[0]["id"]
    client.pages.update(
        page_id=page_id,
        properties={
            "AI Rating": {"select": {"name": rating}},
        },
    )

    return json.dumps({
        "success": True,
        "message": f"Updated {symbol} AI Rating to '{rating}'",
    })


@_tool()
def detect_anomalies() -> str:
    """Detect anomalies and notable patterns in the stock data.

    Looks for:
    - Stocks with high delivery % (institutional interest signal)
    - Recent changes in promoter holdings
    - Stocks with high Piotroski scores
    - Stocks newly passing/failing the screen

    Returns:
        JSON object with categorized anomalies and notable patterns.
    """
    anomalies = {
        "high_conviction": [],
        "governance_flags": [],
        "strong_fundamentals": [],
        "summary": "",
    }

    # Get all screened stocks
    pages = _query_database("stocks_master", {
        "property": "Passes Screen",
        "checkbox": {"equals": True},
    }, page_size=500)

    for p in pages:
        data = _page_to_dict(p, STOCK_FIELDS)
        symbol = data.get("Symbol", "")

        # High Piotroski (strong fundamentals)
        piotroski = data.get("Piotroski Score")
        if piotroski and piotroski >= 7:
            anomalies["strong_fundamentals"].append({
                "symbol": symbol,
                "piotroski": piotroski,
                "score": data.get("Screen Score"),
            })

        # Promoter hold changes (governance signal)
        ch_promo = data.get("Ch Promo Hold %")
        if ch_promo is not None and ch_promo != 0:
            direction = "increased" if ch_promo > 0 else "decreased"
            anomalies["governance_flags"].append({
                "symbol": symbol,
                "change": ch_promo,
                "direction": direction,
                "pledged": data.get("Pledged %"),
            })

    anomalies["summary"] = (
        f"Found {len(anomalies['strong_fundamentals'])} stocks with Piotroski >= 7, "
        f"{len(anomalies['governance_flags'])} with promoter holding changes."
    )

    return json.dumps(anomalies, indent=2, default=str)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_to_blocks(text: str) -> list[dict]:
    """Convert markdown-ish text into Notion blocks.

    Splits on double newlines into paragraphs, handles headers (##).
    Each block is capped at 2000 chars for Notion's limit.
    """
    blocks = []
    paragraphs = text.split("\n\n")

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Check for headers
        if para.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": para[4:100]}}]
                },
            })
        elif para.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": para[3:100]}}]
                },
            })
        elif para.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": para[2:100]}}]
                },
            })
        elif para.startswith("- ") or para.startswith("• "):
            # Bulleted list items
            items = para.split("\n")
            for item in items:
                item_text = item.lstrip("-•").strip()
                if item_text:
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": item_text[:2000]}}]
                        },
                    })
        else:
            # Regular paragraph — chunk if longer than 2000
            for i in range(0, len(para), 2000):
                chunk = para[i:i + 2000]
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    },
                })

    return blocks


# ---------------------------------------------------------------------------
# MCP Prompts (suggested workflows for the AI)
# ---------------------------------------------------------------------------

@_prompt()
def stock_deep_dive(symbol: str) -> str:
    """Generate a prompt for a deep-dive analysis of a specific stock."""
    return f"""Analyze the stock {symbol.upper()} using the StockPulse tools:

1. First, use get_stock_details to fetch its fundamental data
2. Use get_price_history to see recent price and delivery trends
3. Use get_stocks_by_industry to compare with sector peers
4. Use get_screening_conditions to reference the 12-condition framework

Write a comprehensive analysis covering:
- Fundamental Health Assessment (PE, EPS, ROCE, Debt metrics)
- Price Trend & Delivery Analysis (is smart money accumulating?)
- Industry Comparison (how does it rank vs peers?)
- Risk Flags (pledging, promoter exits, profit decline)
- Overall Rating (Strong Buy / Buy / Hold / Avoid)

Then use write_analysis_report to save the analysis to Notion with type "Stock Analysis",
and use update_stock_ai_rating to set the appropriate rating."""


@_prompt()
def weekly_market_scan() -> str:
    """Generate a prompt for a weekly market scanning report."""
    return """Perform a comprehensive weekly market scan using StockPulse tools:

1. Use get_screened_stocks with min_score=70 to find top-quality stocks
2. Use list_industries to see sector distribution
3. Use detect_anomalies to find notable patterns
4. Pick the top 3-5 sectors by stock count and use get_stocks_by_industry for each

Write a "Weekly Market Pulse" report covering:
- Market Overview: How many stocks pass the fundamental screen this week?
- Top Picks: The highest-scored stocks and why
- Sector Spotlight: Which sectors have the most quality stocks?
- Anomalies & Signals: Any unusual patterns detected?
- Watchlist Candidates: 5 stocks worth investigating further

Then use write_analysis_report to save with type "Weekly Summary",
and use add_to_watchlist for the top candidates."""


@_prompt()
def anomaly_investigation() -> str:
    """Generate a prompt for investigating data anomalies."""
    return """Investigate anomalies in the stock data:

1. Use detect_anomalies to find all notable patterns
2. For each governance flag (promoter holding change), use get_stock_details
   to get the full picture
3. For stocks with high Piotroski scores, check price history with get_price_history

Write an "Anomaly Alert" report covering:
- Governance Alerts: Stocks where promoters are increasing/decreasing holdings
- High Conviction Picks: Stocks with Piotroski >= 7 (strong fundamentals)
- Action Items: Which anomalies warrant adding to watchlist?

Save the report using write_analysis_report with type "Anomaly Alert"."""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the MCP server."""
    if not HAS_MCP:
        print("ERROR: The 'mcp' package is required. Install with:")
        print("  pip install 'mcp>=1.0.0'")
        print("  (Requires Python 3.10+)")
        raise SystemExit(1)
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
