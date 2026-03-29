# MCP Server

StockPulse uses a **dual-MCP architecture**: the official **Notion MCP** server handles all Notion I/O (reading databases, creating pages, updating properties), while a custom **StockPulse MCP** server provides pure computation tools (screening, scoring, anomaly detection, report formatting). The AI agent orchestrates between both servers.

```
┌──────────────────────────────────────────────────┐
│                   AI Agent                        │
│           (Claude / GPT / Copilot)                │
│                                                   │
│  Notion MCP Tools:     StockPulse MCP Tools:      │
│  - notion-search       - screen_stock             │
│  - notion-fetch        - screen_multiple_stocks   │
│  - create-a-page       - detect_anomalies         │
│  - update-a-page       - compare_sector           │
│  - query-a-database    - generate_report_content  │
│  - ...                 - get_screening_conditions │
└──────────┬─────────────────────────┬──────────────┘
           │                         │
           ▼                         ▼
   Notion Workspace          Pure Python Engine
   (5 databases)             (no Notion SDK calls)
```

---

## Requirements

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | FastMCP requires 3.10. The rest of StockPulse works on 3.9+. |
| `mcp` package | Install with `pip install -e ".[mcp]"` |
| Notion MCP connected | Connect via OAuth at `https://mcp.notion.com/mcp` |
| Notion databases populated | Run `stockpulse pipeline` first |

---

## Setting Up the Dual-MCP Architecture

### 1. Connect Notion MCP (Official)

Notion MCP is Notion's hosted server that gives AI tools direct access to your Notion workspace via OAuth. No local setup needed.

**VS Code (GitHub Copilot):** Create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "notion": {
      "type": "http",
      "url": "https://mcp.notion.com/mcp"
    }
  }
}
```

**Claude Desktop:** Go to Settings → Connectors → Add Connector → enter `https://mcp.notion.com/mcp` and complete the OAuth flow.

**Cursor:** Settings → MCP → Add new global MCP server → paste `{"mcpServers": {"notion": {"url": "https://mcp.notion.com/mcp"}}}`

### 2. Start StockPulse MCP (Custom Computation Server)

```bash
stockpulse serve
# or
python -m stockpulse serve
```

The server communicates over **stdio** (standard input/output). 

**VS Code (GitHub Copilot):** Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "notion": {
      "type": "http",
      "url": "https://mcp.notion.com/mcp"
    },
    "stockpulse": {
      "type": "stdio",
      "command": "zsh",
      "args": ["-c", "source /path/to/notion-mcp/.venv/bin/activate && python -m stockpulse serve"]
    }
  }
}
```

**Claude Desktop:** Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "stockpulse": {
      "command": "python",
      "args": ["-m", "stockpulse", "serve"],
      "cwd": "/path/to/notion-mcp"
    }
  }
}
```

> **Note:** Notion MCP is configured as a Connector in Claude Desktop (Settings → Connectors), not in `claude_desktop_config.json`. StockPulse MCP goes in the JSON config file since it's a local stdio server.

---

## Why Two MCP Servers?

| Concern | Notion MCP | StockPulse MCP |
|---------|-----------|----------------|
| **Notion I/O** | ✅ Search, fetch, create, update pages | ❌ No Notion SDK calls |
| **Computation** | ❌ Can't run screening algorithms | ✅ 12-condition screener, scoring, anomaly detection |
| **Authentication** | OAuth (managed by Notion) | None needed (stateless computation) |
| **Data access** | Full workspace access | Receives data as JSON input from AI |

The AI agent is the orchestrator. It fetches data from Notion using the official Notion MCP tools, passes that data to StockPulse MCP for analysis, and then writes results back to Notion using Notion MCP.

---

## StockPulse MCP Tools Reference

### Computation Tools

---

#### `get_screening_conditions`

Get the definition of all 12 screening conditions.

**Parameters:** None

**Returns:** JSON array with field name, operator, and threshold for each condition.

---

#### `screen_stock`

Screen one stock against the 12 conditions and compute a quality score (0–100).

| Parameter | Type | Description |
|-----------|------|-------------|
| `stock_data` | str (JSON) | Stock properties fetched from Notion via Notion MCP |

**Returns:** JSON with `passes_screen`, `score`, `conditions_met`, `passed`, `failed`, `unknown`.

**Example workflow:**
```
1. AI uses Notion MCP: notion-search("HCLTECH") → gets page
2. AI uses Notion MCP: notion-fetch(page_id) → gets all properties
3. AI uses StockPulse MCP: screen_stock({"PE": 28.5, "EPS": 62, ...}) → screening result
```

---

#### `screen_multiple_stocks`

Screen multiple stocks at once, returning ranked results by score.

| Parameter | Type | Description |
|-----------|------|-------------|
| `stocks_data` | str (JSON array) | Array of stock objects from Notion |

**Returns:** JSON with `results` array (sorted by score) and `summary` counts.

---

#### `detect_anomalies`

Detect notable patterns in stock data.

| Parameter | Type | Description |
|-----------|------|-------------|
| `stocks_data` | str (JSON array) | Array of stock objects from Notion |

Detects:
- **Piotroski Score ≥ 7**: strong fundamental quality
- **Promoter holding changes**: governance signals
- **High delivery %** (≥ 70%): potential institutional interest

**Returns:** JSON with `strong_fundamentals`, `governance_flags`, `high_delivery`, and `summary`.

---

#### `compare_sector`

Rank a stock against its sector peers on key metrics.

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_stock` | str (JSON) | The stock to rank |
| `peer_stocks` | str (JSON array) | Peer stocks from the same industry |

**Returns:** JSON with per-metric rankings (ROCE, ROE, PE, Debt, Promoter Hold, Piotroski, Screen Score) and an overall sector percentile.

---

#### `generate_report_content`

Generate structured markdown for a Notion page.

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_type` | str | One of: `Stock Analysis`, `Weekly Summary`, `Sector Report`, `Anomaly Alert`, `Screener Report` |
| `analysis_data` | str (JSON) | The analysis results to format into a report |

**Returns:** JSON with `title`, `report_type`, `content` (markdown), and `symbols_covered`. The AI then uses Notion MCP's `create-a-page` to publish this to Notion.

---

## Notion MCP Tools Used

These are tools provided by the official Notion MCP server (`https://mcp.notion.com/mcp`). StockPulse workflows use the following:

| Tool | Usage in StockPulse |
|------|-------------------|
| `notion-search` | Find stocks, databases, reports by name |
| `notion-fetch` | Get full page content and properties |
| `query-a-database-view` | Query Stocks Master, Daily Prices, Watchlist with filters |
| `create-a-page` | Write analysis reports, add to watchlist |
| `update-a-page` | Set AI Rating on stocks, update watchlist status |

See [Notion MCP Supported Tools](https://developers.notion.com/docs/mcp-supported-tools) for the full list.

---

## Prompt Templates

Prompts are multi-step orchestration templates that tell the AI agent which tools from **both** MCP servers to call and in what order.

---

### `stock_deep_dive(symbol)`

A full research brief for a single stock.

**Orchestration flow:**
1. **Notion MCP** → `notion-search` + `notion-fetch` to get stock fundamentals
2. **Notion MCP** → `query-a-database-view` to get price history
3. **StockPulse MCP** → `screen_stock` for 12-condition screening + score
4. **StockPulse MCP** → `detect_anomalies` for risk flags
5. **Notion MCP** → `query-a-database-view` to get sector peers
6. **StockPulse MCP** → `compare_sector` for ranking
7. **StockPulse MCP** → `generate_report_content` for formatted markdown
8. **Notion MCP** → `create-a-page` to save the report
9. **Notion MCP** → `update-a-page` to set AI Rating

**Invocation:** `Use the stock_deep_dive prompt for TRENT`

---

### `weekly_market_scan()`

A market-wide weekly scan that surfaces the best opportunities.

**Orchestration flow:**
1. **Notion MCP** → `query-a-database-view` to get all screened stocks
2. **StockPulse MCP** → `screen_multiple_stocks` for fresh rankings
3. **StockPulse MCP** → `detect_anomalies` for pattern detection
4. **StockPulse MCP** → `compare_sector` on top sectors
5. **StockPulse MCP** → `generate_report_content` for the report
6. **Notion MCP** → `create-a-page` to save the Weekly Summary
7. **Notion MCP** → `create-a-page` to add watchlist candidates

**Invocation:** `Run the weekly_market_scan prompt`

---

### `anomaly_investigation()`

A deep investigation of data anomalies.

**Orchestration flow:**
1. **Notion MCP** → `query-a-database-view` to fetch stock data
2. **StockPulse MCP** → `detect_anomalies` to find patterns
3. **Notion MCP** → `notion-fetch` for deep dives on flagged stocks
4. **StockPulse MCP** → `screen_stock` + `compare_sector` for analysis
5. **StockPulse MCP** → `generate_report_content` for the report
6. **Notion MCP** → `create-a-page` to save as Anomaly Alert

**Invocation:** `Investigate anomalies using the anomaly_investigation prompt`

---

## Example Conversations

### "Research a specific stock"
```
User: Deep dive on ABBOTINDIA and save the report to Notion

Claude: [Notion MCP: notion-search("ABBOTINDIA")]
[Notion MCP: notion-fetch(page_id) → gets fundamentals]
[Notion MCP: query-a-database-view(Daily Prices, filter) → gets prices]
[StockPulse MCP: screen_stock({PE: 48, EPS: 320, ...}) → score 87, passes]
[Notion MCP: query-a-database-view(Stocks Master, industry=Pharma) → peers]
[StockPulse MCP: compare_sector(target, peers) → 92nd percentile]
[StockPulse MCP: generate_report_content("Stock Analysis", {...})]
[Notion MCP: create-a-page(AI Reports DB, report_content)]
[Notion MCP: update-a-page(stock_page_id, AI Rating="Strong Buy")]

I've analyzed ABBOTINDIA and saved the report to Notion...
```

### "Weekly market scan"
```
User: Run the weekly market scan

Claude: [Notion MCP: query-a-database-view(Stocks Master, Passes Screen=true)]
[StockPulse MCP: screen_multiple_stocks([...898 stocks...])]
[StockPulse MCP: detect_anomalies([...data...])]
[StockPulse MCP: generate_report_content("Weekly Summary", {...})]
[Notion MCP: create-a-page(AI Reports DB, weekly_report)]
[Notion MCP: create-a-page(Watchlist DB, {Stock: "TRENT", Status: "Watching"})]

Weekly Market Pulse report saved to Notion with 5 watchlist candidates...
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

When `HAS_MCP = False`, the `@_tool()` and `@_prompt()` decorators become no-ops. Tool functions are still importable and callable as regular Python functions — they just aren't registered in an MCP server. The `serve` command will print a warning and exit cleanly.
