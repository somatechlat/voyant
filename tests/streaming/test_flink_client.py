"""Tests for apps/streaming/flink_client.py."""

import pytest
import httpx

from apps.streaming.flink_client import FlinkClient, FlinkClientError


def _make_response(status_code, json_data=None):
    """Create an httpx.Response with a mock request attached."""
    request = httpx.Request("GET", "http://flink:8081/test")
    resp = httpx.Response(status_code, json=json_data or {}, request=request)
    return resp


class TestFlinkClientInit:
    def test_raises_when_no_url_configured(self):
        with pytest.raises(ValueError, match="FLINK_JOBMANAGER_URL"):
            FlinkClient(jobmanager_url="")

    def test_strips_trailing_slash(self):
        client = FlinkClient(jobmanager_url="http://flink:8081/")
        assert client.base_url == "http://flink:8081"

    def test_accepts_explicit_url(self):
        client = FlinkClient(jobmanager_url="http://custom:9999")
        assert client.base_url == "http://custom:9999"


class TestFlinkClientGetOverview:
    def test_returns_json_on_success(self, monkeypatch):
        client = FlinkClient(jobmanager_url="http://flink:8081")
        monkeypatch.setattr(
            httpx, "get",
            lambda url, timeout=None: _make_response(200, {"taskmanagers": 2, "slots-total": 8})
        )
        result = client.get_overview()
        assert result["taskmanagers"] == 2

    def test_raises_on_connection_error(self, monkeypatch):
        client = FlinkClient(jobmanager_url="http://flink:8081")
        monkeypatch.setattr(httpx, "get", lambda url, timeout=None: (_ for _ in ()).throw(httpx.ConnectError("refused")))
        with pytest.raises(FlinkClientError, match="Connection failed"):
            client.get_overview()

    def test_raises_on_http_error(self, monkeypatch):
        client = FlinkClient(jobmanager_url="http://flink:8081")
        monkeypatch.setattr(
            httpx, "get",
            lambda url, timeout=None: _make_response(500, {"error": "internal"})
        )
        with pytest.raises(FlinkClientError, match="API error"):
            client.get_overview()


class TestFlinkClientListJobs:
    def test_returns_jobs_on_success(self, monkeypatch):
        client = FlinkClient(jobmanager_url="http://flink:8081")
        monkeypatch.setattr(
            httpx, "get",
            lambda url, timeout=None: _make_response(200, {"jobs": [{"id": "abc", "status": "RUNNING"}]})
        )
        result = client.list_jobs()
        assert len(result["jobs"]) == 1

    def test_raises_on_failure(self, monkeypatch):
        client = FlinkClient(jobmanager_url="http://flink:8081")
        monkeypatch.setattr(httpx, "get", lambda url, timeout=None: (_ for _ in ()).throw(httpx.ConnectError("timeout")))
        with pytest.raises(FlinkClientError, match="Failed to list jobs"):
            client.list_jobs()


class TestFlinkClientSubmitJar:
    def test_returns_job_id_on_success(self, monkeypatch):
        client = FlinkClient(jobmanager_url="http://flink:8081")
        monkeypatch.setattr(
            httpx, "post",
            lambda url, json=None, timeout=None: _make_response(200, {"jobid": "job-456"})
        )
        job_id = client.submit_jar(jar_id="jar-123", entry_class="com.Main")
        assert job_id == "job-456"

    def test_raises_when_no_jobid_in_response(self, monkeypatch):
        client = FlinkClient(jobmanager_url="http://flink:8081")
        monkeypatch.setattr(
            httpx, "post",
            lambda url, json=None, timeout=None: _make_response(200, {})
        )
        with pytest.raises(FlinkClientError, match="did not include jobid"):
            client.submit_jar(jar_id="jar-123")

    def test_builds_payload_with_all_params(self, monkeypatch):
        client = FlinkClient(jobmanager_url="http://flink:8081")
        captured = {}

        def mock_post(url, json=None, timeout=None):
            captured["json"] = json
            return _make_response(200, {"jobid": "job-789"})

        monkeypatch.setattr(httpx, "post", mock_post)
        client.submit_jar(jar_id="jar-123", entry_class="com.Main", program_args="--input", parallelism=4)
        assert captured["json"]["entryClass"] == "com.Main"
        assert captured["json"]["parallelism"] == 4


class TestFlinkClientUploadJar:
    def test_raises_when_file_not_found(self):
        client = FlinkClient(jobmanager_url="http://flink:8081")
        with pytest.raises(FlinkClientError, match="JAR file not found"):
            client.upload_jar("/nonexistent/path/app.jar")
