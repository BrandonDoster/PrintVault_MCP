# Print Vault MCP Server — Design Document

**Author:** Brandon — Denali AI  
**Date:** March 2026  
**Source:** github.com/shaxs/print-vault (v1.1.0)

---

## Executive Summary

This document defines the design for a Model Context Protocol (MCP) server that wraps the Print Vault REST API, enabling AI assistants (Claude Desktop, Claude Code, or any MCP-compatible client) to interact with a self-hosted Print Vault instance. The MCP server will expose tools for inventory queries, filament tracking, printer management, project organization, print tracker operations, and dashboard analytics.

The integration is highly feasible. Print Vault is built on Django REST Framework with a fully exposed, unauthenticated REST API. Every endpoint uses `AllowAny` permissions, meaning the MCP server only needs the base URL of the running instance to begin making requests. No token management, OAuth flows, or credential storage is required.

### Feasibility Assessment

| Factor | Finding | Impact |
|--------|---------|--------|
| API Availability | Full REST API at `/api/` with 20+ registered ViewSets | No reverse engineering needed |
| Authentication | `AllowAny` on every endpoint (single-user app) | Zero auth complexity for MCP |
| Data Format | Standard JSON request/response throughout | Direct serialization in MCP tools |
| Search & Filtering | DRF SearchFilter + OrderingFilter + django-filters | Natural language queries map cleanly |
| Custom Actions | Rich action endpoints (shopping list, allocation, weight tracking) | High-value MCP tools beyond basic CRUD |
| Network Access | HTTP on configurable port, Tailscale-compatible | Reachable from local or Tailnet |

---

## Architecture Overview

The MCP server sits between the AI client and the Print Vault instance as a thin protocol translation layer. It receives structured tool calls from the AI client via the MCP protocol (stdio or SSE transport), translates them into HTTP requests against the Print Vault REST API, and returns structured responses that the AI can reason about.

### Component Topology

```
AI Client (Claude Desktop / Claude Code / MCP Host)
    │
    │  MCP Protocol (stdio or SSE)
    ▼
MCP Server (Python, stateless)
    │
    │  HTTP/HTTPS (JSON)
    ▼
Print Vault Instance (Django + DRF + PostgreSQL)
```

All three components can run on the same machine, or the Print Vault instance can be on a separate server reachable via local network or Tailscale.

### Technology Choices

| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| Language | Python 3.11+ | Matches Print Vault backend; rich MCP SDK support; familiar toolchain |
| MCP SDK | `mcp` (official Python SDK) | First-party Anthropic SDK; handles protocol negotiation, tool registration, stdio/SSE transport |
| HTTP Client | `httpx` (async) | Async-native; connection pooling; timeout control; pairs well with async MCP handlers |
| Transport | stdio (primary), SSE (optional) | stdio for Claude Desktop/Code; SSE if exposing to remote clients |
| Config | Environment variables + `.env` | Consistent with Print Vault's own config pattern; `PRINT_VAULT_URL` as the sole required variable |
| Packaging | Docker container (optional) | Can run alongside Print Vault in the same compose stack; also runnable standalone |

> **Note:** The MCP server is stateless. It holds no data of its own and makes no database connections. Every operation is a passthrough to the Print Vault API. This means upgrades to Print Vault that add or change API endpoints only require updating the MCP tool definitions, not any data migration.

---

## Print Vault API Surface

The following is the complete API surface extracted from the Print Vault source code (`urls.py`, `views.py`, `models.py`, `serializers.py`). This forms the contract that the MCP server will consume.

### Router-Registered Endpoints (CRUD)

All endpoints below are registered via DRF's `DefaultRouter`, providing standard `list`, `create`, `retrieve`, `update`, `partial_update`, and `destroy` operations at `/api/{prefix}/`.

| Route Prefix | ViewSet | Model | Key Fields |
|-------------|---------|-------|------------|
| `/api/brands/` | BrandViewSet | Brand | name |
| `/api/parttypes/` | PartTypeViewSet | PartType | name |
| `/api/locations/` | LocationViewSet | Location | name |
| `/api/vendors/` | VendorViewSet | Vendor | name |
| `/api/material-features/` | MaterialFeatureViewSet | MaterialFeature | name |
| `/api/materials/` | MaterialViewSet | Material | name, brand, base_material, colors, temps, density, is_generic |
| `/api/material-photos/` | MaterialPhotoViewSet | MaterialPhoto | material, image, caption, order |
| `/api/filament-spools/` | FilamentSpoolViewSet | FilamentSpool | filament_type, quantity, weight, status, location, printer |
| `/api/inventoryitems/` | InventoryItemViewSet | InventoryItem | title, brand, part_type, quantity, cost, location, is_consumable |
| `/api/printers/` | PrinterViewSet | Printer | title, manufacturer, serial_number, status, maintenance dates |
| `/api/mods/` | ModViewSet | Mod | printer, name, link, status |
| `/api/modfiles/` | ModFileViewSet | ModFile | mod, file |
| `/api/projects/` | ProjectViewSet | Project | project_name, description, status, dates, materials |
| `/api/projectinventory/` | ProjectInventoryViewSet | ProjectInventory | project, inventory_item, quantity_used |
| `/api/projectprinters/` | ProjectPrintersViewSet | ProjectPrinters | project, printer |
| `/api/projectbomitems/` | ProjectBOMItemViewSet | ProjectBOMItem | project, description, quantity_needed, status |
| `/api/projectlinks/` | ProjectLinkViewSet | ProjectLink | project, name, url |
| `/api/projectfiles/` | ProjectFileViewSet | ProjectFile | project, file |
| `/api/trackers/` | TrackerViewSet | Tracker | name, github_url, creation_mode, materials |
| `/api/tracker-files/` | TrackerFileViewSet | TrackerFile | tracker, filename, quantity, printed_quantity, category |
| `/api/reminders/` | ReminderViewSet | (read-only) | Reminder aggregation |
| `/api/low-stock/` | LowStockItemsViewSet | InventoryItem | Read-only low stock filter |

### Custom Action Endpoints

Beyond standard CRUD, several ViewSets expose custom actions via `@action` decorators. These represent the highest-value operations for AI interaction.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/materials/{id}/toggle-favorite/` | POST | Toggle favorite status on a material blueprint (max 5) |
| `/api/materials/{id}/spools/` | GET | List all physical spools for a given material blueprint |
| `/api/materials/{id}/photos/` | GET/POST | List or upload additional photos for a material |
| `/api/filament-spools/{id}/split/` | POST | Split a multi-quantity spool entry into individual records |
| `/api/filament-spools/{id}/open-spool/` | POST | Mark a spool as opened (locks quantity to 1) |
| `/api/filament-spools/{id}/update-weight/` | POST | Update current weight of a spool (gram tracking) |
| `/api/filament-spools/{id}/mark-empty/` | POST | Mark a spool as empty, clear printer assignment |
| `/api/filament-spools/{id}/archive/` | POST | Archive an empty spool |
| `/api/filament-spools/bulk-archive/` | POST | Bulk archive multiple empty spools |
| `/api/inventoryitems/{id}/allocation/` | GET | Allocation summary: qty on hand, needed, available, overallocation flag |
| `/api/mods/{id}/download-files/` | GET | Download all files for a mod as ZIP |
| `/api/projects/{id}/remove-inventory/` | POST | Remove an inventory item from a project |
| `/api/projectbomitems/reorder/` | POST | Bulk update sort_order for BOM items |
| `/api/projectbomitems/shopping_list/` | GET | Consolidated shopping list across all active projects |
| `/api/trackers/crawl-github/` | POST | Crawl a GitHub repo and create a tracker with file list |
| `/api/trackers/fetch-url-metadata/` | POST | Fetch metadata from a direct download URL |
| `/api/trackers/create-manual/` | POST | Create a tracker with manually entered files |
| `/api/trackers/{id}/add-files/` | POST | Add files to an existing tracker |
| `/api/trackers/{id}/download-all-files/` | POST | Trigger download of all tracker files |
| `/api/trackers/{id}/download-zip/` | GET | Download all tracker files as a ZIP |
| `/api/trackers/{id}/upload-files/` | POST | Upload local files to a tracker |
| `/api/trackers/{id}/update_materials/` | POST | Update material assignments on a tracker |
| `/api/tracker-files/{id}/update_status/` | PATCH | Update print status of a tracker file |

### Standalone API Endpoints

These endpoints are registered directly in `urlpatterns` rather than through the router.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/` | GET | Full dashboard payload: alerts (critical/warning/info), stats, featured trackers, active projects |
| `/api/alerts/dismiss/` | POST | Dismiss a specific dashboard alert by type and ID |
| `/api/alerts/dismiss-all/` | POST | Dismiss all current dashboard alerts |
| `/api/version/` | GET | Current Print Vault version info |
| `/api/version/check-update/` | GET | Check for available updates |
| `/api/export/data/` | GET | Export all data as ZIP (CSV + media files) |
| `/api/validate-backup/` | POST | Validate a backup ZIP before import |
| `/api/import-data/` | POST | Import data from a backup ZIP |
| `/api/delete-all-data/` | POST | Delete all data (destructive, requires confirmation) |

### Search & Filtering Capabilities

Several ViewSets include DRF `SearchFilter` and `OrderingFilter`, enabling query-string-based search and sort that the MCP tools can expose as natural parameters.

| ViewSet | Search Fields | Ordering Fields | Filter Fields |
|---------|--------------|-----------------|---------------|
| InventoryItemViewSet | title, brand, part_type, location, notes | title, quantity, cost | brand__name, part_type__name, location__name |
| PrinterViewSet | title, manufacturer, serial, status, notes | title, manufacturer, status, purchase_date | manufacturer__name, status |
| ProjectViewSet | project_name, description, status, notes | project_name, status, start_date, due_date | status |
| TrackerViewSet | name, github_url | name, created_date, updated_date | — |
| FilamentSpoolViewSet | (custom get_queryset filtering) | date_added, current_weight, status | status, filament_type, location, printer |

---

## MCP Tool Design

The MCP tools are organized into logical groups matching Print Vault's domain areas. Each tool maps to one or more API calls and is designed to be useful in conversational AI interactions. Tool names follow MCP conventions (snake_case, descriptive verb-noun patterns).

### Tool Group 1: Inventory Management

Core inventory operations for hardware parts and components.

| Tool Name | Maps To | Parameters | Use Case |
|-----------|---------|-----------|----------|
| `search_inventory` | GET /api/inventoryitems/?search= | query, brand, part_type, location | "How many M3 screws do I have?" |
| `get_inventory_item` | GET /api/inventoryitems/{id}/ | item_id | Get full detail on a specific item |
| `add_inventory_item` | POST /api/inventoryitems/ | title, quantity, brand, part_type, location, cost, is_consumable, low_stock_threshold | "Add 50 M3x8 SHCS to the hardware drawer" |
| `update_inventory_item` | PATCH /api/inventoryitems/{id}/ | item_id + any writable fields | "Update the M3 screw count to 45" |
| `get_low_stock` | GET /api/low-stock/ | (none) | "What parts am I running low on?" |
| `get_item_allocation` | GET /api/inventoryitems/{id}/allocation/ | item_id | "Which projects are using my heat inserts?" |

### Tool Group 2: Filament Management

Material blueprints and physical spool tracking.

| Tool Name | Maps To | Parameters | Use Case |
|-----------|---------|-----------|----------|
| `list_materials` | GET /api/materials/ | search, is_generic, brand | "Show me all my PLA blueprints" |
| `get_material_spools` | GET /api/materials/{id}/spools/ | material_id | "How many spools of Sunlu Black PLA do I have?" |
| `add_filament_spool` | POST /api/filament-spools/ | filament_type, initial_weight, location, quantity | "I just bought 3 spools of eSun PETG" |
| `update_spool_weight` | POST .../update-weight/ | spool_id, current_weight | "My black PLA spool weighs 340g now" |
| `mark_spool_empty` | POST .../mark-empty/ | spool_id | "Mark spool 12 as empty" |
| `open_spool` | POST .../open-spool/ | spool_id | "I just opened a new spool" |
| `archive_spools` | POST .../bulk-archive/ | spool_ids[] | "Archive all my empty spools" |

### Tool Group 3: Printer Management

Printer records, mods, and maintenance tracking.

| Tool Name | Maps To | Parameters | Use Case |
|-----------|---------|-----------|----------|
| `list_printers` | GET /api/printers/ | search, status | "Show me my active printers" |
| `get_printer` | GET /api/printers/{id}/ | printer_id | "What mods are on my V2.4?" |
| `update_printer` | PATCH /api/printers/{id}/ | printer_id + fields | "Mark my Trident as Under Repair" |
| `add_mod` | POST /api/mods/ | printer_id, name, link, status | "Add the Klicky probe mod to my V2.4" |
| `update_mod` | PATCH /api/mods/{id}/ | mod_id, status | "Mark the Klicky mod as completed" |

### Tool Group 4: Project Management

Projects, BOM items, linked inventory, and shopping lists.

| Tool Name | Maps To | Parameters | Use Case |
|-----------|---------|-----------|----------|
| `list_projects` | GET /api/projects/ | search, status | "What projects are in progress?" |
| `get_project` | GET /api/projects/{id}/ | project_id | Full project detail with linked items |
| `create_project` | POST /api/projects/ | project_name, description, status, dates | "Create a new project for my ERCF build" |
| `add_bom_item` | POST /api/projectbomitems/ | project_id, description, quantity_needed, inventory_item_id | "Add 20 M3x8 SHCS to the ERCF BOM" |
| `get_shopping_list` | GET .../shopping_list/ | (none) | "What do I need to buy across all projects?" |
| `link_printer` | POST /api/projectprinters/ | project_id, printer_id | "Assign my V2.4 to the ERCF project" |

### Tool Group 5: Print Tracker

GitHub repo imports, file tracking, and print queue management.

| Tool Name | Maps To | Parameters | Use Case |
|-----------|---------|-----------|----------|
| `list_trackers` | GET /api/trackers/ | search | "Show my active print trackers" |
| `get_tracker` | GET /api/trackers/{id}/ | tracker_id | Full tracker with file list and progress |
| `create_tracker_from_github` | POST .../crawl-github/ | github_url, name | "Import the ERCF repo as a print tracker" |
| `update_file_status` | PATCH .../update_status/ | file_id, printed_quantity | "I printed 2 of the latch file" |
| `get_tracker_progress` | GET /api/trackers/{id}/ | tracker_id | "How far along am I on the ERCF tracker?" |

### Tool Group 6: Dashboard & Analytics

Overview data, alerts, and system status.

| Tool Name | Maps To | Parameters | Use Case |
|-----------|---------|-----------|----------|
| `get_dashboard` | GET /api/dashboard/ | (none) | "Give me a status update on my print lab" |
| `dismiss_alert` | POST /api/alerts/dismiss/ | alert_type, alert_id | "Dismiss the low stock alert for M3 screws" |
| `get_version` | GET /api/version/ | (none) | "What version of Print Vault am I running?" |

---

## Data Model Reference

Key models and their relationships, extracted from `inventory/models.py`. Understanding these relationships is essential for building MCP tools that correctly compose multi-entity operations.

### Core Entities

| Model | Purpose | Key Relationships |
|-------|---------|-------------------|
| Brand | Manufacturer/brand names | Used by InventoryItem, Material, Printer, FilamentSpool |
| PartType | Hardware categories (screws, bearings, etc.) | Used by InventoryItem |
| Location | Physical storage locations | Used by InventoryItem, FilamentSpool |
| Vendor | Purchase sources | Used by InventoryItem, Material |
| Material | Filament blueprint (generic PLA or specific Sunlu PLA+) | `is_generic` flag splits generics vs blueprints; FK to Brand and self (`base_material`); M2M to MaterialFeature |
| FilamentSpool | Physical spool instance | FK to Material (blueprint), Location, Printer, Project; supports Quick Add (null `filament_type`) |
| InventoryItem | Hardware part/component | FK to Brand, PartType, Location, Vendor; M2M to Project via ProjectInventory |
| Printer | 3D printer record | FK to Brand (manufacturer); has Mods, maintenance dates, filament assignments; M2M to Project via ProjectPrinters |
| Mod | Printer modification/upgrade | FK to Printer; has ModFiles |
| Project | Build/print project | M2M to InventoryItem, Printer; has BOM items, links, files, materials JSON |
| ProjectBOMItem | Bill of materials line item | FK to Project and InventoryItem (optional); status: linked/unlinked/needs_purchase; drives inventory reservation |
| Tracker | Print file tracker (GitHub import or manual) | Has TrackerFiles; tracks materials, progress, categories |
| TrackerFile | Individual file in a tracker | FK to Tracker; tracks quantity, printed_quantity, category, download status |

### Inventory Reservation Model

`ProjectBOMItem` drives an inventory reservation system. When a BOM item with status `linked` is created on an active project (Planning, In Progress, On Hold), the linked `InventoryItem.quantity` is decremented by `quantity_needed`. Deleting or completing the project restores the quantity. This means `InventoryItem.quantity` reflects **available** stock, not total stock. The MCP server should be aware of this when reporting inventory counts.

---

## Implementation Status

### Completed (v0.1.0)

**Phase 1 — Foundation + Read-Only Tools**
- Project scaffold: `pyproject.toml`, uv-managed, `mcp` + `httpx` + `python-dotenv` deps
- Async HTTP client (`client.py`): connection pooling, timeout control, error handling
- AI-friendly response formatters (`formatters.py`): concise text output for all entity types
- Read tools: `get_dashboard`, `get_version`, `list_printers`, `get_printer`, `search_inventory`, `get_inventory_item`, `get_low_stock`, `get_item_allocation`, `list_materials`, `get_material_spools`, `list_spools`, `list_projects`, `get_project`, `get_shopping_list`, `list_trackers`, `get_tracker`
- Reference data tools: `list_brands`, `list_locations`, `list_part_types`, `list_vendors`

**Phase 2 — Write Operations**
- Inventory writes: `add_inventory_item`, `update_inventory_item`
- Filament writes: `add_filament_spool`, `update_spool_weight`, `mark_spool_empty`, `open_spool`, `archive_spools`, `toggle_material_favorite`
- Printer writes: `update_printer`, `add_mod`, `update_mod`
- Project writes: `create_project`, `update_project`, `add_bom_item`, `link_printer_to_project`

**Phase 3 — Advanced Operations**
- Tracker: `create_tracker_from_github`, `update_file_status`
- Alerts: `dismiss_alert`

**Total: 38 tools registered and verified.**

### Remaining (Future)

**Phase 4 — Polish & Optimization**
- MCP resources for reference data (brands, locations, part types) to reduce tool call overhead
- MCP prompt templates for common workflows ("project setup wizard", "inventory audit")
- Composite tools that chain multiple API calls
- Docker packaging (Dockerfile + compose sidecar definition)
- SSE transport support for remote clients
- Enhanced error handling for Print Vault being offline or returning unexpected shapes

**Deliberately Excluded**
- `delete-all-data` — never exposed via MCP (destructive, no undo)
- `import-data` / `export-data` — too risky for AI-driven invocation
- File upload endpoints — deferred until multipart support is justified

---

## Configuration & Deployment

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PRINT_VAULT_URL` | Yes | (none) | Base URL of Print Vault instance (e.g., `http://192.168.1.100:8000`) |
| `PRINT_VAULT_TIMEOUT` | No | `30` | HTTP request timeout in seconds |

### Claude Desktop Integration

Add to `claude_desktop_config.json`:

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

### Claude Code Integration

```bash
claude mcp add print-vault \
  --command "uv --directory /path/to/PrintVaultMCP run print-vault-mcp" \
  --env PRINT_VAULT_URL=http://192.168.1.100:8000
```

---

## Reference Source Files

Extracts from the Print Vault repository that define the complete API contract are stored in `docs/reference/`. These were used during initial development and remain useful for adding new tools.

| File | Contains |
|------|----------|
| `docs/reference/urls.py` | Complete route map — all `router.register()` calls and standalone URL patterns |
| `docs/reference/views.py` | All ViewSets, custom `@action` endpoints, request/response shapes, query logic |
| `docs/reference/serializers.py` | All DRF serializers — exact JSON field names, validation, nested objects |

---

## Risks & Considerations

### No Authentication

Print Vault uses `AllowAny` on every endpoint. This is by design for a single-user self-hosted app, but it means anyone with network access to the instance can read and modify all data. The MCP server inherits this posture. If the Print Vault instance is exposed beyond the local network (e.g., via Tailscale), ensure that only trusted devices are on the Tailnet.

### Destructive Operations

The API includes endpoints for deleting all data (`/api/delete-all-data/`) and importing full backups (`/api/import-data/`). These should be deliberately excluded from MCP tool registration or gated behind explicit confirmation flows. The MCP server should **never** expose `delete-all-data` as a tool.

### File Upload Limitations

Some endpoints accept file uploads (photos, project files, mod files, tracker uploads). MCP tools that involve file uploads will need to handle multipart form encoding and may require the user to provide a file path. This adds complexity and should be deferred to Phase 3 or later.

### API Stability

Print Vault is under active development (v1.1.0, 149 commits, solo developer with AI assistance). The API surface may change between releases. The MCP server should handle unexpected response shapes gracefully and log warnings rather than crashing. Pinning to a known-good Print Vault version in the README is recommended.

### Large Response Payloads

Some endpoints (particularly the full tracker detail and dashboard) can return large JSON payloads. MCP tools should consider summarizing or extracting relevant fields rather than passing the raw response back to the AI, to avoid consuming excessive context window tokens.

