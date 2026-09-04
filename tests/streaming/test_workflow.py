"""Tests for apps/streaming/workflow.py."""

from apps.streaming.workflow import StreamingJobInput, StreamingJobWorkflow


class TestStreamingJobInput:
    def test_defaults(self):
        inp = StreamingJobInput(
            job_name="test",
            job_type="kpi",
            source_topic="input",
        )
        assert inp.job_name == "test"
        assert inp.job_type == "kpi"
        assert inp.source_topic == "input"
        assert inp.sink_topic is None
        assert inp.config is None

    def test_with_all_fields(self):
        inp = StreamingJobInput(
            job_name="anomaly-detector",
            job_type="anomaly_detection",
            source_topic="metrics",
            sink_topic="alerts",
            config={"window_size": 60},
        )
        assert inp.sink_topic == "alerts"
        assert inp.config == {"window_size": 60}


class TestStreamingJobWorkflow:
    def test_workflow_class_exists(self):
        assert hasattr(StreamingJobWorkflow, "run")

    def test_workflow_is_decorated(self):
        import temporalio.workflow
        # Verify the workflow class is properly decorated
        assert hasattr(StreamingJobWorkflow, "__temporal_workflow_definition")
