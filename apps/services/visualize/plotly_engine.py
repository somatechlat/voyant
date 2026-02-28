"""
Plotly Physical Rendering Engine

Converts pure mathematical data inputs into physical image architectures
using Plotly and Kaleido. Outputs are returned as strict hashes from
the native ArtifactStore.
"""

import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from apps.core.lib.artifact_store import store_artifact

logger = logging.getLogger(__name__)


class PlotlyRenderer:
    """
    100% Generic Chart Rendering Engine.
    Requires kaleido for physical static image generation safely without external browsers.
    """

    @classmethod
    def render_bar_comparison(
        cls, df: pd.DataFrame, x_col: str, y_col: str, tenant_id: str
    ) -> str:
        """
        Generates a generic bar comparison chart purely from a dataframe.
        """
        logger.info(f"Rendering generic bar chart for {tenant_id}")
        if df.empty or x_col not in df.columns or y_col not in df.columns:
            raise ValueError(
                f"Invalid parameters for bar_comparison: Missing {x_col} or {y_col}"
            )

        fig = px.bar(df, x=x_col, y=y_col, template="plotly_white")
        fig.update_layout(width=800, height=600, showlegend=True)
        return cls._save_to_artifact_store(fig, tenant_id, "bar_comparison")

    @classmethod
    def render_time_series(
        cls, df: pd.DataFrame, date_col: str, value_col: str, tenant_id: str
    ) -> str:
        """
        Generates a standard time series line chart.
        """
        logger.info(f"Rendering generic time_series chart for {tenant_id}")
        fig = px.line(df, x=date_col, y=value_col, template="plotly_white")
        fig.update_layout(width=800, height=400, showlegend=True)
        return cls._save_to_artifact_store(fig, tenant_id, "time_series")

    @classmethod
    def _save_to_artifact_store(
        cls, fig: go.Figure, tenant_id: str, prefix: str
    ) -> str:
        """
        Physically writes the static PNG to the ArtifactStore.
        Renders the plotly figure to bytes via kaleido securely.
        """
        # Real execution: Convert strictly to byte array via Kaleido engine
        img_bytes = fig.to_image(format="png", engine="kaleido")

        # Real storage: Push the byte array into the content-addressable storage
        ref = store_artifact(
            content=img_bytes,
            artifact_type=f"chart_{prefix}",
            metadata={"tenant_id": tenant_id, "source_engine": "plotly"},
        )

        logger.info(f"Generated physical chart artifact successfully: {ref.hash}")
        return ref.hash
