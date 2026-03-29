# Setup Guide

This guide walks you through getting StockPulse India running from scratch, including all Notion configuration steps.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.9+ | 3.12 recommended. MCP server requires 3.10+. |
| Notion account | Free tier is sufficient |
| Notion integration (API key) | Takes 2 minutes — see below |
| Excel workbooks | `DailyData_Fundamentally Good Ones.xlsx` in `workbook/` |

---

## Step 1 — Clone and Install

```bash
git clone <repo-url>
cd notion-mcp

# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate   # Windows

# Install the package and all dependencies
pip install -e .
```

**Verify the install:**
```bash
stockpulse --help
# or:
python -m stockpulse --help
```

You should see the list of 9 commands.

### Optional: MCP server support

The MCP server requires Python 3.10+ and the `mcp` package:
```bash
pip install -e ".[mcp]"
```

---

## Step 2 — Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **New integration**
3. Name it (e.g., `StockPulse`)
4. Select your workspace
5. Under **Capabilities**, make sure all three are enabled:
   - Read content
   - Update content
   - Insert content
6. Click **Save**
7. Copy the **Internal Integration Token** — it looks like `secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## Step 3 — Create a Notion Page for the Databases

StockPulse needs a parent page in Notion to create its 5 databases under.

1. Open Notion in your browser
2. In the left sidebar, click **+ New page**
3. Name it something like `StockPulse India`
4. **Share this page with your integration:**
   - Click the **...** (three dots) menu at the top right
   - Click **Connections** (or **Share** → **Invite**)
   - Find your `StockPulse` integration and click **Confirm**

5. **Get the page ID:**
   - Look at the URL in your browser: `https://www.notion.so/Your-Page-Name-`**`18770b1b6e3b402e9b1e42883ec5d284`**
   - The long hex string at the end is the page ID
   - If it has hyphens already: `18770b1b-6e3b-402e-9b1e-42883ec5d284` — either format works

---

## Step 4 — Configure `.env`

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_PARENT_PAGE_ID=18770b1b6e3b402e9b1e42883ec5d284
```

You can verify this with:
```bash
python - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv()
print("Token set:", bool(os.getenv("NOTION_TOKEN")))
print("Page ID set:", bool(os.getenv("NOTION_PARENT_PAGE_ID")))
PY
```

---

## Step 5 — Place Your Excel Workbooks

The workbooks should be in the `workbook/` directory:

```
notion-mcp/
└── workbook/
    ├── DailyData_Fundamentally Good Ones.xlsx   ← required
    └── DailyData_All_With Chart2.xlsx           ← optional
```

If your files are elsewhere, use the `--file` flag with any command:
```bash
stockpulse pipeline --file /path/to/your/workbook.xlsx
```

---

## Step 6 — Create Notion Databases

```bash
python -m stockpulse setup
```

This creates 5 databases under your parent page:
- `StockPulse — Stocks Master`
- `StockPulse — Daily Prices`
- `StockPulse — Screener Results`
- `StockPulse — Watchlist`
- `StockPulse — AI Reports`

Their IDs are saved to `notion_db_ids.json` in the project root. Do not delete this file.

**Expected output:**
```
Setting up Notion databases...

Databases created:
  stocks_master: 18770b1b-6e3b-...
  daily_prices: f4bd67d6-3b7e-...
  screener: 45ed576d-2bf8-...
  watchlist: fb5d5479-29a0-...
  reports: cb8f5a3c-3cfb-...

Database IDs saved to notion_db_ids.json
```

---

## Step 7 — Verify with Parse & Screen

Before uploading, verify your data looks correct:

```bash
# Verify data parsing
python -m stockpulse parse

# Run the screener only (no Notion calls)
python -m stockpulse screen
```

**Expected `parse` output:**
```
Parsing Excel data...

Stocks Master: 5750 stocks, 96 columns
Daily Prices: 109561 rows, 440 symbols
Date range: 2025-01-20 → 2026-03-06

Sample columns: ['symbol', 'bse_code', 'bse_id', 'cmp', 'industry', ...]

Top 10 stocks (by market cap):
  RELIANCE            ₹  1,999,742 Cr  [Refineries]
  TCS                 ₹  1,402,831 Cr  [IT - Software]
  ...
```

**Expected `screen` output:**
```
=== StockPulse India — Screener Results ===
Total stocks analyzed: 5750
Stocks passing ALL conditions: 898 (15.6%)
Average score (passing stocks): 82.9 / 100

Top 10 by score:
  HARSHDEEP          100.0   12/12   (all pass)
  PIXTRANS           100.0   12/12   (all pass)
  ...
```

---

## Step 8 — Run the Full Pipeline

```bash
python -m stockpulse pipeline
```

This runs everything in sequence:
1. Parses Excel data
2. Runs the screener
3. Uploads 5,750 stocks to Notion
4. Uploads 898 screener results
5. Uploads 15 days of price data
6. Creates the dashboard page

**Time estimate:** 35–50 minutes (bulk of the time is the stock upload — ~5,750 API calls at rate-limited 3 req/s).

**Progress output:**
```
============================================================
  StockPulse India — Full Pipeline
============================================================

[1/5] Parsing Excel data...
  → 5750 stocks loaded

[2/5] Running 12-condition screener...
=== Screener Results ===
... (summary)

[3/5] Uploading stocks to Notion...
Schema ensured for stocks_master ✅
Schema ensured for daily_prices ✅
Schema ensured for screener ✅
Schema ensured for watchlist ✅
Schema ensured for reports ✅
Uploading 5750 stocks to Stocks Master ...
  → 5750 stocks uploaded

  Uploading screener results...

[4/5] Uploading last 15 days of prices...
  → XXXX price rows uploaded

[5/5] Creating dashboard page...

============================================================
  Pipeline complete! Check your Notion workspace.
============================================================
```

---

## Step 9 — Connect Both MCP Servers

StockPulse uses a **dual-MCP architecture**:

| Server | Role | Transport |
|--------|------|-----------|
| **Notion MCP** (`https://mcp.notion.com/mcp`) | All Notion reads & writes (search, fetch, create, update pages) | HTTP / OAuth |
| **StockPulse MCP** (`python -m stockpulse serve`) | Pure computation — screening, scoring, anomaly detection, sector comparison, report generation | stdio |

The AI agent orchestrates between both: it reads data from Notion via the official Notion MCP, sends it to StockPulse MCP for analysis, then writes results back to Notion.

### Option A — VS Code (GitHub Copilot)

A `.vscode/mcp.json` is included in the repo with both servers pre-configured:

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

When you open the project in VS Code:
1. You'll be prompted to approve the MCP servers — click **Allow**
2. For Notion MCP, complete the OAuth flow when prompted
3. Both servers should show as connected in the Copilot chat panel

### Option B — Claude Desktop

**1. Connect Notion MCP:**
- Open Claude Desktop → Settings → Connectors
- Add `https://mcp.notion.com/mcp`
- Complete the OAuth flow to authorize your Notion workspace

**2. Connect StockPulse MCP:**

Open or create `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "stockpulse": {
      "command": "/path/to/notion-mcp/.venv/bin/python",
      "args": ["-m", "stockpulse", "serve"],
      "cwd": "/path/to/notion-mcp"
    }
  }
}
```

**3.** Restart Claude Desktop

**4.** You should see a hammer icon (🔨) in the Claude input area — that indicates MCP tools are available

**5.** Try:
   ```
   Use the weekly_market_scan prompt to analyze the stock market
   ```

### Option C — Cursor

Add both servers in Cursor's MCP settings (Settings → MCP):

- **Notion MCP**: Type `http`, URL `https://mcp.notion.com/mcp`
- **StockPulse MCP**: Type `stdio`, command `python -m stockpulse serve`, cwd `/path/to/notion-mcp`

---

## Subsequent Runs

After the first full pipeline run, you typically only need to refresh prices:

```bash
# Upload only the last N days of prices (much faster)
python -m stockpulse upload-prices --days 5
```

Or re-run the full pipeline to refresh fundamentals (quarterly):
```bash
python -m stockpulse pipeline
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NOTION_TOKEN` | Yes | — | Integration secret from notion.so/my-integrations |
| `NOTION_PARENT_PAGE_ID` | Yes | — | Page ID of the parent Notion page |
| `DATA_DIR` | No | `./data` | Directory for downloaded data files |
| `WORKBOOK_DIR` | No | `./workbook` | Directory containing Excel workbooks |
