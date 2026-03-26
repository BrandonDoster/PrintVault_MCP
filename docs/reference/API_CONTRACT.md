# Print Vault API Contract Reference

This MCP server is built against the [Print Vault](https://github.com/shaxs/print-vault) REST API (v1.1.0).

## Source Files

The following files in the Print Vault repository define the complete API contract. Consult these when adding or modifying MCP tools:

| File | Contains |
|------|----------|
| [`backend/urls.py`](https://github.com/shaxs/print-vault/blob/main/backend/urls.py) | Complete route map — all `router.register()` calls and standalone URL patterns |
| [`inventory/views.py`](https://github.com/shaxs/print-vault/blob/main/inventory/views.py) | All ViewSets, custom `@action` endpoints, request/response shapes, query logic |
| [`inventory/serializers.py`](https://github.com/shaxs/print-vault/blob/main/inventory/serializers.py) | All DRF serializers — exact JSON field names, validation, nested objects |
| [`inventory/models.py`](https://github.com/shaxs/print-vault/blob/main/inventory/models.py) | All Django models — field definitions, choices, relationships, constraints |
| [`inventory/filters.py`](https://github.com/shaxs/print-vault/blob/main/inventory/filters.py) | FilterSet definitions for query parameter filtering |

## Key Patterns

- **Nested FK creation**: POST/PATCH endpoints accept `{"name": "..."}` for brands, locations, part types, and vendors. The server auto-creates via `get_or_create`.
- **Filament dual mode**: `POST /api/filament-spools/` supports both blueprint-based (requires `filament_type_id`) and quick-add (requires `is_quick_add: true` with `standalone_*` fields).
- **Material hierarchy**: Generic materials (`is_generic: true`) are base types. Blueprints (`is_generic: false`) reference a generic via `base_material_id`. Spools link to blueprints.
- **Inventory reservation**: BOM items with status `linked` on active projects decrement `InventoryItem.quantity`. The quantity field reflects *available* stock, not total.
- **AllowAny auth**: Every endpoint uses `AllowAny` permissions — no tokens needed.

## Endpoint Quick Reference

See the full endpoint tables in [design.md](../design.md) under "Print Vault API Surface".
