"""
Voyant Scraper - HTML Parser for Structured Data Extraction.

This module provides a pure execution HTML parsing utility, designed to
extract structured data from raw HTML content using agent-provided CSS or
XPath selectors. It leverages `lxml` for high-performance parsing and
`cssselect` for flexible selector capabilities.
"""

import logging
from typing import Any, Dict, List, Union

from lxml import html as lxml_html
from lxml.cssselect import CSSSelector

logger = logging.getLogger(__name__)


class HTMLParser:
    """
    A robust HTML parser for extracting content based on CSS and XPath selectors.

    This parser operates as a pure execution tool: it takes HTML and a map of
    selectors and mechanically extracts the specified data, without any
    internal intelligence or LLM integration for selector generation.
    """

    def __init__(self):
        """Initializes the HTMLParser."""
        pass

    def extract(self, raw_html: str, selectors: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts data from raw HTML content using a map of CSS or XPath selectors.

        Args:
            raw_html (str): The raw HTML content as a string.
            selectors (Dict[str, Any]): A dictionary defining the extraction rules.
                                         Keys are the names of the fields to extract,
                                         and values are CSS/XPath selectors.
                                         Supports nested extraction for lists of items.
                                         Example:
                                         {
                                             "title": "h1::text",
                                             "links": "a::attr(href)",
                                             "items": {"root": ".product", "fields": {"name": ".name::text"}}
                                         }

        Returns:
            Dict[str, Any]: A dictionary containing the extracted data,
                            structured according to the `selectors` map.
                            Missing or failed extractions will result in `None` values.
        """
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
                result[field] = None  # Assign None if extraction for a field fails.

        return result

    def _extract_single(self, tree: lxml_html.HtmlElement, selector: str) -> Union[List[str], str, None]:
        """
        Internal method: Extracts a single value or a list of values using a CSS or XPath selector.

        Args:
            tree (lxml.html.HtmlElement): The lxml HTML element tree to search within.
            selector (str): The CSS or XPath selector string.

        Returns:
            Union[List[str], str, None]: A list of extracted strings, a single string, or None if not found/error.
        """
        if selector.startswith("//"):
            # XPath selector. lxml's xpath method returns a list.
            return tree.xpath(selector)

        elif "::" in selector:
            # CSS selector with pseudo-element (e.g., ::text, ::attr(href)).
            return self._css_extract(tree, selector)

        else:
            # Plain CSS selector. Default to extracting text content.
            return self._css_extract(tree, selector + "::text")

    def _css_extract(self, tree: lxml_html.HtmlElement, selector: str) -> List[str]:
        """
        Internal method: Extracts content using a CSS selector, supporting pseudo-elements.

        Args:
            tree (lxml.html.HtmlElement): The lxml HTML element tree to search within.
            selector (str): The CSS selector string, possibly with a pseudo-element
                            like "::text" or "::attr(attribute_name)".

        Returns:
            List[str]: A list of extracted strings.
        """
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
            return [lxml_html.tostring(el, encoding="unicode") for el in elements]
        else:
            # Fallback for unrecognized pseudo-elements, extract text content.
            return [el.text_content().strip() for el in elements if el.text_content()]

    def _extract_nested(self, tree: lxml_html.HtmlElement, selector_config: Dict) -> List[Dict[str, Any]]:
        """
        Internal method: Extracts nested data from a list of repeating elements.

        This is used for structures like product listings, where each product
        has its own set of fields.

        Args:
            tree (lxml.html.HtmlElement): The lxml HTML element tree to search within.
            selector_config (Dict): A dictionary defining the root selector for repeating items
                                    and a map of selectors for fields within each item.
                                    Example: `{"root": ".product", "fields": {"name": ".name::text"}}`.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                  represents an extracted item with its fields.
        """
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
                logger.warning(f"Invalid root selector '{root_selector}' for nested extraction: {e}")
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

    def get_all_links(self, raw_html: str) -> List[str]:
        """
        Extracts all `href` attributes from `<a>` tags in the HTML.

        Args:
            raw_html (str): The raw HTML content.

        Returns:
            List[str]: A list of all link URLs found.
        """
        tree = lxml_html.fromstring(raw_html)
        return tree.xpath("//a/@href")

    def get_all_images(self, raw_html: str) -> List[str]:
        """
        Extracts all `src` attributes from `<img>` tags in the HTML.

        Args:
            raw_html (str): The raw HTML content.

        Returns:
            List[str]: A list of all image source URLs found.
        """
        tree = lxml_html.fromstring(raw_html)
        return tree.xpath("//img/@src")

    def get_all_media(self, raw_html: str) -> List[str]:
        """
        Extracts all `src` attributes from `<video>` and `<audio>` tags in the HTML.

        Args:
            raw_html (str): The raw HTML content.

        Returns:
            List[str]: A list of all media source URLs found.
        """
        tree = lxml_html.fromstring(raw_html)
        return tree.xpath("//video/source/@src | //audio/source/@src")
