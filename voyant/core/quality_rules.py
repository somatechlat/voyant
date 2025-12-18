"""
Data Quality Rules Engine

Declarative validation for tabular data.
Reference: docs/CANONICAL_ARCHITECTURE.md - Data Governance

Personas:
- PhD Developer: Protocol-based rule definition
- ISO Documenter: Traceable validation failure reasons
- QA Engineer: Fail-fast validation
"""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of a quality rule check."""
    rule_name: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule_name,
            "passed": self.passed,
            "details": self.details
        }

class QualityRule(abc.ABC):
    """Abstract base class for quality rules."""
    
    def __init__(self, column: str):
        self.column = column

    @abc.abstractmethod
    def check(self, df: pd.DataFrame) -> ValidationResult:
        """Run the check against a dataframe."""
        pass
    
    def get_name(self) -> str:
        return f"{self.__class__.__name__}({self.column})"

class NullCheck(QualityRule):
    """Fail if null percentage exceeds threshold (0.0 to 1.0)."""
    
    def __init__(self, column: str, max_null_pct: float = 0.0):
        super().__init__(column)
        self.max_null_pct = max_null_pct
        
    def check(self, df: pd.DataFrame) -> ValidationResult:
        if self.column not in df.columns:
            return ValidationResult(self.get_name(), False, {"error": "Column not found"})
            
        total = len(df)
        if total == 0:
             return ValidationResult(self.get_name(), True, {"reason": "Empty dataset"})
             
        null_count = df[self.column].isnull().sum()
        null_pct = null_count / total
        
        passed = null_pct <= self.max_null_pct
        
        return ValidationResult(
            self.get_name(),
            passed,
            {
                "null_count": int(null_count), 
                "null_pct": float(null_pct),
                "threshold": self.max_null_pct
            }
        )

class RangeCheck(QualityRule):
    """Fail if values outside [min, max]."""
    
    def __init__(self, column: str, min_val: Optional[float] = None, max_val: Optional[float] = None):
        super().__init__(column)
        self.min_val = min_val
        self.max_val = max_val
        
    def check(self, df: pd.DataFrame) -> ValidationResult:
        if self.column not in df.columns:
            return ValidationResult(self.get_name(), False, {"error": "Column not found"})
        
        # Filter for non-null numeric values
        series = pd.to_numeric(df[self.column], errors='coerce').dropna()
        if series.empty:
             return ValidationResult(self.get_name(), True, {"reason": "No numeric values"})
        
        failures = 0
        if self.min_val is not None:
            failures += (series < self.min_val).sum()
            
        if self.max_val is not None:
            failures += (series > self.max_val).sum()
            
        return ValidationResult(
            self.get_name(),
            failures == 0,
            {
                "failures": int(failures),
                "min_checked": self.min_val,
                "max_checked": self.max_val
            }
        )

class UniqueCheck(QualityRule):
    """Fail if duplicates found."""
    
    def __init__(self, column: str):
        super().__init__(column)
        
    def check(self, df: pd.DataFrame) -> ValidationResult:
        if self.column not in df.columns:
            return ValidationResult(self.get_name(), False, {"error": "Column not found"})
            
        total = len(df)
        unique = df[self.column].nunique()
        # Note: nunique ignores NaNs by default. 
        # If we want strict uniqueness including NaNs, we'd need len(df[col].unique())
        # But usually unique constraints imply non-null or allow one null.
        # Let's check duplicates directly.
        
        dupes = df.duplicated(subset=[self.column]).sum()
        
        return ValidationResult(
            self.get_name(),
            dupes == 0,
            {"duplicates": int(dupes), "total": total}
        )

class QualityEngine:
    """Executes a suite of rules."""
    
    def __init__(self, rules: List[QualityRule]):
        self.rules = rules
        
    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run all checks and return summary."""
        results = [rule.check(df) for rule in self.rules]
        
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        
        return {
            "total_checks": len(results),
            "passed": passed_count,
            "failed": failed_count,
            "is_valid": failed_count == 0,
            "results": [r.to_dict() for r in results]
        }
