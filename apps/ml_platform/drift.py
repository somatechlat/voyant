"""
Drift Detector — Statistical tests for data and prediction drift.

Monitors deployed models for feature drift (KS test for numeric, chi-square
for categorical) and prediction drift (Population Stability Index).

When drift is detected, creates a Notification via the notification service.
"""

from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds (configurable per deployment in the future)
# ---------------------------------------------------------------------------
KS_THRESHOLD = 0.1       # Kolmogorov-Smirnov statistic threshold
PSI_THRESHOLD = 0.2      # Population Stability Index threshold
CHI2_PVALUE_THRESHOLD = 0.05  # Chi-square p-value threshold


# ---------------------------------------------------------------------------
# Drift report dataclass
# ---------------------------------------------------------------------------
@dataclass
class DriftResult:
    """Result of a single feature drift computation."""

    feature_name: str
    drift_metric: str   # "ks_statistic", "chi_square", "psi"
    drift_value: float
    threshold: float
    is_drifted: bool
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Drift Detector
# ---------------------------------------------------------------------------


class DriftDetector:
    """
    Statistical drift detection for model monitoring.

    Supports:
    - **Feature drift**: KS test (numeric) and chi-square test (categorical).
    - **Prediction drift**: Population Stability Index (PSI).

    Usage::

        detector = DriftDetector()
        result = detector.compute_feature_drift(ref_data, cur_data, "age")
        report = detector.generate_drift_report(deployment_id)
    """

    # ── Feature Drift ────────────────────────────────────────────────────

    def compute_feature_drift(
        self,
        reference_data: list[float | int | str],
        current_data: list[float | int | str],
        feature_name: str,
        feature_type: str = "numeric",
    ) -> DriftResult:
        """
        Compute drift for a single feature between reference and current data.

        For **numeric** features: two-sample Kolmogorov-Smirnov test.
        For **categorical** features: chi-square test.

        Args:
            reference_data: Baseline distribution values.
            current_data: Production / recent distribution values.
            feature_name: Name of the feature.
            feature_type: ``"numeric"`` or ``"categorical"``.

        Returns:
            ``DriftResult`` with metric value, threshold, and is_drifted flag.
        """
        if feature_type == "categorical":
            return self._chi_square_drift(reference_data, current_data, feature_name)
        return self._ks_drift(reference_data, current_data, feature_name)

    def _ks_drift(
        self,
        reference: list[float | int],
        current: list[float | int],
        feature_name: str,
    ) -> DriftResult:
        """Two-sample Kolmogorov-Smirnov test for numeric features."""
        ref_sorted = sorted(float(x) for x in reference)
        cur_sorted = sorted(float(x) for x in current)

        n_ref = len(ref_sorted)
        n_cur = len(cur_sorted)

        if n_ref == 0 or n_cur == 0:
            return DriftResult(
                feature_name=feature_name,
                drift_metric="ks_statistic",
                drift_value=0.0,
                threshold=KS_THRESHOLD,
                is_drifted=False,
                details={"error": "empty input"},
            )

        # Compute empirical CDFs and max distance
        all_values = sorted(set(ref_sorted + cur_sorted))
        ks_stat = 0.0
        cdf_ref = 0.0
        cdf_cur = 0.0
        i_ref = 0
        i_cur = 0

        for val in all_values:
            while i_ref < n_ref and ref_sorted[i_ref] <= val:
                cdf_ref += 1.0 / n_ref
                i_ref += 1
            while i_cur < n_cur and cur_sorted[i_cur] <= val:
                cdf_cur += 1.0 / n_cur
                i_cur += 1
            ks_stat = max(ks_stat, abs(cdf_ref - cdf_cur))

        # Approximate critical value at alpha=0.05 for two-sample KS
        critical = 1.36 * math.sqrt((n_ref + n_cur) / (n_ref * n_cur))
        is_drifted = ks_stat > KS_THRESHOLD

        if is_drifted:
            logger.warning(
                "Feature drift detected: %s (KS=%.4f > %.4f)",
                feature_name, ks_stat, KS_THRESHOLD,
            )

        return DriftResult(
            feature_name=feature_name,
            drift_metric="ks_statistic",
            drift_value=round(ks_stat, 6),
            threshold=KS_THRESHOLD,
            is_drifted=is_drifted,
            details={
                "reference_size": n_ref,
                "current_size": n_cur,
                "critical_value": round(critical, 6),
            },
        )

    def _chi_square_drift(
        self,
        reference: list[str | Any],
        current: list[str | Any],
        feature_name: str,
    ) -> DriftResult:
        """Chi-square test for categorical features."""
        # Build frequency tables from both distributions
        all_categories = sorted(set(reference) | set(current))
        n_ref = len(reference)
        n_cur = len(current)

        if n_ref == 0 or n_cur == 0:
            return DriftResult(
                feature_name=feature_name,
                drift_metric="chi_square",
                drift_value=0.0,
                threshold=CHI2_PVALUE_THRESHOLD,
                is_drifted=False,
                details={"error": "empty input"},
            )

        ref_counts = {cat: 0 for cat in all_categories}
        cur_counts = {cat: 0 for cat in all_categories}
        for v in reference:
            ref_counts[v] = ref_counts.get(v, 0) + 1
        for v in current:
            cur_counts[v] = cur_counts.get(v, 0) + 1

        # Expected frequencies based on reference proportions
        chi2 = 0.0
        for cat in all_categories:
            expected = ref_counts[cat] / n_ref * n_cur
            if expected > 0:
                chi2 += (cur_counts[cat] - expected) ** 2 / expected

        # Degrees of freedom
        df = len(all_categories) - 1
        if df <= 0:
            df = 1

        # Approximate p-value using chi2 survival function approximation
        p_value = self._chi2_survival(chi2, df)
        is_drifted = p_value < CHI2_PVALUE_THRESHOLD

        if is_drifted:
            logger.warning(
                "Categorical drift detected: %s (chi2=%.4f, p=%.6f < %.4f)",
                feature_name, chi2, p_value, CHI2_PVALUE_THRESHOLD,
            )

        return DriftResult(
            feature_name=feature_name,
            drift_metric="chi_square",
            drift_value=round(chi2, 6),
            threshold=CHI2_PVALUE_THRESHOLD,
            is_drifted=is_drifted,
            details={
                "p_value": round(p_value, 8),
                "degrees_of_freedom": df,
                "reference_size": n_ref,
                "current_size": n_cur,
                "n_categories": len(all_categories),
            },
        )

    @staticmethod
    def _chi2_survival(x: float, k: int) -> float:
        """
        Approximate chi-square survival function P(X > x) with df=k.

        Uses the regularized incomplete gamma function approximation
        (no scipy dependency required).
        """
        if x <= 0:
            return 1.0

        a = k / 2.0
        z = x / 2.0

        # Series expansion of lower incomplete gamma
        total = 0.0
        term = 1.0 / a
        total = term
        for n in range(1, 200):
            term *= z / (a + n)
            total += term
            if abs(term) < 1e-12:
                break

        import math as _math

        log_gamma_a = _math.lgamma(a)
        lower_gamma = total * _math.exp(-z + a * _math.log(z) - log_gamma_a)

        return max(0.0, min(1.0, 1.0 - lower_gamma))

    # ── Prediction Drift (PSI) ──────────────────────────────────────────

    def compute_prediction_drift(
        self,
        reference_dist: list[float],
        current_dist: list[float],
        n_bins: int = 10,
    ) -> DriftResult:
        """
        Compute Population Stability Index (PSI) between two distributions.

        PSI measures how much a distribution has shifted:
        - PSI < 0.1: no significant change
        - 0.1 <= PSI < 0.2: moderate change
        - PSI >= 0.2: significant change

        Args:
            reference_dist: Baseline prediction distribution (probabilities or values).
            current_dist: Current production prediction distribution.
            n_bins: Number of bins for discretization.

        Returns:
            ``DriftResult`` with PSI value.
        """
        if not reference_dist or not current_dist:
            return DriftResult(
                feature_name="prediction",
                drift_metric="psi",
                drift_value=0.0,
                threshold=PSI_THRESHOLD,
                is_drifted=False,
                details={"error": "empty distribution"},
            )

        ref = [float(x) for x in reference_dist]
        cur = [float(x) for x in current_dist]

        # Determine bin edges from combined data
        all_vals = ref + cur
        min_val = min(all_vals)
        max_val = max(all_vals)

        if min_val == max_val:
            # All values identical — no drift possible
            return DriftResult(
                feature_name="prediction",
                drift_metric="psi",
                drift_value=0.0,
                threshold=PSI_THRESHOLD,
                is_drifted=False,
                details={"note": "all values identical"},
            )

        bin_width = (max_val - min_val) / n_bins

        def _bin_proportions(data: list[float]) -> list[float]:
            counts = [0] * n_bins
            for v in data:
                idx = min(int((v - min_val) / bin_width), n_bins - 1)
                counts[idx] += 1
            total = len(data)
            return [max(c / total, 1e-6) for c in counts]  # avoid log(0)

        ref_props = _bin_proportions(ref)
        cur_props = _bin_proportions(cur)

        psi = 0.0
        for r_p, c_p in zip(ref_props, cur_props):
            psi += (c_p - r_p) * math.log(c_p / r_p)

        is_drifted = psi >= PSI_THRESHOLD

        if is_drifted:
            logger.warning(
                "Prediction drift detected: PSI=%.4f >= %.4f", psi, PSI_THRESHOLD
            )

        return DriftResult(
            feature_name="prediction",
            drift_metric="psi",
            drift_value=round(psi, 6),
            threshold=PSI_THRESHOLD,
            is_drifted=is_drifted,
            details={
                "n_bins": n_bins,
                "reference_size": len(ref),
                "current_size": len(cur),
                "ref_proportions": [round(p, 4) for p in ref_props],
                "cur_proportions": [round(p, 4) for p in cur_props],
            },
        )

    # ── Drift Report ────────────────────────────────────────────────────

    def generate_drift_report(self, deployment_id: str) -> dict[str, Any]:
        """
        Generate a comprehensive drift report for a deployment.

        Checks all features registered for the deployment against recent
        production data. Returns a summary with per-feature results and
        an overall drift status.

        Args:
            deployment_id: UUID of the ``ModelEndpoint`` / deployment.

        Returns:
            dict with drift results, overall status, and timestamps.
        """
        from apps.ml_platform.models import DriftReport, ModelEndpoint

        endpoint = ModelEndpoint.objects.filter(id=deployment_id).first()
        if not endpoint:
            raise ValueError(f"Deployment {deployment_id} not found")

        # Fetch stored drift reports for this deployment
        reports = DriftReport.objects.filter(
            deployment=endpoint
        ).order_by("-timestamp")[:50]

        features_drifted = 0
        features_checked = 0
        feature_results: list[dict[str, Any]] = []

        for report in reports:
            features_checked += 1
            if report.is_drifted:
                features_drifted += 1
            feature_results.append(
                {
                    "feature_name": report.feature_name,
                    "drift_metric": report.drift_metric,
                    "drift_value": report.drift_value,
                    "threshold": report.threshold,
                    "is_drifted": report.is_drifted,
                    "timestamp": report.timestamp.isoformat(),
                }
            )

        return {
            "deployment_id": str(endpoint.id),
            "deployment_name": endpoint.name,
            "model_version": (
                str(endpoint.model_version_id) if endpoint.model_version_id else None
            ),
            "features_checked": features_checked,
            "features_drifted": features_drifted,
            "overall_drifted": features_drifted > 0,
            "results": feature_results,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def check_and_alert(
        self,
        deployment_id: str,
        feature_name: str,
        drift_result: DriftResult,
        tenant_id: str,
    ) -> None:
        """
        Persist a drift result and send a notification if drift is detected.

        Creates a ``DriftReport`` record. If ``is_drifted`` is True, dispatches
        a warning notification via the notification service.
        """
        from apps.ml_platform.models import DriftReport, ModelEndpoint

        endpoint = ModelEndpoint.objects.filter(id=deployment_id).first()
        if not endpoint:
            return

        # Persist drift report
        DriftReport.objects.create(
            deployment=endpoint,
            tenant_id=tenant_id,
            feature_name=feature_name,
            drift_metric=drift_result.drift_metric,
            drift_value=drift_result.drift_value,
            threshold=drift_result.threshold,
            is_drifted=drift_result.is_drifted,
            details=drift_result.details,
        )

        # Alert if drifted
        if drift_result.is_drifted:
            try:
                from apps.notifications.services import NotificationService

                NotificationService.create(
                    tenant_id=tenant_id,
                    user_id="system",
                    title=f"Data drift detected: {endpoint.name}",
                    message=(
                        f"Feature '{feature_name}' has drifted on deployment "
                        f"'{endpoint.name}'. "
                        f"Metric: {drift_result.drift_metric} = "
                        f"{drift_result.drift_value:.4f} "
                        f"(threshold: {drift_result.threshold})."
                    ),
                    notification_type="warning",
                    resource_type="ml_deployment",
                    resource_id=str(endpoint.id),
                )
            except Exception:
                logger.debug("Failed to send drift notification", exc_info=True)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------
_detector: DriftDetector | None = None
_detector_lock = threading.Lock()


def get_drift_detector() -> DriftDetector:
    """Get or create the global DriftDetector singleton."""
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                _detector = DriftDetector()
    return _detector
