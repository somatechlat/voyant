"""
Unstructured Document Pipeline: Processing for Various Document Types.

This module provides utilities for ingesting and processing unstructured documents
(e.g., PDF, DOCX, HTML, images) by leveraging the `unstructured` library.
It aims to extract structured elements, text, and metadata from these documents,
making them suitable for further analysis and integration into data pipelines.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from apps.core.errors import IngestionError

logger = logging.getLogger(__name__)


class UnstructuredPipeline:
    """
    A pipeline for processing and extracting structured elements from unstructured documents.

    This class wraps the `unstructured` library to provide a unified interface
    for handling various document formats, converting them into a list of
    extractable elements with associated text and metadata.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the UnstructuredPipeline.

        Args:
            api_key (Optional[str]): An optional API key for the Unstructured API.
                                     If not provided, it defaults to the `UNSTRUCTURED_API_KEY`
                                     environment variable.
        """
        self.api_key = api_key or os.getenv("UNSTRUCTURED_API_KEY")

    def process_document(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Processes a single document file and returns a list of extracted elements.

        This method uses the `unstructured` library's auto-partitioning feature
        to intelligently break down the document into logical elements (e.g., titles,
        paragraphs, tables).

        Args:
            file_path (str): The absolute path to the document file to process.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                  represents an extracted element with its type,
                                  text content, and metadata.

        Raises:
            IngestionError: If the file is not found, the `unstructured` library
                            is not installed, or document partitioning fails.
        """
        if not os.path.exists(file_path):
            raise IngestionError("VYNT-4004", f"Document file not found: {file_path}")

        try:
            from unstructured.partition.auto import partition

            # The `partition` function automatically detects the file type and applies
            # appropriate processing for local partitioning. In a production setting,
            # this might be configured to offload to an Unstructured API endpoint.
            elements = partition(filename=file_path)

            # Convert library-specific element objects to a generic dictionary format.
            return [self._element_to_dict(el) for el in elements]

        except ImportError as e:
            logger.error(f"Unstructured library not installed: {e}")
            raise IngestionError(
                "VYNT-4005",
                "The 'unstructured' library is not installed. Please install it to use unstructured document processing.",
                resolution="pip install unstructured[all]",
            ) from e
        except Exception as e:
            logger.error(f"Failed to partition document '{file_path}': {e}")
            raise IngestionError("VYNT-4006", f"Failed to process document: {e}") from e

    def _element_to_dict(self, element: Any) -> Dict[str, Any]:
        """
        Internal method: Converts an `unstructured` library element object into a dictionary.

        Args:
            element (Any): An element object returned by the `unstructured` library's partition function.

        Returns:
            Dict[str, Any]: A dictionary representation of the element, including its type,
                            text content, and metadata.
        """
        return {
            "type": str(type(element).__name__),  # e.g., "Title", "NarrativeText".
            "text": str(element),
            "metadata": (
                element.metadata.to_dict() if hasattr(element, "metadata") else {}
            ),
        }
