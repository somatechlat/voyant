"""Structured JSON logging setup."""
from __future__ import annotations
import json
import logging
import sys
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore
        base: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for attr in ("correlation_id", "tenant"):
            if hasattr(record, attr):
                base[attr] = getattr(record, attr)
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)

def configure_json_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]
