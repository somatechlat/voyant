"""Tests for apps.analysis.lib.segmentation."""

import pytest

from apps.analysis.lib.segmentation import (
    SegmentComparison,
    SegmentProfiler,
    SegmentProfileResult,
    SegmentStats,
    SegmentType,
    compare_segments,
    detect_segment_drift,
    profile_segments,
)


@pytest.fixture
def sample_data():
    return [
        {"region": "North", "revenue": 100, "count": 10},
        {"region": "North", "revenue": 120, "count": 12},
        {"region": "North", "revenue": 110, "count": 11},
        {"region": "South", "revenue": 200, "count": 20},
        {"region": "South", "revenue": 220, "count": 22},
        {"region": "South", "revenue": 210, "count": 21},
        {"region": "East", "revenue": 150, "count": 15},
        {"region": "East", "revenue": 160, "count": 16},
    ]


# ---------------------------------------------------------------------------
# SegmentProfiler.profile
# ---------------------------------------------------------------------------


class TestSegmentProfiler:
    def test_basic_profiling(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.profile(sample_data, "region")
        assert result.segment_column == "region"
        assert result.total_rows == 8
        assert len(result.segments) == 3

    def test_segment_counts(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.profile(sample_data, "region")
        counts = {s.segment_value: s.row_count for s in result.segments}
        assert counts["North"] == 3
        assert counts["South"] == 3
        assert counts["East"] == 2

    def test_percentage_of_total(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.profile(sample_data, "region")
        for seg in result.segments:
            assert 0.0 < seg.percentage_of_total <= 1.0

    def test_numeric_stats(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.profile(sample_data, "region", numeric_columns=["revenue"])
        north = next(s for s in result.segments if s.segment_value == "North")
        assert "revenue" in north.numeric_stats
        stats = north.numeric_stats["revenue"]
        assert "mean" in stats
        assert "median" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["mean"] == pytest.approx(110.0)

    def test_empty_data(self):
        profiler = SegmentProfiler()
        result = profiler.profile([], "region")
        assert result.total_rows == 0
        assert result.segments == []

    def test_missing_column_raises(self, sample_data):
        profiler = SegmentProfiler()
        with pytest.raises(ValueError, match="not found"):
            profiler.profile(sample_data, "nonexistent_column")

    def test_max_segments_limit(self):
        data = [{"group": str(i), "val": i} for i in range(200)]
        profiler = SegmentProfiler(max_segments=5)
        result = profiler.profile(data, "group")
        assert len(result.segments) <= 5

    def test_auto_detect_numeric_columns(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.profile(sample_data, "region")
        north = next(s for s in result.segments if s.segment_value == "North")
        assert "revenue" in north.numeric_stats
        assert "count" in north.numeric_stats

    def test_sorted_by_count_descending(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.profile(sample_data, "region")
        counts = [s.row_count for s in result.segments]
        assert counts == sorted(counts, reverse=True)


# ---------------------------------------------------------------------------
# SegmentProfiler.compare
# ---------------------------------------------------------------------------


class TestSegmentComparison:
    def test_basic_comparison(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.compare(sample_data, "region", "North", "South")
        assert result.segment_a == "North"
        assert result.segment_b == "South"
        assert "revenue" in result.numeric_differences

    def test_mean_difference(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.compare(sample_data, "region", "North", "South")
        diff = result.numeric_differences["revenue"]
        assert diff["mean_a"] == pytest.approx(110.0)
        assert diff["mean_b"] == pytest.approx(210.0)
        assert diff["difference"] == pytest.approx(-100.0)

    def test_significance_p_value(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.compare(sample_data, "region", "North", "South")
        assert "revenue" in result.significance
        p = result.significance["revenue"]
        assert 0.0 <= p <= 1.0

    def test_size_ratio(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.compare(sample_data, "region", "North", "East")
        assert result.size_ratio == pytest.approx(3 / 2)

    def test_comparison_to_dict(self, sample_data):
        profiler = SegmentProfiler()
        result = profiler.compare(sample_data, "region", "North", "South")
        d = result.to_dict()
        assert "segment_a" in d
        assert "numeric_differences" in d


# ---------------------------------------------------------------------------
# SegmentStats.to_dict
# ---------------------------------------------------------------------------


class TestSegmentStatsDict:
    def test_to_dict(self):
        stats = SegmentStats(
            segment_name="region",
            segment_value="North",
            row_count=3,
            numeric_stats={"revenue": {"mean": 110.0, "std": 10.0}},
            percentage_of_total=0.375,
        )
        d = stats.to_dict()
        assert d["segment_name"] == "region"
        assert d["row_count"] == 3
        assert d["percentage_of_total"] == 0.375


# ---------------------------------------------------------------------------
# SegmentProfileResult.to_dict
# ---------------------------------------------------------------------------


class TestSegmentProfileResultDict:
    def test_to_dict(self, sample_data):
        result = profile_segments(sample_data, "region")
        d = result.to_dict()
        assert "segment_column" in d
        assert "total_rows" in d
        assert "segment_count" in d
        assert "segments" in d


# ---------------------------------------------------------------------------
# profile_segments (convenience function)
# ---------------------------------------------------------------------------


class TestProfileSegments:
    def test_basic(self, sample_data):
        result = profile_segments(sample_data, "region")
        assert isinstance(result, SegmentProfileResult)
        assert len(result.segments) == 3

    def test_with_numeric_columns(self, sample_data):
        result = profile_segments(sample_data, "region", numeric_columns=["revenue"])
        for seg in result.segments:
            assert "revenue" in seg.numeric_stats
            assert "count" not in seg.numeric_stats  # Not requested


# ---------------------------------------------------------------------------
# compare_segments (convenience function)
# ---------------------------------------------------------------------------


class TestCompareSegments:
    def test_basic(self, sample_data):
        result = compare_segments(sample_data, "region", "North", "South")
        assert isinstance(result, SegmentComparison)


# ---------------------------------------------------------------------------
# detect_segment_drift
# ---------------------------------------------------------------------------


class TestDetectSegmentDrift:
    def test_no_drift(self):
        old_data = [{"g": "A"}] * 50 + [{"g": "B"}] * 50
        new_data = [{"g": "A"}] * 50 + [{"g": "B"}] * 50
        result = detect_segment_drift(old_data, new_data, "g")
        assert result["segments_changed"] == 0

    def test_drift_detected(self):
        old_data = [{"g": "A"}] * 80 + [{"g": "B"}] * 20
        new_data = [{"g": "A"}] * 20 + [{"g": "B"}] * 80
        result = detect_segment_drift(old_data, new_data, "g")
        assert result["segments_changed"] >= 1
        assert "drifts" in result

    def test_new_segment_in_new_data(self):
        old_data = [{"g": "A"}] * 10
        new_data = [{"g": "A"}] * 5 + [{"g": "C"}] * 5
        result = detect_segment_drift(old_data, new_data, "g")
        assert "C" in result["drifts"]


# ---------------------------------------------------------------------------
# SegmentType enum
# ---------------------------------------------------------------------------


class TestSegmentType:
    def test_values(self):
        assert SegmentType.CATEGORICAL == "categorical"
        assert SegmentType.RANGE == "range"
        assert SegmentType.TEMPORAL == "temporal"
        assert SegmentType.CUSTOM == "custom"
