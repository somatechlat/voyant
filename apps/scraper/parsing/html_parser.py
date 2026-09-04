"""HTML parser for structured data extraction using CSS/XPath selectors."""

import logging
from typing import Any

from lxml import html as lxml_html
from lxml.cssselect import CSSSelector

logger = logging.getLogger(__name__)


class HTMLParser:
    """
    Pure execution HTML parser — takes HTML and a map of selectors
    and extracts specified data without any LLM integration.
    """

    def __init__(self):
        pass

    def extract(self, raw_html: str, selectors: dict[str, Any]) -> dict[str, Any]:
        try:
            tree = lxml_html.fromstring(raw_html)
        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            return {"error": str(e)}

        result = {}

        for field, selector in selectors.items():
            try:
                if isinstance(selector, str):
                    result[field] = self._extract_single(tree, selector)
                elif isinstance(selector, dict):
                    result[field] = self._extract_nested(tree, selector)
            except Exception as e:
                logger.warning(f"Selector '{field}' failed during extraction: {e}")
                result[field] = None

        return result

    def _extract_single(self, tree: lxml_html.HtmlElement, selector: str) -> list[str] | str | None:
        if selector.startswith("//"):
            # XPath selector. lxml's xpath method returns a list.
            return tree.xpath(selector)

        elif "::" in selector:
            # CSS selector with pseudo-element (e.g., ::text, ::attr(href)).
            return self._css_extract(tree, selector)

        else:
            # Plain CSS selector. Default to extracting text content.
            return self._css_extract(tree, selector + "::text")

    def _css_extract(self, tree: lxml_html.HtmlElement, selector: str) -> list[str]:
        parts = selector.rsplit("::", 1)
        css = parts[0]
        pseudo = parts[1] if len(parts) > 1 else "text"

        try:
            sel = CSSSelector(css)
            elements = sel(tree)
        except Exception as e:
            logger.warning(f"Invalid CSS selector '{css}': {e}")
            return []

        if pseudo == "text":
            return [el.text_content().strip() for el in elements if el.text_content()]
        elif pseudo.startswith("attr(") and pseudo.endswith(")"):
            attr = pseudo[5:-1]  # Extract attribute name.
            return [el.get(attr) for el in elements if el.get(attr) is not None]
        elif pseudo == "html":
            return [lxml_html.tostring(el, encoding="unicode") for el in elements]  # type: ignore[return-value]
        else:
            # Fallback for unrecognized pseudo-elements, extract text content.
            return [el.text_content().strip() for el in elements if el.text_content()]

    def _extract_nested(
        self, tree: lxml_html.HtmlElement, selector_config: dict
    ) -> list[dict[str, Any]]:
        root_selector = selector_config.get("root", "")
        fields_map = selector_config.get("fields", {})

        # Find all root elements that represent the repeating items.
        if root_selector.startswith("//"):
            items = tree.xpath(root_selector)
        else:
            try:
                sel = CSSSelector(root_selector)
                items = sel(tree)
            except Exception as e:
                logger.warning(
                    f"Invalid root selector '{root_selector}' for nested extraction: {e}"
                )
                return []

        results = []
        for item_element in items:
            row = {}
            for field_name, field_selector in fields_map.items():
                try:
                    values = self._extract_single(item_element, field_selector)
                    # For nested fields, usually only the first value is desired.
                    row[field_name] = values[0] if values else None
                except Exception as e:
                    logger.warning(f"Nested selector '{field_name}' failed for an item: {e}")
                    row[field_name] = None
            results.append(row)

        return results

    def get_all_links(self, raw_html: str) -> list[str]:
        tree = lxml_html.fromstring(raw_html)
        return tree.xpath("//a/@href")

    def get_all_images(self, raw_html: str) -> list[str]:
        tree = lxml_html.fromstring(raw_html)
        return tree.xpath("//img/@src")

    def get_all_media(self, raw_html: str) -> list[str]:
        tree = lxml_html.fromstring(raw_html)
        return tree.xpath("//video/source/@src | //audio/source/@src")
