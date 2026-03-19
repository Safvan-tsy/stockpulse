# Architecture Overview

## Core Concept

StockPulse India is built around a single principle: **Notion is the single source of truth**. All data flows into Notion, and all AI interactions happen through the Notion layer.

```
┌──────────────────────────────────────────────────────────────────┐
│                        NOTION WORKSPACE                          │
│                                                                  │
│  ┌─────────────────┐    ┌──────────────────┐                    │
│  │  Stocks Master  │◄───│  Screener Results│                    │
│  │  (5,750 rows)   │    │  (898 rows)      │                    │
│  └────────┬────────┘    └──────────────────┘                    │
│           │                                                      │
│  ┌────────▼────────┐    ┌──────────────────┐                    │
│  │  Daily Prices   │    │    Watchlist      │                    │
│  │  (109k+ rows)   │    │  (user curated)  │                    │
│  └─────────────────┘    └──────────────────┘                    │
│                                                                  │
│  ┌──────────────────────────────────────────┐                   │
│  │          AI Analysis Reports              │                   │
│  │  (pages written by AI agent)             │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │ Notion API (Data Sources)
       ┌─────────────────┼─────────────────────┐
       │                 │                     │
  ┌────▼────┐    ┌────────▼──────┐    ┌────────▼──────┐
  │  MCP    │    │   Uploader    │    │    Notion     │
  │ Server  │    │   Pipeline    │    │    Setup      │
  │(11 tools│    │(bulk inserts) │    │(schema mgmt)  │
  │3 prompts│    └────────┬──────┘    └───────────────┘
  └────┬────┘             │
       │           ┌──────▼──────┐
       │           │   Screener  │
       │           │  (12 rules) │
       │           └──────┬──────┘
       │                  │
       │           ┌──────▼──────┐
       │           │   Parser    │
  ┌────▼────┐      │  (Excel →   │
  │  Claude │      │  DataFrame) │
  │  / GPT  │      └──────┬──────┘
  │  (AI)   │             │
  └─────────┘      ┌──────▼──────┐
                   │  Workbooks  │
                   │  (NSE/BSE   │
                   │   .xlsx)    │
                   └─────────────┘
```

---

## Components

### 1. Parser (`parser.py`)

Reads the Excel workbooks and produces clean pandas DataFrames.

**Input files (in `workbook/`):**

| File | Size | Contents |
|------|------|----------|
| `DailyData_Fundamentally Good Ones.xlsx` | 68 MB | Primary workbook — 5,750 stocks, fundamentals + prices |
| `DailyData_All_With Chart2.xlsx` | 257 MB | All-stocks version (optional, for broader queries) |

**Sheets parsed:**

| Sheet | Output | Rows |
|-------|--------|------|
| `Funda_Comparisons` | `stocks_master` DataFrame | 5,750 stocks × 96 cols |
| `Data` | `daily_prices` DataFrame | 109,561 rows × 17 cols |

**Key transforms:**
- Maps raw Excel headers to clean snake_case field names
- Filters out junk rows (`(blank)` symbols, numeric-only symbols)
- Deduplicates by `symbol` (keeps first occurrence)
- Parses dates, coerces numerics

---

### 2. Screener (`screener.py`)

Applies 12 fundamental conditions to every stock in the master DataFrame.

**Conditions:**

| # | Name | Field | Condition | Category |
|---|------|-------|-----------|----------|
| 1 | pe_positive | `pe` | > 0 | Valuation |
| 2 | eps_positive | `eps` | > 0 | Profitability |
| 3 | sales_qtr_positive | `sales_qrt` | > 0 | Revenue |
| 4 | yoy_sales_growth | `sales_var_pct` | > 0% | Growth |
| 5 | net_profit_positive | `np_qrt` | > 0 | Profitability |
| 6 | yoy_profit_not_declining | `profit_var_pct` | > -10% | Growth |
| 7 | low_pledging | `pledged_pct` | < 10% | Governance |
| 8 | unpledged_promo_hold | `unpledged_promo_pct` | > 30% | Governance |
| 9 | promo_hold_stable | `ch_promo_hold_pct` | >= 0% | Conviction |
| 10 | low_debt | `Debt Eq Ratio %` | 0–1 | Financial Health |
| 11 | current_ratio_healthy | `Current Ratio %` | > 1 | Liquidity |
| 12 | roce_decent | `ROCE` | >= 10% | Efficiency |

**Scoring:**
- Each condition contributes to a 0–100 score
- `passes_screen` = True only if all non-missing conditions pass
- **Results as of March 2026:** 898 stocks pass (out of 5,750 total)

---

### 3. Notion Setup (`notion_setup.py`)

Creates the 5 Notion databases and manages their schemas.

**Key function:** `ensure_all_db_schemas(db_ids=None) -> dict[str, str]`

- Reads `notion_db_ids.json` (or the passed mapping)
- For each database, calls `client.data_sources.retrieve()` to check existing properties
- Adds any missing properties via `client.data_sources.update()`
- Renames the default `Name` title property to the correct name per DB
- Returns a `{db_key: data_source_id}` mapping used by uploader/mcp_server

> **Why this exists:** Notion's API now creates databases backed by a *Data Source* object. Properties live under `data_source_id` rather than `database_id`. Classic `databases.retrieve()` returns `properties: null`. This function bridges that gap. See [Notion Integration](./notion-integration.md) for the full story.

---

### 4. Uploader (`uploader.py`)

Bulk-inserts stock data into Notion with rate limiting.

**Three upload functions:**

| Function | Source | Target DB | Volume |
|----------|--------|-----------|--------|
| `upload_stocks_master(master, screen_results)` | stocks DataFrame | Stocks Master | 5,750 pages |
| `upload_screener_results(screen_results, symbol_to_page)` | screener DataFrame | Screener Results | 898 pages |
| `upload_daily_prices(prices, symbol_to_page)` | prices DataFrame | Daily Prices | up to 109k pages |

**Rate limiting:** A 0.34 s pause between API calls (~3 req/s, respecting Notion's limit of ~3 req/s per integration).

---

### 5. MCP Server (`mcp_server.py`)

Exposes the Notion databases as tools for an AI agent.

**Built on:** FastMCP (from the `mcp` package — Python 3.10+ only; gracefully degrades on 3.9)

**11 Tools:**

| Tool | Category | Reads/Writes |
|------|----------|-------------|
| `get_screened_stocks` | Query | Reads Stocks Master |
| `get_stock_details` | Query | Reads Stocks Master |
| `get_price_history` | Query | Reads Daily Prices |
| `get_stocks_by_industry` | Query | Reads Stocks Master |
| `list_industries` | Query | Reads Stocks Master |
| `get_screening_conditions` | Info | (static) |
| `get_watchlist` | Query | Reads Watchlist |
| `add_to_watchlist` | Action | Writes Watchlist |
| `write_analysis_report` | Action | Writes AI Reports |
| `update_stock_ai_rating` | Action | Writes Stocks Master |
| `detect_anomalies` | Analysis | Reads Daily Prices + Stocks Master |

**3 Prompt Templates:**
- `stock_deep_dive(symbol)` — Full research brief for a single stock
- `weekly_market_scan()` — Market-wide scan, sector breakdown, top picks
- `anomaly_investigation(symbol)` — Delivery/price anomaly deep dive

---

### 6. Dashboard (`dashboard.py`)

Creates a Notion page that serves as the StockPulse home page, including:
- Project description
- Links to each of the 5 databases
- Summary of screening conditions
- Instructions for AI agent use

---

### 7. CLI (`cli.py`)

Click-based command-line interface with 9 commands. See [CLI Reference](./cli-reference.md).

---

## Data Flow (Full Pipeline)

```
workbook/*.xlsx
      │
      ▼ parser.build_stocks_master()
stocks DataFrame (5,750 rows × 96 cols)
      │
      ├──▶ screener.screen_dataframe()
      │           │
      │           ▼
      │    screen_results DataFrame (5,750 rows, adds: passes_screen, score, failed_conditions)
      │
      ▼ uploader.upload_stocks_master(master, screen_results)
Notion: Stocks Master DB ← 5,750 pages
Returns: {symbol: page_id} mapping
      │
      ├──▶ uploader.upload_screener_results(screen_results, symbol_to_page)
      │           └──▶ Notion: Screener Results DB ← 898 pages (linked to Stocks Master)
      │
      ▼ parser.get_latest_prices(days=15)
prices DataFrame (last 15 days, all 440 symbols)
      │
      ▼ uploader.upload_daily_prices(prices, symbol_to_page)
Notion: Daily Prices DB ← ~6,600 pages (linked to Stocks Master)
      │
      ▼ dashboard.create_dashboard_page()
Notion: Dashboard page created
```

---

## Notion Database Schemas

### Stocks Master
Primary reference table. One row per stock symbol.

| Property | Notion Type | Notes |
|----------|------------|-------|
| Symbol | Title | Primary key (e.g., `HCLTECH`) |
| BSE Code | Number | BSE numeric code |
| ISIN | Text | ISIN identifier |
| Industry | Select | e.g., `IT - Software` |
| Group | Select | BSE group: A, B, T, etc. |
| CMP | Number (₹) | Current market price |
| Market Cap (Cr) | Number | In crores INR |
| PE | Number | Price-to-earnings ratio |
| EPS | Number | Earnings per share |
| Sales Qrt (Cr) | Number | Quarterly sales |
| NP Qrt (Cr) | Number | Quarterly net profit |
| Sales Var % | Number (%) | YoY quarterly sales growth |
| Profit Var % | Number (%) | YoY quarterly profit growth |
| Debt/Equity | Number | Leverage ratio |
| Current Ratio | Number | Short-term liquidity |
| ROCE % | Number (%) | Return on capital employed |
| ROE % | Number (%) | Return on equity |
| Promoter Hold % | Number (%) | Promoter shareholding |
| Pledged % | Number (%) | Pledged shares as % |
| Unpledged Promo % | Number (%) | Free promoter holding |
| Ch Promo Hold % | Number (%) | Change in promoter holding |
| FII Hold % | Number (%) | Foreign institutional investors |
| DII Hold % | Number (%) | Domestic institutional investors |
| Piotroski Score | Number | 0–9 financial strength score |
| Passes Screen | Checkbox | True if all 12 conditions pass |
| Screen Score | Number | 0–100 quality score |
| AI Rating | Select | Strong Buy / Buy / Hold / Avoid |
| Last Updated | Date | Date of last data update |

### Daily Prices
Time-series table. One row per symbol per trading day.

| Property | Notion Type | Notes |
|----------|------------|-------|
| Entry | Title | `SYMBOL-YYYY-MM-DD` |
| Date | Date | Trading date |
| Open / High / Low / Close | Number (₹) | OHLC prices |
| Prev Close | Number (₹) | Previous close |
| Volume | Number | Total traded quantity |
| Delivery Qty | Number | Delivery quantity |
| Delivery % | Number (%) | Delivery as % of volume |
| Turnover (Cr) | Number | Turnover in crores |
| Total Trades | Number | Number of trades |
| Stock | Relation | → Stocks Master |

### Screener Results
Filtered output. One row per stock that passes the screen.

| Property | Notion Type |
|----------|------------|
| Stock (Title) | Title |
| Screen Date | Date |
| Conditions Met | Number |
| Failed Conditions | Multi-select |
| Score | Number (0–100) |
| AI Commentary | Text |

### Watchlist
User-curated list of stocks under active monitoring.

| Property | Notion Type |
|----------|------------|
| Stock | Title |
| Added Date | Date |
| User Notes | Text |
| AI Alerts | Text |
| Status | Select (Watching / Entered / Exited) |
| Stock Ref | Relation → Stocks Master |

### AI Analysis Reports
Page-level reports written by the AI agent.

| Property | Notion Type |
|----------|------------|
| Title | Title |
| Report Date | Date |
| Report Type | Select (Weekly Scan / Deep Dive / Anomaly / Custom) |
| Stocks Covered | Multi-select |

---

## Directory Structure

```
notion-mcp/
├── src/
│   └── stockpulse/
│       ├── __init__.py
│       ├── __main__.py        # Entry point: python -m stockpulse
│       ├── cli.py             # Click CLI (9 commands)
│       ├── config.py          # .env loader, DB names, screen conditions
│       ├── parser.py          # Excel → DataFrame
│       ├── screener.py        # 12-condition engine + scoring
│       ├── notion_setup.py    # DB creation, schema management
│       ├── uploader.py        # Bulk upload to Notion
│       ├── mcp_server.py      # FastMCP server (11 tools, 3 prompts)
│       ├── dashboard.py       # Notion dashboard page creator
│       └── downloader.py      # NSE/BSE BhavCopy downloader
├── workbook/
│   ├── DailyData_Fundamentally Good Ones.xlsx   # Primary data (68 MB)
│   └── DailyData_All_With Chart2.xlsx           # Full universe (257 MB)
├── docs/                      # This documentation
├── notion_db_ids.json         # Auto-generated after setup (gitignored)
├── .env                       # Secrets (gitignored)
├── .env.example               # Template for .env
├── pyproject.toml             # Package config + dependencies
└── requirements.txt           # Pip-installable deps list
```
