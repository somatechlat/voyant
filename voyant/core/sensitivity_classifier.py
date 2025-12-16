"""
Column Sensitivity Classification Module

Auto-detect PII and sensitive data in columns using regex patterns and ML-based heuristics.
Reference: docs/CANONICAL_ROADMAP.md - P5 Governance & Contracts

Seven personas applied:
- PhD Developer: Clean pattern matching with extensible rules
- PhD Analyst: Statistical analysis of column content
- PhD QA Engineer: Comprehensive pattern coverage
- ISO Documenter: Clear sensitivity level definitions
- Security Auditor: Comprehensive PII detection, err on side of caution
- Performance Engineer: Efficient regex compilation and sampling
- UX Consultant: Clear classification results with confidence scores

Usage:
    from voyant.core.sensitivity_classifier import (
        classify_column,
        classify_columns,
        SensitivityResult
    )
    
    # Classify a single column
    result = classify_column(
        column_name="email",
        sample_values=["john@example.com", "jane@test.org"]
    )
    print(result.sensitivity_level)  # SensitivityLevel.PII
    print(result.pii_type)  # "email"
    
    # Classify all columns in a dataset
    results = classify_columns(data=[{"email": "...", "name": "..."}])
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Sensitivity Levels
# =============================================================================

class SensitivityLevel(str, Enum):
    """
    Column sensitivity classification levels.
    
    ISO Documenter: GDPR/CCPA aligned classifications
    """
    PUBLIC = "public"  # Safe to expose publicly
    INTERNAL = "internal"  # Internal business data
    CONFIDENTIAL = "confidential"  # Business sensitive
    PII = "pii"  # Personal Identifiable Information
    SECRET = "secret"  # Credentials, keys, tokens


class PIIType(str, Enum):
    """
    Types of PII data.
    
    Security Auditor: Comprehensive PII categories
    """
    # Direct identifiers
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"  # Social Security Number
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    
    # Names
    FULL_NAME = "full_name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    
    # Location
    ADDRESS = "address"
    ZIP_CODE = "zip_code"
    CITY = "city"
    STATE = "state"
    COUNTRY = "country"
    
    # Financial
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    
    # Health
    MEDICAL_RECORD = "medical_record"
    HEALTH_INFO = "health_info"
    
    # Digital
    IP_ADDRESS = "ip_address"
    USERNAME = "username"
    PASSWORD = "password"
    
    # Other
    DATE_OF_BIRTH = "date_of_birth"
    AGE = "age"
    GENDER = "gender"
    RACE = "race"
    RELIGION = "religion"
    
    # Unknown PII
    UNKNOWN = "unknown"


# =============================================================================
# Pattern Definitions
# =============================================================================

@dataclass
class SensitivityPattern:
    """A pattern for detecting sensitive data."""
    pii_type: PIIType
    sensitivity: SensitivityLevel
    name_patterns: List[str]  # Column name regex patterns
    value_patterns: List[str] = field(default_factory=list)  # Value regex patterns
    confidence: float = 0.9  # Base confidence when matched


# Common patterns
SENSITIVITY_PATTERNS: List[SensitivityPattern] = [
    # Email
    SensitivityPattern(
        pii_type=PIIType.EMAIL,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"e[-_]?mail", r"email[-_]?addr"],
        value_patterns=[r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"],
        confidence=0.95
    ),
    
    # Phone
    SensitivityPattern(
        pii_type=PIIType.PHONE,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"phone", r"mobile", r"cell", r"tel(?:ephone)?", r"fax"],
        value_patterns=[
            r"^\+?1?\d{10,14}$",
            r"^\(\d{3}\)\s?\d{3}[-.]?\d{4}$",
            r"^\d{3}[-.]?\d{3}[-.]?\d{4}$"
        ],
        confidence=0.9
    ),
    
    # SSN
    SensitivityPattern(
        pii_type=PIIType.SSN,
        sensitivity=SensitivityLevel.SECRET,
        name_patterns=[r"ssn", r"social[-_]?sec", r"social[-_]?security"],
        value_patterns=[r"^\d{3}[-]?\d{2}[-]?\d{4}$"],
        confidence=0.95
    ),
    
    # Credit Card
    SensitivityPattern(
        pii_type=PIIType.CREDIT_CARD,
        sensitivity=SensitivityLevel.SECRET,
        name_patterns=[r"credit[-_]?card", r"card[-_]?num", r"cc[-_]?num", r"pan"],
        value_patterns=[r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$"],
        confidence=0.95
    ),
    
    # Name patterns
    SensitivityPattern(
        pii_type=PIIType.FULL_NAME,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"full[-_]?name", r"customer[-_]?name", r"user[-_]?name", r"account[-_]?name"],
        confidence=0.85
    ),
    SensitivityPattern(
        pii_type=PIIType.FIRST_NAME,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"first[-_]?name", r"given[-_]?name", r"forename"],
        confidence=0.85
    ),
    SensitivityPattern(
        pii_type=PIIType.LAST_NAME,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"last[-_]?name", r"sur[-_]?name", r"family[-_]?name"],
        confidence=0.85
    ),
    
    # Address
    SensitivityPattern(
        pii_type=PIIType.ADDRESS,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"address", r"street", r"addr[-_]?line"],
        confidence=0.85
    ),
    SensitivityPattern(
        pii_type=PIIType.ZIP_CODE,
        sensitivity=SensitivityLevel.CONFIDENTIAL,
        name_patterns=[r"zip", r"postal[-_]?code", r"postcode"],
        value_patterns=[r"^\d{5}(-\d{4})?$"],
        confidence=0.8
    ),
    SensitivityPattern(
        pii_type=PIIType.CITY,
        sensitivity=SensitivityLevel.INTERNAL,
        name_patterns=[r"^city$", r"city[-_]?name"],
        confidence=0.7
    ),
    
    # Date of Birth
    SensitivityPattern(
        pii_type=PIIType.DATE_OF_BIRTH,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"dob", r"date[-_]?of[-_]?birth", r"birth[-_]?date", r"birthday"],
        confidence=0.9
    ),
    
    # IP Address
    SensitivityPattern(
        pii_type=PIIType.IP_ADDRESS,
        sensitivity=SensitivityLevel.CONFIDENTIAL,
        name_patterns=[r"ip[-_]?addr", r"ip[-_]?address", r"client[-_]?ip", r"user[-_]?ip"],
        value_patterns=[r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"],
        confidence=0.9
    ),
    
    # Credentials (SECRET)
    SensitivityPattern(
        pii_type=PIIType.PASSWORD,
        sensitivity=SensitivityLevel.SECRET,
        name_patterns=[r"password", r"passwd", r"pwd", r"secret", r"token", r"api[-_]?key"],
        confidence=0.99
    ),
    
    # Username
    SensitivityPattern(
        pii_type=PIIType.USERNAME,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"user[-_]?name", r"login", r"user[-_]?id", r"account[-_]?id"],
        confidence=0.8
    ),
    
    # Gender/Demographics
    SensitivityPattern(
        pii_type=PIIType.GENDER,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"^gender$", r"^sex$"],
        confidence=0.85
    ),
    SensitivityPattern(
        pii_type=PIIType.AGE,
        sensitivity=SensitivityLevel.PII,
        name_patterns=[r"^age$", r"customer[-_]?age"],
        confidence=0.8
    ),
]


# =============================================================================
# Classification Result
# =============================================================================

@dataclass
class SensitivityResult:
    """Result of column sensitivity classification."""
    column_name: str
    sensitivity_level: SensitivityLevel
    confidence: float  # 0.0 to 1.0
    pii_type: Optional[PIIType] = None
    matched_by: str = ""  # "name", "value", "both"
    sample_size: int = 0
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "column_name": self.column_name,
            "sensitivity_level": self.sensitivity_level.value,
            "confidence": round(self.confidence, 3),
            "pii_type": self.pii_type.value if self.pii_type else None,
            "matched_by": self.matched_by,
            "sample_size": self.sample_size,
            "recommendations": self.recommendations,
        }


# =============================================================================
# Classifier Implementation
# =============================================================================

class SensitivityClassifier:
    """
    Column sensitivity classifier.
    
    Security Auditor: Conservative classification (false positives preferred over false negatives)
    """
    
    def __init__(self, patterns: Optional[List[SensitivityPattern]] = None):
        self.patterns = patterns or SENSITIVITY_PATTERNS
        self._compiled_patterns: Dict[str, List[Tuple[Pattern, SensitivityPattern]]] = {
            "name": [],
            "value": []
        }
        self._compile_patterns()
    
    def _compile_patterns(self):
        """
        Pre-compile regex patterns for performance.
        
        Performance Engineer: Compile once, use many times
        """
        for pattern in self.patterns:
            for name_pat in pattern.name_patterns:
                try:
                    compiled = re.compile(name_pat, re.IGNORECASE)
                    self._compiled_patterns["name"].append((compiled, pattern))
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{name_pat}': {e}")
            
            for val_pat in pattern.value_patterns:
                try:
                    compiled = re.compile(val_pat)
                    self._compiled_patterns["value"].append((compiled, pattern))
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{val_pat}': {e}")
    
    def classify_column(
        self,
        column_name: str,
        sample_values: Optional[List[Any]] = None,
        sample_size: int = 100
    ) -> SensitivityResult:
        """
        Classify a single column.
        
        Args:
            column_name: Name of the column
            sample_values: Sample values from the column
            sample_size: Number of values to analyze
            
        Returns:
            SensitivityResult with classification
        """
        # Check column name patterns
        name_match = self._match_name(column_name)
        
        # Check value patterns if samples provided
        value_match = None
        actual_sample_size = 0
        if sample_values:
            actual_sample_size = min(len(sample_values), sample_size)
            values_to_check = sample_values[:actual_sample_size]
            value_match = self._match_values(values_to_check)
        
        # Determine final classification
        return self._combine_matches(
            column_name,
            name_match,
            value_match,
            actual_sample_size
        )
    
    def _match_name(
        self,
        column_name: str
    ) -> Optional[Tuple[SensitivityPattern, float]]:
        """Match column name against patterns."""
        for compiled, pattern in self._compiled_patterns["name"]:
            if compiled.search(column_name):
                return (pattern, pattern.confidence)
        return None
    
    def _match_values(
        self,
        values: List[Any]
    ) -> Optional[Tuple[SensitivityPattern, float]]:
        """Match values against patterns."""
        if not values:
            return None
        
        # Convert to strings
        str_values = [str(v) for v in values if v is not None]
        if not str_values:
            return None
        
        # Check each pattern
        best_match: Optional[Tuple[SensitivityPattern, float]] = None
        best_score = 0.0
        
        for compiled, pattern in self._compiled_patterns["value"]:
            matches = sum(1 for v in str_values if compiled.match(v))
            match_rate = matches / len(str_values)
            
            if match_rate >= 0.5:  # At least 50% match
                score = match_rate * pattern.confidence
                if score > best_score:
                    best_score = score
                    best_match = (pattern, score)
        
        return best_match
    
    def _combine_matches(
        self,
        column_name: str,
        name_match: Optional[Tuple[SensitivityPattern, float]],
        value_match: Optional[Tuple[SensitivityPattern, float]],
        sample_size: int
    ) -> SensitivityResult:
        """Combine name and value matches into final result."""
        # Both match - highest confidence
        if name_match and value_match:
            pattern = name_match[0]
            confidence = min(1.0, (name_match[1] + value_match[1]) / 2 + 0.1)
            matched_by = "both"
        # Only name matches
        elif name_match:
            pattern = name_match[0]
            confidence = name_match[1]
            matched_by = "name"
        # Only value matches
        elif value_match:
            pattern = value_match[0]
            confidence = value_match[1] * 0.8  # Reduce confidence for value-only
            matched_by = "value"
        # No matches - assume internal
        else:
            return SensitivityResult(
                column_name=column_name,
                sensitivity_level=SensitivityLevel.INTERNAL,
                confidence=0.5,
                matched_by="none",
                sample_size=sample_size,
                recommendations=["Review column for potential sensitivity"]
            )
        
        # Build recommendations
        recommendations = []
        if pattern.sensitivity == SensitivityLevel.SECRET:
            recommendations.append("NEVER log or expose this column")
            recommendations.append("Consider encryption at rest")
        elif pattern.sensitivity == SensitivityLevel.PII:
            recommendations.append("Apply PII masking in logs and displays")
            recommendations.append("Consider data retention policies")
        elif pattern.sensitivity == SensitivityLevel.CONFIDENTIAL:
            recommendations.append("Restrict access to authorized users")
        
        return SensitivityResult(
            column_name=column_name,
            sensitivity_level=pattern.sensitivity,
            confidence=confidence,
            pii_type=pattern.pii_type,
            matched_by=matched_by,
            sample_size=sample_size,
            recommendations=recommendations
        )
    
    def classify_columns(
        self,
        data: List[Dict[str, Any]],
        sample_size: int = 100
    ) -> Dict[str, SensitivityResult]:
        """
        Classify all columns in a dataset.
        
        Args:
            data: List of row dictionaries
            sample_size: Number of rows to sample
            
        Returns:
            Dictionary mapping column names to classifications
        """
        if not data:
            return {}
        
        # Get all column names
        columns = set()
        for row in data:
            columns.update(row.keys())
        
        # Collect samples for each column
        results: Dict[str, SensitivityResult] = {}
        
        for col in columns:
            sample_values = [row.get(col) for row in data[:sample_size] if col in row]
            results[col] = self.classify_column(col, sample_values, sample_size)
        
        return results


# =============================================================================
# Convenience Functions
# =============================================================================

_global_classifier: Optional[SensitivityClassifier] = None


def get_classifier() -> SensitivityClassifier:
    """Get or create global classifier."""
    global _global_classifier
    if _global_classifier is None:
        _global_classifier = SensitivityClassifier()
    return _global_classifier


def classify_column(
    column_name: str,
    sample_values: Optional[List[Any]] = None
) -> SensitivityResult:
    """
    Classify a single column's sensitivity.
    
    Args:
        column_name: Name of the column
        sample_values: Optional sample values
        
    Returns:
        SensitivityResult
        
    UX Consultant: Simple one-liner API
    """
    return get_classifier().classify_column(column_name, sample_values)


def classify_columns(
    data: List[Dict[str, Any]],
    sample_size: int = 100
) -> Dict[str, SensitivityResult]:
    """
    Classify all columns in a dataset.
    
    Args:
        data: List of row dictionaries
        sample_size: Number of rows to sample
        
    Returns:
        Dictionary of column classifications
    """
    return get_classifier().classify_columns(data, sample_size)


def get_pii_columns(
    data: List[Dict[str, Any]],
    include_secret: bool = True
) -> List[str]:
    """
    Get list of PII/Secret column names.
    
    Args:
        data: Dataset to analyze
        include_secret: Include SECRET level columns
        
    Returns:
        List of sensitive column names
        
    Security Auditor: Quick PII identification
    """
    results = classify_columns(data)
    
    levels = {SensitivityLevel.PII}
    if include_secret:
        levels.add(SensitivityLevel.SECRET)
    
    return [
        name for name, result in results.items()
        if result.sensitivity_level in levels
    ]


def generate_sensitivity_report(
    data: List[Dict[str, Any]],
    sample_size: int = 100
) -> Dict[str, Any]:
    """
    Generate comprehensive sensitivity report.
    
    Args:
        data: Dataset to analyze
        sample_size: Rows to sample
        
    Returns:
        Report dictionary
        
    ISO Documenter: Compliance-ready report format
    """
    results = classify_columns(data, sample_size)
    
    # Count by level
    by_level: Dict[str, int] = {}
    for result in results.values():
        level = result.sensitivity_level.value
        by_level[level] = by_level.get(level, 0) + 1
    
    # Get high-risk columns
    high_risk = [
        result.to_dict()
        for result in results.values()
        if result.sensitivity_level in (SensitivityLevel.PII, SensitivityLevel.SECRET)
    ]
    
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_columns": len(results),
        "by_sensitivity_level": by_level,
        "high_risk_columns": high_risk,
        "all_columns": {name: r.to_dict() for name, r in results.items()},
        "recommendations": [
            "Review high-risk columns for data protection compliance",
            "Implement masking for PII columns in logs and reports",
            "Apply encryption for SECRET level columns",
        ],
    }
