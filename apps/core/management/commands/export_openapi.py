"""
export_openapi — Regenerate docs/api/openapi.json from the live NinjaAPI instance.

Run: python manage.py export_openapi [--output PATH] [--check]
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Export the NinjaAPI OpenAPI schema to docs/api/openapi.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=None,
            help="Output file path (default: docs/api/openapi.json)",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Do not write; exit 1 if the file on disk is out of date",
        )

    def handle(self, *args, **options):
        from apps.core.api import api

        output = (
            Path(options["output"])
            if options["output"]
            else Path(settings.BASE_DIR) / "docs" / "api" / "openapi.json"
        )
        schema = api.get_openapi_schema()
        rendered = json.dumps(schema, indent=2, sort_keys=True) + "\n"
        path_count = len(schema.get("paths", {}))

        if options["check"]:
            current = output.read_text(encoding="utf-8") if output.exists() else None
            if current != rendered:
                raise CommandError(
                    f"{output} is out of date (live schema has {path_count} paths); "
                    "run 'python manage.py export_openapi'"
                )
            self.stdout.write(
                self.style.SUCCESS(f"{output} is up to date ({path_count} paths)")
            )
            return

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {output} — {path_count} paths from live NinjaAPI schema"
            )
        )
