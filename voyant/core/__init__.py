"""
Voyant core package.

Important: keep this module side-effect free.

Temporal validates workflows inside a sandbox; importing this package during workflow
validation must not read `.env`, touch the filesystem, or initialize network clients.
"""

from .config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
