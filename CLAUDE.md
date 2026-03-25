# CLAUDE.md — PrintVaultMCP

## What is this project?

An MCP server that wraps the Print Vault REST API, enabling AI assistants to manage 3D printing inventory, filament, printers, projects, and print trackers.

## Tech stack

- **Python 3.11+** managed with **uv**
- **mcp** (official Python MCP SDK) via `FastMCP`
- **httpx** (async HTTP client)
- **stdio** transport (standard MCP pattern)

## Key commands

```bash
uv sync                    # Install dependencies
uv run print-vault-mcp     # Run the server (needs PRINT_VAULT_URL env)
```

## Project layout

```
src/print_vault_mcp/
  __init__.py      # Entry point — exports main() which calls mcp.run()
  __main__.py      # python -m support
  client.py        # PrintVaultClient — async httpx wrapper (GET/POST/PATCH/DELETE)
  formatters.py    # Functions that turn API JSON into concise text for AI consumption
  server.py        # FastMCP server instance + all 38 tool definitions
```

## Architecture patterns

- **Stateless passthrough**: Every tool maps to one Print Vault API call. No local state or DB.
- **Tool functions**: Each `@mcp.tool()` function takes explicit typed parameters, calls `_get_client().verb()`, formats the response via `formatters.py`, and returns a string.
- **Error handling**: All tools catch exceptions and return `_err(e)` — a human-readable error string. Never raise from a tool.
- **Formatters**: Each entity type has a `format_*` function. Keep output concise — the AI's context window is the bottleneck.
- **Nested FK creation**: Print Vault's API accepts `{"name": "..."}` for brands, locations, part types, and vendors — the server auto-creates them via `get_or_create`. MCP tools pass these as plain strings.

## Important conventions

- All tools return `str`, not structured data. The formatter layer handles summarization.
- Destructive endpoints (`delete-all-data`, `import-data`) are deliberately never exposed.
- `update_*` tools use explicit optional parameters (not `**kwargs`) so FastMCP generates proper JSON schemas.
- The `_get_client()` singleton reads `PRINT_VAULT_URL` from env on first call.

## Reference files

Print Vault API contract source extracts live in `docs/reference/` (urls.py, views.py, serializers.py). Consult these when adding new tools.
