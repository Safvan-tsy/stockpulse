"""
StockPulse MCP Server — Pure computation tools for stock intelligence.

This is a **stateless computation engine** that works alongside the official
Notion MCP server (https://mcp.notion.com/mcp).  The AI agent uses Notion MCP
for all Notion I/O (search, fetch, create/update pages) and StockPulse MCP for
domain-specific intelligence: screening, scoring, anomaly detection, and
report generation.

Architecture:
    Notion MCP  ←→  AI Agent  ←→  StockPulse MCP
    (all Notion I/O)          (pure computation)

Requires Python 3.10+ and the `mcp` package: pip install mcp
"""

from __future__ import annotations

import json
import logging

try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from stockpulse.screener import (
    SCREEN_CONDITIONS,
    check_condition,
    _compute_score,
    _safe_numeric,
)

logger = logging.getLogger(__name__)

if HAS_MCP:
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
# MCP Tools — Pure Computation (no Notion SDK calls)
# ---------------------------------------------------------------------------

@_tool()
def get_screening_conditions() -> str:
    """Get the 12 fundamental screening conditions used to filter stocks.

    These are the rules StockPulse uses to screen 5,000+ Indian stocks.
    Use this to understand what each condition means before screening.

    Returns:
        JSON array of conditions, each with name, field, operator, threshold.
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
def screen_stock(stock_data: str) -> str:
    """Screen a single stock against the 12 fundamental conditions and compute a quality score.

    Takes raw stock data (as JSON) fetched via Notion MCP and applies
    StockPulse's 12-condition screening engine + weighted scoring.

    The input JSON should contain fundamental fields from the Stocks Master
    database. Field names are matched case-insensitively. Common fields:
    PE, EPS, Sales Qrt (Cr), NP Qrt (Cr), Sales Var %, Profit Var %,
    Debt/Equity, Current Ratio, ROCE %, Promoter Hold %, Pledged %,
    Unpledged Promo %, Ch Promo Hold %, Piotroski Score.

    Args:
        stock_data: JSON string of one stock's properties from Notion.
                    Example: {"Symbol": "HCLTECH", "PE": 28.5, "EPS": 62.1, ...}

    Returns:
        JSON object with screening result: passed/failed/unknown conditions,
        conditions_met count, passes_screen boolean, and quality score (0-100).
    """
    try:
        data = json.loads(stock_data)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input. Pass a JSON object of stock properties."})

    # Normalize keys: map Notion property names to screener field names
    normalized = _normalize_stock_fields(data)

    passed = []
    failed = []
    unknown = []

    for name, condition in SCREEN_CONDITIONS.items():
        result = check_condition(normalized, condition)
        if result is True:
            passed.append(name)
        elif result is False:
            failed.append(name)
        else:
            unknown.append(name)

    total = len(SCREEN_CONDITIONS)
    met = len(passed)
    score = _compute_score(normalized, met, total)

    return json.dumps({
        "symbol": data.get("Symbol", data.get("symbol", "?")),
        "passes_screen": len(failed) == 0 and met > 0,
        "score": score,
        "conditions_met": met,
        "total_conditions": total,
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
    }, indent=2)


@_tool()
def screen_multiple_stocks(stocks_data: str) -> str:
    """Screen multiple stocks at once and return ranked results.

    Takes a JSON array of stock objects (fetched via Notion MCP) and screens
    each one against the 12 conditions. Returns results sorted by score.

    Args:
        stocks_data: JSON array of stock objects from Notion.
                     Example: [{"Symbol": "HCLTECH", "PE": 28.5, ...}, ...]

    Returns:
        JSON object with:
        - results: array of screening results sorted by score (highest first)
        - summary: total screened, passed, failed counts
    """
    try:
        stocks = json.loads(stocks_data)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input. Pass a JSON array of stock objects."})

    if not isinstance(stocks, list):
        return json.dumps({"error": "Input must be a JSON array of stock objects."})

    results = []
    for data in stocks:
        normalized = _normalize_stock_fields(data)
        passed = []
        failed = []
        unknown = []

        for name, condition in SCREEN_CONDITIONS.items():
            result = check_condition(normalized, condition)
            if result is True:
                passed.append(name)
            elif result is False:
                failed.append(name)
            else:
                unknown.append(name)

        total = len(SCREEN_CONDITIONS)
        met = len(passed)
        score = _compute_score(normalized, met, total)

        results.append({
            "symbol": data.get("Symbol", data.get("symbol", "?")),
            "passes_screen": len(failed) == 0 and met > 0,
            "score": score,
            "conditions_met": met,
            "passed": passed,
            "failed": failed,
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    passed_count = sum(1 for r in results if r["passes_screen"])
    return json.dumps({
        "results": results,
        "summary": {
            "total_screened": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
        },
    }, indent=2)


@_tool()
def detect_anomalies(stocks_data: str) -> str:
    """Detect anomalies and notable patterns in stock data.

    Takes a JSON array of stock objects (fetched via Notion MCP) and
    identifies notable patterns:
    - Stocks with Piotroski Score >= 7 (strong fundamental quality)
    - Recent changes in promoter holdings (governance signal)
    - High delivery % stocks (potential institutional interest)

    Args:
        stocks_data: JSON array of stock objects with fundamental data.

    Returns:
        JSON object with categorized anomalies: strong_fundamentals,
        governance_flags, high_delivery, and a summary.
    """
    try:
        stocks = json.loads(stocks_data)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input. Pass a JSON array of stock objects."})

    if not isinstance(stocks, list):
        return json.dumps({"error": "Input must be a JSON array of stock objects."})

    anomalies = {
        "strong_fundamentals": [],
        "governance_flags": [],
        "high_delivery": [],
        "summary": "",
    }

    for data in stocks:
        symbol = data.get("Symbol", data.get("symbol", "?"))

        # High Piotroski (strong fundamentals)
        piotroski = _safe_numeric(data.get("Piotroski Score", data.get("piotroski_score")))
        if piotroski is not None and piotroski >= 7:
            anomalies["strong_fundamentals"].append({
                "symbol": symbol,
                "piotroski": piotroski,
                "score": _safe_numeric(data.get("Screen Score", data.get("score"))),
            })

        # Promoter hold changes (governance signal)
        ch_promo = _safe_numeric(data.get("Ch Promo Hold %", data.get("ch_promo_hold_pct")))
        if ch_promo is not None and ch_promo != 0:
            direction = "increased" if ch_promo > 0 else "decreased"
            anomalies["governance_flags"].append({
                "symbol": symbol,
                "change": ch_promo,
                "direction": direction,
                "pledged": _safe_numeric(data.get("Pledged %", data.get("pledged_pct"))),
            })

        # High delivery % (institutional interest)
        delivery_pct = _safe_numeric(data.get("Delivery %", data.get("delivery_pct")))
        if delivery_pct is not None and delivery_pct >= 70:
            anomalies["high_delivery"].append({
                "symbol": symbol,
                "delivery_pct": delivery_pct,
            })

    anomalies["summary"] = (
        f"Analyzed {len(stocks)} stocks. "
        f"Found {len(anomalies['strong_fundamentals'])} with Piotroski >= 7, "
        f"{len(anomalies['governance_flags'])} with promoter holding changes, "
        f"{len(anomalies['high_delivery'])} with delivery % >= 70%."
    )

    return json.dumps(anomalies, indent=2, default=str)


@_tool()
def compare_sector(target_stock: str, peer_stocks: str) -> str:
    """Compare a stock against its sector peers on key fundamental metrics.

    Takes a target stock and an array of peer stocks (all fetched via Notion MCP)
    and ranks the target within its sector.

    Args:
        target_stock: JSON string of the target stock's properties.
        peer_stocks: JSON array of peer stock objects from the same industry.

    Returns:
        JSON object with the target's rank on each metric and an overall
        sector percentile.
    """
    try:
        target = json.loads(target_stock)
        peers = json.loads(peer_stocks)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input."})

    if not isinstance(peers, list):
        return json.dumps({"error": "peer_stocks must be a JSON array."})

    all_stocks = peers + [target]
    target_symbol = target.get("Symbol", target.get("symbol", "?"))

    metrics = {
        "ROCE %": "higher_better",
        "ROE %": "higher_better",
        "PE": "lower_better",
        "Debt/Equity": "lower_better",
        "Promoter Hold %": "higher_better",
        "Piotroski Score": "higher_better",
        "Screen Score": "higher_better",
    }

    rankings = {}
    for metric, direction in metrics.items():
        values = []
        for s in all_stocks:
            sym = s.get("Symbol", s.get("symbol", "?"))
            val = _safe_numeric(s.get(metric))
            if val is not None:
                values.append((sym, val))

        if not values:
            continue

        reverse = direction == "higher_better"
        values.sort(key=lambda x: x[1], reverse=reverse)

        rank = None
        for i, (sym, _) in enumerate(values):
            if sym == target_symbol:
                rank = i + 1
                break

        rankings[metric] = {
            "rank": rank,
            "total": len(values),
            "percentile": round((1 - (rank - 1) / len(values)) * 100) if rank else None,
        }

    # Overall percentile: average of all metric percentiles
    percentiles = [r["percentile"] for r in rankings.values() if r.get("percentile") is not None]
    overall = round(sum(percentiles) / len(percentiles)) if percentiles else None

    return json.dumps({
        "symbol": target_symbol,
        "industry": target.get("Industry", target.get("industry", "?")),
        "peer_count": len(peers),
        "rankings": rankings,
        "overall_sector_percentile": overall,
    }, indent=2)


@_tool()
def generate_report_content(
    report_type: str,
    analysis_data: str,
) -> str:
    """Generate structured markdown content for an analysis report.

    Takes computed analysis data and produces well-formatted markdown
    suitable for creating a Notion page via Notion MCP's create-a-page tool.

    Args:
        report_type: One of 'Stock Analysis', 'Weekly Summary', 'Sector Report',
                     'Anomaly Alert', 'Screener Report'.
        analysis_data: JSON string containing the analysis results.
                       Structure depends on report_type.

    Returns:
        JSON object with 'title', 'report_type', 'content' (markdown string),
        and 'symbols_covered'. Pass these to Notion MCP's create-a-page tool.
    """
    try:
        data = json.loads(analysis_data)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for analysis_data."})

    if report_type == "Stock Analysis":
        content = _format_stock_analysis(data)
    elif report_type == "Weekly Summary":
        content = _format_weekly_summary(data)
    elif report_type == "Sector Report":
        content = _format_sector_report(data)
    elif report_type == "Anomaly Alert":
        content = _format_anomaly_report(data)
    elif report_type == "Screener Report":
        content = _format_screener_report(data)
    else:
        content = json.dumps(data, indent=2, default=str)

    symbols = data.get("symbols", data.get("symbol", ""))
    if isinstance(symbols, list):
        symbols = ", ".join(symbols)

    title = data.get("title", f"{report_type} — StockPulse")

    return json.dumps({
        "title": title,
        "report_type": report_type,
        "content": content,
        "symbols_covered": symbols,
    }, indent=2)


# ---------------------------------------------------------------------------
# Report formatters
# ---------------------------------------------------------------------------

def _format_stock_analysis(data: dict) -> str:
    """Format a stock analysis report."""
    symbol = data.get("symbol", "?")
    screening = data.get("screening", {})
    fundamentals = data.get("fundamentals", {})
    sector = data.get("sector_comparison", {})
    rating = data.get("rating", "Hold")

    lines = [
        f"# {symbol} — Stock Analysis",
        "",
        f"**AI Rating: {rating}**",
        "",
        "## Fundamental Health",
        f"- PE: {fundamentals.get('PE', 'N/A')}",
        f"- EPS: {fundamentals.get('EPS', 'N/A')}",
        f"- ROCE: {fundamentals.get('ROCE %', 'N/A')}%",
        f"- Debt/Equity: {fundamentals.get('Debt/Equity', 'N/A')}",
        f"- Current Ratio: {fundamentals.get('Current Ratio', 'N/A')}",
        f"- Piotroski Score: {fundamentals.get('Piotroski Score', 'N/A')}/9",
        "",
        "## Screening Result",
        f"- Passes Screen: {'Yes' if screening.get('passes_screen') else 'No'}",
        f"- Quality Score: {screening.get('score', 'N/A')}/100",
        f"- Conditions Met: {screening.get('conditions_met', '?')}/{screening.get('total_conditions', 12)}",
    ]

    if screening.get("failed"):
        lines.append(f"- Failed: {', '.join(screening['failed'])}")

    if sector:
        lines.extend([
            "",
            "## Sector Comparison",
            f"- Industry: {sector.get('industry', 'N/A')}",
            f"- Sector Percentile: {sector.get('overall_sector_percentile', 'N/A')}%",
            f"- Peers Compared: {sector.get('peer_count', 'N/A')}",
        ])

    if data.get("notes"):
        lines.extend(["", "## Additional Notes", data["notes"]])

    return "\n".join(lines)


def _format_weekly_summary(data: dict) -> str:
    """Format a weekly market summary report."""
    lines = [
        "# Weekly Market Pulse — StockPulse India",
        "",
        "## Market Overview",
        data.get("overview", "No overview data provided."),
        "",
        "## Top Picks",
    ]
    for stock in data.get("top_picks", []):
        lines.append(f"- **{stock.get('symbol', '?')}** — Score: {stock.get('score', '?')}")

    lines.extend(["", "## Sector Spotlight"])
    for sector, count in data.get("sectors", {}).items():
        lines.append(f"- {sector}: {count} stocks")

    if data.get("anomalies"):
        lines.extend(["", "## Anomalies & Signals", data["anomalies"]])

    if data.get("watchlist_candidates"):
        lines.extend(["", "## Watchlist Candidates"])
        for s in data["watchlist_candidates"]:
            lines.append(f"- {s}")

    return "\n".join(lines)


def _format_sector_report(data: dict) -> str:
    """Format a sector analysis report."""
    industry = data.get("industry", "?")
    lines = [
        f"# Sector Report — {industry}",
        "",
        f"## Industry: {industry}",
        f"Total screened stocks: {data.get('total', '?')}",
        "",
        "## Top Performers",
    ]
    for stock in data.get("top_stocks", []):
        lines.append(f"- **{stock.get('symbol', '?')}** — Score: {stock.get('score', '?')}, ROCE: {stock.get('roce', '?')}%")

    if data.get("notes"):
        lines.extend(["", "## Notes", data["notes"]])

    return "\n".join(lines)


def _format_anomaly_report(data: dict) -> str:
    """Format an anomaly alert report."""
    lines = [
        "# Anomaly Alert — StockPulse India",
        "",
        data.get("summary", ""),
        "",
        "## Governance Alerts",
    ]
    for flag in data.get("governance_flags", []):
        lines.append(f"- **{flag.get('symbol', '?')}**: Promoter holding {flag.get('direction', '?')} by {flag.get('change', '?')}%")

    lines.extend(["", "## Strong Fundamentals (Piotroski >= 7)"])
    for s in data.get("strong_fundamentals", []):
        lines.append(f"- **{s.get('symbol', '?')}** — Piotroski: {s.get('piotroski', '?')}")

    if data.get("action_items"):
        lines.extend(["", "## Action Items", data["action_items"]])

    return "\n".join(lines)


def _format_screener_report(data: dict) -> str:
    """Format a screener summary report."""
    lines = [
        "# Screener Report — StockPulse India",
        "",
        f"Total screened: {data.get('total_screened', '?')}",
        f"Passed: {data.get('passed', '?')}",
        f"Failed: {data.get('failed', '?')}",
        "",
        "## Top Scored Stocks",
    ]
    for stock in data.get("top_stocks", []):
        lines.append(f"- **{stock.get('symbol', '?')}** — Score: {stock.get('score', '?')}/100")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Field normalization helper
# ---------------------------------------------------------------------------

def _normalize_stock_fields(data: dict) -> dict:
    """Normalize Notion property names to screener field names.

    The screener conditions reference snake_case field names from the parser,
    but Notion stores them in title-case.  This maps both formats.
    """
    mapping = {
        # Notion property name → screener field name
        "PE": "pe",
        "EPS": "eps",
        "Sales Qrt (Cr)": "sales_qrt",
        "NP Qrt (Cr)": "np_qrt",
        "Sales Var %": "sales_var_pct",
        "Profit Var %": "profit_var_pct",
        "Pledged %": "pledged_pct",
        "Unpledged Promo %": "unpledged_promo_pct",
        "Ch Promo Hold %": "ch_promo_hold_pct",
        "Debt/Equity": "Debt Eq Ratio %",
        "Current Ratio": "Current Ratio %",
        "ROCE %": "ROCE",
        "Promoter Hold %": "promoter_hold_pct",
        "Piotroski Score": "PiotriskiScore",
        "ROE %": "roe_pct",
    }

    normalized = dict(data)  # keep original fields too
    for notion_key, screener_key in mapping.items():
        if notion_key in data and data[notion_key] is not None:
            normalized[screener_key] = data[notion_key]

    return normalized


# ---------------------------------------------------------------------------
# MCP Prompts — Orchestrate both Notion MCP + StockPulse MCP
# ---------------------------------------------------------------------------

@_prompt()
def stock_deep_dive(symbol: str) -> str:
    """Generate a prompt for a deep-dive analysis of a specific stock.

    This orchestrates BOTH the Notion MCP (for data access) and
    StockPulse MCP (for computation) to produce a full research report.
    """
    return f"""Perform a deep-dive analysis of {symbol.upper()} using both Notion MCP and StockPulse tools.

**Step 1 — Fetch Data (via Notion MCP):**
- Use the `notion-search` tool to find "{symbol.upper()}" in the Stocks Master database
- Use the `notion-fetch` tool to get the full page with all fundamental properties
- Use `query-a-database-view` on the Daily Prices database filtered by entries starting with "{symbol.upper()}" to get recent price data
- Use `query-a-database-view` on the Stocks Master database filtered by the same Industry to get sector peers

**Step 2 — Analyze (via StockPulse MCP):**
- Use `screen_stock` with the fundamental data to get the 12-condition screening result and quality score
- Use `detect_anomalies` with the stock data (as a single-element array) to check for governance flags
- Use `compare_sector` with the stock data and peer data to get sector rankings
- Use `get_screening_conditions` to reference the 12-condition framework in your analysis

**Step 3 — Generate Report (via StockPulse MCP):**
- Use `generate_report_content` with report_type="Stock Analysis" to create formatted markdown
  Pass: {{"symbol": "{symbol.upper()}", "screening": <screen_result>, "fundamentals": <stock_data>, "sector_comparison": <sector_result>, "rating": "<your_rating>", "title": "{symbol.upper()} — Deep Dive Analysis"}}

**Step 4 — Save to Notion (via Notion MCP):**
- Use `create-a-page` in the AI Reports database with the generated title, content, and properties:
  - Title: from the report
  - Report Type: "Stock Analysis"
  - Date: today's date
  - Symbols Covered: "{symbol.upper()}"
- Use `update-a-page` on the stock's page in Stocks Master to set AI Rating

Write your analysis covering: Fundamental Health, Price Trends, Sector Ranking, Risk Flags, and Overall Rating."""


@_prompt()
def weekly_market_scan() -> str:
    """Generate a prompt for a weekly market scanning report.

    Orchestrates Notion MCP + StockPulse MCP for a full market scan.
    """
    return """Perform a comprehensive weekly market scan using Notion MCP and StockPulse tools.

**Step 1 — Fetch Data (via Notion MCP):**
- Use `query-a-database-view` on the Stocks Master database with filter: Passes Screen = true
  to get all screened stocks
- Note the total count of passing stocks

**Step 2 — Analyze (via StockPulse MCP):**
- Use `screen_multiple_stocks` with all the stock data to get fresh scores and rankings
- Use `detect_anomalies` with the same data to find patterns
- Use `get_screening_conditions` for context on what each condition means

**Step 3 — Sector Deep Dives (via Notion MCP + StockPulse MCP):**
- Group stocks by Industry from the data
- For the top 3-5 sectors by count, use `compare_sector` on the top stocks

**Step 4 — Generate Report (via StockPulse MCP):**
- Use `generate_report_content` with report_type="Weekly Summary"
  Pass: {{"overview": "<summary>", "top_picks": [<top_stocks>], "sectors": {{<sector_counts>}}, "anomalies": "<anomaly_summary>", "watchlist_candidates": [<symbols>], "title": "Weekly Market Pulse — <date>"}}

**Step 5 — Save to Notion (via Notion MCP):**
- Use `create-a-page` in the AI Reports database with the generated content
- For top 5 watchlist candidates, use `create-a-page` in the Watchlist database
  with properties: Stock (title), Added Date, Status="Watching", User Notes

Cover: Market Overview, Top Picks, Sector Spotlight, Anomalies, and Watchlist Candidates."""


@_prompt()
def anomaly_investigation() -> str:
    """Generate a prompt for investigating data anomalies.

    Orchestrates Notion MCP + StockPulse MCP for anomaly detection.
    """
    return """Investigate anomalies in the stock data using Notion MCP and StockPulse tools.

**Step 1 — Fetch Data (via Notion MCP):**
- Use `query-a-database-view` on the Stocks Master database with filter: Passes Screen = true
  to get all screened stocks with their fundamental data

**Step 2 — Detect Anomalies (via StockPulse MCP):**
- Use `detect_anomalies` with the fetched stock data
- Note stocks with Piotroski >= 7, promoter changes, and high delivery %

**Step 3 — Deep Dive on Flagged Stocks (via Notion MCP):**
- For each governance flag, use `notion-fetch` to get the full stock page
- For stocks with high Piotroski, use `query-a-database-view` on Daily Prices
  to check recent price/delivery trends

**Step 4 — Score Flagged Stocks (via StockPulse MCP):**
- Use `screen_stock` on each flagged stock for fresh scoring
- Use `compare_sector` for the most interesting anomalies

**Step 5 — Generate Report (via StockPulse MCP):**
- Use `generate_report_content` with report_type="Anomaly Alert"
  Pass the full anomaly data including governance_flags, strong_fundamentals, summary

**Step 6 — Save to Notion (via Notion MCP):**
- Use `create-a-page` in the AI Reports database with the report
- For actionable anomalies, use `create-a-page` in the Watchlist database

Cover: Governance Alerts, High Conviction Picks, and Action Items."""


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
