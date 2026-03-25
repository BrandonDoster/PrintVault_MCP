# Print Vault MCP Server

An [MCP](https://modelcontextprotocol.io) server that gives AI assistants full access to a self-hosted [Print Vault](https://github.com/shaxs/print-vault) instance — the 3D printing inventory, filament, printer, project, and print-tracker management app.

Built for Claude Desktop, Claude Code, and any MCP-compatible client.

---

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- A running Print Vault instance (v1.1.0+)

### Install & Run

```bash
# Clone the repo
git clone https://github.com/your-org/PrintVaultMCP.git
cd PrintVaultMCP

# Copy and configure environment
cp .env.example .env
# Edit .env and set PRINT_VAULT_URL to your instance

# Run the server
uv run print-vault-mcp
```

### Add to Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "print-vault": {
      "command": "uv",
      "args": ["--directory", "/path/to/PrintVaultMCP", "run", "print-vault-mcp"],
      "env": {
        "PRINT_VAULT_URL": "http://192.168.1.100:8000"
      }
    }
  }
}
```

### Add to Claude Code

```bash
claude mcp add print-vault \
  --command "uv --directory /path/to/PrintVaultMCP run print-vault-mcp" \
  --env PRINT_VAULT_URL=http://192.168.1.100:8000
```

---

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PRINT_VAULT_URL` | Yes | — | Base URL of your Print Vault instance |
| `PRINT_VAULT_TIMEOUT` | No | `30` | HTTP request timeout in seconds |

---

## Tools

38 tools organized across 7 groups:

### Dashboard & System

| Tool | Description |
|------|-------------|
| `get_dashboard` | Full status overview — alerts, stats, featured trackers, active projects |
| `get_version` | Current Print Vault version |
| `dismiss_alert` | Dismiss a specific dashboard alert |

### Inventory Management

| Tool | Description |
|------|-------------|
| `search_inventory` | Search items by keyword, brand, part type, or location |
| `get_inventory_item` | Full detail on a specific item |
| `add_inventory_item` | Add a new item (auto-creates brands, locations, etc.) |
| `update_inventory_item` | Update any field on an existing item |
| `get_low_stock` | List all consumables at or below threshold |
| `get_item_allocation` | See which projects are using an item |

### Filament Management

| Tool | Description |
|------|-------------|
| `list_materials` | Browse material blueprints and generic types |
| `get_material_spools` | List physical spools for a material blueprint |
| `list_spools` | Browse spools with status/printer/color filters |
| `add_filament_spool` | Add new spool(s) linked to a material blueprint |
| `update_spool_weight` | Update current weight (auto-updates status) |
| `mark_spool_empty` | Mark a spool as empty |
| `open_spool` | Open a spool from an unopened batch |
| `archive_spools` | Bulk archive empty spools |
| `toggle_material_favorite` | Toggle favorite on a material (max 5) |

### Printer Management

| Tool | Description |
|------|-------------|
| `list_printers` | List printers with search and status filter |
| `get_printer` | Full detail including mods and filament |
| `update_printer` | Update status, notes, etc. |
| `add_mod` | Add a mod/upgrade to a printer |
| `update_mod` | Update mod status |

### Project Management

| Tool | Description |
|------|-------------|
| `list_projects` | List projects with search and status filter |
| `get_project` | Full detail with BOM, inventory, printers, trackers |
| `create_project` | Create a new project |
| `update_project` | Update project fields |
| `add_bom_item` | Add a BOM line item (auto-reserves linked inventory) |
| `get_shopping_list` | Consolidated buy list across all active projects |
| `link_printer_to_project` | Associate a printer with a project |

### Print Tracker

| Tool | Description |
|------|-------------|
| `list_trackers` | List all print trackers |
| `get_tracker` | Full tracker detail with file list and progress |
| `create_tracker_from_github` | Crawl a GitHub repo for printable files |
| `update_file_status` | Update print status of a tracker file |

### Reference Data

| Tool | Description |
|------|-------------|
| `list_brands` | All brands/manufacturers |
| `list_locations` | All storage locations |
| `list_part_types` | All part type categories |
| `list_vendors` | All vendors/suppliers |

---

## Project Structure

```
PrintVaultMCP/
├── src/print_vault_mcp/
│   ├── __init__.py          # Package entry point
│   ├── __main__.py          # python -m support
│   ├── client.py            # Async HTTP client for Print Vault API
│   ├── formatters.py        # AI-friendly response formatters
│   └── server.py            # MCP server & tool definitions
├── docs/
│   ├── design.md            # Architecture & design document
│   └── reference/           # Print Vault source extracts (API contract)
├── .env.example             # Environment variable template
├── .gitignore
├── pyproject.toml           # uv/pip package configuration
└── README.md
```

---

## Development

```bash
# Install dependencies
uv sync

# Run the server locally (stdio mode)
PRINT_VAULT_URL=http://localhost:8000 uv run print-vault-mcp

# Run with the MCP inspector for debugging
npx @modelcontextprotocol/inspector uv run print-vault-mcp
```

---

## How It Works

The server is a stateless protocol translation layer. It receives structured tool calls from AI clients via MCP (stdio transport), translates them into HTTP requests against the Print Vault REST API, and returns formatted text responses the AI can reason about.

```
AI Client  ──MCP (stdio)──>  PrintVaultMCP  ──HTTP/JSON──>  Print Vault
```

Print Vault uses `AllowAny` permissions on every endpoint (single-user self-hosted app), so the MCP server only needs the base URL — no tokens or credentials required.

---

## License

MIT
