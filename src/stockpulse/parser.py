"""
Excel Data Parser — Extracts stock data from the workbook Excel files.

Reads both the "All" and "Fundamentally Good Ones" workbooks and produces
clean DataFrames for: daily prices, fundamentals, and industry comparisons.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from stockpulse.config import EXCEL_ALL, EXCEL_FILTERED

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column mappings from the Excel sheets
# ---------------------------------------------------------------------------

PRICE_COLS = {
    "TIMESTAMP": "date",
    "SYMBOL": "symbol",
    "ScCode": "bse_code",
    "Industry": "industry",
    "GROUP": "group",
    "SERIES": "series",
    "OPEN": "open",
    "HIGH": "high",
    "LOW": "low",
    "CLOSE": "close",
    "PREVCLOSE": "prev_close",
    "TOTALTRADES": "total_trades",
    "TOTTRDQTY": "volume",
    "TurnoverRsCr": "turnover_cr",
    "ISIN1": "isin",
    "DeliQty": "delivery_qty",
    "DeliValRsCr": "delivery_val_cr",
}

FUNDA_COLS_MAP = {
    "SYMBOL": "symbol",
    "BSE Code": "bse_code",
    "BSE ID": "bse_id",
    "CMP (Rs.)": "cmp",
    "Industry": "industry",
    "MarketCap Rs Cr": "market_cap_cr",
    "Sales Qrt (Rs. Cr.)": "sales_qrt",
    "Debt Rs. Cr.": "debt_cr",
    "Reserves Rs. Cr.": "reserves_cr",
    "NP Qrt (Rs. Cr.)": "np_qrt",
    "Other Inc Qrt (Rs. Cr.)": "other_inc_qrt",
    "P/E": "pe",
    "EPS": "eps",
    "Qrtly Sales Var (%)": "sales_var_pct",
    "Qrt Prof Var %": "profit_var_pct",
    "Share Qty (Cr.)": "shares_cr",
    "Promotor Hold %": "promoter_hold_pct",
    "Pledged %": "pledged_pct",
    "Unpledged Promo Hold %": "unpledged_promo_pct",
    "Ch In Promo Hold %": "ch_promo_hold_pct",
}

CHART_DATA_COLS = [
    "date", "delivery_val_cr", "open", "high", "low", "close",
    "bse_code", "delivery_pct", "avg_trade_worth", "avg_qty_per_trade",
    "avg_price", "book_value", "ind_pe", "pe", "eps", "sales_qrt",
    "sales_qrt_var_pct", "np_qrt", "qrt_other_inc", "qrt_profit_var_pct",
    "shares_cr", "promoter_hold_pct", "pledged_pct", "ch_promo_hold_pct",
    "unpledged_promo_pct",
]

FUNDA_CHART_COLS = [
    "symbol", "mkt_cap_to_industry_pct", "sales_to_industry_pct",
    "debt_to_industry_pct", "qrtly_sales_var", "qrtly_profit_var_pct",
    "debt_eq_ratio", "unpledged_promo_pct", "pledged_pct",
    "ch_promo_hold_pct", "fii_hold_pct", "ch_fii_hold_pct",
    "dii_hold_pct", "ch_dii_hold_pct", "cmp_bv", "current_ratio",
    "roce_pct", "roe_pct", "roa_pct", "asset_turnover_pct",
    "interest_coverage", "roic", "quick_ratio", "div_pct",
    "earnings_yield", "piotroski_score", "export_pct",
    "sales_growth_5y_pct", "sales_growth_3y_pct", "profit_growth_5y_pct",
]


def load_price_data(excel_path: Path | None = None) -> pd.DataFrame:
    """Load daily price + delivery data from the 'Data' sheet."""
    path = excel_path or EXCEL_FILTERED
    logger.info("Loading price data from %s ...", path.name)

    df = pd.read_excel(path, sheet_name="Data", engine="openpyxl")

    # Rename known columns
    rename = {k: v for k, v in PRICE_COLS.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Parse date
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

    # Compute delivery %
    if "delivery_qty" in df.columns and "volume" in df.columns:
        df["delivery_pct"] = (
            df["delivery_qty"] / df["volume"].replace(0, float("nan")) * 100
        ).round(2)

    logger.info("Loaded %d price rows for %d symbols", len(df), df["symbol"].nunique())
    return df


def load_fundamentals(excel_path: Path | None = None) -> pd.DataFrame:
    """Load fundamental comparison data from the 'Funda_Comparisons' sheet."""
    path = excel_path or EXCEL_FILTERED
    logger.info("Loading fundamentals from %s ...", path.name)

    df = pd.read_excel(path, sheet_name="Funda_Comparisons", engine="openpyxl")

    rename = {k: v for k, v in FUNDA_COLS_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "symbol" not in df.columns and "bse_id" in df.columns:
        df = df.rename(columns={"bse_id": "symbol"})

    logger.info("Loaded fundamentals for %d stocks", len(df))
    return df


def load_funda_charts(excel_path: Path | None = None) -> pd.DataFrame:
    """Load the detailed fundamental metrics from the 'Funda Charts' sheet.

    This sheet has a non-standard layout: Row 3 has headers, Row 4+ has
    alternating symbol-name rows and data rows.  We parse it carefully.
    """
    path = excel_path or EXCEL_FILTERED
    logger.info("Loading funda charts from %s ...", path.name)

    df_raw = pd.read_excel(
        path, sheet_name="Funda Charts", header=None, engine="openpyxl"
    )

    # The sheet interleaves symbol rows and numeric helper rows.
    # We only keep rows where first column is a valid symbol string.
    records = []
    for i in range(3, len(df_raw)):
        symbol_row = df_raw.iloc[i].tolist()
        symbol = symbol_row[0]

        if symbol is None or pd.isna(symbol):
            continue
        if not isinstance(symbol, str):
            continue

        symbol = symbol.strip()
        if not symbol or symbol.lower() in {"row labels", "symbol"}:
            continue

        record = {"symbol": symbol}
        # Use FUNDA_CHART_COLS (skip first 'symbol').
        for idx, col_name in enumerate(FUNDA_CHART_COLS[1:], start=1):
            val = symbol_row[idx] if idx < len(symbol_row) else None
            if val == "NIL" or (val is not None and str(val).strip() == "NIL"):
                val = None
            record[col_name] = val
        records.append(record)

    df = pd.DataFrame(records)
    logger.info("Loaded funda chart data for %d stocks", len(df))
    return df


def load_chart_data_for_symbol(
    symbol: str, excel_path: Path | None = None
) -> pd.DataFrame:
    """Load per-symbol chart data from 'Chart Data' sheet.

    The Chart Data sheet encodes each symbol's data in a vertical block.
    We search for the symbol name and extract its rows.
    """
    path = excel_path or EXCEL_FILTERED
    logger.info("Loading chart data for %s ...", symbol)

    df_raw = pd.read_excel(
        path, sheet_name="Chart Data", header=None, engine="openpyxl"
    )

    # Find the symbol's block — look for row where col B == symbol
    symbol_indices = df_raw.index[df_raw.iloc[:, 1] == symbol].tolist()
    if not symbol_indices:
        logger.warning("Symbol %s not found in Chart Data", symbol)
        return pd.DataFrame()

    start = symbol_indices[0] + 3  # Data starts 3 rows after the symbol row

    # Find end — next symbol row or end of data
    rows = []
    for idx in range(start, len(df_raw)):
        row = df_raw.iloc[idx].tolist()
        if row[0] is None or pd.isna(row[0]):
            break
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    n_cols = min(len(CHART_DATA_COLS), len(rows[0]))
    df = pd.DataFrame(rows, columns=CHART_DATA_COLS[:n_cols] + [
        f"extra_{i}" for i in range(max(0, len(rows[0]) - n_cols))
    ])

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["symbol"] = symbol
    logger.info("Loaded %d chart-data rows for %s", len(df), symbol)
    return df


def build_stocks_master(excel_path: Path | None = None) -> pd.DataFrame:
    """Build a consolidated master DataFrame by merging fundamentals + funda charts.

    This is the main stock-level dataset with one row per symbol.
    """
    funda = load_fundamentals(excel_path)
    charts = load_funda_charts(excel_path)

    # Merge on symbol
    if not charts.empty and not funda.empty:
        # Use BSE ID as symbol in funda if needed
        if "symbol" in funda.columns and "symbol" in charts.columns:
            master = funda.merge(charts, on="symbol", how="outer", suffixes=("", "_fc"))
        else:
            master = funda
    elif not funda.empty:
        master = funda
    else:
        master = charts

    if "symbol" in master.columns:
        sym = master["symbol"].astype(str).str.strip()
        master = master[(sym != "") & (sym.str.lower() != "(blank)")]
        master = master.drop_duplicates(subset=["symbol"], keep="first")

    logger.info("Built stocks master with %d stocks, %d columns",
                len(master), len(master.columns))
    return master


def get_latest_prices(excel_path: Path | None = None, days: int = 30) -> pd.DataFrame:
    """Load price data and filter to the most recent N trading days."""
    df = load_price_data(excel_path)
    if df.empty:
        return df

    latest_date = df["date"].max()
    unique_dates = sorted(df["date"].unique(), reverse=True)
    cutoff_dates = unique_dates[:days]
    return df[df["date"].isin(cutoff_dates)].copy()


def get_symbol_list(excel_path: Path | None = None) -> list[str]:
    """Return sorted list of all symbols in the filtered workbook."""
    df = load_price_data(excel_path)
    return sorted(df["symbol"].unique().tolist())
