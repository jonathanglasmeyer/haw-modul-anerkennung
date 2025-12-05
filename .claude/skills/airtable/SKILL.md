---
name: airtable
description: Interact with Airtable bases via mcporter. Use when user asks to read, create, update Airtable records, list bases/tables, or manage Airtable data.
---

# Airtable MCP

Access Airtable via mcporter with the airtable-mcp-server.

## Setup

Token is stored in project `.env`. Load before calling mcporter:

```bash
export $(grep AIRTABLE_API_KEY .env | xargs) && mcporter list airtable
```

## Common Commands

```bash
# List available tools
export $(grep AIRTABLE_API_KEY .env | xargs) && mcporter list airtable

# List bases
export $(grep AIRTABLE_API_KEY .env | xargs) && mcporter airtable.list_bases

# List tables in a base
export $(grep AIRTABLE_API_KEY .env | xargs) && mcporter airtable.list_tables baseId=appXXX

# List records
export $(grep AIRTABLE_API_KEY .env | xargs) && mcporter airtable.list_records baseId=appXXX tableId=tblXXX

# Create record
export $(grep AIRTABLE_API_KEY .env | xargs) && mcporter airtable.create_record baseId=appXXX tableId=tblXXX fields='{"Name":"Test"}'
```

## Token Location

- `.env` in project root (gitignored)
- Format: `AIRTABLE_API_KEY=pat...`
- Get token: https://airtable.com/create/tokens
