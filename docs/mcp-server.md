# MCP Server

StockPulse ships an MCP (Model Context Protocol) server that exposes 11 tools and 3 prompt templates. This lets any MCP-compatible AI agent (Claude, GPT-4 with MCP support, etc.) interact directly with the stock data stored in Notion.

---

## Requirements

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | FastMCP requires 3.10. The rest of StockPulse works on 3.9+. |
| `mcp` package | Install with `pip install -e ".[mcp]"` |
| Notion databases populated | Run `stockpulse pipeline` first |

---

## Starting the Server

```bash
stockpulse serve
# or
python -m stockpulse serve
```

The server communicates over **stdio** (standard input/output). You won't see much in the terminal — it's waiting for an MCP client to connect. Claude Desktop manages this process automatically.

---

## Connecting to Claude Desktop

**macOS:** Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** Edit `%APPDATA%\Claude\claude_desktop_config.json`

Add the `stockpulse` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "stockpulse": {
      "command": "zsh",
      "args": [
        "-c",
        "source /Users/safvan/Desktop/hackathons/notion-mcp/.venv/bin/activate && python -m stockpulse serve"
      ],
      "cwd": "/Users/safvan/Desktop/hackathons/notion-mcp",
      "env": {
        "NOTION_TOKEN": "ntn_i6569599185bgFqs6ZAWCvmGViBacbib6mAysWIzQO1b5W",
        "NOTION_PARENT_PAGE_ID": "3221879420d180c785d1eb25e8956ce4"
      }
    }
  }
}
```

> **Tip:** Use the absolute path to `.venv/bin/python` (not just `python`) to ensure the virtual environment is used.

Restart Claude Desktop. You should see a hammer icon (🔨) in the chat input — that indicates MCP tools are loaded.

---

## Tools Reference

### Query Tools (read-only)

---

#### `get_screened_stocks`

Fetch stocks from the Stocks Master database that pass the 12-condition screen.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_score` | int | 0 | Minimum quality score (0–100) |
| `limit` | int | 50 | Maximum number of stocks to return |

**Returns:** JSON array of stocks sorted by score descending.

**Example:**
```
What are the top 20 stocks with a score above 90?
→ Tool call: get_screened_stocks(min_score=90, limit=20)
```

---

#### `get_stock_details`

Get full fundamental data for a single stock symbol.

| Parameter | Type | Description |
|-----------|------|-------------|
| `symbol` | str | Stock ticker (e.g., `HCLTECH`, `TRENT`) |

**Returns:** JSON object with all 27 properties from the Stocks Master database.

**Example:**
```
Tell me about ABBOTINDIA.
→ Tool call: get_stock_details(symbol="ABBOTINDIA")
```

---

#### `get_price_history`

Get recent daily OHLCV + delivery data for a stock.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbol` | str | — | Stock ticker |
| `days` | int | 30 | Number of trading days (max 60) |

**Returns:** JSON array of daily price rows, newest first.

**Example:**
```
Show me TRENT's price action over the last 2 weeks.
→ Tool call: get_price_history(symbol="TRENT", days=10)
```

---

#### `get_stocks_by_industry`

Get all screened stocks in a specific sector.

| Parameter | Type | Description |
|-----------|------|-------------|
| `industry` | str | Industry name (e.g., `IT - Software`, `Pharmaceuticals`) |

**Returns:** JSON array of screened stocks in that industry.

**Example tip:** Use `list_industries` first to see the exact industry names.

---

#### `list_industries`

Get a breakdown of all industries with screened stock counts.

**Returns:** JSON object mapping industry name → stock count, sorted by count.

**Example:**
```
Which sectors have the most fundamentally sound stocks?
→ Tool call: list_industries()
```

---

#### `get_screening_conditions`

Get the definition of all 12 screening conditions.

**Returns:** JSON array with field name, operator, and threshold for each condition.

---

#### `get_watchlist`

Fetch the current watchlist.

**Returns:** JSON array with stock name, notes, AI alerts, and status for each watchlist entry.

---

### Action Tools (write to Notion)

---

#### `add_to_watchlist`

Add a stock to the Watchlist database in Notion.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbol` | str | — | Stock ticker |
| `notes` | str | `""` | Reason for watching |
| `status` | str | `"Watching"` | One of: `Watching`, `Entered`, `Exited`, `Alerted` |

**Returns:** Confirmation JSON.

---

#### `write_analysis_report`

Create a new page in the AI Reports database. Supports Markdown-style headings and bullets.

| Parameter | Type | Description |
|-----------|------|-------------|
| `title` | str | Report title |
| `report_type` | str | One of: `Stock Analysis`, `Weekly Summary`, `Sector Report`, `Anomaly Alert`, `Screener Report` |
| `content` | str | Full analysis text (Markdown) |
| `symbols` | str | Comma-separated symbols covered (optional) |

**Returns:** JSON with `page_id` and `url` of the created page.

---

#### `update_stock_ai_rating`

Set the AI Rating field on a stock in the Stocks Master database.

| Parameter | Type | Description |
|-----------|------|-------------|
| `symbol` | str | Stock ticker |
| `rating` | str | One of: `Strong Buy`, `Buy`, `Hold`, `Avoid` |

**Returns:** Confirmation JSON.

---

### Analysis Tools

---

#### `detect_anomalies`

Scans the Stocks Master database to identify notable patterns.

Currently detects:
- **High Piotroski Score** (≥ 7): indicates strong financial health across 9 accounting metrics
- **Promoter holding changes**: any increase or decrease in insider ownership

**Returns:** JSON with `strong_fundamentals` and `governance_flags` arrays plus a summary string.

---

## Prompt Templates

Prompts are multi-step guidance templates that tell the AI agent what tools to call and what to produce. Available in Claude as conversation starters.

---

### `stock_deep_dive(symbol)`

A full research brief for a single stock.

**What it instructs the AI to do:**
1. Call `get_stock_details` for fundamentals
2. Call `get_price_history` for price/delivery trends
3. Call `get_stocks_by_industry` for sector peer comparison
4. Write a comprehensive analysis covering health, trends, risks, and rating
5. Call `write_analysis_report` to save the analysis to Notion
6. Call `update_stock_ai_rating` to record the rating

**Invocation:**
```
Use the stock_deep_dive prompt for TRENT
```

---

### `weekly_market_scan()`

A market-wide weekly scan that surfaces the best opportunities.

**What it instructs the AI to do:**
1. Call `get_screened_stocks` (min_score=70)
2. Call `list_industries` for sector distribution
3. Call `detect_anomalies` for notable patterns
4. Deep dive into top 3–5 sectors using `get_stocks_by_industry`
5. Write a "Weekly Market Pulse" report with sector highlights, top picks, and risk flags
6. Save to Notion as a "Weekly Summary" report

**Invocation:**
```
Run the weekly_market_scan prompt
```

---

### `anomaly_investigation(symbol)`

A deeper investigation of a specific stock's price/delivery anomalies.

**What it instructs the AI to do:**
1. Call `get_price_history` for recent data
2. Analyze delivery % vs normal levels
3. Cross-reference with `get_stock_details` for fundamental context
4. Identify if the anomaly is likely: institutional accumulation, distribution, or news-driven
5. Save findings as an "Anomaly Alert" report in Notion

**Invocation:**
```
Investigate price anomaly in PIXTRANS using anomaly_investigation
```

---

## Example Conversations with Claude

### "Give me today's best opportunities"
```
User: Use get_screened_stocks with min_score=85 and tell me the top 10 stocks

Claude: [calls get_screened_stocks(min_score=85, limit=10)]
Here are the top 10 fundamentally screened stocks...
[lists stocks with PE, ROCE, score]
```

### "Research a specific stock"
```
User: Deep dive on ABBOTINDIA and save the report to Notion

Claude: [calls get_stock_details("ABBOTINDIA")]
[calls get_price_history("ABBOTINDIA", 30)]
[calls get_stocks_by_industry("Pharmaceuticals")]
[writes analysis]
[calls write_analysis_report(...)]
[calls update_stock_ai_rating("ABBOTINDIA", "Strong Buy")]

I've analyzed ABBOTINDIA and saved the report to Notion...
```

### "Add to watchlist"
```
User: Add PIXTRANS to my watchlist, I'm watching for a breakout above ₹200

Claude: [calls add_to_watchlist("PIXTRANS", "Watching for breakout above ₹200")]
Done! PIXTRANS has been added to your Notion watchlist.
```

---

## Python 3.9 Fallback

If `mcp` is not installed or Python < 3.10, the server module degrades gracefully:

```python
try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
```

When `HAS_MCP = False`, the `@_tool()` and `@_prompt()` decorators become no-ops, meaning all tool functions are still importable and callable as regular Python functions — they just aren't registered in an MCP server. The `serve` command will print a warning and exit cleanly.
