# Data Pipeline

This document explains how StockPulse reads, processes, and screens stock data before sending it to Notion.

---

## Data Sources

### Excel Workbooks

All data comes from Excel workbooks produced by the NSE/BSE data download scripts. Two workbooks are used:

| Workbook | Size | Purpose |
|----------|------|---------|
| `DailyData_Fundamentally Good Ones.xlsx` | 68 MB | Primary source — the ~440 stocks that pass the basic screen, plus fundamentals |
| `DailyData_All_With Chart2.xlsx` | 257 MB | All-stocks version (~5,000+ stocks) — optional, broader queries |

The primary workbook has these sheets:

| Sheet | Contents |
|-------|----------|
| `Data` | Daily OHLCV + delivery data (timeseries) |
| `Funda_Comparisons` | Fundamental data for all stocks (one row per symbol) |
| `Funda Charts` | Per-stock chart data (multi-row per symbol) |
| `Industry Comparisons` | Sector-level aggregates |

---

## Stage 1: Parsing (`parser.py`)

### `build_stocks_master(excel_path=None) → DataFrame`

Builds the main stocks DataFrame from the `Funda_Comparisons` sheet.

**Process:**
1. Opens `Funda_Comparisons` sheet using `openpyxl` engine
2. Maps raw headers to clean snake_case names using `FUNDA_COLS_MAP`
3. Enriches with additional columns from `Funda Charts` sheet (ROCE, Current Ratio, Debt/Equity, Piotroski Score, etc.)
4. Filters junk rows:
   - Skips rows where `symbol` is `(blank)`
   - Skips rows where `symbol` is a pure numeric string (e.g., `1.32`, `3.53` — artefacts from chart rows)
5. Deduplicates by `symbol` — keeps the first occurrence

**Output:** DataFrame with ~96 columns and 5,750 rows.

**Key column mappings:**

| Excel Column | DataFrame Column | Description |
|-------------|-----------------|-------------|
| `SYMBOL` | `symbol` | Stock ticker |
| `BSE Code` | `bse_code` | BSE numeric code |
| `CMP (Rs.)` | `cmp` | Current market price |
| `Industry` | `industry` | Sector/industry |
| `MarketCap Rs Cr` | `market_cap_cr` | Market cap in crores |
| `P/E` | `pe` | Price/earnings ratio |
| `EPS` | `eps` | Earnings per share |
| `Sales Qrt (Rs. Cr.)` | `sales_qrt` | Quarterly sales |
| `NP Qrt (Rs. Cr.)` | `np_qrt` | Quarterly net profit |
| `Qrtly Sales Var (%)` | `sales_var_pct` | YoY quarterly sales growth |
| `Qrt Prof Var %` | `profit_var_pct` | YoY quarterly profit growth |
| `Promotor Hold %` | `promoter_hold_pct` | Promoter shareholding |
| `Pledged %` | `pledged_pct` | Pledged shares % |
| `Unpledged Promo Hold %` | `unpledged_promo_pct` | Free promoter % |
| `Ch In Promo Hold %` | `ch_promo_hold_pct` | Change in promoter holding |

From the `Funda Charts` sheet (merged in):

| Excel Column | DataFrame Column | Description |
|-------------|-----------------|-------------|
| `Debt Eq Ratio %` | `Debt Eq Ratio %` | Debt/equity ratio |
| `Current Ratio %` | `Current Ratio %` | Current ratio |
| `ROCE` | `ROCE` | Return on capital employed |
| `ROE %` | `roe_pct` | Return on equity |
| `FII Hold %` | `fii_hold_pct` | FII shareholding |
| `DII Hold %` | `dii_hold_pct` | DII shareholding |
| `Piotroski Score` | `piotroski_score` | 0–9 financial health score |

---

### `load_price_data(excel_path=None) → DataFrame`

Loads the timeseries OHLCV + delivery data from the `Data` sheet.

**Output:** DataFrame with ~17 columns and 109,561 rows covering Jan 2025 → Mar 2026.

| DataFrame Column | Description |
|-----------------|-------------|
| `date` | Trading date |
| `symbol` | Stock ticker |
| `open`, `high`, `low`, `close` | OHLC prices (₹) |
| `prev_close` | Previous close |
| `volume` | Total traded quantity |
| `delivery_qty` | Delivery quantity |
| `delivery_val_cr` | Delivery value (crores) |
| `turnover_cr` | Total turnover (crores) |
| `total_trades` | Number of trades |
| `industry` | Industry classification |

---

### `get_latest_prices(excel_path=None, days=15) → DataFrame`

Filters `load_price_data()` to the most recent N trading days.

Used by `upload-prices` and `pipeline` commands to avoid uploading the entire 109k-row history on every run.

---

## Stage 2: Screening (`screener.py`)

### `screen_dataframe(master_df) → DataFrame`

Applies all 12 conditions to every row in the master DataFrame and returns an enriched DataFrame with screening results.

**Process (per stock):**
1. For each of the 12 conditions, call `check_condition(row, condition)`
2. A condition returns `True` (pass), `False` (fail), or `None` (data missing)
3. A stock `passes_screen` if it has zero `False` results (missing data is tolerated)
4. Score is computed via `_compute_score(row, met, total)`

**Output columns added to the DataFrame:**

| Column | Description |
|--------|-------------|
| `passes_screen` | `True` if all non-missing conditions pass |
| `conditions_met` | Count of conditions passed |
| `failed_conditions` | Comma-separated list of failed condition names |
| `unknown_conditions` | Conditions with missing data |
| `score` | 0–100 quality score |

**Score calculation:**

The score is not simply `conditions_met / 12 * 100`. It uses a weighted approach:
- Base score from proportion of conditions met
- Bonus for stronger fundamentals (e.g., higher ROCE, lower pledging)
- Penalty for data gaps (many `unknown` conditions reduce the score)

**Results as of March 2026:**
- Total stocks analyzed: 5,750
- Stocks passing all conditions: **898** (15.6%)
- Average score (passing stocks): **82.9 / 100**
- Top scorers: HARSHDEEP, PIXTRANS, DMR, JBCHEPHARM, MEHUL, ABBOTINDIA (score 95–100)

---

## The 12 Conditions — Deep Dive

### Why These 12?

These conditions were designed to find stocks that are:
- **Profitable right now** (PE > 0, EPS > 0, Net Profit > 0)
- **Growing** (sales and profit year-over-year)
- **Trustworthy insiders** (low pledging, promoters not dumping)
- **Financially healthy** (manageable debt, good liquidity, efficient capital use)

A stock passing all 12 is not guaranteed to go up — but one failing even a single condition has a known risk flag attached. The 12 conditions serve as a quality gate, not a buy signal.

### Condition Details

**1. PE > 0 (`pe_positive`)**
- Field: `pe`
- Meaning: The company is profitable enough to have a positive price/earnings ratio. A zero or negative PE means the company has no earnings, making valuation impossible.

**2. EPS > 0 (`eps_positive`)**
- Field: `eps`
- Meaning: Earnings per share is positive — the company is earning money for its shareholders.

**3. Sales Qtr > 0 (`sales_qtr_positive`)**
- Field: `sales_qrt`
- Meaning: The company had revenue this quarter. Filters out shell companies or inactive listing.

**4. YoY Sales Growth > 0 (`yoy_sales_growth`)**
- Field: `sales_var_pct`
- Meaning: Revenue is growing year-over-year. A business that isn't growing is stagnating.

**5. Net Profit Qtr > 0 (`net_profit_positive`)**
- Field: `np_qrt`
- Meaning: Bottom-line profitability this quarter. Ensures operating profit isn't offset by extraordinary charges.

**6. YoY Profit > −10% (`yoy_profit_not_declining`)**
- Field: `profit_var_pct`
- Threshold: > -10% (allows mild dips)
- Meaning: Profit isn't collapsing. A mild dip is acceptable; a freefall is not.

**7. Pledged % < 10% (`low_pledging`)**
- Field: `pledged_pct`
- Meaning: Promoters (insiders/founders) have not heavily pledged their shares as loan collateral. High pledging is a red flag — forced selling risk.

**8. Unpledged Promo Hold > 30% (`unpledged_promo_hold`)**
- Field: `unpledged_promo_pct`
- Meaning: Promoters own a meaningful, unencumbered stake. Skin-in-the-game signal.

**9. Change in Promo Hold ≥ 0 (`promo_hold_stable`)**
- Field: `ch_promo_hold_pct`
- Meaning: Promoters are not reducing their stake. A reduction signals lack of confidence.

**10. Debt/Equity 0–1 (`low_debt`)**
- Field: `Debt Eq Ratio %`
- Threshold: ≤ 1
- Meaning: The company isn't over-leveraged. Debt higher than equity raises solvency risk.

**11. Current Ratio > 1 (`current_ratio_healthy`)**
- Field: `Current Ratio %`
- Meaning: Current assets exceed current liabilities. Company can meet its short-term obligations.

**12. ROCE ≥ 10% (`roce_decent`)**
- Field: `ROCE`
- Meaning: Return on capital employed is at least 10%. Capital is being put to productive use.

---

## Stage 3: Upload (`uploader.py`)

### Rate Limiting

Notion's API allows approximately 3 requests per second per integration. The uploader enforces a `_rate_limit_pause()` (0.34 s delay) between every API call.

At this rate:
- 5,750 stocks = ~32 minutes
- 898 screener rows = ~5 minutes
- 6,600 price rows (15 days × 440 stocks) = ~37 minutes

### Property Serialization

Each DataFrame row is converted to a Notion property dict:

| Python type | Notion property |
|-------------|----------------|
| `float` (number) | `{"number": value}` |
| `str` | `{"rich_text": [{"text": {"content": value}}]}` |
| Title field | `{"title": [{"text": {"content": value}}]}` |
| `float` percentage | `{"number": value / 100}` (Notion stores % as decimal) |
| `datetime` / `Timestamp` | `{"date": {"start": "YYYY-MM-DD"}}` |
| Select | `{"select": {"name": value}}` |
| Checkbox | `{"checkbox": bool_value}` |
| Relation | `{"relation": [{"id": page_id}]}` |

### Relations

When uploading `daily_prices` and `screener_results`, the uploader links each row back to its stock in `Stocks Master` using the `symbol_to_page` dict returned by `upload_stocks_master()`.

If a symbol is missing from `symbol_to_page` (e.g., a price row for a symbol not in the screened universe), the relation is skipped rather than failing.

---

## Data Freshness

StockPulse does not maintain a live connection to NSE/BSE. Data freshness depends on when you:
1. Download new BhavCopy files using `stockpulse download`
2. Update your Excel workbook with fresh data
3. Re-run `stockpulse upload-prices` or `stockpulse pipeline`

For daily use:
```bash
# Morning routine
stockpulse download                   # fetch yesterday's data
# ... update your Excel workbook ...
stockpulse upload-prices --days 1    # push new prices to Notion
```

For quarterly use (when fundamental data changes):
```bash
# After a fresh workbook with updated PE, EPS, etc.
stockpulse pipeline                  # full refresh
```
