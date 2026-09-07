"""
Template SDK — JSON schema + builder for scraper templates.

Every template is agent-accessible via MCP tools. Agents can:
  - List templates by category
  - Get template details
  - Create templates programmatically
  - Run templates with parameters
  - Generate templates from URL (AI auto-detect)

Template Format v1.0:
{
  "id": "amazon-product-search",
  "name": "Amazon Product Search",
  "version": "1.0.0",
  "category": "ecommerce",
  "site_pattern": "amazon.com",
  "description": "Search Amazon products by keyword",
  "engine": "playwright",
  "parameters": [...],
  "workflow": [...],
  "output_schema": {...},
  "pagination": {...},
  "anti_bot": {...},
}
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Template Schema ─────────────────────────────────────────────────────────

TEMPLATE_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "category", "workflow"],
    "properties": {
        "id": {"type": "string", "description": "Unique template identifier (kebab-case)"},
        "name": {"type": "string", "description": "Human-readable template name"},
        "version": {"type": "string", "default": "1.0.0"},
        "category": {
            "type": "string",
            "enum": [
                "ecommerce", "social", "maps", "news", "finance", "jobs",
                "realestate", "travel", "education", "developer", "leadgen",
                "directory", "search", "universal",
            ],
        },
        "site_pattern": {"type": "string", "description": "Domain pattern (e.g. amazon.com)"},
        "description": {"type": "string"},
        "engine": {"type": "string", "enum": ["playwright", "httpx", "scrapy"], "default": "playwright"},
        "language": {"type": "string", "default": "en"},
        "parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type"],
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["string", "number", "boolean", "url"]},
                    "required": {"type": "boolean", "default": False},
                    "description": {"type": "string"},
                    "default": {},
                },
            },
        },
        "workflow": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "navigate", "click", "scroll", "wait", "extract",
                            "enter_text", "hover", "loop", "condition", "back",
                            "new_tab", "close_popup", "screenshot", "download",
                        ],
                    },
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "selectors": {"type": "object"},
                    "text": {"type": "string"},
                    "times": {"type": "integer"},
                    "wait_ms": {"type": "integer"},
                    "direction": {"type": "string", "enum": ["up", "down"]},
                    "amount": {"type": "integer"},
                    "condition": {"type": "object"},
                    "variable": {"type": "string"},
                },
            },
        },
        "output_schema": {
            "type": "object",
            "description": "Map of field_name → {type, description}",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["string", "number", "url", "image", "html", "date"]},
                    "description": {"type": "string"},
                    "selector": {"type": "string"},
                },
            },
        },
        "pagination": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["next_button", "page_numbers", "load_more", "infinite_scroll", "url_pattern"]},
                "selector": {"type": "string"},
                "url_pattern": {"type": "string"},
                "max_pages": {"type": "integer", "default": 10},
                "scroll_times": {"type": "integer", "default": 5},
            },
        },
        "anti_bot": {
            "type": "object",
            "properties": {
                "rotate_ua": {"type": "boolean", "default": False},
                "block_resources": {"type": "boolean", "default": True},
                "evasion_mode": {"type": "boolean", "default": False},
                "stealth": {"type": "boolean", "default": False},
                "proxy": {"type": "string"},
            },
        },
        "schedule": {
            "type": "object",
            "properties": {
                "frequency": {"type": "string", "enum": ["once", "hourly", "daily", "weekly", "monthly"]},
                "cron": {"type": "string"},
            },
        },
        "export": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["json", "csv", "xlsx", "parquet", "database"]},
                "destination": {"type": "string"},
            },
        },
        "success_rate": {"type": "number", "minimum": 0, "maximum": 1},
        "last_verified": {"type": "string", "format": "date"},
        "author": {"type": "string", "default": "voyant"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
}


# ── Builder ─────────────────────────────────────────────────────────────────


class TemplateBuilder:
    """
    Fluent builder for scraper templates.

    Usage:
        template = (
            TemplateBuilder("Amazon Product Search")
            .category("ecommerce")
            .site("amazon.com")
            .description("Search Amazon products by keyword")
            .engine("playwright")
            .param("search_query", type="string", required=True, description="Search term")
            .navigate("https://amazon.com/s?k={{search_query}}", wait_until="domcontentloaded")
            .scroll(times=3, wait_ms=1000)
            .extract(title="h2 a span", price=".a-price .a-offscreen", rating=".a-icon-alt")
            .paginate(type="next_button", selector=".s-pagination-next", max_pages=10)
            .anti_bot(rotate_ua=True, block_resources=True)
            .output_field("title", type="string", description="Product title")
            .output_field("price", type="string", description="Product price")
            .tag("product")
            .tag("search")
            .build()
        )
    """

    def __init__(self, name: str):
        self._data: dict[str, Any] = {
            "id": self._to_id(name),
            "name": name,
            "version": "1.0.0",
            "category": "universal",
            "engine": "playwright",
            "parameters": [],
            "workflow": [],
            "output_schema": {},
            "anti_bot": {"block_resources": True},
            "tags": [],
        }

    def _to_id(self, name: str) -> str:
        return name.lower().replace(" ", "-").replace("_", "-")

    def category(self, cat: str) -> TemplateBuilder:
        self._data["category"] = cat
        return self

    def site(self, pattern: str) -> TemplateBuilder:
        self._data["site_pattern"] = pattern
        return self

    def description(self, desc: str) -> TemplateBuilder:
        self._data["description"] = desc
        return self

    def engine(self, engine: str) -> TemplateBuilder:
        self._data["engine"] = engine
        return self

    def language(self, lang: str) -> TemplateBuilder:
        self._data["language"] = lang
        return self

    def version(self, ver: str) -> TemplateBuilder:
        self._data["version"] = ver
        return self

    def author(self, author: str) -> TemplateBuilder:
        self._data["author"] = author
        return self

    # ── Parameters ──────────────────────────────────────────────────────

    def param(
        self,
        name: str,
        type: str = "string",
        required: bool = False,
        description: str = "",
        default: Any = None,
    ) -> TemplateBuilder:
        p: dict[str, Any] = {"name": name, "type": type, "required": required}
        if description:
            p["description"] = description
        if default is not None:
            p["default"] = default
        self._data["parameters"].append(p)
        return self

    # ── Workflow Steps ──────────────────────────────────────────────────

    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> TemplateBuilder:
        step: dict[str, Any] = {"action": "navigate", "url": url}
        if wait_until != "domcontentloaded":
            step["wait_until"] = wait_until
        self._data["workflow"].append(step)
        return self

    def click(self, selector: str) -> TemplateBuilder:
        self._data["workflow"].append({"action": "click", "selector": selector})
        return self

    def scroll(self, direction: str = "down", times: int = 3, wait_ms: int = 1000) -> TemplateBuilder:
        self._data["workflow"].append({
            "action": "scroll",
            "direction": direction,
            "times": times,
            "wait_ms": wait_ms,
        })
        return self

    def wait(self, ms: int) -> TemplateBuilder:
        self._data["workflow"].append({"action": "wait", "wait_ms": ms})
        return self

    def extract(self, **selectors: str) -> TemplateBuilder:
        self._data["workflow"].append({"action": "extract", "selectors": selectors})
        return self

    def enter_text(self, selector: str, text: str) -> TemplateBuilder:
        self._data["workflow"].append({"action": "enter_text", "selector": selector, "text": text})
        return self

    def hover(self, selector: str) -> TemplateBuilder:
        self._data["workflow"].append({"action": "hover", "selector": selector})
        return self

    def back(self) -> TemplateBuilder:
        self._data["workflow"].append({"action": "back"})
        return self

    def new_tab(self) -> TemplateBuilder:
        self._data["workflow"].append({"action": "new_tab"})
        return self

    def close_popup(self, selector: str = "") -> TemplateBuilder:
        step: dict[str, Any] = {"action": "close_popup"}
        if selector:
            step["selector"] = selector
        self._data["workflow"].append(step)
        return self

    def screenshot(self) -> TemplateBuilder:
        self._data["workflow"].append({"action": "screenshot"})
        return self

    def loop(self, selector: str, variable: str = "item") -> TemplateBuilder:
        self._data["workflow"].append({"action": "loop", "selector": selector, "variable": variable})
        return self

    def condition(self, field: str, operator: str, value: str) -> TemplateBuilder:
        self._data["workflow"].append({
            "action": "condition",
            "condition": {"field": field, "operator": operator, "value": value},
        })
        return self

    def step(self, action: str, **kwargs: Any) -> TemplateBuilder:
        """Add an arbitrary workflow step."""
        step: dict[str, Any] = {"action": action}
        step.update(kwargs)
        self._data["workflow"].append(step)
        return self

    # ── Output ──────────────────────────────────────────────────────────

    def output_field(self, name: str, type: str = "string", description: str = "", selector: str = "") -> TemplateBuilder:
        field_def: dict[str, Any] = {"type": type}
        if description:
            field_def["description"] = description
        if selector:
            field_def["selector"] = selector
        self._data["output_schema"][name] = field_def
        return self

    # ── Pagination ──────────────────────────────────────────────────────

    def paginate(
        self,
        type: str = "next_button",
        selector: str = "",
        url_pattern: str = "",
        max_pages: int = 10,
        scroll_times: int = 5,
    ) -> TemplateBuilder:
        pagination: dict[str, Any] = {"type": type, "max_pages": max_pages}
        if selector:
            pagination["selector"] = selector
        if url_pattern:
            pagination["url_pattern"] = url_pattern
        if type == "infinite_scroll":
            pagination["scroll_times"] = scroll_times
        self._data["pagination"] = pagination
        return self

    # ── Anti-bot ────────────────────────────────────────────────────────

    def anti_bot(
        self,
        rotate_ua: bool = False,
        block_resources: bool = True,
        evasion_mode: bool = False,
        stealth: bool = False,
        proxy: str = "",
    ) -> TemplateBuilder:
        self._data["anti_bot"] = {
            "rotate_ua": rotate_ua,
            "block_resources": block_resources,
            "evasion_mode": evasion_mode,
            "stealth": stealth,
        }
        if proxy:
            self._data["anti_bot"]["proxy"] = proxy
        return self

    # ── Schedule / Export ───────────────────────────────────────────────

    def schedule(self, frequency: str = "daily", cron: str = "") -> TemplateBuilder:
        sched: dict[str, Any] = {"frequency": frequency}
        if cron:
            sched["cron"] = cron
        self._data["schedule"] = sched
        return self

    def export(self, format: str = "json", destination: str = "") -> TemplateBuilder:
        exp: dict[str, Any] = {"format": format}
        if destination:
            exp["destination"] = destination
        self._data["export"] = exp
        return self

    # ── Tags ────────────────────────────────────────────────────────────

    def tag(self, tag: str) -> TemplateBuilder:
        if tag not in self._data["tags"]:
            self._data["tags"].append(tag)
        return self

    # ── Build ───────────────────────────────────────────────────────────

    def build(self) -> dict[str, Any]:
        """Build and validate the template."""
        if not self._data.get("workflow"):
            raise ValueError("Template must have at least one workflow step")
        if not self._data.get("category"):
            raise ValueError("Template must have a category")

        # Generate content hash
        content = json.dumps(self._data, sort_keys=True)
        self._data["content_hash"] = hashlib.sha256(content.encode()).hexdigest()[:16]

        return self._data

    def build_json(self, indent: int = 2) -> str:
        """Build and return as JSON string."""
        return json.dumps(self.build(), indent=indent)

    def save(self, path: str) -> None:
        """Save template to a JSON file."""
        with open(path, "w") as f:
            f.write(self.build_json())
        logger.info("Template saved to %s", path)


# ── Template Loader ─────────────────────────────────────────────────────────


def load_template(path: str) -> dict[str, Any]:
    """Load a template from a JSON file."""
    with open(path) as f:
        return json.load(f)


def load_templates_from_dir(directory: str) -> list[dict[str, Any]]:
    """Load all templates from a directory of JSON files."""
    import os
    templates = []
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".json"):
            try:
                templates.append(load_template(os.path.join(directory, filename)))
            except Exception as exc:
                logger.warning("Failed to load template %s: %s", filename, exc)
    return templates


def template_to_mcp_params(template: dict[str, Any]) -> dict[str, Any]:
    """Convert a template to MCP tool parameters format."""
    params: dict[str, Any] = {}
    for p in template.get("parameters", []):
        params[p["name"]] = {
            "type": p.get("type", "string"),
            "description": p.get("description", ""),
            "required": p.get("required", False),
        }
        if "default" in p:
            params[p["name"]]["default"] = p["default"]
    return params


def validate_template(template: dict[str, Any]) -> list[str]:
    """Validate a template against the schema. Returns list of errors."""
    errors = []

    if not template.get("id"):
        errors.append("Template must have an 'id'")
    if not template.get("name"):
        errors.append("Template must have a 'name'")
    if not template.get("category"):
        errors.append("Template must have a 'category'")
    if not template.get("workflow"):
        errors.append("Template must have at least one workflow step")

    valid_categories = [
        "ecommerce", "social", "maps", "news", "finance", "jobs",
        "realestate", "travel", "education", "developer", "leadgen",
        "directory", "search", "universal",
    ]
    if template.get("category") and template["category"] not in valid_categories:
        errors.append(f"Invalid category: {template['category']}. Must be one of {valid_categories}")

    valid_actions = [
        "navigate", "click", "scroll", "wait", "extract", "enter_text",
        "hover", "loop", "condition", "back", "new_tab", "close_popup",
        "screenshot", "download",
    ]
    for i, step in enumerate(template.get("workflow", [])):
        if not step.get("action"):
            errors.append(f"Workflow step {i} must have an 'action'")
        elif step["action"] not in valid_actions:
            errors.append(f"Workflow step {i} has invalid action: {step['action']}")

    return errors
