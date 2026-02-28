"""
Voyant Scraper - Tesseract-based OCR Processor.

This module provides a dedicated Optical Character Recognition (OCR) processor
specifically designed to extract text from images using the Tesseract OCR engine.
It includes functionalities for basic text extraction, structured extraction
with bounding box data, and image preprocessing to enhance OCR accuracy.

Architectural Note:
This module (`apps/scraper/parsing/ocr_processor.py`) implements a Tesseract-specific
OCR processor. There is an architectural redundancy with `apps/scraper/media/ocr.py`,
which also defines an `OCRProcessor` class but acts as a higher-level orchestrator
for different OCR engines (including Tesseract, pdfplumber, and Tika).
For future refactoring, these two modules should be consolidated.
"""

import io
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    A processor for extracting text from images using the Tesseract OCR engine.

    This class provides both plain text and structured text extraction capabilities,
    and includes image preprocessing steps to improve OCR accuracy.
    """

    def __init__(self, language: str = "spa+eng"):
        """
        Initializes the OCRProcessor.

        Args:
            language (str, optional): The language(s) to use for Tesseract OCR (e.g., "eng", "spa+eng").
                                      Defaults to "spa+eng" (Spanish and English).
        """
        self.language = language
        # Tesseract configuration for LSTM engine mode and automatic page segmentation.
        self.config = "--oem 3 --psm 3"

    def extract(self, image_source: Union[bytes, str]) -> Dict[str, Any]:
        """
        Extracts plain text content from an image.

        Args:
            image_source (Union[bytes, str]): The image data as bytes or a file path to the image.

        Returns:
            Dict[str, Any]: A dictionary containing the extracted text, an estimated
                            confidence score, the language used, and image dimensions.

        Raises:
            ImportError: If `pytesseract` or `Pillow` are not installed.
            TesseractError: If Tesseract encounters an error during OCR.
            Exception: For other errors during image loading or processing.
        """
        import pytesseract
        from PIL import Image

        # Load image from bytes or file path.
        if isinstance(image_source, bytes):
            image = Image.open(io.BytesIO(image_source))
        else:
            image = Image.open(image_source)

        # Apply preprocessing steps to enhance OCR accuracy.
        image = self._preprocess(image)

        # Extract text using Tesseract.
        text = pytesseract.image_to_string(
            image, lang=self.language, config=self.config
        )

        # Calculate an average confidence score for the extraction.
        confidence = self._get_confidence(image)

        return {
            "text": text.strip(),
            "confidence": confidence,
            "language": self.language,
            "width": image.width,
            "height": image.height,
        }

    def extract_structured(self, image_source: Union[bytes, str]) -> Dict[str, Any]:
        """
        Extracts text from an image along with structural information (e.g., bounding boxes).

        Args:
            image_source (Union[bytes, str]): The image data as bytes or a file path to the image.

        Returns:
            Dict[str, Any]: A dictionary containing a list of words with their
                            bounding box coordinates and confidence scores, the full extracted
                            text, and the total word count.

        Raises:
            ImportError: If `pytesseract` or `Pillow` are not installed.
            TesseractError: If Tesseract encounters an error during OCR.
            Exception: For other errors during image loading or processing.
        """
        import pytesseract
        from PIL import Image

        if isinstance(image_source, bytes):
            image = Image.open(io.BytesIO(image_source))
        else:
            image = Image.open(image_source)

        # Extract data including box coordinates and confidence.
        data = pytesseract.image_to_data(
            image, lang=self.language, output_type=pytesseract.Output.DICT
        )

        words = []
        # Iterate through detected words and format their data.
        for i, word in enumerate(data["text"]):
            if word and word.strip():  # Ensure the word is not empty.
                words.append(
                    {
                        "text": word,
                        "left": data["left"][i],
                        "top": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i],
                        "confidence": data["conf"][i],
                    }
                )

        return {
            "words": words,
            "full_text": " ".join(
                filter(None, data["text"])
            ).strip(),  # Join non-empty words.
            "word_count": len(words),
        }

    def _preprocess(self, image: Any) -> Any:
        """
        Internal method: Applies image preprocessing steps to enhance OCR accuracy.

        Args:
            image (PIL.Image.Image): The Pillow Image object to preprocess.

        Returns:
            PIL.Image.Image: The processed Pillow Image object.
        """
        from PIL import ImageEnhance, ImageFilter

        # Convert to RGB mode if necessary for consistent processing.
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Enhance contrast to make text more distinct.
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        # Apply sharpening filter to improve character definition.
        image = image.filter(ImageFilter.SHARPEN)

        return image

    def _get_confidence(self, image: Any) -> float:
        """
        Internal method: Calculates the average confidence score of the OCR extraction.

        Args:
            image (PIL.Image.Image): The Pillow Image object from which text was extracted.

        Returns:
            float: The average confidence score (0.0 to 1.0), or 0.0 if calculation fails.
        """
        import pytesseract

        try:
            data = pytesseract.image_to_data(
                image, lang=self.language, output_type=pytesseract.Output.DICT
            )
            # Filter out zero-confidence entries (often non-text regions).
            confidences = [c for c in data["conf"] if c > 0]
            if confidences:
                return round(sum(confidences) / len(confidences) / 100, 2)
        except Exception as e:
            logger.warning(f"Confidence calculation failed: {e}")

        return 0.0

    def batch_extract(self, images: List[Union[bytes, str]]) -> List[Dict[str, Any]]:
        """
        Extracts text from a list of images in a batch.

        Args:
            images (List[Union[bytes, str]]): A list of image data as bytes or file paths.

        Returns:
            List[Dict[str, Any]]: A list of extraction results, one dictionary per image.
                                  Includes an "error" field if an image fails processing.
        """
        results = []
        for img_source in images:
            try:
                results.append(self.extract(img_source))
            except Exception as e:
                logger.error(f"Batch OCR failed for an image: {e}")
                results.append({"error": str(e)})
        return results
