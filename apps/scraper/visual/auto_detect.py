"""
Auto-Detect Engine — finds lists, tables, pagination, and forms on web pages.

Inspired by Octoparse's ML auto-detect but uses deterministic DOM analysis
rather than ML — faster, more reliable, zero dependencies.

Detects:
  - Product/article/item lists (repeating DOM patterns)
  - Data tables (thead/tbody structures)
  - Pagination (next/prev buttons, page numbers)
  - Search/input forms
  - Infinite scroll containers
  - Load-more buttons
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from lxml import html as lxml_html

logger = logging.getLogger(__name__)


@dataclass
class DetectedList:
    """A detected repeating list of items."""

    name: str
    selector: str
    item_selector: str
    item_count: int
    fields: list[
        dict[str, str]
    ]  # [{"name": "title", "selector": "h3", "type": "text"}]
    sample_data: list[dict[str, str]]  # First3 items


@dataclass
class DetectedTable:
    """A detected data table."""

    name: str
    selector: str
    headers: list[str]
    row_count: int
    sample_rows: list[list[str]]


@dataclass
class DetectedPagination:
    """A detected pagination mechanism."""

    type: str  # "next_button", "page_numbers", "load_more", "infinite_scroll"
    selector: str
    current_page: str | None = None
    total_pages: str | None = None


@dataclass
class DetectedForm:
    """A detected search/input form."""

    selector: str
    inputs: list[
        dict[str, str]
    ]  # [{"name": "search", "selector": "input[name=q]", "type": "text"}]
    submit_selector: str


@dataclass
class DetectResult:
    """Complete auto-detect result."""

    lists: list[DetectedList] = field(default_factory=list)
    tables: list[DetectedTable] = field(default_factory=list)
    pagination: list[DetectedPagination] = field(default_factory=list)
    forms: list[DetectedForm] = field(default_factory=list)
    has_infinite_scroll: bool = False
    has_load_more: bool = False
    load_more_selector: str = ""


class AutoDetectEngine:
    """Analyzes HTML to find extractable data patterns."""

    def detect(self, html: str, url: str = "") -> dict[str, Any]:
        """Run full auto-detect analysis on HTML content."""
        try:
            tree = lxml_html.fromstring(html)
        except Exception:
            return {"lists": [], "tables": [], "pagination": [], "forms": []}

        lists = self._detect_lists(tree)
        tables = self._detect_tables(tree)
        pagination = self._detect_pagination(tree)
        forms = self._detect_forms(tree)
        load_more = self._detect_load_more(tree)

        return {
            "lists": [
                {
                    "name": lst.name,
                    "selector": lst.selector,
                    "item_selector": lst.item_selector,
                    "item_count": lst.item_count,
                    "fields": lst.fields,
                    "sample_data": lst.sample_data,
                }
                for lst in lists
            ],
            "tables": [
                {
                    "name": t.name,
                    "selector": t.selector,
                    "headers": t.headers,
                    "row_count": t.row_count,
                    "sample_rows": t.sample_rows,
                }
                for t in tables
            ],
            "pagination": [
                {
                    "type": p.type,
                    "selector": p.selector,
                    "current_page": p.current_page,
                    "total_pages": p.total_pages,
                }
                for p in pagination
            ],
            "forms": [
                {
                    "selector": f.selector,
                    "inputs": f.inputs,
                    "submit_selector": f.submit_selector,
                }
                for f in forms
            ],
            "load_more": load_more,
        }

    def _detect_lists(self, tree) -> list[DetectedList]:
        """Find repeating DOM patterns that represent item lists."""
        lists: list[DetectedList] = []

        # Strategy: find parent elements with multiple children sharing the same tag+class
        candidates = tree.xpath("//*[count(*) > 3]")
        seen_selectors: set[str] = set()

        for parent in candidates[:200]:  # Limit for performance
            children = list(parent)
            if len(children) < 3:
                continue

            # Group children by tag+class
            groups: dict[str, list] = {}
            for child in children:
                tag = child.tag
                classes = child.get("class", "")
                key = f"{tag}.{classes}"
                if key not in groups:
                    groups[key] = []
                groups[key].append(child)

            # Find groups with 3+ similar children
            for key, items in groups.items():
                if len(items) < 3:
                    continue

                selector = self._build_selector(parent)
                item_selector = f"{selector} > {key.split('.')[0]}"
                if "." in key:
                    item_selector = f"{selector} > {key}"

                if item_selector in seen_selectors:
                    continue
                seen_selectors.add(item_selector)

                # Extract fields from first item
                first_item = items[0]
                fields = self._extract_fields(first_item)

                # Sample data
                sample = []
                for item in items[:3]:
                    row: dict[str, str] = {}
                    for f in fields:
                        el = item.xpath(f["selector"])
                        row[f["name"]] = (
                            el[0].text_content().strip()[:200] if el else ""
                        )
                    sample.append(row)

                # Determine name from context
                name = self._infer_list_name(parent, items[0])

                lists.append(
                    DetectedList(
                        name=name,
                        selector=selector,
                        item_selector=item_selector,
                        item_count=len(items),
                        fields=fields,
                        sample_data=sample,
                    )
                )

                if len(lists) >= 5:
                    break

        # Sort by item count (more items = more likely to be the main list)
        lists.sort(key=lambda lst: lst.item_count, reverse=True)
        return lists[:5]

    def _detect_tables(self, tree) -> list[DetectedTable]:
        """Find HTML tables with structured data."""
        tables: list[DetectedTable] = []

        for table in tree.xpath("//table"):
            # Get headers
            headers = table.xpath(".//thead//th//text()|.//thead//td//text()")
            headers = [h.strip() for h in headers if h.strip()]

            if not headers:
                # Try first row as headers
                first_row = table.xpath(".//tr[1]//td//text()|.//tr[1]//th//text()")
                headers = [h.strip() for h in first_row if h.strip()]

            if not headers:
                continue

            # Get rows
            rows = table.xpath(".//tbody//tr|.//tr[position()>1]")
            sample_rows = []
            for row in rows[:3]:
                cells = row.xpath(".//td//text()|.//th//text()")
                sample_rows.append([c.strip()[:100] for c in cells if c.strip()])

            if len(rows) < 2:
                continue

            selector = self._build_selector(table)
            name = self._infer_table_name(table)

            tables.append(
                DetectedTable(
                    name=name,
                    selector=selector,
                    headers=headers[:20],
                    row_count=len(rows),
                    sample_rows=sample_rows,
                )
            )

        return tables[:3]

    def _detect_pagination(self, tree) -> list[DetectedPagination]:
        """Find pagination controls."""
        pagination: list[DetectedPagination] = []

        # Next button patterns
        next_patterns = [
            "//a[contains(@class, 'next')]",
            "//a[contains(@class, 'Next')]",
            "//a[contains(text(), 'Next')]",
            "//a[contains(text(), 'next')]",
            "//button[contains(text(), 'Next')]",
            "//button[contains(@class, 'next')]",
            "//a[contains(@aria-label, 'Next')]",
            "//a[contains(@aria-label, 'next')]",
            "//li[contains(@class, 'next')]//a",
            "//a[contains(@rel, 'next')]",
        ]

        for pattern in next_patterns:
            elements = tree.xpath(pattern)
            if elements:
                el = elements[0]
                selector = self._build_selector(el)
                pagination.append(
                    DetectedPagination(
                        type="next_button",
                        selector=selector,
                    )
                )
                break

        # Page number patterns
        page_links = tree.xpath("//a[contains(@class, 'page')]")
        if len(page_links) >= 3:
            pagination.append(
                DetectedPagination(
                    type="page_numbers",
                    selector=self._build_selector(page_links[0].getparent()),
                    total_pages=str(len(page_links)),
                )
            )

        # Load more button
        load_more_patterns = [
            "//button[contains(text(), 'Load More')]",
            "//button[contains(text(), 'load more')]",
            "//button[contains(text(), 'Show More')]",
            "//a[contains(text(), 'Load More')]",
            "//a[contains(text(), 'Show More')]",
            "//button[contains(@class, 'load-more')]",
            "//button[contains(@class, 'show-more')]",
        ]

        for pattern in load_more_patterns:
            elements = tree.xpath(pattern)
            if elements:
                pagination.append(
                    DetectedPagination(
                        type="load_more",
                        selector=self._build_selector(elements[0]),
                    )
                )
                break

        return pagination

    def _detect_forms(self, tree) -> list[DetectedForm]:
        """Find search/input forms."""
        forms: list[DetectedForm] = []

        for form in tree.xpath("//form"):
            inputs = []
            for inp in form.xpath(
                ".//input[@type='text']|.//input[@type='search']|.//input[@type='email']|.//input[not(@type)]"
            ):
                name = inp.get("name", inp.get("placeholder", inp.get("id", "input")))
                selector = self._build_selector(inp)
                inputs.append(
                    {
                        "name": name,
                        "selector": selector,
                        "type": inp.get("type", "text"),
                    }
                )

            if not inputs:
                continue

            submit = form.xpath(
                ".//button[@type='submit']|.//input[@type='submit']|.//button"
            )
            submit_selector = self._build_selector(submit[0]) if submit else ""

            forms.append(
                DetectedForm(
                    selector=self._build_selector(form),
                    inputs=inputs,
                    submit_selector=submit_selector,
                )
            )

        return forms[:3]

    def _detect_load_more(self, tree) -> dict[str, Any]:
        """Detect load-more buttons and infinite scroll indicators."""
        # Load more button
        patterns = [
            "//button[contains(text(), 'Load More')]",
            "//button[contains(text(), 'Show More')]",
            "//button[contains(@class, 'load-more')]",
            "//a[contains(text(), 'Load More')]",
        ]
        for pattern in patterns:
            elements = tree.xpath(pattern)
            if elements:
                return {
                    "has_load_more": True,
                    "selector": self._build_selector(elements[0]),
                    "has_infinite_scroll": False,
                }

        # Infinite scroll indicators
        scroll_indicators = tree.xpath(
            "//*[contains(@class, 'infinite-scroll')]"
            "|//*[contains(@class, 'lazy-load')]"
            "|//*[contains(@data-infinite-scroll, 'true')]"
        )
        if scroll_indicators:
            return {
                "has_load_more": False,
                "selector": "",
                "has_infinite_scroll": True,
            }

        return {"has_load_more": False, "selector": "", "has_infinite_scroll": False}

    # ── Helper methods ──────────────────────────────────────────────────────

    def _build_selector(self, element) -> str:
        """Build a CSS selector for an element."""
        if element is None:
            return ""

        tag = element.tag
        el_id = element.get("id", "")
        classes = element.get("class", "")

        if el_id:
            return f"#{el_id}"

        if classes:
            class_list = classes.strip().split()[:3]
            return f"{tag}.{'.'.join(class_list)}"

        return tag

    def _extract_fields(self, element) -> list[dict[str, str]]:
        """Extract field definitions from a list item element."""
        fields: list[dict[str, str]] = []

        # Text elements
        for tag in [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "span",
            "a",
            "div",
            "td",
            "th",
        ]:
            els = element.xpath(f".//{tag}")
            for el in els[:5]:
                text = el.text_content().strip()
                if text and len(text) > 2:
                    name = tag
                    if tag.startswith("h"):
                        name = "title"
                    elif tag == "p":
                        name = "description"
                    elif tag == "a":
                        name = "link"
                    elif tag == "span":
                        name = "text"

                    # Avoid duplicates
                    if not any(f["name"] == name for f in fields):
                        fields.append(
                            {
                                "name": name,
                                "selector": self._build_selector(el),
                                "type": "text" if tag != "a" else "link",
                            }
                        )

        # Images
        imgs = element.xpath(".//img")
        if imgs:
            fields.append(
                {
                    "name": "image",
                    "selector": self._build_selector(imgs[0]),
                    "type": "image",
                }
            )

        # Prices (common pattern)
        price_els = element.xpath(
            ".//*[contains(@class, 'price')]|.//*[contains(@class, 'Price')]"
        )
        if price_els:
            fields.append(
                {
                    "name": "price",
                    "selector": self._build_selector(price_els[0]),
                    "type": "text",
                }
            )

        return fields[:10]

    def _infer_list_name(self, parent, first_item) -> str:
        """Infer a human-readable name for a detected list."""
        # Check parent for clues
        parent_class = parent.get("class", "")
        parent_id = parent.get("id", "")

        for clue in [
            "product",
            "item",
            "card",
            "listing",
            "result",
            "post",
            "article",
            "row",
        ]:
            if clue in parent_class.lower() or clue in parent_id.lower():
                return f"{clue.title()} List"

        # Check first item
        item_class = first_item.get("class", "")
        for clue in ["product", "item", "card", "listing", "result", "post", "article"]:
            if clue in item_class.lower():
                return f"{clue.title()} List"

        return "Detected List"

    def _infer_table_name(self, table) -> str:
        """Infer a human-readable name for a detected table."""
        # Check for caption
        caption = table.xpath(".//caption/text()")
        if caption:
            return caption[0].strip()[:50]

        # Check preceding heading
        prev = table.xpath(
            "preceding-sibling::*[self::h1 or self::h2 or self::h3][1]/text()"
        )
        if prev:
            return prev[0].strip()[:50]

        # Check parent class
        parent = table.getparent()
        if parent is not None:
            parent_class = parent.get("class", "")
            if "table" in parent_class.lower():
                return parent_class.replace("-", " ").title()[:50]

        return "Data Table"
