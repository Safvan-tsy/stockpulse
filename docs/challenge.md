# Challenge & Motivation

## The Notion MCP Challenge

The **Notion MCP Challenge** (Mar 4–29, 2026) was run by DEV Community in partnership with Notion. The prompt was simple and open-ended:

> *"Build the most impressive system or process using Notion MCP (Model Context Protocol)."*

**Prizes:** 3 winners × $500 USD + DEV++ subscription + Exclusive Winner Badge. All valid submissions earn a completion badge.

**Judging criteria:**
1. **Originality & Creativity** — Is the use-case unique? Does it feel fresh?
2. **Technical Complexity** — Non-trivial architecture, real integrations, custom code
3. **Practical Implementation** — Does it solve a real problem end-to-end?

The challenge explicitly encouraged using AI tools in your workflow, building on open-source, and focusing on "human-in-the-loop" workflows where Notion acts as the centralized knowledge hub.

---

## Why We Built This

### The Starting Point: An Excel Strategy

The seed idea came from a real-world problem. A friend had built an Excel-based system to screen Indian stocks from NSE/BSE data:

- Every morning, download BhavCopy CSV files from NSE and BSE
- Run the data through a handcrafted set of 12 fundamental conditions
- The 440 or so stocks that passed all 12 conditions were the "fundamentally clean" universe to watch
- Any stock in that universe showing unusual delivery or price action got researched further

**The problem:** This was entirely manual. New data every morning, re-run the Excel, scan the output by eye, do the research yourself. It worked, but it didn't scale, couldn't be shared, provided no AI augmentation, and lived in a local file no one else could access.

### The Insight: Notion + MCP = the Perfect Upgrade

Notion as a database backend gives you:
- Persistent, shareable, multi-device storage for all 5,750 stocks
- Native filtering, sorting, and views (gallery, table, calendar)
- Human-friendly interface for adding notes, creating watchlists, flagging stocks

Notion MCP on top of that gives you:
- An AI that can read and write your actual stock data
- The ability to ask "show me IT sector stocks with PE under 20 that pass the screen" and get a structured answer
- The ability to have the AI write a research report directly into a Notion page
- A "human-in-the-loop" workflow: AI surfaces the signal, human decides the action

**The result:** Your friend's strategy, supercharged with AI and centralized in Notion.

---

## How It Meets the Judging Criteria

### 1. Originality & Creativity ⭐⭐⭐⭐⭐

- **No existing challenge submission** (at the time of building) covered Indian stock market analysis as a use-case
- Uses a *real, tested, manual strategy* and translates it into a fully automated system — not a toy demo
- The "human-in-the-loop" angle is authentic: an investor reviews AI insights, marks stocks, adds notes. Notion is the collaboration layer
- Covers a domain that is visual, financially meaningful, and globally relatable while being India-specific (a market of 1.4 billion people with 5,000+ listed stocks)

### 2. Technical Complexity ⭐⭐⭐⭐⭐

| Component | Technical Merit |
|-----------|----------------|
| Excel parser | Reads multi-sheet `.xlsx` workbooks (68–257 MB), maps ~96 columns across 5 sheets into clean DataFrames |
| 12-condition screener | Operationally flexible condition engine with scoring; 898 of 5,750 stocks pass |
| Notion integration | 5 linked databases, auto-schema repair, Notion Data Sources API (see below) |
| MCP server | 11 tools + 3 prompt templates, FastMCP, pagination, graceful Python 3.9 fallback |
| Data pipeline | Handles 5,750 stocks × 28 properties + 109,561 price rows × 12 properties with rate limiting and retry |
| CLI | 9 commands covering the full lifecycle (setup, parse, screen, upload, download, serve, pipeline) |

A notable unexpected challenge: Notion's API changed its database behavior. New databases are backed by a **Data Source** object rather than the classic `properties` block. The project had to discover and implement the Data Sources API (`data_sources.retrieve`, `data_sources.update`, `data_sources.query`) to make the entire upload and query pipeline work. This is documented in detail in [Notion Integration](./notion-integration.md).

### 3. Practical Implementation ⭐⭐⭐⭐⭐

- **Real data:** 5,750 actual NSE/BSE-listed stocks with real fundamentals (PE, EPS, ROCE, promoter holding, etc.)
- **Real strategy:** The 12 conditions are not made up — they are a documented, working strategy used by a real investor
- **Real output:** After running the pipeline, you have a Notion workspace with 898 fundamentally screened stocks, all their metrics, and an AI that can answer questions about them
- **Working end-to-end:** `python -m stockpulse pipeline` takes you from Excel files to a fully populated Notion workspace with zero manual steps

---

## Comparison to Other Submissions

Looking at the pattern emerging from the top challenge submissions:

| Pattern | StockPulse India |
|---------|-----------------|
| Uses Notion as both data storage and output | ✅ 5 databases + AI report pages |
| AI reads from and writes to Notion via MCP | ✅ 11 tools; `write_analysis_report`, `update_stock_ai_rating` write back |
| Solves a real-world, non-trivial problem | ✅ Real stock screening strategy |
| Human-in-the-loop workflow | ✅ Human reviews AI ratings, manages watchlist |
| Code + demo available | ✅ Full source on GitHub |
| Interesting, engaging domain | ✅ Stock market, India-specific, financially relevant |

---

## Project Timeline

| Date | Milestone |
|------|-----------|
| Mar 10 | Project ideated; challenge brief reviewed; strategy analyzed |
| Mar 10–11 | Core source files written (parser, screener, uploader, notion_setup, mcp_server, dashboard, cli) |
| Mar 11 | Python 3.9 compatibility fixes; mcp package made optional |
| Mar 12 | CLI tested; screener validated (898/5750 pass) |
| Mar 12 | Notion upload hit 400 errors; Data Sources API root cause found |
| Mar 12–13 | Full Notion integration rewritten for Data Sources API |
| Mar 13 | Pipeline end-to-end confirmed; all 5,750 stocks uploading with 200 OK |
| Mar 15 | Documentation written |

---

## What "Meets the Challenge" Looks Like

The challenge rubric asks for a system that:

- **Uses Notion MCP as a core part** — StockPulse's MCP server exposes 11 tools and 3 prompt templates specifically designed to let an AI agent work with Notion-hosted stock data. Every tool reads from or writes to Notion.
- **Demonstrates a "sick integration"** — 5 Notion databases, live fundamental data, screener results, price history, and AI-generated research reports all linked and query-able
- **Is a working solution** — `python -m stockpulse pipeline` runs start-to-finish and populates your Notion workspace with real data
- **Automates a realistic workflow** — replaces a manual daily Excel process with an automated, AI-augmented pipeline

The one aspect where a human must still act: connecting to Claude Desktop and invoking the MCP prompts. This is by design — the "human-in-the-loop" is the investor who decides what to investigate and what decisions to make based on the AI's analysis.
