"""
Voyant Billing Package.

This package provides the public interface for the Voyant billing system,
primarily exposing the `LagoClient` and convenience functions for interacting
with the Lago usage-based billing API.
"""

from .lago import LagoClient, emit_usage, get_lago_client

__all__ = ["LagoClient", "get_lago_client", "emit_usage"]
