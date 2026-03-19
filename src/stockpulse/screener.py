"""
12-Condition Stock Screener Engine.

Applies the fundamental screening conditions to stock data and produces
scored results with pass/fail details for each condition.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from stockpulse.config import SCREEN_CONDITIONS

logger = logging.getLogger(__name__)

# Operator mapping
OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}


def _safe_numeric(val: Any) -> float | None:
    """Convert a value to float, returning None for non-numeric."""
    if val is None or (isinstance(val, str) and val.strip() in ("NIL", "", "-")):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def check_condition(row: dict, condition: dict) -> bool | None:
    """Check a single condition against a row.

    Returns True if passed, False if failed, None if data missing.
    """
    field = condition["field"]
    op = condition["op"]
    threshold = condition["value"]

    val = _safe_numeric(row.get(field))
    if val is None:
        return None

    op_func = OPS.get(op)
    if op_func is None:
        return None

    # For debt/equity with range check (0 <= x <= 1)
    if field == "Debt/Equity" and op == "<=":
        return 0 <= val <= threshold

    return op_func(val, threshold)


def screen_stock(row: dict) -> dict:
    """Screen a single stock against all 12 conditions.

    Returns a dict with:
        - symbol: stock symbol
        - passed: list of condition names that passed
        - failed: list of condition names that failed
        - unknown: list of conditions with missing data
        - conditions_met: count of passed conditions
        - total_conditions: 12
        - passes_screen: True if all non-unknown conditions pass
        - score: 0-100 quality score
    """
    passed = []
    failed = []
    unknown = []

    for name, condition in SCREEN_CONDITIONS.items():
        result = check_condition(row, condition)
        if result is True:
            passed.append(name)
        elif result is False:
            failed.append(name)
        else:
            unknown.append(name)

    total = len(SCREEN_CONDITIONS)
    met = len(passed)

    # Score: weighted average based on condition strength
    score = _compute_score(row, met, total)

    return {
        "symbol": row.get("symbol", row.get("SYMBOL", "?")),
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "conditions_met": met,
        "total_conditions": total,
        "passes_screen": len(failed) == 0 and met > 0,
        "score": score,
    }


def _compute_score(row: dict, conditions_met: int, total: int) -> int:
    """Compute a 0-100 quality score based on fundamental strength.

    Factors in:
    - Number of conditions met (base score)
    - ROCE strength (above 10 is pass, but 30+ is excellent)
    - Debt/Equity (lower is better)
    - Promoter holding conviction
    - Piotroski score if available
    """
    if total == 0:
        return 0

    # Base score: conditions met (0-60 points)
    base = (conditions_met / total) * 60

    bonus = 0.0

    # ROCE bonus (0-15 points)
    roce = _safe_numeric(row.get("ROCE") or row.get("roce_pct"))
    if roce is not None:
        if roce >= 25:
            bonus += 15
        elif roce >= 15:
            bonus += 10
        elif roce >= 10:
            bonus += 5

    # Low debt bonus (0-10 points)
    de = _safe_numeric(row.get("Debt Eq Ratio %") or row.get("debt_eq_ratio"))
    if de is not None:
        if de <= 0.1:
            bonus += 10
        elif de <= 0.3:
            bonus += 7
        elif de <= 0.5:
            bonus += 4

    # Promoter conviction bonus (0-10 points)
    promo = _safe_numeric(row.get("promoter_hold_pct"))
    ch_promo = _safe_numeric(row.get("ch_promo_hold_pct"))
    if promo is not None:
        if promo >= 60:
            bonus += 5
        elif promo >= 45:
            bonus += 3
    if ch_promo is not None and ch_promo > 0:
        bonus += 5

    # Piotroski bonus (0-5 points)
    piotroski = _safe_numeric(row.get("PiotriskiScore") or row.get("piotroski_score"))
    if piotroski is not None:
        if piotroski >= 7:
            bonus += 5
        elif piotroski >= 5:
            bonus += 3

    return min(100, int(base + bonus))


def screen_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Screen all stocks in a DataFrame.

    Expects a DataFrame with one row per stock (master data).
    Returns a DataFrame with screening results.
    """
    logger.info("Screening %d stocks against %d conditions ...",
                len(df), len(SCREEN_CONDITIONS))

    results = []
    for _, row in df.iterrows():
        result = screen_stock(row.to_dict())
        results.append(result)

    results_df = pd.DataFrame(results)

    passed_count = results_df["passes_screen"].sum()
    logger.info("Screening complete: %d/%d stocks pass all conditions",
                passed_count, len(df))

    return results_df


def get_top_stocks(
    results_df: pd.DataFrame, n: int = 20, min_score: int = 0
) -> pd.DataFrame:
    """Get top N stocks by score from screening results."""
    filtered = results_df[
        (results_df["passes_screen"]) & (results_df["score"] >= min_score)
    ]
    return filtered.nlargest(n, "score")


def format_screen_summary(results_df: pd.DataFrame) -> str:
    """Format a human-readable screening summary."""
    total = len(results_df)
    passed = results_df["passes_screen"].sum()
    avg_score = results_df.loc[results_df["passes_screen"], "score"].mean()

    lines = [
        f"📊 Screening Summary",
        f"  Total stocks analyzed: {total}",
        f"  Passed all conditions: {passed}",
        f"  Average score (passed): {avg_score:.1f}/100" if passed > 0 else "",
        "",
        f"🏆 Top 10 by Score:",
    ]

    top = get_top_stocks(results_df, n=10)
    for _, row in top.iterrows():
        lines.append(
            f"  {row['symbol']:20s}  Score: {row['score']:3d}  "
            f"({row['conditions_met']}/{row['total_conditions']} conditions)"
        )

    return "\n".join(lines)
