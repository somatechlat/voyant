"""
Unit tests for Octopus Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from apps.scraper.octopus.schemas import (
    BrowserAction,
    OctopusARM,
    OctopusRequest,
    OctopusResult,
)


class TestOctopusARM:
    """Tests for the ARM enum."""

    def test_all_arms_present(self):
        arms = set(OctopusARM)
        expected = {
            OctopusARM.STATIC,
            OctopusARM.DYNAMIC,
            OctopusARM.EVASION,
            OctopusARM.CRAWL,
            OctopusARM.API_INTERCEPT,
            OctopusARM.DOCUMENT,
            OctopusARM.OCR,
            OctopusARM.TRANSCRIBE,
            OctopusARM.ARCHIVE,
        }
        assert arms == expected

    def test_arm_values(self):
        assert OctopusARM.STATIC.value == "static"
        assert OctopusARM.DYNAMIC.value == "dynamic"
        assert OctopusARM.OCR.value == "ocr"


class TestBrowserAction:
    """Tests for the BrowserAction schema."""

    def test_minimal_action(self):
        action = BrowserAction(type="click")
        assert action.type == "click"
        assert action.timeout_ms == 5000

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            BrowserAction(type="click", unknown_field="bad")


class TestOctopusRequest:
    """Tests for the unified request schema."""

    def test_minimal_request(self):
        req = OctopusRequest(
            url="https://example.com",
            arm=OctopusARM.STATIC,
            tenant_id="t1",
        )
        assert req.url == "https://example.com"
        assert req.arm == OctopusARM.STATIC
        assert req.timeout_seconds == 60
        assert req.css_selectors == {}

    def test_full_request(self):
        req = OctopusRequest(
            url="https://example.com",
            arm=OctopusARM.DYNAMIC,
            tenant_id="t1",
            css_selectors={"title": "h1"},
            actions=[BrowserAction(type="scroll")],
            evasion_mode="curl_cffi",
        )
        assert req.css_selectors == {"title": "h1"}
        assert len(req.actions) == 1
        assert req.evasion_mode == "curl_cffi"

    def test_missing_url_raises(self):
        with pytest.raises(ValidationError):
            OctopusRequest(arm=OctopusARM.STATIC, tenant_id="t1")

    def test_missing_tenant_raises(self):
        with pytest.raises(ValidationError):
            OctopusRequest(url="https://example.com", arm=OctopusARM.STATIC)

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            OctopusRequest(
                url="https://example.com",
                arm=OctopusARM.STATIC,
                tenant_id="t1",
                evil="injection",
            )


class TestOctopusResult:
    """Tests for the unified result schema."""

    def test_success_result(self):
        result = OctopusResult(
            arm="static",
            url="https://example.com",
            tenant_id="t1",
            success=True,
            html="<html></html>",
            status_code=200,
        )
        assert result.success is True
        assert result.error_code is None

    def test_error_result(self):
        result = OctopusResult(
            arm="static",
            url="https://example.com",
            tenant_id="t1",
            success=False,
            error_code="TIMEOUT",
            error_message="Request timed out",
        )
        assert result.success is False
        assert result.error_code == "TIMEOUT"
