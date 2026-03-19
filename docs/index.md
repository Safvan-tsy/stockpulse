# StockPulse India — Documentation

> AI-Powered Indian Stock Intelligence on Notion
> Built for the [Notion MCP Challenge](https://dev.to/challenges/notion-2026-03-04) by DEV Community × Notion

---

## What Is This?

**StockPulse India** is a full-stack AI stock research system that:

- Downloads and parses **5,750+ Indian stocks** from NSE/BSE data files
- Screens them through **12 battle-tested fundamental conditions**
- Pushes the entire dataset into **5 linked Notion databases**
- Exposes an **MCP server** with 11 tools and 3 prompts so an AI agent (Claude, GPT-4, etc.) can query, analyze, and write reports directly into your Notion workspace

The result: manual Excel screening strategy -> automated, AI-annotated, and living in Notion.

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [Challenge & Motivation](./challenge.md) | Why we built this, what the Notion MCP Challenge asked for, and how this submission maps to the judging criteria |
| [Architecture Overview](./architecture.md) | System design, component map, data flow, and the 5 Notion database schemas |
| [Setup Guide](./setup.md) | Prerequisites, installation (pip + .env + Notion integration), and first-run walkthrough |
| [Data Pipeline](./data-pipeline.md) | Excel parsing, the 12-condition screener engine, and how data flows from worksheet to Notion |
| [CLI Reference](./cli-reference.md) | Every `stockpulse` command with flags, examples, and expected output |
| [MCP Server](./mcp-server.md) | The 11 MCP tools, 3 prompts, Claude Desktop config, and example AI conversations |
| [Notion Integration](./notion-integration.md) | Notion setup walkthrough, Data Sources API specifics, database schemas, and known quirks |
| [Troubleshooting](./troubleshooting.md) | Common errors, fixes, and the Notion Data Sources API migration story |

---

## Quick Navigation

**I want to run this for the first time** → [Setup Guide](./setup.md)

**I want to understand how the project works** → [Architecture Overview](./architecture.md)

**I want to use the CLI** → [CLI Reference](./cli-reference.md)

**I want to connect it to Claude** → [MCP Server](./mcp-server.md)

**Something broke** → [Troubleshooting](./troubleshooting.md)

**Reading for the hackathon submission** → [Challenge & Motivation](./challenge.md)
