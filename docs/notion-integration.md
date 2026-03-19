# Notion Integration

This document covers everything about how StockPulse integrates with Notion — from the initial setup to the API behavior that drove a significant mid-project rewrite.

---

## How Notion Is Used

StockPulse uses Notion as its **primary database backend**. All stock data, screener results, price history, watchlist entries, and AI-generated reports live in Notion. The Python code writes to Notion, and the MCP server reads from it for AI agent queries.

This means:
- Data persists across sessions (no local database needed)
- Multiple team members could view the same data in Notion
- Human-in-the-loop actions (editing notes, flagging stocks) happen naturally in the Notion UI
- AI reads and writes use the exact same data the human sees

---

## Initial Notion Setup

### 1. Create a Notion Integration

1. Visit [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **+ New integration**
3. Set a name (e.g., `StockPulse`)
4. Select your workspace
5. Under **Capabilities**, enable:
   - Read content ✅
   - Update content ✅
   - Insert content ✅
6. Save and copy the **Internal Integration Token** (`secret_xxx...`)

### 2. Create a Parent Page

You need a Notion page to hold the 5 StockPulse databases.

1. In Notion, create a new full-page (not an inline page)
2. Name it `StockPulse India` (or anything)
3. **Share it with your integration:**
   - Open the page
   - Click `...` menu → **Connections**
   - Find your integration and **Connect**
4. **Copy the page ID** from the URL:
   - URL: `https://www.notion.so/Your-Page-**18770b1b6e3b402e9b1e42883ec5d284**`
   - The 32-character hex string is the page ID
   - Dashes are optional (`18770b1b-6e3b-...` and `18770b1b6e3b...` both work)

### 3. Create Databases

```bash
python -m stockpulse setup
```

This creates 5 databases as sub-pages of your parent page and saves their IDs to `notion_db_ids.json`.

---

## The `notion_db_ids.json` File

After `setup`, this file is created at the project root:

```json
{
  "stocks_master": "18770b1b-6e3b-402e-9b1e-42883ec5d284",
  "daily_prices": "f4bd67d6-3b7e-44fa-b13c-709d72206a00",
  "screener": "45ed576d-2bf8-43dc-b4fe-6b224a325ed4",
  "watchlist": "fb5d5479-29a0-4be2-ad01-0eada1af21cc",
  "reports": "cb8f5a3c-3cfb-465b-98ff-97f6c9fe143a"
}
```

These are the Notion database IDs. **Don't delete this file.** If you do, re-run `setup` and point the new databases correctly, or find the IDs from the database URLs in Notion.

---

## The Data Sources API (Critical)

### What Changed in Notion

StockPulse hit a significant blocker during development: every single stock upload was returning a 400 error:

```
Failed to upload DHATRE: Symbol is not a property that exists.
BSE Code is not a property that exists.
...
```

**Root cause:** Notion's API changed behavior for recently-created databases.

**Old behavior (classic databases):**
- `databases.retrieve(database_id=...)` returns `properties: { "Symbol": {...}, ... }`
- Pages are created with `parent={"database_id": "..."}`
- Queried with `databases.query(database_id=...)`

**New behavior (data source–backed databases):**
- `databases.retrieve(database_id=...)` returns `properties: null`
- The schema lives in a separate **Data Source** object
- The database object includes `data_sources: [{"id": "xxxx"}]`
- `data_sources.retrieve(data_source_id=...)` returns the actual schema
- Pages are created with `parent={"data_source_id": "..."}`
- Queried with `data_sources.query(data_source_id=...)`

This affects all databases created via the API after Notion rolled out this new internal architecture.

### How StockPulse Handles It

The `ensure_all_db_schemas()` function in `notion_setup.py` handles this transparently:

```python
# 1. Retrieve the database to get data_source_id
db = client.databases.retrieve(database_id=db_id)
ds_list = db.get("data_sources", [])
data_source_id = ds_list[0]["id"]  # Extract the data_source_id

# 2. Check existing properties
ds_obj = client.data_sources.retrieve(data_source_id=data_source_id)
existing = set(ds_obj.get("properties", {}).keys())

# 3. Add missing properties
missing = {k: v for k, v in desired_props.items() if k not in existing}
if missing:
    client.data_sources.update(
        data_source_id=data_source_id,
        properties=missing,
    )
```

For page creation:
```python
# Use data_source_id, not database_id
client.pages.create(
    parent={"data_source_id": data_source_id},
    properties={...},
)
```

For queries:
```python
# Use data_sources.query, not databases.query
response = client.data_sources.query(
    data_source_id=data_source_id,
    filter={...},
)
```

This function is called automatically before every upload operation and before the MCP server makes any queries, so the schema is always in sync.

---

## Database Schema Management

### Schema Definitions

The `SCHEMAS` dict in `notion_setup.py` defines the desired properties for each database:

```python
SCHEMAS = {
    "stocks_master": {
        "title": "Symbol",          # Title property name
        "properties": {             # Non-title properties
            "BSE Code": {"number": {"format": "number"}},
            "ISIN": {"rich_text": {}},
            "Industry": {"select": {"options": []}},
            "PE": {"number": {"format": "number"}},
            "Passes Screen": {"checkbox": {}},
            "AI Rating": {"select": {"options": [
                {"name": "Strong Buy", "color": "green"},
                ...
            ]}},
            ...
        }
    },
    "daily_prices": { ... },
    "screener": { ... },
    "watchlist": { ... },
    "reports": { ... },
}
```

### Title Property Renaming

When Notion creates a database, it defaults the title property to `"Name"`. StockPulse renames this to the correct field name (`Symbol`, `Entry`, `Stock`, `Title`) using `data_sources.update()`.

This happens automatically during `ensure_all_db_schemas()`.

### Relation Properties

The `daily_prices` and `screener` databases have relation properties pointing to `stocks_master`. These are defined using `data_source_id` (not `database_id`):

```python
"Stock": {
    "relation": {
        "data_source_id": "<stocks_master_data_source_id>",
        "type": "single_property",
    }
}
```

The placeholder is resolved at runtime in `ensure_all_db_schemas()` by first looking up the Stocks Master data source ID.

---

## API Rate Limits

Notion enforces approximately **3 requests per second** per integration token. StockPulse respects this with a built-in `_rate_limit_pause()`:

```python
def _rate_limit_pause():
    time.sleep(0.34)  # ~3 req/s
```

This is called between every `pages.create()` call in the uploader. For large uploads:
- 5,750 stocks: ~32 minutes
- 898 screener rows: ~5 minutes

There is no burst mode or parallelism — Notion's rate limit applies per token, not per connection, so spawning multiple threads would just result in 429 errors.

### Handling 429s

If you hit a rate limit anyway (e.g., other tools also using the same integration concurrently), the `tenacity` library is available in requirements and can be used to wrap API calls with exponential backoff retry logic.

---

## Notion Views to Create

After the pipeline runs, it helps to set up useful views in Notion:

### Stocks Master — Useful Views

| View Type | Filter | Sort | Purpose |
|-----------|--------|------|---------|
| Table | Passes Screen = ✅ | Screen Score DESC | Top performers |
| Gallery | Passes Screen = ✅ | — | Visual browsing |
| Table | AI Rating = Strong Buy | Score DESC | AI top picks |
| Table | Industry = "IT - Software" | Score DESC | Sector view |

### Daily Prices — Useful Views

| View Type | Filter | Sort |
|-----------|--------|------|
| Table | Date = Today | — |
| Table | Symbol = "XXXX" | Date DESC |

### Screener Results — Useful Views

| View Type | Sort |
|-----------|------|
| Table | Score DESC |
| Table | Conditions Met DESC |

---

## Security Notes

- Your `NOTION_TOKEN` gives full read/write access to everything shared with the integration
- Never commit `.env` to version control (it's in `.gitignore`)
- `notion_db_ids.json` is safe to commit (it's just database IDs, not secrets)
- The integration has access only to pages/databases explicitly shared with it — it cannot access your entire Notion workspace
