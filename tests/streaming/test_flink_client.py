"""Tests for apps/streaming/flink_client.py."""

import pytest
import httpx

from apps.streaming.flink_client import FlinkClient, FlinkClientError


class TestFlinkClientInit:
    def test_raises_when_no_url_configured(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "")
        with pytest.raises(ValueError, match="FLINK_JOBMANAGER_URL"):
            FlinkClient()

    def test_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081/")
        client = FlinkClient()
        assert client.base_url == "http://flink:8081"

    def test_accepts_explicit_url(self):
        client = FlinkClient(jobmanager_url="http://custom:9999")
        assert client.base_url == "http://custom:9999"


class TestFlinkClientGetOverview:
    def test_returns_json_on_success(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        client = FlinkClient()

        def mock_get(url, timeout=None):
            return httpx.Response(200, json={"taskmanagers": 2, "slots-total": 8})

        monkeypatch.setattr(httpx, "get", mock_get)
        result = client.get_overview()
        assert result["taskmanagers"] == 2
        assert result["slots-total"] == 8

    def test_raises_on_connection_error(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        client = FlinkClient()

        def mock_get(url, timeout=None):
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx, "get", mock_get)
        with pytest.raises(FlinkClientError, match="Connection failed"):
            client.get_overview()

    def test_raises_on_http_error(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        client = FlinkClient()

        def mock_get(url, timeout=None):
            return httpx.Response(500, text="Internal Server Error")

        monkeypatch.setattr(httpx, "get", mock_get)
        with pytest.raises(FlinkClientError, match="API error"):
            client.get_overview()


class TestFlinkClientListJobs:
    def test_returns_jobs_on_success(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        client = FlinkClient()

        def mock_get(url, timeout=None):
            return httpx.Response(200, json={"jobs": [{"id": "abc123", "status": "RUNNING"}]})

        monkeypatch.setattr(httpx, "get", mock_get)
        result = client.list_jobs()
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["id"] == "abc123"

    def test_raises_on_failure(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        client = FlinkClient()

        def mock_get(url, timeout=None):
            raise httpx.ConnectError("Timeout")

        monkeypatch.setattr(httpx, "get", mock_get)
        with pytest.raises(FlinkClientError, match="Failed to list jobs"):
            client.list_jobs()


class TestFlinkClientSubmitJar:
    def test_returns_job_id_on_success(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        client = FlinkClient()

        def mock_post(url, json=None, timeout=None):
            return httpx.Response(200, json={"jobid": "job-456"})

        monkeypatch.setattr(httpx, "post", mock_post)
        job_id = client.submit_jar(jar_id="jar-123", entry_class="com.Main")
        assert job_id == "job-456"

    def test_raises_when_no_jobid_in_response(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        client = FlinkClient()

        def mock_post(url, json=None, timeout=None):
            return httpx.Response(200, json={})

        monkeypatch.setattr(httpx, "post", mock_post)
        with pytest.raises(FlinkClientError, match="did not include jobid"):
            client.submit_jar(jar_id="jar-123")

    def test_builds_payload_with_all_params(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        client = FlinkClient()
        captured = {}

        def mock_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            return httpx.Response(200, json={"jobid": "job-789"})

        monkeypatch.setattr(httpx, "post", mock_post)
        client.submit_jar(
            jar_id="jar-123",
            entry_class="com.Main",
            program_args="--input topic",
            parallelism=4,
        )
        assert captured["json"]["entryClass"] == "com.Main"
        assert captured["json"]["programArgs"] == "--input topic"
        assert captured["json"]["parallelism"] == 4


class TestFlinkClientUploadJar:
    def test_raises_when_file_not_found(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        client = FlinkClient()
        with pytest.raises(FlinkClientError, match="JAR file not found"):
            client.upload_jar("/nonexistent/path/app.jar")
