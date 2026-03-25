"""Print Vault MCP Server — AI-powered access to your Print Vault instance."""

from .server import mcp


def main():
    """Entry point for the MCP server."""
    mcp.run()
