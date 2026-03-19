"""
NSE/BSE Data Downloader — Robust, cross-platform rewrite.

Downloads BhavCopy (price) and MTO (delivery) data from NSE and BSE
for a given date or date range. Fixes all issues from the original script.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from stockpulse.config import DATA_DIR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL templates
# ---------------------------------------------------------------------------

NSE_BHAVCOPY_URL = (
    "https://nsearchives.nseindia.com/content/cm/"
    "BhavCopy_NSE_CM_0_0_0_{date_ymd}_F_0000.csv.zip"
)
NSE_MTO_URL = (
    "https://nsearchives.nseindia.com/archives/equities/mto/MTO_{date_dmy}.DAT"
)
BSE_BHAVCOPY_URL = (
    "https://www.bseindia.com/download/BhavCopy/Equity/"
    "BhavCopy_BSE_CM_0_0_0_{date_ymd}_F_0000.CSV"
)
BSE_DELIVERY_URL = (
    "https://www.bseindia.com/BSEDATA/gross/{year}/SCBSEALL{day}{month}.zip"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# NSE requires a session with cookies
_nse_session: requests.Session | None = None


def _get_nse_session() -> requests.Session:
    """Get/create a requests session with NSE cookies."""
    global _nse_session
    if _nse_session is None:
        _nse_session = requests.Session()
        _nse_session.headers.update(HEADERS)
        # Hit the NSE homepage first to get cookies
        try:
            _nse_session.get("https://www.nseindia.com", timeout=10)
        except requests.RequestException:
            pass
    return _nse_session


def _format_date_ymd(d: date) -> str:
    """Format date as YYYYMMDD."""
    return d.strftime("%Y%m%d")


def _format_date_dmy(d: date) -> str:
    """Format date as DDMMYYYY."""
    return d.strftime("%d%m%Y")


def _ensure_data_dir() -> Path:
    """Create and return the data directory."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def _download(url: str, session: requests.Session | None = None) -> requests.Response:
    """Download a URL with retry logic."""
    sess = session or requests.Session()
    sess.headers.update(HEADERS)
    resp = sess.get(url, timeout=30)
    resp.raise_for_status()
    return resp


def download_nse_bhavcopy(d: date) -> Path | None:
    """Download NSE BhavCopy CSV for a given date."""
    data_dir = _ensure_data_dir()
    date_ymd = _format_date_ymd(d)
    url = NSE_BHAVCOPY_URL.format(date_ymd=date_ymd)
    session = _get_nse_session()

    try:
        resp = _download(url, session)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = zf.namelist()
            zf.extractall(data_dir)
            out = data_dir / names[0]
            logger.info("[NSE BhavCopy] %s → %s", d, out.name)
            return out
    except Exception as e:
        logger.warning("[NSE BhavCopy] Failed for %s: %s", d, e)
        return None


def download_nse_delivery(d: date) -> Path | None:
    """Download NSE MTO (delivery) data for a given date and convert to CSV."""
    data_dir = _ensure_data_dir()
    date_dmy = _format_date_dmy(d)
    url = NSE_MTO_URL.format(date_dmy=date_dmy)
    session = _get_nse_session()

    try:
        resp = _download(url, session)
        content = resp.text
        lines = content.strip().split("\n")

        # Extract trade date from header (line 3, 0-indexed line 2)
        trade_date = d.strftime("%Y-%m-%d")
        if len(lines) > 2:
            header_line = lines[2]
            # Try to extract date from header
            for part in header_line.split():
                part_clean = part.strip("<>,")
                try:
                    parsed = datetime.strptime(part_clean, "%d-%b-%Y")
                    trade_date = parsed.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

        # Data starts from line 5 (0-indexed line 4)
        data_lines = lines[4:] if len(lines) > 4 else []

        out_path = data_dir / f"MTO_{date_dmy}.csv"
        with open(out_path, "w", newline="") as f:
            for line in data_lines:
                if line.strip():
                    f.write(f"{trade_date},{line}\n")

        logger.info("[NSE Delivery] %s → %s", d, out_path.name)
        return out_path
    except Exception as e:
        logger.warning("[NSE Delivery] Failed for %s: %s", d, e)
        return None


def download_bse_bhavcopy(d: date) -> Path | None:
    """Download BSE BhavCopy CSV for a given date."""
    data_dir = _ensure_data_dir()
    date_ymd = _format_date_ymd(d)
    url = BSE_BHAVCOPY_URL.format(date_ymd=date_ymd)

    try:
        resp = _download(url)
        out_path = data_dir / f"BhavCopy_BSE_CM_0_0_0_{date_ymd}_F_0000.csv"
        with open(out_path, "wb") as f:
            f.write(resp.content)
        logger.info("[BSE BhavCopy] %s → %s", d, out_path.name)
        return out_path
    except Exception as e:
        logger.warning("[BSE BhavCopy] Failed for %s: %s", d, e)
        return None


def download_bse_delivery(d: date) -> Path | None:
    """Download BSE delivery data ZIP for a given date."""
    data_dir = _ensure_data_dir()
    url = BSE_DELIVERY_URL.format(
        year=d.strftime("%Y"),
        month=d.strftime("%m"),
        day=d.strftime("%d"),
    )

    try:
        resp = _download(url)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = zf.namelist()
            zf.extractall(data_dir)
            out = data_dir / names[0]
            logger.info("[BSE Delivery] %s → %s", d, out.name)
            return out
    except Exception as e:
        logger.warning("[BSE Delivery] Failed for %s: %s", d, e)
        return None


def download_all_for_date(d: date) -> dict[str, Path | None]:
    """Download all 4 data sources for a given date."""
    logger.info("Downloading all data for %s ...", d)
    return {
        "nse_bhavcopy": download_nse_bhavcopy(d),
        "nse_delivery": download_nse_delivery(d),
        "bse_bhavcopy": download_bse_bhavcopy(d),
        "bse_delivery": download_bse_delivery(d),
    }


def download_date_range(
    start: date, end: date, skip_weekends: bool = True
) -> list[dict]:
    """Download data for a range of dates."""
    results = []
    current = start
    while current <= end:
        if skip_weekends and current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        result = download_all_for_date(current)
        result["date"] = current
        results.append(result)
        current += timedelta(days=1)
    return results
