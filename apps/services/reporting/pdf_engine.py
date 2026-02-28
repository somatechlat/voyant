"""
Universal PDF Rendering Engine

Architect Mandate: The Agent never creates custom layouts. The Agent only supplies
parameters to the UPTP Engine, which synthesizes HTML via Jinja2 and compiles it
to secure, pixel-perfect PDFs via WeasyPrint.
"""

import logging
import os
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from apps.core.lib.artifact_store import store_artifact

logger = logging.getLogger(__name__)


class PDFAssembler:
    """WeasyPrint physical compiler for generic ISO documents."""

    @classmethod
    def compile_pdf(
        cls, template_name: str, params: Dict[str, Any], tenant_id: str
    ) -> str:
        """
        Binds parameters to a stored HTML layout and compiles to PDF.
        """
        logger.info(f"Compiling physical {template_name} PDF for {tenant_id}")

        template_dir = os.path.join(os.path.dirname(__file__), "templates")

        # Ensure the templates directory physically exists to prevent loading errors
        if not os.path.exists(template_dir):
            os.makedirs(template_dir, exist_ok=True)

        # Security: Prevent path traversal by strictly enforcing Jinja2 FileSystemLoader
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        template = env.get_template(f"{template_name}.html")
        hydrated_content = template.render(**params)

        # Genuine compilation via WeasyPrint directly to memory bytes
        pdf_bytes = HTML(string=hydrated_content).write_pdf()

        # Real storage: Content-addressable physical store
        ref = store_artifact(
            content=pdf_bytes,
            artifact_type=f"document_pdf_{template_name}",
            metadata={"tenant_id": tenant_id, "source_engine": "weasyprint"},
        )

        logger.info(f"Document firmly assembled to {ref.hash}")
        return ref.hash
