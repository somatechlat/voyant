"""
Voyant MCP (Model Context Protocol) Server Package.

This package provides the public interface for the Voyant MCP server,
allowing external AI agents to interact with Voyant's data capabilities
via the Model Context Protocol.
"""

from .server import VoyantMCPServer, main

__all__ = ["VoyantMCPServer", "main"]
