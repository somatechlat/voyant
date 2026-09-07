"""Tests for apps/streaming/activities.py."""


from apps.streaming.activities import FlinkJobResult, StreamingActivities


class TestFlinkJobResult:
    def test_defaults(self):
        r = FlinkJobResult(success=True)
        assert r.success is True
        assert r.job_id is None
        assert r.message == ""
        assert r.details is None

    def test_with_all_fields(self):
        r = FlinkJobResult(
            success=False,
            job_id="j-123",
            message="failed",
            details={"error": "timeout"},
        )
        assert r.success is False
        assert r.job_id == "j-123"
        assert r.details == {"error": "timeout"}


class TestStreamingActivitiesInit:
    def test_creates_instance(self):
        activities = StreamingActivities()
        assert activities.settings is not None


class TestStreamingActivitiesSubmitJob:
    def test_returns_failure_when_no_slots(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        activities = StreamingActivities()

        class MockClient:
            def get_overview(self):
                return {"slots-available": 0, "slots-total": 8}

        monkeypatch.setattr(activities, "_get_client", lambda: MockClient())
        import asyncio
        result = asyncio.run(
            activities.submit_streaming_job("test-job", {"jar_id": "jar-1"})
        )
        assert result.success is False
        assert "No available slots" in result.message

    def test_returns_failure_when_no_jar(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        activities = StreamingActivities()

        class MockClient:
            def get_overview(self):
                return {"slots-available": 4, "slots-total": 8}

        monkeypatch.setattr(activities, "_get_client", lambda: MockClient())
        import asyncio
        result = asyncio.run(
            activities.submit_streaming_job("test-job", {})
        )
        assert result.success is False
        assert "Missing required" in result.message

    def test_returns_success_on_submit(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        activities = StreamingActivities()

        class MockClient:
            def get_overview(self):
                return {"slots-available": 4, "slots-total": 8}

            def submit_jar(self, jar_id, entry_class=None, program_args=None, parallelism=None):
                return "job-abc"

        monkeypatch.setattr(activities, "_get_client", lambda: MockClient())
        import asyncio
        result = asyncio.run(
            activities.submit_streaming_job("test-job", {"jar_id": "jar-1"})
        )
        assert result.success is True
        assert result.job_id == "job-abc"

    def test_handles_flink_client_error(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        activities = StreamingActivities()

        class MockClient:
            def get_overview(self):
                from apps.streaming.flink_client import FlinkClientError
                raise FlinkClientError("Connection refused")

        monkeypatch.setattr(activities, "_get_client", lambda: MockClient())
        import asyncio
        result = asyncio.run(
            activities.submit_streaming_job("test-job", {"jar_id": "jar-1"})
        )
        assert result.success is False
        assert "Connection refused" in result.message

    def test_program_args_list_conversion(self, monkeypatch):
        monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink:8081")
        activities = StreamingActivities()
        captured = {}

        class MockClient:
            def get_overview(self):
                return {"slots-available": 4, "slots-total": 8}

            def submit_jar(self, jar_id, entry_class=None, program_args=None, parallelism=None):
                captured["program_args"] = program_args
                return "job-abc"

        monkeypatch.setattr(activities, "_get_client", lambda: MockClient())
        import asyncio
        asyncio.run(
            activities.submit_streaming_job(
                "test-job", {"jar_id": "jar-1", "program_args": ["--input", "topic1"]}
            )
        )
        assert captured["program_args"] == "--input topic1"
