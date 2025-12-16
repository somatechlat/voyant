"""
Unstructured Document Pipeline

Utilities for ingesting unstructured documents (PDF, DOCX, etc.) via the unstructured library.
Adheres to Vibe Coding Rules: Vibe Rule #5 - If doc is missing/unstable, define clear boundaries.
"""
from typing import Any, Dict, List, Optional
import os

from voyant.core.errors import IngestionError

class UnstructuredPipeline:
    """Pipeline for processing unstructured documents."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("UNSTRUCTURED_API_KEY")

    def process_document(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process a single document and return elements.
        
        Args:
            file_path: Absolute path to the file.
            
        Returns:
            List of elements (dicts) with text and metadata.
        """
        if not os.path.exists(file_path):
            raise IngestionError("VYNT-4004", f"File not found: {file_path}")

        try:
            from unstructured.partition.auto import partition
            
            # Using local partition (library base)
            # In production, this might offload to the Unstructured API if local deps are missing
            elements = partition(filename=file_path)
            
            # Convert to dicts
            return [self._element_to_dict(el) for el in elements]
            
        except ImportError:
            raise IngestionError(
                "VYNT-4005", 
                "Unstructured library not installed.", 
                resolution="pip install unstructured[all]"
            )
        except Exception as e:
            raise IngestionError("VYNT-4006", f"Failed to partition document: {e}")

    def _element_to_dict(self, element: Any) -> Dict[str, Any]:
        """Convert unstructured element to dictionary."""
        return {
            "type": str(type(element).__name__),
            "text": str(element),
            "metadata": element.metadata.to_dict() if hasattr(element, "metadata") else {}
        }
