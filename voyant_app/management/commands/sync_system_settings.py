from __future__ import annotations

import json
from typing import Any, get_origin

from django.core.management.base import BaseCommand

from voyant.core.config import Settings
from voyant_app.models import SystemSetting


def _value_type_for_annotation(annotation: Any) -> str:
    origin = get_origin(annotation)
    target = origin or annotation
    if target is bool:
        return SystemSetting.ValueType.BOOLEAN
    if target is int:
        return SystemSetting.ValueType.INTEGER
    if target is float:
        return SystemSetting.ValueType.FLOAT
    if target in (dict, list):
        return SystemSetting.ValueType.JSON
    return SystemSetting.ValueType.STRING


def _serialize_value(value: Any, value_type: str) -> str:
    if value is None:
        return ""
    if value_type == SystemSetting.ValueType.JSON:
        return json.dumps(value)
    return str(value)


class Command(BaseCommand):
    help = "Sync Settings schema into voyant_app_systemsetting for DB-managed configuration."

    def handle(self, *args: Any, **options: Any) -> None:
        snapshot = Settings()
        created = 0
        updated = 0

        for key, model_field in snapshot.model_fields.items():
            if key.startswith("_"):
                continue
            value_type = _value_type_for_annotation(model_field.annotation)
            is_runtime = key in Settings.RUNTIME_ENV_KEYS
            is_secret = key in Settings.SECRET_KEYS
            managed_in_db = not is_runtime and not is_secret
            value = ""
            if managed_in_db:
                value = _serialize_value(getattr(snapshot, key), value_type)

            obj, was_created = SystemSetting.objects.update_or_create(
                key=key,
                defaults={
                    "value": value,
                    "value_type": value_type,
                    "description": model_field.description or "",
                    "is_secret": is_secret,
                    "is_runtime": is_runtime,
                    "managed_in_db": managed_in_db,
                    "updated_by": "sync_system_settings",
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"System settings synchronized: created={created}, updated={updated}"
            )
        )

