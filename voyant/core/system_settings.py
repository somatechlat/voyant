"""ORM-backed managed settings overlay for application configuration."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.apps import apps
from django.db import DatabaseError, OperationalError

logger = logging.getLogger(__name__)


def _coerce_value(raw_value: str, value_type: str) -> Any:
    if value_type == "integer":
        return int(raw_value)
    if value_type == "float":
        return float(raw_value)
    if value_type == "boolean":
        return raw_value.strip().lower() in {"1", "true", "yes", "on"}
    if value_type == "json":
        return json.loads(raw_value) if raw_value.strip() else {}
    return raw_value


def get_db_settings_overrides(
    settings: Any,
    runtime_keys: set[str],
    secret_keys: set[str],
) -> dict[str, Any]:
    """Return config overrides loaded from the SystemSetting ORM table."""
    if not apps.ready:
        return {}

    try:
        SystemSetting = apps.get_model("voyant_app", "SystemSetting")
    except LookupError:
        return {}

    try:
        managed = SystemSetting.objects.filter(managed_in_db=True, is_secret=False)
    except (OperationalError, DatabaseError):
        return {}

    model_fields = set(type(settings).model_fields.keys())
    overrides: dict[str, Any] = {}

    for item in managed.iterator():
        key = str(item.key).strip()
        if not key or key not in model_fields:
            continue
        if key in runtime_keys or key in secret_keys:
            continue
        try:
            overrides[key] = _coerce_value(str(item.value), item.value_type)
        except Exception as exc:
            logger.warning(
                "Ignoring invalid DB setting value for key '%s': %s",
                key,
                exc,
            )
    return overrides
