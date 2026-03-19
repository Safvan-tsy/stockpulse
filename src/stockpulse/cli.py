"""
StockPulse CLI — Command-line interface for all StockPulse operations.

Usage:
    python -m stockpulse setup          # Create Notion databases
    python -m stockpulse parse          # Parse Excel and show summary
    python -m stockpulse screen         # Run the 12-condition screener
    python -m stockpulse upload         # Upload data to Notion
    python -m stockpulse upload-prices  # Upload recent prices to Notion
    python -m stockpulse dashboard      # Create the Notion dashboard page
    python -m stockpulse download       # Download fresh NSE/BSE data
    python -m stockpulse serve          # Start the MCP server
    python -m stockpulse pipeline       # Run full pipeline (parse→screen→upload)
"""

import logging
import sys
from datetime import date, datetime, timedelta

import click

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("stockpulse")


@click.group()
def cli():
    """StockPulse India — AI-Powered Stock Intelligence on Notion."""
    pass


@cli.command()
def setup():
    """Create all Notion databases (run this first)."""
    from stockpulse.notion_setup import setup_all_databases

    click.echo("Setting up Notion databases...")
    db_ids = setup_all_databases()
    click.echo("\nDatabases created:")
    for name, db_id in db_ids.items():
        click.echo(f"  {name}: {db_id}")
    click.echo("\nDatabase IDs saved to notion_db_ids.json")


@cli.command()
@click.option("--file", "excel_file", default=None, help="Path to Excel file")
def parse(excel_file):
    """Parse Excel workbooks and show a data summary."""
    from pathlib import Path
    from stockpulse.parser import build_stocks_master, load_price_data

    path = Path(excel_file) if excel_file else None

    click.echo("Parsing Excel data...")
    master = build_stocks_master(path)
    prices = load_price_data(path)

    click.echo(f"\nStocks Master: {len(master)} stocks, {len(master.columns)} columns")
    click.echo(f"Daily Prices: {len(prices)} rows, {prices['symbol'].nunique()} symbols")

    if "date" in prices.columns:
        click.echo(f"Date range: {prices['date'].min()} → {prices['date'].max()}")

    click.echo(f"\nSample columns: {list(master.columns[:15])}")
    click.echo(f"\nTop 10 stocks (by market cap):")
    if "market_cap_cr" in master.columns:
        top = master.nlargest(10, "market_cap_cr")
        for _, row in top.iterrows():
            sym = row.get("symbol", row.get("bse_id", "?"))
            mc = row.get("market_cap_cr", 0)
            ind = row.get("industry", "?")
            click.echo(f"  {sym:20s}  ₹{mc:>10,.0f} Cr  [{ind}]")


@cli.command()
@click.option("--file", "excel_file", default=None, help="Path to Excel file")
def screen(excel_file):
    """Run the 12-condition screener on the data."""
    from pathlib import Path
    from stockpulse.parser import build_stocks_master
    from stockpulse.screener import screen_dataframe, format_screen_summary

    path = Path(excel_file) if excel_file else None

    click.echo("Loading data and running screener...")
    master = build_stocks_master(path)
    results = screen_dataframe(master)

    click.echo(format_screen_summary(results))

    # Save results locally
    out_file = "screener_results.csv"
    results.to_csv(out_file, index=False)
    click.echo(f"\nResults saved to {out_file}")


@cli.command()
@click.option("--file", "excel_file", default=None, help="Path to Excel file")
@click.option("--days", default=30, help="Upload last N days of prices")
@click.option("--skip-prices", is_flag=True, help="Skip uploading daily prices")
def upload(excel_file, days, skip_prices):
    """Upload stocks master + screening results + recent prices to Notion."""
    from pathlib import Path
    from stockpulse.parser import build_stocks_master, get_latest_prices
    from stockpulse.screener import screen_dataframe
    from stockpulse.uploader import (
        upload_stocks_master,
        upload_daily_prices,
        upload_screener_results,
    )

    path = Path(excel_file) if excel_file else None

    click.echo("Step 1/4: Parsing Excel data...")
    master = build_stocks_master(path)

    click.echo("Step 2/4: Running screener...")
    screen_results = screen_dataframe(master)

    click.echo("Step 3/4: Uploading stocks master to Notion...")
    symbol_to_page = upload_stocks_master(master, screen_results)
    click.echo(f"  Uploaded {len(symbol_to_page)} stocks")

    click.echo("  Uploading screener results...")
    upload_screener_results(screen_results, symbol_to_page)

    if not skip_prices:
        click.echo(f"Step 4/4: Uploading last {days} days of prices...")
        prices = get_latest_prices(path, days=days)
        count = upload_daily_prices(prices, symbol_to_page)
        click.echo(f"  Uploaded {count} price rows")
    else:
        click.echo("Step 4/4: Skipping prices (--skip-prices flag)")

    click.echo("\nDone! Check your Notion workspace.")


@cli.command("upload-prices")
@click.option("--file", "excel_file", default=None, help="Path to Excel file")
@click.option("--days", default=10, help="Upload last N days of prices")
def upload_prices(excel_file, days):
    """Upload only recent daily prices to Notion (faster than full upload)."""
    from pathlib import Path
    from stockpulse.parser import get_latest_prices
    from stockpulse.uploader import upload_daily_prices
    from stockpulse.notion_setup import load_db_ids

    path = Path(excel_file) if excel_file else None

    click.echo(f"Loading last {days} days of prices...")
    prices = get_latest_prices(path, days=days)
    click.echo(f"  {len(prices)} price rows to upload")

    # We need symbol→page mapping. For now use empty (no relation linking)
    click.echo("Uploading to Notion (without stock relations)...")
    count = upload_daily_prices(prices, {})
    click.echo(f"  Uploaded {count} price rows")


@cli.command()
def dashboard():
    """Create the StockPulse dashboard page in Notion."""
    from stockpulse.dashboard import create_dashboard_page

    click.echo("Creating dashboard page...")
    page_id = create_dashboard_page()
    click.echo(f"Dashboard created: {page_id}")


@cli.command()
@click.option("--date", "target_date", default=None, help="Date (YYYY-MM-DD)")
def download(target_date):
    """Download fresh NSE/BSE data for a date."""
    from stockpulse.downloader import download_all_for_date

    if target_date:
        d = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        # Default to last trading day
        d = date.today()
        if d.weekday() == 0:  # Monday → Friday
            d -= timedelta(days=3)
        elif d.weekday() == 6:  # Sunday → Friday
            d -= timedelta(days=2)
        elif d.weekday() == 5:  # Saturday → Friday
            d -= timedelta(days=1)

    click.echo(f"Downloading data for {d}...")
    results = download_all_for_date(d)
    for source, path in results.items():
        status = f"✓ {path}" if path else "✗ failed"
        click.echo(f"  {source}: {status}")


@cli.command()
def serve():
    """Start the MCP server for AI agent integration."""
    from stockpulse.mcp_server import main as mcp_main

    mcp_main()


@cli.command()
@click.option("--file", "excel_file", default=None, help="Path to Excel file")
@click.option("--days", default=15, help="Days of price data to upload")
def pipeline(excel_file, days):
    """Run the full pipeline: parse → screen → upload → dashboard."""
    from pathlib import Path
    from stockpulse.parser import build_stocks_master, get_latest_prices
    from stockpulse.screener import screen_dataframe, format_screen_summary
    from stockpulse.uploader import (
        upload_stocks_master,
        upload_daily_prices,
        upload_screener_results,
    )
    from stockpulse.dashboard import create_dashboard_page

    path = Path(excel_file) if excel_file else None

    click.echo("=" * 60)
    click.echo("  StockPulse India — Full Pipeline")
    click.echo("=" * 60)

    click.echo("\n[1/5] Parsing Excel data...")
    master = build_stocks_master(path)
    click.echo(f"  → {len(master)} stocks loaded")

    click.echo("\n[2/5] Running 12-condition screener...")
    screen_results = screen_dataframe(master)
    click.echo(format_screen_summary(screen_results))

    click.echo("\n[3/5] Uploading stocks to Notion...")
    symbol_to_page = upload_stocks_master(master, screen_results)
    click.echo(f"  → {len(symbol_to_page)} stocks uploaded")

    click.echo("\n  Uploading screener results...")
    upload_screener_results(screen_results, symbol_to_page)

    click.echo(f"\n[4/5] Uploading last {days} days of prices...")
    prices = get_latest_prices(path, days=days)
    count = upload_daily_prices(prices, symbol_to_page)
    click.echo(f"  → {count} price rows uploaded")

    click.echo("\n[5/5] Creating dashboard page...")
    create_dashboard_page()

    click.echo("\n" + "=" * 60)
    click.echo("  Pipeline complete! Check your Notion workspace.")
    click.echo("=" * 60)


def main():
    cli()


if __name__ == "__main__":
    main()
