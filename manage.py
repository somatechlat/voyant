#!/usr/bin/env python3
"""Django management utility for Voyant."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed or not configured."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
