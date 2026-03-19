# StockPulse India 📈

**AI-Powered Indian Stock Intelligence on Notion** — Built for the [Notion MCP Challenge](https://dev.to/challenges/notion-2026-03-04).

StockPulse takes daily price and delivery data from NSE & BSE, screens 5000+ stocks through **12 battle-tested fundamental conditions**, and uses an **AI agent (via Notion MCP)** to generate research reports, detect anomalies, and maintain a smart watchlist — all centralized in Notion.

## What It Does

1. **Data Pipeline** — Downloads BhavCopy + delivery data from NSE/BSE, or reads from pre-built Excel workbooks
2. **12-Condition Screener** — Filters stocks for: profitability (PE, EPS), growth (sales, profit YoY), governance (promoter pledging), financial health (debt/equity, current ratio, ROCE)
3. **Notion as Single Source of Truth** — 5 linked databases: Stocks Master, Daily Prices, Screener Results, Watchlist, AI Reports
4. **AI Intelligence via MCP** — An MCP server exposes tools for an AI agent to: query screened stocks, analyze fundamentals, detect anomalies, write research reports, and manage a watchlist — all reading from and writing to Notion

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

### Connect to Claude Desktop

Add to your Claude Desktop MCP config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "stockpulse": {
      "command": "python",
      "args": ["-m", "stockpulse", "serve"],
      "cwd": "/path/to/notion-mcp",
      "env": {
        "NOTION_TOKEN": "your-token-here",
        "NOTION_PARENT_PAGE_ID": "your-page-id"
      }
    }
  }
}
```

Then ask Claude: *"Use the weekly_market_scan prompt to analyze my stock portfolio"*

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

## MCP Tools (for AI Agents)

| Tool | What It Does |
|------|-------------|
| `get_screened_stocks` | Fetch stocks passing all 12 conditions, ranked by score |
| `get_stock_details` | Deep fundamental data for a specific symbol |
| `get_price_history` | Recent OHLCV + delivery data for a symbol |
| `get_stocks_by_industry` | All screened stocks in a sector |
| `list_industries` | Sector breakdown with stock counts |
| `get_screening_conditions` | The 12 screening rules |
| `get_watchlist` | Current watchlist with notes & alerts |
| `add_to_watchlist` | Add a stock to the watchlist |
| `write_analysis_report` | Create an AI research report in Notion |
| `update_stock_ai_rating` | Set AI rating (Strong Buy/Buy/Hold/Avoid) |
| `detect_anomalies` | Find unusual patterns in the data |

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
NSE/BSE APIs → Python Data Pipeline → Notion Databases → MCP Server → AI Agent
                                            ↕
                                      Human-in-the-Loop
                                   (review, watchlist, notes)
```

## License

MIT
