"""
Universal XLS Rendering Engine

Architect Mandate: Excel files are constructed exclusively from generic
DataFrames with rigid structural parameters enforced via XlsxWriter.
"""

import io
import logging
from typing import Dict

import pandas as pd

from apps.core.lib.artifact_store import store_artifact

logger = logging.getLogger(__name__)


class XLSAssembler:
    """XlsxWriter physical compiler for structured data streams."""

    @classmethod
    def compile_xls(
        cls, dataframes: Dict[str, pd.DataFrame], tenant_id: str, report_name: str
    ) -> str:
        """
        Compiles multiple dataframes into strictly formatted tabs and stores artifact.
        """
        logger.info(f"Compiling generic XLS {report_name} for {tenant_id}")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for sheet_name, df in dataframes.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                # Enforce strict column formatting (Security/UX Mandate: no infinite width columns)
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(df.columns):
                    max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, min(max_len, 50))

        xls_bytes = output.getvalue()

        # Real storage via native ArtifactStore
        ref = store_artifact(
            content=xls_bytes,
            artifact_type=f"document_xls_{report_name}",
            metadata={"tenant_id": tenant_id, "source_engine": "xlsxwriter"},
        )

        logger.info(f"XLS Firmly assembled in store: {ref.hash}")
        return ref.hash
