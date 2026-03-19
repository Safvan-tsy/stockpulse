# Troubleshooting

Common issues encountered during development and their fixes.

---

## Upload Errors

### `"Symbol is not a property that exists"` (400 Bad Request)

**Symptom:** Every stock upload fails with a message like:
```
Failed to upload DHATRE: Symbol is not a property that exists.
BSE Code is not a property that exists.
CMP is not a property that exists.
```

**Cause:** Notion's API now creates databases backed by a **Data Source** object. The classic `databases.retrieve()` returns `properties: null` for these. The schema lives under a separate data source endpoint, and pages must be created with `parent={"data_source_id": ...}` instead of `parent={"database_id": ...}`.

**Fix:** Run `stockpulse setup` or re-run `stockpulse pipeline` — `ensure_all_db_schemas()` is called automatically and repairs the schema before any upload.

If you're still seeing this after `setup`:
```bash
python - <<'PY'
from stockpulse.notion_setup import ensure_all_db_schemas
result = ensure_all_db_schemas()
for k, v in result.items():
    print(k, "→", v)
PY
```
This should print 5 data_source_ids. If any key maps to `None`, your `notion_db_ids.json` may have a stale or invalid database ID.

---

### `"Object not found"` (404)

**Symptom:**
```
notion_client.errors.APIResponseError: Could not find database with ID: xxxxx
```

**Cause:** The database ID in `notion_db_ids.json` is wrong, or the database was deleted from Notion.

**Fix:**
1. Check if the databases exist in Notion (open the parent page)
2. If deleted, re-run `stockpulse setup` to recreate them
3. If they exist but IDs have changed, copy the correct IDs from the database URLs and update `notion_db_ids.json`

---

### Rate Limit Errors (429)

**Symptom:**
```
notion_client.errors.APIResponseError: Rate Limited
```

**Cause:** Notion allows ~3 API calls/second per integration. If you're running other tools that also use the same integration token, you may hit this.

**Fix:**
- Don't run multiple `stockpulse` commands simultaneously
- Consider creating a separate Notion integration token just for StockPulse
- The built-in 0.34s delay between calls is designed to stay within limits

---

### `"Page not found"` when creating pages

**Symptom:** Creates fail with 404 on `pages.create()`.

**Cause:** Often happens when `data_source_id` is `None` (schema setup failed silently).

**Diagnosis:**
```bash
python - <<'PY'
from stockpulse.notion_setup import ensure_all_db_schemas
ds = ensure_all_db_schemas()
print(ds)
PY
```
Any `None` values indicate the data source ID wasn't retrieved.

---

## Setup Issues

### `"NOTION_TOKEN" not set`

**Symptom:**
```
notion_client.errors.APIResponseError: API token is invalid.
```

**Fix:**
1. Check your `.env` file has `NOTION_TOKEN=secret_xxx...`
2. Make sure you're running from the project root (where `.env` is)
3. Or set the environment variable directly:
   ```bash
   export NOTION_TOKEN=secret_xxxxxxx
   ```

---

### `notion_db_ids.json` not found

**Symptom:**
```
FileNotFoundError: notion_db_ids.json
```

**Fix:** Run setup first:
```bash
stockpulse setup
```

---

### `"The parent page isn't shared with this integration"`

**Symptom:**
```
notion_client.errors.APIResponseError: The parent page isn't shared with this integration.
```

**Fix:** You need to share the parent Notion page with your integration:
1. Open the parent page in Notion
2. Click `...` → **Connections**
3. Find your StockPulse integration and click **Connect**

---

## Parser Issues

### `KeyError` on specific columns

**Symptom:**
```
KeyError: 'pe'
```
or
```
KeyError: 'ROCE'
```

**Cause:** The Excel file has different column names than expected in `FUNDA_COLS_MAP` or `FUNDA_CHART_COLS`.

**Diagnosis:**
```bash
python - <<'PY'
import pandas as pd
df = pd.read_excel("workbook/DailyData_Fundamentally Good Ones.xlsx",
                   sheet_name="Funda_Comparisons", nrows=2, engine="openpyxl")
print(df.columns.tolist())
PY
```
Compare the output to `FUNDA_COLS_MAP` in [src/stockpulse/parser.py](../src/stockpulse/parser.py) and update the mappings if your Excel has different headers.

---

### Numeric or `(blank)` symbols in the data

**Symptom:** The screener output shows rows like `1.32`, `3.53`, `(blank)` as stock symbols.

**Cause:** The `Funda Charts` sheet has a different structure where the first rows are numeric metadata before the `Symbol` column starts.

**Fix:** Already handled in the current parser. The `build_stocks_master()` function:
- Filters rows where `symbol` is `(blank)`
- Filters rows where `symbol` looks like a pure number (`symbol.replace('.','').isdigit()`)
- Deduplicates by symbol

If you're still seeing this with a different workbook, check `load_funda_charts()` in `parser.py`.

---

### Empty stocks DataFrame

**Symptom:**
```
Stocks Master: 0 stocks, 0 columns
```

**Cause:** The workbook path is wrong or the sheet name doesn't match.

**Fix:**
```bash
# Check the sheet names in your workbook
python - <<'PY'
import openpyxl
wb = openpyxl.load_workbook("workbook/DailyData_Fundamentally Good Ones.xlsx",
                             read_only=True)
print(wb.sheetnames)
wb.close()
PY
```
The parser expects sheets named `Funda_Comparisons`, `Data`, and `Funda Charts`. If your workbook uses different names, update the `sheet_name=` arguments in `parser.py`.

---

## MCP Server Issues

### `"stockpulse serve" prints warning and exits`

**Symptom:**
```
MCP package not available. Install: pip install -e ".[mcp]"
```

**Fix:**
1. Confirm you're using Python 3.10+:
   ```bash
   python --version
   ```
2. Install the MCP extra:
   ```bash
   pip install -e ".[mcp]"
   ```
3. If you have Python 3.9 only, the MCP server cannot be used. You can still use all the CLI commands and the Notion integration — just not the AI agent tools.

---

### Claude Desktop doesn't show the 🔨 icon

**Causes and fixes:**

1. **Config file not found:** Make sure you're editing the right file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **JSON syntax error:** Validate your config file:
   ```bash
   python -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. **Wrong Python path:** Use the absolute path to `.venv/bin/python`:
   ```bash
   which python  # if .venv is activated
   # Copy this exact path into the config
   ```

4. **Claude not restarted:** Fully quit and restart Claude Desktop after saving the config.

---

### MCP tools return empty results

**Symptom:** Claude calls a tool like `get_screened_stocks` but gets `[]`.

**Cause:** The pipeline hasn't been run yet, or ran with errors.

**Fix:**
1. Run `stockpulse pipeline` to populate the databases
2. Then open Notion and confirm rows exist in the Stocks Master database with `Passes Screen = ✅`

---

## Performance

### Upload is very slow

**Expected behavior:** 5,750 stocks takes ~32 minutes. This is by design — Notion's rate limit is 3 requests/second.

**If you need a faster first test:**
```bash
# Upload only stocks + screener, skip prices
stockpulse upload --skip-prices

# Or just test with a small batch manually
python - <<'PY'
import pandas as pd
from stockpulse.parser import build_stocks_master
from stockpulse.screener import screen_dataframe
from stockpulse.uploader import upload_stocks_master

master = build_stocks_master()
master_small = master.head(50)  # test with first 50 only
screen = screen_dataframe(master_small)
upload_stocks_master(master_small, screen)
PY
```

---

### Python is too slow to parse the 68 MB Excel

**Symptom:** `stockpulse parse` takes more than 2 minutes.

**Cause:** `openpyxl` is slow for large workbooks. This is expected.

**Options:**
- Use `engine="calamine"` if `python-calamine` is installed (faster reader)
- Pre-export the `Funda_Comparisons` sheet to a CSV for faster parsing

---

## Still Stuck?

1. Check the logs — all operations log at INFO level to stderr. Run with `2>&1 | tee debug.log` to capture them.
2. Check the [Notion API status](https://status.notion.so/) for outages.
3. Verify your integration token is still valid at [notion.so/my-integrations](https://www.notion.so/my-integrations).
4. For Data Sources API errors, see the full story in [Notion Integration](./notion-integration.md).
