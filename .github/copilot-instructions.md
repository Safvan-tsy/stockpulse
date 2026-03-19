# StockPulse Workspace Instructions

These instructions guide the AI on the codebase conventions, technical stack, and architecture of the StockPulse Notion MCP project.

## Python Conventions
- **Version:** Project requires Python 3.10+ (for `FastMCP` and type hints).
- **Type Hinting:** Always use modern type hinting. Include `from __future__ import annotations` at the top of Python files.
- **Logging:** Use the standard `logging` library instead of `print()`. Instantiate a logger at the top of each file: `logger = logging.getLogger(__name__)`.
- **Formatting & Style:** Follow PEP 8 style guidelines. Ensure clean docstrings for all functions, especially MCP tools.
- **Dependencies:** Core libraries include `pandas` for data manipulation, `notion-client` for Notion API interactions, and `mcp` (`FastMCP`) for building the Model Context Protocol server.

## Architecture Guidelines
- **Notion Integration:** 
  - Treat Notion as a strict database schema. Use the official `notion_client` SDK.
  - Operations manipulating database schemas or fetching properties should handle Notion API rate limits natively natively (or gracefully error).
  - Use `stockpulse.notion_setup` for schema and ID management. IDs are typically cached locally in `notion_db_ids.json`.
- **MCP Server:**
  - Tools are defined in `src/stockpulse/mcp_server.py` using `FastMCP`.
  - Prefix new tool functions with the `@_tool()` decorator defined in `mcp_server.py`.
  - Tool arguments should have strictly typed parameters and clear python docstrings to define their function for the LLM. Returns should generally be stringified JSON or plain text for easy LLM parsing.
- **Screener (`screener.py`):** Maintain complex logic using `pandas`. Make operations vectorized over dataframes rather than iterating row-by-row when applying fundamental stock conditions.

## Project Structure Notes
- **`src/stockpulse/`**: Core package modules.
- **`docs/`**: Documentation (Architecture, CLI, Notion Integration, Setup). Keep these up-to-date with code changes.
- **`workbook/`**: Base scripts for NSE/BSE data extraction.

## Terminal Commands reference
Use the predefined CLI entrypoints (`python -m stockpulse <command>`):
- `setup`, `parse`, `screen`, `upload`, `upload-prices`, `dashboard`, `serve`, `pipeline`.
