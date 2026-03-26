"""Print Vault MCP Server — AI-powered access to your Print Vault instance."""

import os

from .server import mcp


def main():
    """Entry point for the MCP server."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.settings.host = os.getenv("MCP_HOST", "0.0.0.0")
        mcp.settings.port = int(os.getenv("MCP_PORT", "8080"))
        mcp.settings.transport_security.enable_dns_rebinding_protection = False
        mcp.run(transport="sse")
    else:
        mcp.run()
