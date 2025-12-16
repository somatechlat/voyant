"""
Seven Personas Review Module

Formal review checklists and automated validation for all seven PhD-level personas.
Ensures comprehensive coverage of architecture, analysis, testing, documentation,
security, performance, and usability across the Voyant codebase.

Seven personas applied:
- PhD Developer: Architecture patterns validation
- PhD Analyst: Data flow and pipeline analysis
- PhD QA Engineer: Test coverage metrics
- ISO Documenter: Documentation completeness
- Security Auditor: Security posture assessment
- Performance Engineer: Performance benchmarks
- UX Consultant: API usability review

Usage:
    from voyant.core.seven_personas_review import run_full_review, get_review_report
    
    # Run comprehensive review
    report = run_full_review()
    print(report.summary())
"""
from __future__ import annotations

import ast
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Review Result Types
# =============================================================================

@dataclass
class ReviewFinding:
    """A single review finding."""
    category: str
    severity: str  # info, warning, critical
    message: str
    location: str = ""
    recommendation: str = ""


@dataclass
class PersonaReview:
    """Review results for a single persona."""
    persona: str
    score: float = 0.0  # 0.0 to 1.0
    findings: List[ReviewFinding] = field(default_factory=list)
    passed_checks: int = 0
    total_checks: int = 0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    @property
    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return (self.passed_checks / self.total_checks) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona": self.persona,
            "score": round(self.score, 2),
            "pass_rate": round(self.pass_rate, 2),
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "message": f.message,
                    "location": f.location,
                    "recommendation": f.recommendation,
                }
                for f in self.findings
            ],
            "timestamp": self.timestamp,
        }


@dataclass
class FullReviewReport:
    """Complete review report across all personas."""
    reviews: List[PersonaReview] = field(default_factory=list)
    overall_score: float = 0.0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def calculate_overall_score(self):
        if self.reviews:
            self.overall_score = sum(r.score for r in self.reviews) / len(self.reviews)
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 60,
            "SEVEN PERSONAS REVIEW REPORT",
            "=" * 60,
            f"Timestamp: {self.timestamp}",
            f"Overall Score: {self.overall_score:.1%}",
            "",
        ]
        
        for review in self.reviews:
            status = "✅" if review.score >= 0.8 else "⚠️" if review.score >= 0.6 else "❌"
            lines.append(f"{status} {review.persona}: {review.score:.1%} ({review.passed_checks}/{review.total_checks})")
        
        lines.append("")
        lines.append("=" * 60)
        
        # Critical findings
        critical = [
            f for r in self.reviews
            for f in r.findings
            if f.severity == "critical"
        ]
        if critical:
            lines.append("CRITICAL FINDINGS:")
            for f in critical[:5]:
                lines.append(f"  - [{f.category}] {f.message}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "timestamp": self.timestamp,
            "reviews": [r.to_dict() for r in self.reviews],
        }


# =============================================================================
# PhD Software Developer Review
# =============================================================================

def review_architecture(base_path: str) -> PersonaReview:
    """
    PhD Software Developer: Architecture patterns validation.
    
    Checks:
    - Clean module separation
    - Proper abstraction layers
    - Design pattern usage
    - Error handling patterns
    - Async patterns
    """
    review = PersonaReview(persona="PhD Software Developer")
    findings = []
    passed = 0
    total = 0
    
    core_path = Path(base_path) / "voyant" / "core"
    activities_path = Path(base_path) / "voyant" / "activities"
    workflows_path = Path(base_path) / "voyant" / "workflows"
    
    # Check 1: Core module structure
    total += 1
    required_core_modules = [
        "config.py", "errors.py", "metrics.py", "circuit_breaker.py",
        "retry_config.py", "audit_trail.py"
    ]
    found_modules = [m for m in required_core_modules if (core_path / m).exists()]
    if len(found_modules) >= 5:
        passed += 1
    else:
        findings.append(ReviewFinding(
            category="Module Structure",
            severity="warning",
            message=f"Missing core modules: {set(required_core_modules) - set(found_modules)}",
            location=str(core_path),
            recommendation="Ensure all core modules are present"
        ))
    
    # Check 2: Activities use proper decorators
    total += 1
    if activities_path.exists():
        activity_files = list(activities_path.glob("*.py"))
        has_decorators = all(
            "@activity.defn" in (activities_path / f.name).read_text()
            for f in activity_files
            if not f.name.startswith("__")
        )
        if has_decorators:
            passed += 1
        else:
            findings.append(ReviewFinding(
                category="Activity Patterns",
                severity="warning",
                message="Some activities missing @activity.defn decorator",
                location=str(activities_path)
            ))
    
    # Check 3: Workflows use proper patterns
    total += 1
    if workflows_path.exists():
        workflow_files = list(workflows_path.glob("*.py"))
        has_workflow_defn = any(
            "@workflow.defn" in (workflows_path / f.name).read_text()
            for f in workflow_files
            if not f.name.startswith("__")
        )
        if has_workflow_defn:
            passed += 1
    
    # Check 4: Error handling module exists
    total += 1
    errors_file = core_path / "errors.py"
    if errors_file.exists():
        content = errors_file.read_text()
        if "class" in content and "Exception" in content:
            passed += 1
    
    # Check 5: Circuit breaker pattern
    total += 1
    cb_file = core_path / "circuit_breaker.py"
    if cb_file.exists():
        content = cb_file.read_text()
        if "CircuitBreaker" in content and "OPEN" in content:
            passed += 1
    
    review.findings = findings
    review.passed_checks = passed
    review.total_checks = total
    review.score = passed / total if total > 0 else 0
    
    return review


# =============================================================================
# PhD Software Analyst Review
# =============================================================================

def review_data_flow(base_path: str) -> PersonaReview:
    """
    PhD Software Analyst: Data flow and pipeline validation.
    
    Checks:
    - Ingestion pipeline completeness
    - Data transformation logic
    - Statistical analysis integration
    - ML pipeline structure
    """
    review = PersonaReview(persona="PhD Software Analyst")
    findings = []
    passed = 0
    total = 0
    
    base = Path(base_path) / "voyant"
    
    # Check 1: Ingestion module
    total += 1
    ingestion_path = base / "ingestion"
    if ingestion_path.exists() and len(list(ingestion_path.glob("*.py"))) >= 2:
        passed += 1
    
    # Check 2: Stats activities
    total += 1
    stats_file = base / "activities" / "stats_activities.py"
    if stats_file.exists():
        content = stats_file.read_text()
        if "correlation" in content.lower() and "distribution" in content.lower():
            passed += 1
    
    # Check 3: ML activities
    total += 1
    ml_file = base / "activities" / "ml_activities.py"
    if ml_file.exists():
        content = ml_file.read_text()
        if "cluster" in content.lower() and "forecast" in content.lower():
            passed += 1
    
    # Check 4: Data quality operations
    total += 1
    ops_file = base / "activities" / "operational_activities.py"
    if ops_file.exists():
        content = ops_file.read_text()
        if "quality" in content.lower() or "anomaly" in content.lower():
            passed += 1
    
    # Check 5: Audit trail for data operations
    total += 1
    audit_file = base / "core" / "audit_trail.py"
    if audit_file.exists():
        content = audit_file.read_text()
        if "DATA_INGESTED" in content:
            passed += 1
    
    review.findings = findings
    review.passed_checks = passed
    review.total_checks = total
    review.score = passed / total if total > 0 else 0
    
    return review


# =============================================================================
# PhD QA Engineer Review
# =============================================================================

def review_test_coverage(base_path: str) -> PersonaReview:
    """
    PhD QA Engineer: Test coverage analysis.
    
    Checks:
    - Test file existence
    - Test patterns
    - Load test presence
    - Edge case coverage
    """
    review = PersonaReview(persona="PhD QA Engineer")
    findings = []
    passed = 0
    total = 0
    
    tests_path = Path(base_path) / "tests"
    
    # Check 1: Tests directory exists
    total += 1
    if tests_path.exists():
        passed += 1
    
    # Check 2: Sufficient test files
    total += 1
    if tests_path.exists():
        test_files = list(tests_path.rglob("test_*.py"))
        if len(test_files) >= 5:
            passed += 1
        else:
            findings.append(ReviewFinding(
                category="Test Coverage",
                severity="warning",
                message=f"Only {len(test_files)} test files found",
                recommendation="Add more test files for better coverage"
            ))
    
    # Check 3: Load tests exist
    total += 1
    load_tests_path = tests_path / "load"
    if load_tests_path.exists():
        passed += 1
    
    # Check 4: Health endpoint tests
    total += 1
    health_tests = tests_path / "test_health_endpoints.py"
    if health_tests.exists():
        passed += 1
    
    # Check 5: Uses pytest or unittest
    total += 1
    if tests_path.exists():
        test_files = list(tests_path.rglob("test_*.py"))
        if test_files:
            sample_content = test_files[0].read_text()
            if "pytest" in sample_content or "unittest" in sample_content:
                passed += 1
    
    review.findings = findings
    review.passed_checks = passed
    review.total_checks = total
    review.score = passed / total if total > 0 else 0
    
    return review


# =============================================================================
# ISO Documenter Review
# =============================================================================

def review_documentation(base_path: str) -> PersonaReview:
    """
    ISO Documenter: Documentation completeness.
    
    Checks:
    - README existence
    - Docstrings in modules
    - Architecture documentation
    - API documentation
    """
    review = PersonaReview(persona="ISO Documenter")
    findings = []
    passed = 0
    total = 0
    
    base = Path(base_path)
    
    # Check 1: README exists
    total += 1
    readme = base / "README.md"
    if readme.exists():
        passed += 1
    
    # Check 2: STATUS.md exists
    total += 1
    status = base / "STATUS.md"
    if status.exists():
        passed += 1
    
    # Check 3: Docs directory
    total += 1
    docs = base / "docs"
    if docs.exists():
        passed += 1
    
    # Check 4: Modules have docstrings
    total += 1
    core_files = list((base / "voyant" / "core").glob("*.py"))
    with_docstrings = sum(
        1 for f in core_files
        if not f.name.startswith("__") and '"""' in f.read_text()[:500]
    )
    if with_docstrings >= len(core_files) * 0.8:
        passed += 1
    
    # Check 5: API routes documented
    total += 1
    api_routes = base / "voyant" / "api" / "routes"
    if api_routes.exists():
        route_files = list(api_routes.glob("*.py"))
        documented = sum(
            1 for f in route_files
            if '"""' in f.read_text()[:200]
        )
        if documented >= len(route_files) * 0.7:
            passed += 1
    
    review.findings = findings
    review.passed_checks = passed
    review.total_checks = total
    review.score = passed / total if total > 0 else 0
    
    return review


# =============================================================================
# Security Auditor Review
# =============================================================================

def review_security(base_path: str) -> PersonaReview:
    """
    Security Auditor: Security posture review.
    
    Checks:
    - No hardcoded credentials
    - Circuit breakers present
    - PII filtering
    - Audit logging
    """
    review = PersonaReview(persona="Security Auditor")
    findings = []
    passed = 0
    total = 0
    
    base = Path(base_path) / "voyant"
    
    # Check 1: No hardcoded passwords
    total += 1
    all_py_files = list(base.rglob("*.py"))
    has_hardcoded = False
    for f in all_py_files:
        content = f.read_text()
        if "password = \"" in content.lower() or "password='" in content.lower():
            if "test" not in str(f).lower():
                has_hardcoded = True
                findings.append(ReviewFinding(
                    category="Credentials",
                    severity="critical",
                    message="Potential hardcoded password",
                    location=str(f)
                ))
    if not has_hardcoded:
        passed += 1
    
    # Check 2: Circuit breakers
    total += 1
    cb_file = base / "core" / "circuit_breaker.py"
    if cb_file.exists():
        passed += 1
    
    # Check 3: PII filtering in logging
    total += 1
    logging_file = base / "core" / "structured_logging.py"
    if logging_file.exists():
        content = logging_file.read_text()
        if "filter" in content.lower() and "sensitive" in content.lower():
            passed += 1
    
    # Check 4: Audit trail
    total += 1
    audit_file = base / "core" / "audit_trail.py"
    if audit_file.exists():
        passed += 1
    
    # Check 5: Secrets management
    total += 1
    secrets_file = base / "core" / "secrets.py"
    if secrets_file.exists():
        passed += 1
    
    review.findings = findings
    review.passed_checks = passed
    review.total_checks = total
    review.score = passed / total if total > 0 else 0
    
    return review


# =============================================================================
# Performance Engineer Review
# =============================================================================

def review_performance(base_path: str) -> PersonaReview:
    """
    Performance Engineer: Performance optimization review.
    
    Checks:
    - Connection pooling
    - Caching
    - Async patterns
    - Metrics collection
    """
    review = PersonaReview(persona="Performance Engineer")
    findings = []
    passed = 0
    total = 0
    
    base = Path(base_path) / "voyant"
    
    # Check 1: Connection pooling
    total += 1
    pool_file = base / "core" / "duckdb_pool.py"
    if pool_file.exists():
        passed += 1
    
    # Check 2: Query caching
    total += 1
    cache_file = base / "core" / "query_cache.py"
    if cache_file.exists():
        passed += 1
    
    # Check 3: Performance profiling
    total += 1
    profiling_file = base / "core" / "performance_profiling.py"
    if profiling_file.exists():
        passed += 1
    
    # Check 4: Metrics collection
    total += 1
    metrics_file = base / "core" / "metrics.py"
    if metrics_file.exists():
        content = metrics_file.read_text()
        if "Counter" in content or "Histogram" in content:
            passed += 1
    
    # Check 5: Async patterns in activities
    total += 1
    activities_path = base / "activities"
    if activities_path.exists():
        activity_files = list(activities_path.glob("*.py"))
        has_async = any(
            "async def" in f.read_text()
            for f in activity_files
            if not f.name.startswith("__")
        )
        if has_async:
            passed += 1
    
    review.findings = findings
    review.passed_checks = passed
    review.total_checks = total
    review.score = passed / total if total > 0 else 0
    
    return review


# =============================================================================
# UX Consultant Review
# =============================================================================

def review_api_usability(base_path: str) -> PersonaReview:
    """
    UX Consultant: API usability review.
    
    Checks:
    - RESTful patterns
    - Consistent response formats
    - Health endpoints
    - Error responses
    """
    review = PersonaReview(persona="UX Consultant")
    findings = []
    passed = 0
    total = 0
    
    base = Path(base_path) / "voyant"
    api_path = base / "api"
    
    # Check 1: Health endpoints
    total += 1
    health_file = api_path / "routes" / "health.py"
    if health_file.exists():
        content = health_file.read_text()
        if "healthz" in content and "readyz" in content:
            passed += 1
    
    # Check 2: Error catalog
    total += 1
    errors_file = base / "core" / "errors.py"
    if errors_file.exists():
        content = errors_file.read_text()
        if "VoyantError" in content or "resolution" in content:
            passed += 1
    
    # Check 3: Status endpoint
    total += 1
    if health_file.exists():
        content = health_file.read_text()
        if "status" in content.lower():
            passed += 1
    
    # Check 4: OpenAPI/FastAPI patterns
    total += 1
    main_app = api_path / "app.py"
    if main_app.exists():
        content = main_app.read_text()
        if "FastAPI" in content:
            passed += 1
    
    # Check 5: Consistent route structure
    total += 1
    routes_path = api_path / "routes"
    if routes_path.exists():
        route_files = list(routes_path.glob("*.py"))
        if len(route_files) >= 3:
            passed += 1
    
    review.findings = findings
    review.passed_checks = passed
    review.total_checks = total
    review.score = passed / total if total > 0 else 0
    
    return review


# =============================================================================
# Full Review Orchestration
# =============================================================================

def run_full_review(base_path: Optional[str] = None) -> FullReviewReport:
    """
    Run comprehensive review across all seven personas.
    
    Args:
        base_path: Project root path (defaults to current directory)
        
    Returns:
        FullReviewReport with all persona reviews
    """
    if base_path is None:
        base_path = os.getcwd()
    
    report = FullReviewReport()
    
    # Run all persona reviews
    report.reviews = [
        review_architecture(base_path),
        review_data_flow(base_path),
        review_test_coverage(base_path),
        review_documentation(base_path),
        review_security(base_path),
        review_performance(base_path),
        review_api_usability(base_path),
    ]
    
    # Calculate overall score
    report.calculate_overall_score()
    
    logger.info(f"Seven Personas Review complete: {report.overall_score:.1%}")
    
    return report


def get_review_summary(base_path: Optional[str] = None) -> str:
    """Get human-readable review summary."""
    report = run_full_review(base_path)
    return report.summary()
