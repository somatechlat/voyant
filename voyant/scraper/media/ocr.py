"""
Voyant Scraper - OCR Processing

Optical Character Recognition for images and PDFs using pytesseract and Apache Tika.
"""
from typing import Optional, Dict, Any, List
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    OCR processor for extracting text from images and PDFs.
    
    Engines:
    - pytesseract: Local Tesseract OCR
    - tika: Apache Tika for document extraction
    """
    
    def __init__(
        self,
        engine: str = "pytesseract",
        language: str = "eng+spa",
        tika_url: Optional[str] = None
    ):
        self.engine = engine
        self.language = language
        self.tika_url = tika_url or os.environ.get("TIKA_URL", "http://localhost:9998")
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text from an image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dict with text, confidence, metadata
        """
        if self.engine == "pytesseract":
            return self._tesseract_image(image_path)
        else:
            return self._tika_extract(image_path)
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with text, pages, metadata
        """
        if self.engine == "pdfplumber":
            return self._pdfplumber_extract(pdf_path)
        elif self.engine == "tika":
            return self._tika_extract(pdf_path)
        else:
            return self._tesseract_pdf(pdf_path)
    
    def _tesseract_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text using Tesseract OCR."""
        import pytesseract
        from PIL import Image
        
        image = Image.open(image_path)
        
        # Get detailed output with confidence
        data = pytesseract.image_to_data(
            image, 
            lang=self.language,
            output_type=pytesseract.Output.DICT
        )
        
        # Calculate average confidence
        confidences = [c for c in data['conf'] if c > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Get plain text
        text = pytesseract.image_to_string(image, lang=self.language)
        
        return {
            "text": text.strip(),
            "confidence": avg_confidence / 100,
            "words": len(text.split()),
            "engine": "tesseract"
        }
    
    def _tesseract_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text from PDF using pdf2image + Tesseract."""
        import pytesseract
        from pdf2image import convert_from_path
        
        pages = convert_from_path(pdf_path)
        all_text = []
        total_confidence = 0
        
        for i, page_image in enumerate(pages):
            text = pytesseract.image_to_string(page_image, lang=self.language)
            all_text.append(f"--- Page {i+1} ---\n{text}")
            
            # Get confidence for this page
            data = pytesseract.image_to_data(
                page_image, 
                lang=self.language,
                output_type=pytesseract.Output.DICT
            )
            confidences = [c for c in data['conf'] if c > 0]
            if confidences:
                total_confidence += sum(confidences) / len(confidences)
        
        avg_confidence = (total_confidence / len(pages)) if pages else 0
        
        return {
            "text": "\n\n".join(all_text),
            "pages": len(pages),
            "confidence": avg_confidence / 100,
            "engine": "tesseract+pdf2image"
        }
    
    def _pdfplumber_extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text from PDF using pdfplumber (no OCR, native text)."""
        import pdfplumber
        
        all_text = []
        tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                all_text.append(f"--- Page {i+1} ---\n{text}")
                
                # Extract tables
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
        
        return {
            "text": "\n\n".join(all_text),
            "pages": len(pdf.pages),
            "tables": tables,
            "confidence": 1.0,  # Native text extraction
            "engine": "pdfplumber"
        }
    
    def _tika_extract(self, file_path: str) -> Dict[str, Any]:
        """Extract text using Apache Tika."""
        from tika import parser
        
        parsed = parser.from_file(file_path, serverEndpoint=self.tika_url)
        
        return {
            "text": parsed.get("content", "").strip(),
            "metadata": parsed.get("metadata", {}),
            "confidence": 1.0,
            "engine": "tika"
        }
    
    def process_image_bytes(self, image_bytes: bytes, format: str = "png") -> Dict[str, Any]:
        """
        Process image from bytes.
        
        Args:
            image_bytes: Image file bytes
            format: Image format (png, jpg, etc.)
            
        Returns:
            OCR result
        """
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(image_bytes)
            temp_path = f.name
        
        try:
            return self.process_image(temp_path)
        finally:
            os.unlink(temp_path)
