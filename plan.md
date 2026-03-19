# StockPulse India — AI-Powered Stock Intelligence on Notion

> **Notion MCP Challenge Submission Plan**
> Turn Indian stock market data into an AI-driven research workspace in Notion.

---

## 1. The Idea (What We're Building)

**StockPulse India** — An AI-powered stock screening and analysis system that:

1. **Fetches** daily BhavCopy (price + delivery) data from NSE & BSE automatically
2. **Screens** stocks through 12 battle-tested fundamental filters (your friend's strategy)
3. **Centralizes** everything in Notion as the single source of truth (databases + pages)
4. **Attaches intelligence** — an AI agent (via Notion MCP) that reads the data, generates insights, flags opportunities, detects anomalies, and writes analysis reports directly into Notion

**One-liner:** *"Your friend's Excel screening strategy, supercharged with AI and living in Notion."*

---

## 2. Analysis of Your Friend's Strategy

### The 12 Fundamental Conditions (What They Mean)

| # | Filter | What It Tests | Category |
|---|--------|---------------|----------|
| 1 | PE > 0 | Company is profitable (positive earnings) | Valuation |
| 2 | EPS > 0 | Earnings per share is positive | Profitability |
| 3 | Sales Quarter > 0 | Company has revenue this quarter | Revenue |
| 4 | YoY Sales Growth > 0 | Revenue is growing year-over-year | Growth |
| 5 | Net Profit Quarter > 0 | Company made money this quarter | Profitability |
| 6 | YoY Net Profit Quarter > -10% | Profit isn't declining sharply | Growth |
| 7 | Promoter Pledging < 10% | Insiders haven't pledged too much stock | Red-flag check |
| 8 | Unpledged Promoter Hold > 30% | Insiders own meaningful stake, freely | Governance |
| 9 | Change in Promoter Hold >= 0 | Insiders aren't dumping shares | Conviction |
| 10 | Debt/Equity 0–1 | Company isn't over-leveraged | Financial Health |
| 11 | Current Ratio > 1 | Can pay short-term obligations | Liquidity |
| 12 | ROCE >= 10% | Returns on capital are decent | Efficiency |

**Verdict:** This is a solid **quality + growth** filter. It eliminates loss-making, debt-heavy, and governance-red-flag companies. What survives is a "fundamentally clean" universe (~440 stocks from 5000+). This is a strong foundation.

### The Data Assets

| File | Size | Contents |
|------|------|----------|
| `DailyData_All_With Chart2.xlsx` | 257 MB | ALL stocks, 3 sheets (Data, Chart Data, Chart) |
| `DailyData_Fundamentally Good Ones.xlsx` | 68 MB | Filtered 440 stocks, 6 sheets including Funda Charts, Industry comparisons |
| Data columns | 20+ | OHLC, Volume, Delivery Qty/Value, Trades, ISIN |
| Fundamental columns | 30+ | PE, EPS, Sales, Debt/Eq, ROCE, ROE, Promoter Hold, FII/DII, Piotroski Score, etc. |
| Date range | Jan 2025 – Mar 2026 | ~281 trading days |
| Download script (`main.py`) | — | Downloads BhavCopy + MTO data from NSE & BSE |

### Issues with the Current Script (`main.py`)

The script has several problems that need fixing:

1. **Windows-only paths** — Uses `data\\tmp.dat` (backslash). Won't work on macOS/Linux.
2. **Fragile date parsing** — `Lines[2].split(" ")[2].strip("<").strip(">,Settlement")` is brittle and will break if NSE changes format.
3. **No retry/error handling** — A single network failure kills the whole download.
4. **No fundamental data** — Only downloads price/delivery data. The 12-condition screening needs fundamental data from another source (likely screener.in, Tickertape, or BSE corporate filings).
5. **Manual date input** — User types Year/Month/Day every time. No automation for batch/daily runs.
6. **No data storage** — Downloads to flat files, no database or structured storage.

**For the challenge:** We'll rewrite this as a robust, cross-platform data pipeline that feeds into Notion.

---

## 3. Why This Wins the Challenge

Mapped to the 3 judging criteria:

### Originality/Creativity ⭐⭐⭐⭐⭐
- **No existing submission** covers Indian stock market analysis
- Unique angle: takes a real, manual Excel-based strategy and "Notion-ifies" it
- The "human-in-the-loop" element is natural — investor reviews AI insights, marks favorites, adds notes
- Domain is engaging and visual (candlesticks, delivery charts, fundamentals)

### Technical Complexity ⭐⭐⭐⭐⭐
- Data pipeline (NSE/BSE → Python → Notion databases)
- 12-condition screening algorithm
- AI analysis via MCP (reading Notion DBs, generating insights, writing reports)
- Multiple Notion databases with relations
- Scheduled/automated data refresh
- Chart generation and embedding

### Practical Implementation ⭐⭐⭐⭐⭐
- Solves a REAL problem your friend is already solving manually
- 440 stocks, 281 days of data — this is real, not a toy demo
- Working end-to-end: data fetch → screen → store → analyze → present

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    NOTION WORKSPACE                      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐     │
│  │ Stocks   │  │ Daily    │  │ AI Insights &      │     │
│  │ Master   │──│ Price    │  │ Analysis Reports   │     │
│  │ Database │  │ Database │  │ (Pages)            │     │
│  └──────────┘  └──────────┘  └────────────────────┘     │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐     │
│  │ Screener │  │ Watchlist │  │ Sector Dashboard   │     │
│  │ Results  │  │ & Notes  │  │ (Page)             │     │
│  └──────────┘  └──────────┘  └────────────────────┘     │
└────────────────────────┬────────────────────────────────┘
                         │ Notion MCP
                         │ (read/write)
                    ┌────┴─────┐
                    │  AI Agent│ ← Claude / GPT via MCP
                    │  Server  │
                    └────┬─────┘
                         │
                    ┌────┴─────┐
                    │  Python  │ ← Data Pipeline
                    │  Engine  │
                    └────┬─────┘
                         │
              ┌──────────┴──────────┐
              │                     │
         ┌────┴────┐          ┌────┴────┐
         │  NSE    │          │  BSE    │
         │  APIs   │          │  APIs   │
         └─────────┘          └─────────┘
```

---

## 5. Notion Database Schema

### DB 1: `Stocks Master` (one row per stock)
| Property | Type | Example |
|----------|------|---------|
| Symbol | Title | HCLTECH |
| BSE Code | Number | 532281 |
| ISIN | Text | INE860A01027 |
| Industry | Select | IT - Software |
| Group | Select | A |
| PE | Number | 28.5 |
| EPS | Number | 62.3 |
| Debt/Equity | Number | 0.05 |
| Current Ratio | Number | 2.8 |
| ROCE % | Number | 35.2 |
| Promoter Hold % | Number | 60.3 |
| Pledged % | Number | 0 |
| Piotroski Score | Number | 7 |
| Passes Screen | Checkbox | ✅ |
| AI Rating | Select | Strong Buy / Buy / Hold / Avoid |
| Last Updated | Date | 2026-03-10 |

### DB 2: `Daily Prices` (one row per stock per day)
| Property | Type | Example |
|----------|------|---------|
| Entry | Title | HCLTECH-2026-03-10 |
| Stock | Relation | → Stocks Master |
| Date | Date | 2026-03-10 |
| Open | Number | 1850 |
| High | Number | 1875 |
| Low | Number | 1840 |
| Close | Number | 1868 |
| Volume | Number | 2,500,000 |
| Delivery Qty | Number | 1,200,000 |
| Delivery % | Number | 48% |
| Turnover Cr | Number | 46.5 |

### DB 3: `Screener Results` (filtered output)
| Property | Type | Example |
|----------|------|---------|
| Stock | Relation | → Stocks Master |
| Screen Date | Date | 2026-03-10 |
| Conditions Met | Number | 12/12 |
| Failed Conditions | Multi-select | (empty if all pass) |
| Score | Number | 85 |
| AI Commentary | Text | "Strong delivery uptick with fundamentals intact..." |

### DB 4: `Watchlist` (user's picks with notes)
| Property | Type | Example |
|----------|------|---------|
| Stock | Relation | → Stocks Master |
| Added Date | Date | 2026-03-10 |
| User Notes | Text | "Watching for breakout above 1900" |
| AI Alerts | Text | Auto-populated by AI |
| Status | Select | Watching / Entered / Exited |

### DB 5: `AI Analysis Reports` (pages generated by AI)
- Weekly market summary pages
- Stock-specific deep dives
- Sector comparison reports
- Anomaly/alert reports (e.g., "promoter pledging jumped")

---

## 6. Execution Plan (Day-by-Day)

### Phase 1: Foundation (Days 1–3) — Mar 10–12

**Day 1: Project Setup & Data Pipeline**
- [ ] Set up project structure (Python, requirements.txt, .env)
- [ ] Rewrite `main.py` → cross-platform, robust NSE/BSE downloader
  - Fix path separators (use `os.path.join`)
  - Add retry logic with exponential backoff
  - Add date range batch download mode
  - Add CLI args instead of manual `input()`
- [ ] Parse downloaded BhavCopy CSVs into structured DataFrames
- [ ] Parse the existing Excel workbooks to extract fundamental data

**Day 2: Notion Setup & Data Upload**
- [ ] Create Notion integration + get API token
- [ ] Set up Notion MCP server (follow official guide)
- [ ] Create all 5 databases in Notion (programmatically via MCP or API)
- [ ] Build the upload pipeline: Python → Notion databases
  - Upload Stocks Master (440 stocks with fundamentals)
  - Upload recent Daily Prices (last 30 days to start, not all 281 — Notion has rate limits)
- [ ] Test MCP read/write round-trip

**Day 3: Screening Engine**
- [ ] Implement the 12-condition screener in Python
- [ ] Run screener against Notion data (read from Notion → screen → write results back)
- [ ] Write screener results to `Screener Results` database
- [ ] Add a scoring system (0–100 based on how strongly each condition is met)

### Phase 2: AI Intelligence Layer (Days 4–6) — Mar 13–15

**Day 4: MCP Agent Setup**
- [ ] Configure Notion MCP with Claude Desktop or custom MCP client
- [ ] Build MCP tool definitions for the agent:
  - `get_screened_stocks` — reads Screener Results
  - `get_stock_fundamentals` — reads Stocks Master
  - `get_price_history` — reads Daily Prices
  - `write_analysis` — creates analysis pages
  - `update_watchlist` — adds AI alerts to Watchlist

**Day 5: AI Analysis Features**
- [ ] **Stock Analyzer:** Given a symbol, AI reads all data and writes a deep-dive report page
  - Fundamental health assessment
  - Price trend summary (using delivery % as conviction signal)
  - Comparison to industry peers (using Funda_Comparisons data)
  - Risk flags (pledging increase, FII exit, profit decline)
- [ ] **Market Scanner:** AI reviews all screened stocks, identifies top picks for the week
- [ ] **Anomaly Detector:** AI flags unusual patterns:
  - Sudden delivery % spike (institutional interest)
  - Promoter holding change
  - Stocks newly entering/exiting the 12-condition filter

**Day 6: Alerts & Watchlist Intelligence**
- [ ] AI monitors Watchlist stocks and writes alerts
- [ ] Generate weekly summary page: "This Week in StockPulse"
- [ ] Add sector-level analysis (aggregate metrics per industry)

### Phase 3: Polish & Submit (Days 7–9) — Mar 16–18

**Day 7: Dashboard & UX**
- [ ] Create a beautiful Notion dashboard page (the "home page"):
  - Market overview section
  - Top screened stocks table (embedded DB view)
  - Latest AI insights
  - Quick links to sector pages
- [ ] Add Notion database views: Gallery, Board (by sector), Calendar
- [ ] Ensure all relations and rollups work correctly

**Day 8: Demo & Documentation**
- [ ] Record video demo (~3–5 min):
  - Show the Notion workspace
  - Run the data pipeline
  - Trigger AI analysis via MCP
  - Show AI writing reports and alerts into Notion
- [ ] Write DEV.to post using the submission template:
  - "What I Built"
  - "Video Demo"
  - "Show us the code" (GitHub link)
  - "How I Used Notion MCP"
- [ ] Clean up GitHub repo: README, license (MIT), .env.example

**Day 9: Buffer & Submit**
- [ ] Final testing end-to-end
- [ ] Submit on DEV.to before March 29

---

## 7. Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Data Pipeline | `requests`, `pandas`, `openpyxl` |
| Notion Integration | Notion MCP (official) + `notion-client` SDK as fallback |
| AI Agent | Claude via MCP (primary), or OpenAI API |
| MCP Server | Notion's official MCP server |
| Scheduling | `cron` (macOS) or GitHub Actions for daily runs |
| Charts | `matplotlib` / `plotly` → export as images → embed in Notion |
| Repo | GitHub (public) |

---

## 8. Key Differentiators vs. Other Submissions

| Factor | StockPulse India | Typical Submission |
|--------|------------------|--------------------|
| Data Volume | 440 stocks × 281 days = 123K+ rows | Usually toy data |
| Domain | Real financial analysis with real strategy | Often hypothetical |
| Data Source | Live NSE/BSE feeds (real APIs) | Usually manual input |
| AI Depth | Multiple analysis types (stock, sector, anomaly) | Usually one-shot |
| Human-in-loop | Investor reviews AI picks, adds notes, tracks watchlist | Often fully automated |
| Notion Usage | 5 databases + relations + rollups + pages | Usually 1-2 databases |

---

## 9. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| NSE/BSE blocks scraping | Use existing Excel data as fallback; also try official BSE API |
| Notion API rate limits (3 req/sec) | Batch uploads, throttle, upload incrementally |
| Too much data for Notion | Limit to last 60 days of prices + top 100 stocks initially |
| Fundamental data sourcing | Extract from existing Excel; supplement from free APIs |
| Time crunch | Core MVP (pipeline + screening + 1 AI report) achievable in 5 days |

---

## 10. MVP vs. Full Vision

### MVP (Must Have for Submission) ✅
1. Data pipeline: Excel/CSV → Notion databases
2. 12-condition screener running against Notion data
3. AI agent (via MCP) that reads screened stocks and writes analysis reports
4. Working demo with real data
5. Clean Notion dashboard

### Nice-to-Have (If Time Permits) 🎯
- Live daily data refresh from NSE/BSE
- Candlestick chart generation embedded in Notion pages
- Sector comparison dashboards
- Automated alerts (via email or Slack)
- Portfolio tracking (buy/sell log with P&L)
- Piotroski Score deep explanation per stock

---

## 11. Submission Outline (DEV.to Post)

### Title
**"StockPulse India — AI-Powered Stock Screener & Analyst Living in Notion"**

### What I Built
An intelligent stock analysis system that screens 5000+ Indian stocks down to ~440 fundamentally strong ones using 12 quantitative conditions, stores everything in Notion, and uses an AI agent (via Notion MCP) to generate research reports, detect anomalies, and maintain a smart watchlist — all without leaving Notion.

### How I Used Notion MCP
- **Read operations:** AI reads stock fundamentals, daily prices, and screener results from Notion databases to understand the data landscape
- **Write operations:** AI writes deep-dive analysis pages, weekly market summaries, watchlist alerts, and anomaly flags directly into Notion
- **Bidirectional workflow:** User adds stocks to watchlist in Notion → AI monitors and adds insights → User reviews and makes decisions → cycle repeats

### Video Demo
[3-5 minute walkthrough]

### Show Us the Code
[GitHub link with full source, README, and instructions]
