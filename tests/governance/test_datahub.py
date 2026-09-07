"""Tests for the DataHub client and lineage publishing integration."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.governance.lib import datahub as datahub_module
from apps.governance.lib.datahub import DatasetUrn


@pytest.fixture(autouse=True)
def _cleanup(datahub_module=datahub_module):
    datahub_module.reset_datahub_client()
    datahub_module.settings = getattr(datahub_module, "settings", SimpleNamespace())
    yield
    datahub_module.reset_datahub_client()


class _FakeClient:
    def __init__(self):
        self.registered = []
        self.lineage = []

    async def register_dataset(self, urn, name, description=None, schema_fields=None):
        self.registered.append({"urn": urn, "name": name})
        return True

    async def emit_lineage(self, upstream_urns, downstream_urn):
        self.lineage.append({"upstream": upstream_urns, "downstream": downstream_urn})
        return True


def _configure(datahub_module=datahub_module, enabled=True, gms_url="http://gms:8080"):
    datahub_module.settings = SimpleNamespace(
        enable_datahub=enabled,
        datahub_gms_url=gms_url,
    )


class TestDatasetUrn:
    def test_str_format(self):
        urn = str(DatasetUrn(platform="iceberg", name="raw_orders"))
        assert urn == "urn:li:dataset:(urn:li:dataPlatform:iceberg,raw_orders,PROD)"


class TestPublishJobLineage:
    @pytest.mark.asyncio
    async def test_disabled_skips_publish(self):
        _configure(enabled=False)
        result = await datahub_module.publish_job_lineage(
            source_urns=["urn:src"],
            output_urn="urn:out",
            dataset_name="out",
        )
        assert result == {"published": False, "reason": "datahub_disabled"}

    @pytest.mark.asyncio
    async def test_missing_gms_url_skips_publish(self):
        _configure(enabled=True, gms_url="")
        result = await datahub_module.publish_job_lineage(
            source_urns=["urn:src"],
            output_urn="urn:out",
            dataset_name="out",
        )
        assert result == {"published": False, "reason": "datahub_disabled"}

    @pytest.mark.asyncio
    async def test_publishes_registration_and_lineage(self, monkeypatch):
        _configure()
        fake = _FakeClient()
        monkeypatch.setattr(datahub_module, "get_datahub_client", lambda: fake)

        result = await datahub_module.publish_job_lineage(
            source_urns=["urn:src"],
            output_urn="urn:out",
            dataset_name="out",
            description="desc",
        )
        assert result["published"] is True
        assert result["registered"] is True
        assert result["lineage_emitted"] is True
        assert fake.registered == [{"urn": "urn:out", "name": "out"}]
        assert fake.lineage == [{"upstream": ["urn:src"], "downstream": "urn:out"}]

    @pytest.mark.asyncio
    async def test_no_source_urns_registers_only(self, monkeypatch):
        _configure()
        fake = _FakeClient()
        monkeypatch.setattr(datahub_module, "get_datahub_client", lambda: fake)

        result = await datahub_module.publish_job_lineage(
            source_urns=[],
            output_urn="urn:out",
            dataset_name="out",
        )
        assert result["published"] is True
        assert result["lineage_emitted"] is False
        assert fake.lineage == []

    @pytest.mark.asyncio
    async def test_failure_returns_unpublished(self, monkeypatch):
        _configure()

        class _BrokenClient(_FakeClient):
            async def register_dataset(self, *args, **kwargs):
                raise RuntimeError("boom")

        monkeypatch.setattr(
            datahub_module, "get_datahub_client", lambda: _BrokenClient()
        )
        result = await datahub_module.publish_job_lineage(
            source_urns=["urn:src"],
            output_urn="urn:out",
            dataset_name="out",
        )
        assert result["published"] is False
        assert result["reason"] == "boom"
