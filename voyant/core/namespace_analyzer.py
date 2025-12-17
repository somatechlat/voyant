"""
Table Namespace Analyzer

Enforces tenant isolation by validating table access patterns.
Reference: docs/CANONICAL_ROADMAP.md - P4 Scale & Multi-Tenant

Seven personas applied:
- PhD Developer: Configurable namespace patterns
- PhD Analyst: Clear validation errors
- PhD QA Engineer: Strict negative testing
- ISO Documenter: Security controls documentation
- Security Auditor: Prevent IDOR and cross-tenant data leakage
- Performance Engineer: Fast regex validation (linting)
- UX Consultant: Helpful error messages

Usage:
    from voyant.core.namespace_analyzer import NamespaceAnalyzer, NamespaceConfig
    
    analyzer = NamespaceAnalyzer()
    analyzer.validate_access(tenant_id="t123", table_name="t123_orders")
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Pattern

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class IsolationMode(str, Enum):
    """Tenant isolation modes."""
    PREFIX = "prefix"  # Tables must start with tenant_id prefix
    SCHEMA = "schema"  # Tables must be in tenant schema (schema.table)
    METADATA = "metadata" # Check against allowed list (implementation specific)


@dataclass
class NamespaceConfig:
    """
    Configuration for namespace enforcement.
    
    Security Auditor: Strict defaults
    """
    mode: IsolationMode = IsolationMode.PREFIX
    separator: str = "_"
    strict: bool = True  # Raise exception on violation
    
    # Custom pattern override
    # If set, validation checks if re.match(pattern, table_name) is true
    custom_pattern: Optional[str] = None


class NamespaceViolationError(Exception):
    """Raised when namespace validation fails."""
    pass


# =============================================================================
# Analyzer
# =============================================================================

class NamespaceAnalyzer:
    """
    Validates resource access against tenant namespace configurations.
    
    PhD Developer: Stateless validator
    """
    
    def __init__(self, config: Optional[NamespaceConfig] = None):
        self.config = config or NamespaceConfig()
        self._compiled_pattern: Optional[Pattern] = None
        
        if self.config.custom_pattern:
            self._compiled_pattern = re.compile(self.config.custom_pattern)
            
    def validate_access(self, tenant_id: str, table_name: str) -> bool:
        """
        Validate that a tenant is allowed to access a table.
        
        Args:
            tenant_id: Tenant claiming access
            table_name: Resource being accessed
            
        Returns:
            True if allowed
            
        Raises:
            NamespaceViolationError if strict mode and violation
            
        Security Auditor: Core IDOR prevention logic
        """
        if not tenant_id or not table_name:
            if self.config.strict:
                raise ValueError("tenant_id and table_name required")
            return False

        allowed = False
        
        # 1. Custom Pattern Check
        if self._compiled_pattern:
            if self._compiled_pattern.match(table_name):
                # Pattern must imply tenant ownership or be generic
                # Ideally pattern should contain the tenant_id. 
                # For custom, we assume the pattern enables multi-tenancy correctly.
                allowed = True
            else:
                allowed = False
        
        # 2. Prefix Mode (Default)
        # Expects: {tenant_id}{separator}{anything}
        elif self.config.mode == IsolationMode.PREFIX:
            prefix = f"{tenant_id}{self.config.separator}"
            if table_name.startswith(prefix):
                allowed = True
            else:
                allowed = False
                
        # 3. Schema Mode
        # Expects: {tenant_id}.{table}
        elif self.config.mode == IsolationMode.SCHEMA:
            parts = table_name.split(".", 1)
            if len(parts) == 2 and parts[0] == tenant_id:
                allowed = True
            else:
                allowed = False
        
        # 4. Metadata Mode
        # Placeholder for external lookup
        elif self.config.mode == IsolationMode.METADATA:
            # In a real impl, this would query a catalog
            logger.warning("Metadata isolation mode not fully implemented, failing closed")
            allowed = False

        if not allowed:
            msg = (
                f"Access denied: Table '{table_name}' does not match namespace "
                f"rules for tenant '{tenant_id}' (Mode: {self.config.mode.value})"
            )
            logger.warning(f"Namespace violation: {msg}")
            
            if self.config.strict:
                raise NamespaceViolationError(msg)
            
            return False
            
        return True

    def get_allowed_prefix(self, tenant_id: str) -> str:
        """Get the expected table prefix for a tenant."""
        if self.config.mode == IsolationMode.PREFIX:
            return f"{tenant_id}{self.config.separator}"
        elif self.config.mode == IsolationMode.SCHEMA:
            return f"{tenant_id}."
        return ""


# =============================================================================
# Global Instance
# =============================================================================

_analyzer: Optional[NamespaceAnalyzer] = None


def get_namespace_analyzer(config: Optional[NamespaceConfig] = None) -> NamespaceAnalyzer:
    """Get global analyzer instance."""
    global _analyzer
    if _analyzer is None or config is not None:
        _analyzer = NamespaceAnalyzer(config)
    return _analyzer


def validate_table_access(tenant_id: str, table_name: str):
    """
    Convenience wrapper to validate access.
    Raises NamespaceViolationError on failure.
    """
    get_namespace_analyzer().validate_access(tenant_id, table_name)
    
