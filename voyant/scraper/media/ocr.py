"""
Voyant Scraper - OCR Processing for Extracting Text from Images and PDFs.

This module provides Optical Character Recognition (OCR) capabilities, enabling
the extraction of machine-readable text from various image and PDF formats.
It integrates with different OCR engines (`pytesseract` for local Tesseract,
`pdfplumber` for native PDF text, and `Apache Tika` for broader document support)
to offer flexibility based on document type and desired output quality.
"""

import logging
import os
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    A processor for extracting text content from image files and PDF documents.

    This class provides an abstraction over different OCR and text extraction engines,
    allowing selection based on the specific requirements of the document and
    the available system resources.

    Supported Engines:
    - `pytesseract`: Utilizes the Tesseract OCR engine for image-based text extraction.
    - `pdfplumber`: Extracts native text from PDF documents, preserving layout.
    - `tika`: Leverages an external Apache Tika server for advanced document parsing
              and text extraction from a wide range of file formats.
    """

    def __init__(
        self,
        engine: str = "pytesseract",
        language: str = "eng+spa",
        tika_url: Optional[str] = None,
    ):
        """
        Initializes the OCRProcessor.

        Args:
            engine (str): The primary OCR engine to use ("pytesseract", "pdfplumber", or "tika").
            language (str): The language(s) to use for OCR (e.g., "eng", "spa+eng"). Applicable to pytesseract.
            tika_url (Optional[str]): The URL of the Apache Tika server. If None,
                                      it defaults to environment variable TIKA_URL or "http://localhost:9998".
        """
        self.engine = engine
        self.language = language
        self.tika_url = tika_url or os.environ.get("TIKA_URL", "http://localhost:9998")

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Extracts text from a local image file using the configured OCR engine.

        Args:
            image_path (str): The file path to the image.

        Returns:
            Dict[str, Any]: A dictionary containing the extracted text, confidence score,
                            word count, and the engine used.

        Raises:
            ImportError: If required Python packages for the selected engine are not installed.
            Exception: For any errors encountered during image processing or OCR.
        """
        if self.engine == "pytesseract":
            return self._tesseract_image(image_path)
        elif self.engine == "tika":
            return self._tika_extract(image_path)
        else:
            logger.warning(f"Unsupported OCR engine '{self.engine}' for image processing. Falling back to pytesseract.")
            return self._tesseract_image(image_path)

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extracts text from a local PDF file using the configured engine.

        Args:
            pdf_path (str): The file path to the PDF document.

        Returns:
            Dict[str, Any]: A dictionary containing the extracted text, page count,
                            confidence score, tables (if using pdfplumber), and the engine used.

        Raises:
            ImportError: If required Python packages for the selected engine are not installed.
            Exception: For any errors encountered during PDF processing or text extraction.
        """
        if self.engine == "pdfplumber":
            return self._pdfplumber_extract(pdf_path)
        elif self.engine == "tika":
            return self._tika_extract(pdf_path)
        else:
            logger.warning(f"Unsupported OCR engine '{self.engine}' for PDF processing. Falling back to tesseract.")
            return self._tesseract_pdf(pdf_path)

    def _tesseract_image(self, image_path: str) -> Dict[str, Any]:
        """
        Internal method: Extracts text from an image using `pytesseract`.

        Args:
            image_path (str): Path to the image file.

        Returns:
            Dict[str, Any]: Extracted text, average confidence, word count, and engine name.

        Raises:
            ImportError: If `pytesseract` or `Pillow` are not installed.
            TesseractError: If Tesseract encounters an error.
        """
        import pytesseract
        from PIL import Image

        image = Image.open(image_path)

        # Get detailed output to calculate average confidence.
        data = pytesseract.image_to_data(
            image, lang=self.language, output_type=pytesseract.Output.DICT
        )

        # Calculate average confidence, filtering out zero-confidence words.
        confidences = [c for c in data["conf"] if c > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Extract plain text from the image.
        text = pytesseract.image_to_string(image, lang=self.language)

        return {
            "text": text.strip(),
            "confidence": avg_confidence / 100,  # Convert to 0.0-1.0 range.
            "words": len(text.split()),
            "engine": "pytesseract",
        }

    def _tesseract_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Internal method: Extracts text from a PDF by converting pages to images and
        then applying Tesseract OCR to each image.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            Dict[str, Any]: Extracted text (concatenated), page count, average confidence, and engine name.

        Raises:
            ImportError: If `pytesseract` or `pdf2image` are not installed.
            Exception: For errors during PDF-to-image conversion or OCR.
        """
        import pytesseract
        from pdf2image import convert_from_path

        pages = convert_from_path(pdf_path)
        all_text = []
        total_confidence = 0.0

        for i, page_image in enumerate(pages):
            text = pytesseract.image_to_string(page_image, lang=self.language)
            all_text.append(f"--- Page {i+1} ---\n{text}")

            # Calculate confidence for the current page.
            data = pytesseract.image_to_data(
                page_image, lang=self.language, output_type=pytesseract.Output.DICT
            )
            confidences = [c for c in data["conf"] if c > 0]
            if confidences:
                total_confidence += sum(confidences) / len(confidences)

        # Calculate overall average confidence across all pages.
        avg_confidence = (total_confidence / len(pages)) if pages else 0

        return {
            "text": "\n\n".join(all_text),
            "pages": len(pages),
            "confidence": avg_confidence / 100,
            "engine": "pytesseract+pdf2image",
        }

    def _pdfplumber_extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Internal method: Extracts native text and tables directly from a PDF using `pdfplumber`.

        This method is generally faster and more accurate for machine-generated PDFs
        as it doesn't involve image conversion.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            Dict[str, Any]: Extracted text, page count, tables, and engine name.

        Raises:
            ImportError: If `pdfplumber` is not installed.
            Exception: For errors during PDF parsing.
        """
        import pdfplumber

        all_text = []
        tables = []

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                all_text.append(f"--- Page {i+1} ---\n{text}")

                # Extract tables from the page.
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)

        return {
            "text": "\n\n".join(all_text),
            "pages": len(pdf.pages),
            "tables": tables,
            "confidence": 1.0,  # Native text extraction is assumed to be 100% confident.
            "engine": "pdfplumber",
        }

    def _tika_extract(self, file_path: str) -> Dict[str, Any]:
        """
        Internal method: Extracts text and metadata from a wide range of document types
        using an external Apache Tika server.

        Args:
            file_path (str): Path to the document file (image, PDF, Word, Excel, etc.).

        Returns:
            Dict[str, Any]: Extracted text, metadata, and engine name.

        Raises:
            ImportError: If `tika` Python client is not installed.
            Exception: If the Tika server is unreachable or document parsing fails.
        """
        from tika import parser

        # The Tika server endpoint is configured in __init__.
        parsed = parser.from_file(file_path, serverEndpoint=self.tika_url)

        return {
            "text": parsed.get("content", "").strip(),
            "metadata": parsed.get("metadata", {}),
            "confidence": 1.0,  # Tika generally provides high confidence for structured text.
            "engine": "tika",
        }

    def process_image_bytes(
        self, image_bytes: bytes, format: str = "png"
    ) -> Dict[str, Any]:
        """
        Processes an image provided as bytes, saving it to a temporary file for OCR,
        then deleting the temporary file.

        Args:
            image_bytes (bytes): The raw bytes content of the image file.
            format (str, optional): The format of the image (e.g., "png", "jpg"). Defaults to "png".

        Returns:
            Dict[str, Any]: A dictionary containing the extracted text and related metadata.

        Raises:
            Exception: For any errors encountered during temporary file handling or image processing.
        """
        # Create a temporary file to store the image bytes, as OCR engines typically
        # work with file paths.
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(image_bytes)
            temp_path = f.name

        try:
            return self.process_image(temp_path)
        finally:
            # Ensure the temporary file is deleted after processing.
            os.unlink(temp_path)
