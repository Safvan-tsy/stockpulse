"""
Notion Dashboard Builder — Creates the StockPulse home page in Notion.

Builds a visually organized dashboard page with embedded database views,
summary sections, and links to reports.
"""

from __future__ import annotations

import logging
from datetime import datetime

from notion_client import Client

from stockpulse.notion_setup import get_client, load_db_ids
from stockpulse.config import NOTION_PARENT_PAGE_ID

logger = logging.getLogger(__name__)


def _heading(level: int, text: str) -> dict:
    """Create a heading block."""
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _paragraph(text: str) -> dict:
    """Create a paragraph block."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        },
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _callout(text: str, emoji: str = "📊") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"type": "emoji", "emoji": emoji},
        },
    }


def _linked_db(database_id: str) -> dict:
    """Create a linked/embedded database view block."""
    return {
        "object": "block",
        "type": "child_database",
        "child_database": {"title": ""},
    }


def _table_of_contents() -> dict:
    return {
        "object": "block",
        "type": "table_of_contents",
        "table_of_contents": {},
    }


def _bulleted_item(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        },
    }


def create_dashboard_page() -> str:
    """Create the main StockPulse dashboard page in Notion.

    Returns the page ID.
    """
    client = get_client()
    db_ids = load_db_ids()
    today = datetime.now().strftime("%B %d, %Y")

    blocks = [
        _callout(
            "StockPulse India — AI-Powered Stock Intelligence System\n"
            f"Screening 440+ Indian stocks through 12 fundamental conditions.\n"
            f"Last updated: {today}",
            "🇮🇳"
        ),
        _divider(),
        _table_of_contents(),
        _divider(),

        # Section 1: How It Works
        _heading(1, "How StockPulse Works"),
        _paragraph(
            "StockPulse takes daily price and delivery data from NSE & BSE, "
            "screens it through 12 battle-tested fundamental conditions, "
            "and uses AI to generate research insights — all centralized here in Notion."
        ),
        _heading(3, "The 12 Screening Conditions"),
        _bulleted_item("PE > 0 — Company is profitable"),
        _bulleted_item("EPS > 0 — Positive earnings per share"),
        _bulleted_item("Sales Quarter > 0 — Has revenue this quarter"),
        _bulleted_item("YoY Sales Growth > 0 — Revenue growing year-over-year"),
        _bulleted_item("Net Profit Quarter > 0 — Made money this quarter"),
        _bulleted_item("YoY Net Profit > -10% — Profit not declining sharply"),
        _bulleted_item("Promoter Pledging < 10% — Low insider pledging"),
        _bulleted_item("Unpledged Promoter Hold > 30% — Strong insider ownership"),
        _bulleted_item("Change in Promoter Hold >= 0 — Insiders not dumping"),
        _bulleted_item("Debt/Equity 0–1 — Not over-leveraged"),
        _bulleted_item("Current Ratio > 1 — Can pay short-term obligations"),
        _bulleted_item("ROCE >= 10% — Decent returns on capital"),
        _divider(),

        # Section 2: Top Screened Stocks
        _heading(1, "Top Screened Stocks"),
        _paragraph(
            "Stocks that pass ALL 12 conditions, ranked by quality score. "
            "Higher score = stronger fundamentals across all dimensions."
        ),
        _divider(),

        # Section 3: AI Analysis
        _heading(1, "AI Analysis Reports"),
        _paragraph(
            "AI-generated research reports including stock deep-dives, "
            "weekly market summaries, sector analysis, and anomaly alerts."
        ),
        _divider(),

        # Section 4: Watchlist
        _heading(1, "Watchlist"),
        _paragraph(
            "Your personal watchlist with AI-powered alerts. "
            "Add stocks you're tracking, and the AI will monitor them for notable changes."
        ),
        _divider(),

        # Section 5: Market Overview
        _heading(1, "Market Overview"),
        _paragraph(
            "Data sourced from NSE and BSE exchanges. Covers price, volume, "
            "delivery data, and 30+ fundamental metrics including Piotroski Score, "
            "FII/DII holdings, and sector comparisons."
        ),
        _heading(3, "Data Pipeline"),
        _bulleted_item("Source: NSE BhavCopy + MTO files, BSE BhavCopy + Delivery data"),
        _bulleted_item("Fundamentals: PE, EPS, ROCE, ROE, Debt/Equity, Current Ratio, etc."),
        _bulleted_item("Governance: Promoter holdings, pledging, FII/DII changes"),
        _bulleted_item("Quality: Piotroski Score, sector comparisons"),
        _bulleted_item("Coverage: 440+ fundamentally filtered stocks from 5000+"),
    ]

    page = client.pages.create(
        parent={"type": "page_id", "page_id": NOTION_PARENT_PAGE_ID},
        properties={
            "title": [
                {
                    "type": "text",
                    "text": {"content": "StockPulse India 📈"},
                }
            ]
        },
        icon={"type": "emoji", "emoji": "📈"},
        children=blocks,
    )

    logger.info("Dashboard page created: %s", page["id"])
    return page["id"]
