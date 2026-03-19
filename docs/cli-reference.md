# CLI Reference

StockPulse exposes all functionality through a `stockpulse` command (or `python -m stockpulse`).

```bash
stockpulse --help
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| [`setup`](#setup) | Create all 5 Notion databases |
| [`parse`](#parse) | Parse Excel workbooks and show a data summary |
| [`screen`](#screen) | Run the 12-condition screener and save results |
| [`upload`](#upload) | Upload stocks + screener + prices to Notion |
| [`upload-prices`](#upload-prices) | Upload only recent prices (faster incremental update) |
| [`dashboard`](#dashboard) | Create the StockPulse dashboard page in Notion |
| [`download`](#download) | Download fresh NSE/BSE BhavCopy data |
| [`serve`](#serve) | Start the MCP server |
| [`pipeline`](#pipeline) | Full pipeline: parse → screen → upload → dashboard |

---

## `setup`

Creates all 5 Notion databases under your configured parent page and writes their IDs to `notion_db_ids.json`.

```bash
stockpulse setup
```

**When to use:** Once, before first upload. If you delete databases and need to recreate them.

**Output:**
```
Setting up Notion databases...

Databases created:
  stocks_master: 18770b1b-6e3b-402e-9b1e-42883ec5d284
  daily_prices:  f4bd67d6-3b7e-44fa-b13c-709d72206a00
  screener:      45ed576d-2bf8-43dc-b4fe-6b224a325ed4
  watchlist:     fb5d5479-29a0-4be2-ad01-0eada1af21cc
  reports:       cb8f5a3c-3cfb-465b-98ff-97f6c9fe143a

Database IDs saved to notion_db_ids.json
```

---

## `parse`

Parses the Excel workbooks and prints a data quality summary. Makes no Notion API calls.

```bash
stockpulse parse [--file PATH]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--file PATH` | `workbook/DailyData_Fundamentally Good Ones.xlsx` | Path to Excel workbook |

**When to use:** Verifying that your Excel data is being read correctly before uploading.

**Example output:**
```
Parsing Excel data...

Stocks Master: 5750 stocks, 96 columns
Daily Prices: 109561 rows, 440 symbols
Date range: 2025-01-20 → 2026-03-06

Sample columns: ['symbol', 'bse_code', 'bse_id', 'cmp', 'industry', 'market_cap_cr', ...]

Top 10 stocks (by market cap):
  RELIANCE              ₹  1,999,742 Cr  [Refineries]
  TCS                   ₹  1,402,831 Cr  [IT - Software]
  HDFCBANK              ₹  1,354,920 Cr  [Banks - Private Sector]
  ...
```

---

## `screen`

Runs the 12-condition screener on all stocks and saves results to `screener_results.csv`. Makes no Notion API calls.

```bash
stockpulse screen [--file PATH]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--file PATH` | Default workbook | Path to Excel workbook |

**When to use:** Testing the screener, checking which stocks pass, validating condition logic.

**Example output:**
```
Loading data and running screener...

=== StockPulse India — Screener Results ===
Total stocks analyzed: 5750
Stocks passing ALL conditions: 898 (15.6%)
Average score (passing stocks): 82.9 / 100

Top 10 by score:
  Rank  Symbol          Score   Conditions   Status
     1  HARSHDEEP       100.0   12/12        ✅ PASS
     2  PIXTRANS        100.0   12/12        ✅ PASS
     3  DMR              98.0   12/12        ✅ PASS
     4  JBCHEPHARM       98.0   12/12        ✅ PASS
     5  MEHUL            98.0   12/12        ✅ PASS
     ...

Results saved to screener_results.csv
```

---

## `upload`

Uploads the full dataset (stocks master + screener results + recent prices) to Notion.

```bash
stockpulse upload [--file PATH] [--days N] [--skip-prices]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--file PATH` | Default workbook | Path to Excel workbook |
| `--days N` | `30` | Upload last N days of price data |
| `--skip-prices` | False | Skip price upload (faster, just stocks + screener) |

**When to use:** Full data refresh. If you have already run `setup`, this can be re-run to update data.

**Example:**
```bash
# Upload everything including 7 days of prices
stockpulse upload --days 7

# Upload only stocks and screener results, skip prices
stockpulse upload --skip-prices
```

---

## `upload-prices`

Uploads only recent daily price data to Notion. Much faster than a full upload.

```bash
stockpulse upload-prices [--file PATH] [--days N]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--file PATH` | Default workbook | Path to Excel workbook |
| `--days N` | `10` | Upload last N days |

**When to use:** Daily/incremental updates. Run this each morning after updating your workbook.

**Example:**
```bash
# Upload today's data only
stockpulse upload-prices --days 1

# Upload last week
stockpulse upload-prices --days 5
```

---

## `dashboard`

Creates a Notion page that serves as the StockPulse home page with an overview, links to all databases, and instructions.

```bash
stockpulse dashboard
```

**When to use:** Once, after running `setup` and `upload`. Can be re-run to recreate.

---

## `download`

Downloads fresh BhavCopy + delivery data from NSE and BSE for a given date.

```bash
stockpulse download [--date YYYY-MM-DD]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--date YYYY-MM-DD` | Last trading day | Date to download data for |

**When to use:** Getting fresh data. The downloaded files are saved to `DATA_DIR` (default: `./data/`).

**Example:**
```bash
# Download last trading day
stockpulse download

# Download specific date
stockpulse download --date 2026-03-10
```

---

## `serve`

Starts the MCP server so AI agents can connect to StockPulse.

```bash
stockpulse serve
```

**Requirements:**
- Python 3.10 or higher
- `mcp` package installed: `pip install -e ".[mcp]"`

**When to use:**
- When connecting to Claude Desktop
- When building AI agent workflows

The server runs on stdio (standard input/output), which is how Claude Desktop communicates with MCP servers. You don't invoke this directly in normal use — Claude Desktop manages the process.

**Note:** On Python 3.9, this command will print a warning and exit gracefully since the `mcp` package requires 3.10+.

---

## `pipeline`

Runs the full workflow in sequence: parse → screen → upload stocks → upload screener → upload prices → create dashboard.

```bash
stockpulse pipeline [--file PATH] [--days N]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--file PATH` | Default workbook | Path to Excel workbook |
| `--days N` | `15` | Days of price history to upload |

**When to use:** First run, or a complete periodic refresh.

**Approximate runtime:**
- Parse: ~30 seconds
- Screen: ~5 seconds
- Upload stocks (5,750): ~32 minutes
- Upload screener (898): ~5 minutes
- Upload prices (varies by `--days`): ~3–15 minutes
- Dashboard: ~5 seconds
- **Total: ~40–55 minutes**

**Example:**
```bash
# Full pipeline, last 15 days of prices
stockpulse pipeline

# Full pipeline with custom workbook and 30 days of prices
stockpulse pipeline --file /data/my_workbook.xlsx --days 30
```

---

## Tips

**Using with `python -m` instead of `stockpulse`:**
If the `stockpulse` command is not on your PATH (e.g., virtual environment not activated), use:
```bash
.venv/bin/python -m stockpulse <command>
```

**Verbose logging:**
Log level is INFO by default. To reduce noise for large uploads:
```bash
stockpulse pipeline 2>/dev/null    # suppress INFO logs
```

**Parallel uploads (not supported):**
The Notion API rate limit is ~3 requests/second per integration. All uploads are sequential to respect this limit.
