"""Voyant Temporal Worker - Main Entry Point.

Usage:
    python -m voyant.worker.worker_main
"""

import asyncio

from .worker_main import main

if __name__ == "__main__":
    asyncio.run(main())
