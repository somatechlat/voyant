"""
Unit tests for apps.core.lib.errors — Error catalog, exception hierarchy.

Real code paths. No mocks.
"""

import pytest

from apps.core.lib.errors import (
    ERROR_CATALOG,
    AuthenticationError,
    AuthorizationError,
    DataQualityError,
    ErrorCategory,
    ErrorDefinition,
    ErrorSeverity,
    ExternalServiceError,
    IngestionError,
    QuotaExceededError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    SystemError,
    ValidationError,
    VoyantError,
    error_response,
    get_error_catalog,
    get_errors_by_category,
    list_error_codes,
)


class TestErrorDefinition:
    def test_to_dict_contains_all_fields(self):
        defn = ErrorDefinition(
            code="TEST-001",
            message="Test message",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            http_status=400,
            description="desc",
            resolution="fix it",
            retry_allowed=True,
        )
        d = defn.to_dict()
        assert d["code"] == "TEST-001"
        assert d["message"] == "Test message"
        assert d["category"] == "validation"
        assert d["severity"] == "error"
        assert d["http_status"] == 400
        assert d["description"] == "desc"
        assert d["resolution"] == "fix it"
        assert d["retry_allowed"] is True


class TestErrorCatalog:
    def test_catalog_has_valid_codes(self):
        for code in ERROR_CATALOG:
            assert code.startswith("VYNT-")
            assert len(code) == 9

    def test_catalog_entries_have_required_fields(self):
        for code, defn in ERROR_CATALOG.items():
            assert isinstance(defn, ErrorDefinition)
            assert defn.code == code
            assert 100 <= defn.http_status <= 599
            assert defn.message

    def test_catalog_covers_all_categories(self):
        categories = {defn.category for defn in ERROR_CATALOG.values()}
        assert ErrorCategory.VALIDATION in categories
        assert ErrorCategory.RESOURCE in categories
        assert ErrorCategory.AUTHENTICATION in categories
        assert ErrorCategory.SYSTEM in categories

    def test_get_error_catalog_returns_serializable_dict(self):
        catalog = get_error_catalog()
        assert isinstance(catalog, dict)
        for code, data in catalog.items():
            assert "code" in data
            assert "message" in data
            assert "category" in data

    def test_get_errors_by_category_validation(self):
        errors = get_errors_by_category(ErrorCategory.VALIDATION)
        assert len(errors) > 0
        for err in errors:
            assert err["category"] == "validation"

    def test_list_error_codes_returns_sorted(self):
        codes = list_error_codes()
        assert codes == sorted(codes)
        assert "VYNT-1001" in codes


class TestVoyantError:
    def test_known_code_formats_message(self):
        err = VoyantError("VYNT-1002", column="age")
        assert err.message == "Invalid column name: age"
        assert err.http_status == 400
        assert err.category == ErrorCategory.VALIDATION

    def test_known_code_override_message(self):
        err = VoyantError("VYNT-1001", message="Custom message")
        assert err.message == "Custom message"

    def test_unknown_code_defaults(self):
        err = VoyantError("VYNT-9999", message="Unknown")
        assert err.http_status == 500
        assert err.category == ErrorCategory.SYSTEM

    def test_to_response_structure(self):
        err = VoyantError("VYNT-1001")
        resp = err.to_response(request_id="req-123")
        assert resp["error"]["code"] == "VYNT-1001"
        assert resp["request_id"] == "req-123"
        assert "timestamp" in resp

    def test_to_response_filters_sensitive_details(self):
        err = VoyantError(
            "VYNT-1001",
            details={"password": "secret123", "token": "abc", "safe_data": "ok"},
        )
        resp = err.to_response()
        details = resp["error"]["details"]
        assert "password" not in details
        assert "token" not in details
        assert "safe_data" in details


class TestExceptionHierarchy:
    def test_validation_error_is_voyant_error(self):
        err = ValidationError("VYNT-1001")
        assert isinstance(err, VoyantError)

    def test_resource_not_found_is_voyant_error(self):
        err = ResourceNotFoundError("VYNT-2001", job_id="j-123")
        assert isinstance(err, VoyantError)
        assert err.http_status == 404

    def test_authentication_error(self):
        err = AuthenticationError("VYNT-3001")
        assert err.http_status == 401

    def test_authorization_error(self):
        err = AuthorizationError("VYNT-3003", action="delete")
        assert err.http_status == 403

    def test_quota_exceeded_error(self):
        err = QuotaExceededError("VYNT-4001")
        assert err.http_status == 429

    def test_system_error(self):
        err = SystemError("VYNT-5001")
        assert err.http_status == 500

    def test_external_service_error(self):
        err = ExternalServiceError("VYNT-6001", reason="timeout")
        assert err.http_status == 502

    def test_service_unavailable_error(self):
        err = ServiceUnavailableError("trino")
        assert err.http_status == 503
        assert err.service_name == "trino"

    def test_data_quality_error(self):
        err = DataQualityError("VYNT-7001", violations=5)
        assert err.http_status == 422

    def test_ingestion_error(self):
        err = IngestionError("VYNT-8001", file_path="/data.csv")
        assert err.http_status == 404


class TestErrorResponse:
    def test_error_response_without_raising(self):
        resp = error_response("VYNT-1001", request_id="r-1")
        assert resp["error"]["code"] == "VYNT-1001"
        assert resp["request_id"] == "r-1"

    def test_error_response_with_format_args(self):
        resp = error_response("VYNT-1002", column="price")
        assert "price" in resp["error"]["message"]
