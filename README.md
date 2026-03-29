# StockPulse India 📈

**AI-Powered Indian Stock Intelligence on Notion** — Built for the [Notion MCP Challenge](https://dev.to/challenges/notion-2026-03-04).

StockPulse takes daily price and delivery data from NSE & BSE, screens 5000+ stocks through **12 battle-tested fundamental conditions**, and uses a **dual-MCP architecture** — the official **Notion MCP** for workspace I/O plus a custom **StockPulse MCP** for domain computation — to generate research reports, detect anomalies, and maintain a smart watchlist — all centralized in Notion.

## What It Does

1. **Data Pipeline** — Downloads BhavCopy + delivery data from NSE/BSE, or reads from pre-built Excel workbooks
2. **12-Condition Screener** — Filters stocks for: profitability (PE, EPS), growth (sales, profit YoY), governance (promoter pledging), financial health (debt/equity, current ratio, ROCE)
3. **Notion as Single Source of Truth** — 5 linked databases: Stocks Master, Daily Prices, Screener Results, Watchlist, AI Reports
4. **Dual-MCP AI Intelligence** — The official Notion MCP (`https://mcp.notion.com/mcp`) handles all Notion reads/writes. A custom StockPulse MCP server provides pure computation: screening, scoring, anomaly detection, sector comparison, and report generation. The AI agent orchestrates between both.

## Quick Start

### Prerequisites
- Python 3.9+
- A Notion account with an [integration](https://www.notion.so/my-integrations)

### Setup

```bash
# 1. Clone and install
git clone <repo-url>
cd notion-mcp
pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env with your Notion token and parent page ID

# 3. Create Notion databases
python -m stockpulse setup

# 4. Run the full pipeline (parse Excel → screen → upload to Notion)
python -m stockpulse pipeline

# 5. Start the MCP server (for AI agent integration)
python -m stockpulse serve
```

### Connect Both MCP Servers

**VS Code (GitHub Copilot):** A `.vscode/mcp.json` is included in the repo:

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
      "args": ["-c", "source .venv/bin/activate && python -m stockpulse serve"]
    }
  }
}
```

**Claude Desktop:**
1. Notion MCP: Settings → Connectors → Add `https://mcp.notion.com/mcp` → complete OAuth
2. StockPulse MCP: Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

Then ask Claude: *"Use the weekly_market_scan prompt to analyze the stock market"*

## CLI Commands

| Command | Description |
|---------|-------------|
| `stockpulse setup` | Create all 5 Notion databases |
| `stockpulse parse` | Parse Excel workbooks and show summary |
| `stockpulse screen` | Run the 12-condition screener |
| `stockpulse upload` | Upload stocks + prices + screener results to Notion |
| `stockpulse upload-prices` | Upload only recent prices (faster) |
| `stockpulse dashboard` | Create the StockPulse dashboard page |
| `stockpulse download` | Download fresh NSE/BSE data |
| `stockpulse serve` | Start the MCP server |
| `stockpulse pipeline` | Full pipeline: parse → screen → upload → dashboard |

## MCP Tools (Dual-Server Architecture)

### Notion MCP (Official — `https://mcp.notion.com/mcp`)

Handles all Notion workspace I/O:

| Tool | Usage in StockPulse |
|------|-------------------|
| `notion-search` | Find stocks, databases, reports by name |
| `notion-fetch` | Get full page content and properties |
| `query-a-database-view` | Query Stocks Master, Daily Prices, Watchlist |
| `create-a-page` | Write analysis reports, add to watchlist |
| `update-a-page` | Set AI Rating on stocks, update watchlist |

### StockPulse MCP (Custom Computation Server)

Pure domain intelligence — no Notion SDK calls:

| Tool | What It Does |
|------|-------------|
| `get_screening_conditions` | The 12 screening rules |
| `screen_stock` | Screen one stock, compute quality score (0-100) |
| `screen_multiple_stocks` | Screen many stocks, return ranked results |
| `detect_anomalies` | Find Piotroski ≥7, promoter changes, high delivery |
| `compare_sector` | Rank a stock against sector peers |
| `generate_report_content` | Format analysis into structured markdown |

## The 12 Screening Conditions

| # | Condition | Purpose |
|---|-----------|---------|
| 1 | PE > 0 | Profitable company |
| 2 | EPS > 0 | Positive earnings |
| 3 | Sales Qtr > 0 | Has revenue |
| 4 | YoY Sales Growth > 0% | Revenue growing |
| 5 | Net Profit Qtr > 0 | Making money |
| 6 | YoY Profit > -10% | Profit not collapsing |
| 7 | Promoter Pledging < 10% | Low insider risk |
| 8 | Unpledged Promoter Hold > 30% | Strong insider conviction |
| 9 | Change in Promoter Hold >= 0 | Insiders not dumping |
| 10 | Debt/Equity 0–1 | Not over-leveraged |
| 11 | Current Ratio > 1 | Short-term liquidity |
| 12 | ROCE >= 10% | Efficient capital use |

## Architecture

```
  ┌─────────────────────────────────────────────────┐
  │               NOTION WORKSPACE                   │
  │  Stocks Master │ Daily Prices │ Screener Results │
  │  Watchlist     │ AI Reports                      │
  └──────────┬──────────────────────────────────────┘
             │ Notion MCP (https://mcp.notion.com/mcp)
             │ (all reads + writes)
       ┌─────▼─────────────────────────┐
       │          AI AGENT              │
       │   (Claude / GPT / Copilot)     │
       └─────┬─────────────────────────┘
             │ StockPulse MCP (stdio, local)
             │ (pure computation)
       ┌─────▼─────────────────────────┐
       │   screen_stock()               │
       │   detect_anomalies()           │
       │   compare_sector()             │
       │   generate_report_content()    │
       └───────────────────────────────┘

  Data Pipeline (CLI, separate from MCP):
  NSE/BSE → Parser → Screener → Uploader → Notion DBs
                                     ↕
                               Human-in-the-Loop
                            (review, watchlist, notes)
```

## License

MIT
