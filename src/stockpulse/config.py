"""Configuration loader for StockPulse India."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
WORKBOOK_DIR = Path(os.getenv("WORKBOOK_DIR", PROJECT_ROOT / "workbook"))

# Notion
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")

# File paths
EXCEL_ALL = WORKBOOK_DIR / "DailyData_All_With Chart2.xlsx"
EXCEL_FILTERED = WORKBOOK_DIR / "DailyData_Fundamentally Good Ones.xlsx"

# Notion database names
DB_STOCKS_MASTER = "StockPulse — Stocks Master"
DB_DAILY_PRICES = "StockPulse — Daily Prices"
DB_SCREENER = "StockPulse — Screener Results"
DB_WATCHLIST = "StockPulse — Watchlist"
DB_REPORTS = "StockPulse — AI Reports"

# Screening thresholds (the 12 conditions)
# Field names must match the DataFrame column names from parser.build_stocks_master()
SCREEN_CONDITIONS = {
    "pe_positive": {"field": "pe", "op": ">", "value": 0},
    "eps_positive": {"field": "eps", "op": ">", "value": 0},
    "sales_qtr_positive": {"field": "sales_qrt", "op": ">", "value": 0},
    "yoy_sales_growth": {"field": "sales_var_pct", "op": ">", "value": 0},
    "net_profit_positive": {"field": "np_qrt", "op": ">", "value": 0},
    "yoy_profit_not_declining": {"field": "profit_var_pct", "op": ">", "value": -10},
    "low_pledging": {"field": "pledged_pct", "op": "<", "value": 10},
    "unpledged_promo_hold": {"field": "unpledged_promo_pct", "op": ">", "value": 30},
    "promo_hold_stable": {"field": "ch_promo_hold_pct", "op": ">=", "value": 0},
    "low_debt": {"field": "Debt Eq Ratio %", "op": "<=", "value": 1},
    "current_ratio_healthy": {"field": "Current Ratio %", "op": ">", "value": 1},
    "roce_decent": {"field": "ROCE", "op": ">=", "value": 10},
}
