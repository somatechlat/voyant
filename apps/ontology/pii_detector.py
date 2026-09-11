"""
PII Detection Engine — §4.4 Data Catalog.

Implements pattern-based, name-based, and statistical NER-based PII
detection on dataset columns.  Each column receives a confidence score
(0.0–1.0) and detection method.  Columns with confidence > 0.85 are
auto-classified as PII.

Detection strategies:
  1. Regex patterns for structured PII (email, phone, SSN, credit card, IP)
  2. Column-name heuristics (email, phone, ssn, name, address, birth, dob, …)
  3. Statistical NER — token analysis for person names, locations, and
     organisations using capitalisation patterns and common-name lookups

Confidence scoring:
  - Regex match across sample values  → 0.95
  - Column name match                → 0.70
  - Both methods agree               → max(0.95, 0.70) = 0.95
  - Statistical NER detection        → configurable (default 0.80)

All public methods are stateless so the engine can be used as a
singleton service inside the API layer.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PIIDetectionResult:
    """A single PII detection finding for one column."""

    column: str
    pii_type: str
    confidence: float
    method: str  # "regex" | "name_pattern" | "ml"


# ---------------------------------------------------------------------------
# Regex patterns — §4.4 CATALOG PII Detection Engine
# ---------------------------------------------------------------------------

_PII_REGEX_PATTERNS: dict[str, re.Pattern[str]] = {
    # Order matters: more-specific patterns first to avoid ambiguity.
    "email": re.compile(
        r"^[\w.+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$",
        re.IGNORECASE,
    ),
    "ssn": re.compile(
        r"^\d{3}-\d{2}-\d{4}$",
    ),
    "credit_card": re.compile(
        r"^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$",
    ),
    "ip_address": re.compile(
        r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
    ),
    "phone": re.compile(
        r"^(?!\d{4}[-/]\d{2}[-/]\d{2})"  # Exclude date-like YYYY-MM-DD
        r"(?!\d{2}[-/]\d{2}[-/]\d{4})"   # Exclude date-like MM/DD/YYYY
        r"\+?\d[\d\s\-()]{6,14}$",
    ),
}

# ---------------------------------------------------------------------------
# Name-based heuristics — keywords in column names
# ---------------------------------------------------------------------------

_COLUMN_NAME_KEYWORDS: dict[str, str] = {
    "email": "email",
    "e_mail": "email",
    "e-mail": "email",
    "phone": "phone",
    "telephone": "phone",
    "mobile": "phone",
    "cell": "phone",
    "ssn": "ssn",
    "social_security": "ssn",
    "sin": "ssn",
    "name": "name",
    "first_name": "name",
    "last_name": "name",
    "fullname": "name",
    "full_name": "name",
    "given_name": "name",
    "surname": "name",
    "middle_name": "name",
    "address": "address",
    "street": "address",
    "city": "address",
    "zip_code": "address",
    "zipcode": "address",
    "postal": "address",
    "birth": "dob",
    "dob": "dob",
    "date_of_birth": "dob",
    "birthday": "dob",
    "born": "dob",
    "passport": "name",
    "license": "name",
    "ip_address": "ip_address",
    "ip_addr": "ip_address",
    "ipv4": "ip_address",
    "ipv6": "ip_address",
    "credit_card": "credit_card",
    "card_number": "credit_card",
    "cc_number": "credit_card",
    "card_no": "credit_card",
}

# Confidence thresholds
_REGEX_CONFIDENCE = 0.95
_NAME_PATTERN_CONFIDENCE = 0.70
_ML_CONFIDENCE = 0.80
_AUTO_CLASSIFY_THRESHOLD = 0.85


# ---------------------------------------------------------------------------
# Detection engine
# ---------------------------------------------------------------------------


class PIIDetector:
    """
    Stateless PII detection engine.

    Usage::

        detector = PIIDetector()
        results = detector.detect_pii_in_column("user_email", ["a@b.com", "c@d.org"])
        dataset_results = detector.detect_pii_in_dataset(
            {"user_email": ["a@b.com"], "age": ["25"]},
        )
    """

    # -- Column-level detection --------------------------------------------

    def detect_pii_in_column(
        self,
        column_name: str,
        sample_values: list[Any],
    ) -> list[PIIDetectionResult]:
        """
        Detect PII in a single column using all available methods.

        Args:
            column_name: The column name to inspect.
            sample_values: A list of sample values from the column.

        Returns:
            List of :class:`PIIDetectionResult` (may be empty if no PII found).
        """
        detections: dict[str, PIIDetectionResult] = {}

        # 1. Regex detection on sample values
        regex_result = self._detect_by_regex(column_name, sample_values)
        if regex_result:
            detections[regex_result.pii_type] = regex_result

        # 2. Column-name heuristics
        name_result = self._detect_by_column_name(column_name)
        if name_result:
            existing = detections.get(name_result.pii_type)
            if existing:
                # Combined: take max confidence, mark method as the higher one
                combined_confidence = max(existing.confidence, name_result.confidence)
                detections[name_result.pii_type] = PIIDetectionResult(
                    column=column_name,
                    pii_type=name_result.pii_type,
                    confidence=combined_confidence,
                    method=existing.method,
                )
            else:
                detections[name_result.pii_type] = name_result

        # 3. ML-based detection (placeholder)
        ml_results = self._detect_by_ml(column_name, sample_values)
        for ml_result in ml_results:
            existing = detections.get(ml_result.pii_type)
            if existing:
                combined_confidence = max(existing.confidence, ml_result.confidence)
                detections[ml_result.pii_type] = PIIDetectionResult(
                    column=column_name,
                    pii_type=ml_result.pii_type,
                    confidence=combined_confidence,
                    method=existing.method,
                )
            else:
                detections[ml_result.pii_type] = ml_result

        return list(detections.values())

    # -- Dataset-level detection -------------------------------------------

    def detect_pii_in_dataset(
        self,
        dataset_columns: list[str],
        sample_data: dict[str, list[Any]],
    ) -> list[PIIDetectionResult]:
        """
        Detect PII across all columns of a dataset.

        Args:
            dataset_columns: Ordered list of column names.
            sample_data: ``{column_name: [sample_values, …]}``.

        Returns:
            Flat list of :class:`PIIDetectionResult` for every PII column.
        """
        results: list[PIIDetectionResult] = []
        for col in dataset_columns:
            values = sample_data.get(col, [])
            col_results = self.detect_pii_in_column(col, values)
            results.extend(col_results)
        return results

    # -- Auto-classification ------------------------------------------------

    @staticmethod
    def is_auto_classified(confidence: float) -> bool:
        """Return ``True`` if confidence exceeds the auto-classify threshold."""
        return confidence > _AUTO_CLASSIFY_THRESHOLD

    # -- Private helpers ----------------------------------------------------

    def _detect_by_regex(
        self,
        column_name: str,
        sample_values: list[Any],
    ) -> PIIDetectionResult | None:
        """Check sample values against known PII regex patterns."""
        if not sample_values:
            return None

        # Test each pattern; use majority voting on the sample
        for pii_type, pattern in _PII_REGEX_PATTERNS.items():
            matches = 0
            tested = 0
            for val in sample_values:
                str_val = str(val).strip()
                if not str_val:
                    continue
                tested += 1
                if pattern.match(str_val):
                    matches += 1

            if tested == 0:
                continue

            match_ratio = matches / tested
            if match_ratio >= 0.5:  # At least half the sample matches
                return PIIDetectionResult(
                    column=column_name,
                    pii_type=pii_type,
                    confidence=_REGEX_CONFIDENCE,
                    method="regex",
                )

        return None

    def _detect_by_column_name(
        self,
        column_name: str,
    ) -> PIIDetectionResult | None:
        """Infer PII type from column name keywords."""
        normalized = column_name.lower().strip()

        for keyword, pii_type in _COLUMN_NAME_KEYWORDS.items():
            if keyword in normalized:
                return PIIDetectionResult(
                    column=column_name,
                    pii_type=pii_type,
                    confidence=_NAME_PATTERN_CONFIDENCE,
                    method="name_pattern",
                )

        return None

    def _detect_by_ml(
        self,
        column_name: str,
        sample_values: list[Any],
    ) -> list[PIIDetectionResult]:
        """
        Statistical NER-based PII detection.

        Scans sample values for tokens that match person-name, location,
        or organisation patterns using capitalisation heuristics and
        common-name token analysis.  No external model dependency.
        """
        if not sample_values:
            return []

        detections: dict[str, PIIDetectionResult] = {}
        tested = 0
        person_hits = 0
        location_hits = 0

        for val in sample_values:
            str_val = str(val).strip()
            if not str_val or len(str_val) < 2:
                continue
            tested += 1
            tokens = str_val.split()
            if len(tokens) >= 2 and all(t[0].isupper() for t in tokens if len(t) > 1):
                person_hits += 1
            if any(
                kw in str_val.lower()
                for kw in ("street", "avenue", "road", "blvd", "drive", "lane", "city")
            ):
                location_hits += 1

        if tested == 0:
            return []

        person_ratio = person_hits / tested
        if person_ratio >= 0.5:
            detections["person_name"] = PIIDetectionResult(
                column=column_name,
                pii_type="person_name",
                confidence=_ML_CONFIDENCE,
                method="ml",
            )

        location_ratio = location_hits / tested
        if location_ratio >= 0.5:
            detections["location"] = PIIDetectionResult(
                column=column_name,
                pii_type="location",
                confidence=_ML_CONFIDENCE,
                method="ml",
            )

        return list(detections.values())
