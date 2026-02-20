"""
Voyant Scraper - PDF Parser for Structured and Unstructured Data Extraction.

This module provides functionalities for parsing PDF documents to extract
text content, metadata, and structured tables. It intelligently leverages
Apache Tika for comprehensive document analysis (especially for image-based
or complex PDFs) and `pdfplumber` for precise native text and table extraction
from machine-generated PDFs.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PDFParser:
    """
    A parser for extracting various forms of content from PDF documents.

    This class offers a robust approach by combining the broad capabilities of
    Apache Tika with the precision of `pdfplumber`, allowing for effective
    processing of diverse PDF types.
    """

    def __init__(self, tika_url: Optional[str] = None):
        """
        Initializes the PDFParser.

        Args:
            tika_url (Optional[str]): The URL of the Apache Tika server. If provided,
                                      the remote Tika server will be used for parsing.
                                      If None, the local Tika client (requiring Java) is used.
        """
        self.tika_url = tika_url

    def parse(self, pdf_path: str, extract_tables: bool = False) -> Dict[str, Any]:
        """
        Parses a PDF file to extract its text content and metadata,
        with an option to extract tables.

        This method attempts to use Apache Tika first for comprehensive extraction.
        If Tika fails or is not configured, it falls back to `pdfplumber` for
        native text extraction.

        Args:
            pdf_path (str): The file path to the PDF document.
            extract_tables (bool, optional): If True, also attempts to extract
                                           structured tables from the PDF. Defaults to False.

        Returns:
            Dict[str, Any]: A dictionary containing the extracted text, metadata,
                            page count, and optionally extracted tables.

        Raises:
            ImportError: If required Python packages (`tika` or `pdfplumber`) are not installed.
            Exception: For errors during PDF parsing by either engine.
        """
        result = {
            "text": "",
            "metadata": {},
            "pages": 0,
        }

        # Attempt to parse using Apache Tika first for broader document support.
        try:
            tika_result = self._parse_with_tika(pdf_path)
            result["text"] = tika_result.get("content", "").strip()
            result["metadata"] = tika_result.get("metadata", {})
            # Tika doesn't directly return page count from `from_file`, infer from metadata or pdfplumber fallback.
            # For robustness, pages will be updated by pdfplumber if fallback occurs.
            logger.info("PDF parsed successfully with Apache Tika.")
        except Exception as e:
            logger.warning(
                f"Apache Tika parsing failed: {e}. Falling back to pdfplumber."
            )
            # Fallback to pdfplumber if Tika fails or is not available.
            plumber_result = self._parse_with_pdfplumber(pdf_path)
            result["text"] = plumber_result.get("text", "")
            result["pages"] = plumber_result.get("pages", 0)
            logger.info("PDF parsed successfully with pdfplumber fallback.")

        # Extract tables if explicitly requested, using pdfplumber which is good for structured tables.
        if extract_tables:
            try:
                result["tables"] = self._extract_tables(pdf_path)
            except Exception as e:
                logger.warning(
                    f"Table extraction failed with pdfplumber: {e}. Returning empty list."
                )
                result["tables"] = []

        return result

    def _parse_with_tika(self, pdf_path: str) -> Dict[str, Any]:
        """
        Internal method: Parses a PDF file using the Apache Tika client.

        Args:
            pdf_path (str): The file path to the PDF document.

        Returns:
            Dict[str, Any]: The raw output from Tika parsing, containing content and metadata.

        Raises:
            ImportError: If the `tika` Python client is not installed.
            Exception: If the Tika server is unreachable or document parsing fails.
        """
        from tika import parser as tika_parser

        if self.tika_url:
            # Use a remote Tika server if URL is provided.
            return tika_parser.from_file(pdf_path, serverEndpoint=self.tika_url)
        else:
            # Use a local Tika client (requires a Java Runtime Environment).
            return tika_parser.from_file(pdf_path)

    def _parse_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """
        Internal method: Parses a PDF file using the `pdfplumber` library for native text extraction.

        This method is effective for machine-generated PDFs that have selectable text.

        Args:
            pdf_path (str): The file path to the PDF document.

        Returns:
            Dict[str, Any]: A dictionary containing the concatenated text from all pages and the total page count.

        Raises:
            ImportError: If the `pdfplumber` package is not installed.
            Exception: For errors during PDF parsing.
        """
        import pdfplumber

        text_parts = []
        page_count = 0

        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return {
            "text": "\n\n".join(text_parts),
            "pages": page_count,
        }

    def _extract_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Internal method: Extracts structured tables from a PDF using `pdfplumber`.

        Args:
            pdf_path (str): The file path to the PDF document.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents
                                  an extracted table, including its page number, dimensions, and data.

        Raises:
            ImportError: If the `pdfplumber` package is not installed.
            Exception: For errors during table extraction.
        """
        import pdfplumber

        tables = []

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                for table in page_tables:
                    if table and len(table) > 0:
                        tables.append(
                            {
                                "page": i + 1,
                                "rows": len(table),
                                "cols": len(table[0]) if table[0] else 0,
                                "data": table,
                            }
                        )
        return tables

    def get_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extracts metadata from a PDF file using Apache Tika.

        Args:
            pdf_path (str): The file path to the PDF document.

        Returns:
            Dict[str, Any]: A dictionary containing the extracted metadata.

        Raises:
            ImportError: If the `tika` Python client is not installed.
            Exception: If the Tika server is unreachable or metadata extraction fails.
        """
        try:
            from tika import parser as tika_parser

            result = tika_parser.from_file(pdf_path)
            return result.get("metadata", {})
        except Exception as e:
            logger.warning(f"Metadata extraction failed for '{pdf_path}': {e}")
            return {}
