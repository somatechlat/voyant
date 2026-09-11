"""Tests for apps.analysis.lib.adaptive_sampling."""


from apps.analysis.lib.adaptive_sampling import (
    SamplingStrategy,
    calculate_margin_of_error,
    deterministic_sample,
    get_optimal_sample_size,
    quick_sample,
    random_sample,
    reservoir_sample,
    sample_table,
    select_strategy,
    should_sample,
    stratified_sample,
    systematic_sample,
)

# ---------------------------------------------------------------------------
# get_optimal_sample_size
# ---------------------------------------------------------------------------


class TestGetOptimalSampleSize:
    def test_basic_calculation(self):
        size = get_optimal_sample_size(10000, confidence=0.95, margin_of_error=0.03)
        assert 100 <= size <= 10000

    def test_small_population(self):
        size = get_optimal_sample_size(50)
        assert size <= 50

    def test_large_population(self):
        size = get_optimal_sample_size(1_000_000)
        assert size <= 100_000  # max_sample default

    def test_higher_confidence_larger_sample(self):
        size_90 = get_optimal_sample_size(10000, confidence=0.90)
        size_99 = get_optimal_sample_size(10000, confidence=0.99)
        assert size_99 > size_90

    def test_tighter_margin_larger_sample(self):
        size_wide = get_optimal_sample_size(10000, margin_of_error=0.10)
        size_tight = get_optimal_sample_size(10000, margin_of_error=0.01)
        assert size_tight > size_wide

    def test_min_sample_enforced(self):
        size = get_optimal_sample_size(10000, min_sample=500)
        assert size >= 500

    def test_max_sample_enforced(self):
        size = get_optimal_sample_size(1_000_000, max_sample=1000)
        assert size <= 1000

    def test_zero_population(self):
        size = get_optimal_sample_size(0)
        # With total_rows=0, min(sample_size, total_rows) = min(n, 0) = 0
        assert size >= 0


# ---------------------------------------------------------------------------
# calculate_margin_of_error
# ---------------------------------------------------------------------------


class TestCalculateMarginOfError:
    def test_basic_moe(self):
        moe = calculate_margin_of_error(385, 10000, confidence=0.95)
        assert 0.0 < moe < 0.1

    def test_larger_sample_smaller_moe(self):
        moe_small = calculate_margin_of_error(100, 10000)
        moe_large = calculate_margin_of_error(1000, 10000)
        assert moe_large < moe_small


# ---------------------------------------------------------------------------
# Sampling algorithms
# ---------------------------------------------------------------------------


class TestRandomSample:
    def test_basic(self):
        data = list(range(100))
        result = random_sample(data, 10, seed=42)
        assert len(result) == 10
        assert all(x in data for x in result)

    def test_sample_size_exceeds_data(self):
        data = [1, 2, 3]
        result = random_sample(data, 10)
        assert len(result) == 3

    def test_deterministic_with_seed(self):
        data = list(range(100))
        r1 = random_sample(data, 10, seed=42)
        r2 = random_sample(data, 10, seed=42)
        assert r1 == r2

    def test_different_seeds(self):
        data = list(range(100))
        r1 = random_sample(data, 10, seed=1)
        r2 = random_sample(data, 10, seed=2)
        # Very unlikely to be identical with different seeds
        assert r1 != r2


class TestSystematicSample:
    def test_basic(self):
        data = list(range(100))
        result = systematic_sample(data, 10, seed=42)
        assert len(result) == 10

    def test_sample_size_exceeds_data(self):
        data = [1, 2, 3]
        result = systematic_sample(data, 10)
        assert len(result) == 3

    def test_deterministic_with_seed(self):
        data = list(range(100))
        r1 = systematic_sample(data, 10, seed=42)
        r2 = systematic_sample(data, 10, seed=42)
        assert r1 == r2


class TestStratifiedSample:
    def test_basic(self):
        data = [{"group": "A", "val": i} for i in range(50)] + [
            {"group": "B", "val": i} for i in range(50)
        ]
        result, strata = stratified_sample(data, 20, "group", seed=42)
        assert len(result) <= 20
        assert "A" in strata
        assert "B" in strata

    def test_preserves_proportions(self):
        data = [{"g": "A", "v": 1}] * 80 + [{"g": "B", "v": 2}] * 20
        result, strata = stratified_sample(data, 10, "g", seed=42)
        # A should get ~8, B should get ~2
        assert strata.get("A", 0) > strata.get("B", 0)

    def test_sample_size_exceeds_data(self):
        data = [{"g": "A", "v": 1}]
        result, strata = stratified_sample(data, 10, "g")
        assert len(result) == 1


class TestReservoirSample:
    def test_basic(self):
        data = list(range(100))
        result = reservoir_sample(data, 10, seed=42)
        assert len(result) == 10

    def test_sample_size_exceeds_data(self):
        data = [1, 2, 3]
        result = reservoir_sample(data, 10)
        assert len(result) == 3

    def test_deterministic_with_seed(self):
        data = list(range(100))
        r1 = reservoir_sample(data, 10, seed=42)
        r2 = reservoir_sample(data, 10, seed=42)
        assert r1 == r2


class TestDeterministicSample:
    def test_basic(self):
        data = [{"id": str(i), "val": i} for i in range(100)]
        result = deterministic_sample(data, 10, "id")
        assert len(result) <= 10

    def test_deterministic_reproducibility(self):
        data = [{"id": str(i), "val": i} for i in range(100)]
        r1 = deterministic_sample(data, 10, "id")
        r2 = deterministic_sample(data, 10, "id")
        assert r1 == r2

    def test_sample_size_exceeds_data(self):
        data = [{"id": "1"}]
        result = deterministic_sample(data, 10, "id")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# select_strategy
# ---------------------------------------------------------------------------


class TestSelectStrategy:
    def test_reproducible_selects_deterministic(self):
        assert select_strategy(10000, need_reproducible=True) == SamplingStrategy.DETERMINISTIC

    def test_streaming_selects_reservoir(self):
        assert select_strategy(10000, is_streaming=True) == SamplingStrategy.RESERVOIR

    def test_stratified_for_large_data_with_column(self):
        assert select_strategy(10000, has_strata_column=True) == SamplingStrategy.STRATIFIED

    def test_systematic_for_large_data(self):
        assert select_strategy(200_000) == SamplingStrategy.SYSTEMATIC

    def test_random_for_small_data(self):
        assert select_strategy(100) == SamplingStrategy.RANDOM


# ---------------------------------------------------------------------------
# sample_table (integration)
# ---------------------------------------------------------------------------


class TestSampleTable:
    def test_empty_data(self):
        result = sample_table([])
        assert result.data == []
        assert result.stats.total_rows == 0

    def test_random_strategy(self):
        data = [{"val": i} for i in range(100)]
        result = sample_table(data, strategy=SamplingStrategy.RANDOM, sample_size=10, seed=42)
        assert len(result.data) == 10
        assert result.stats.strategy == SamplingStrategy.RANDOM

    def test_systematic_strategy(self):
        data = [{"val": i} for i in range(100)]
        result = sample_table(data, strategy=SamplingStrategy.SYSTEMATIC, sample_size=10, seed=42)
        assert len(result.data) == 10

    def test_stratified_strategy(self):
        data = [{"g": "A", "v": i} for i in range(50)] + [
            {"g": "B", "v": i} for i in range(50)
        ]
        result = sample_table(
            data, strategy=SamplingStrategy.STRATIFIED, sample_size=20,
            strata_column="g", seed=42
        )
        assert len(result.data) <= 20
        assert result.stats.strata_info

    def test_reservoir_strategy(self):
        data = [{"val": i} for i in range(100)]
        result = sample_table(data, strategy=SamplingStrategy.RESERVOIR, sample_size=10, seed=42)
        assert len(result.data) == 10

    def test_adaptive_strategy(self):
        data = [{"val": i} for i in range(100)]
        result = sample_table(data, strategy=SamplingStrategy.ADAPTIVE, sample_size=10)
        assert len(result.data) <= 10

    def test_auto_sample_size(self):
        data = [{"val": i} for i in range(10000)]
        result = sample_table(data, sample_size=None)
        assert result.stats.sample_size > 0

    def test_stats_to_dict(self):
        data = [{"val": i} for i in range(100)]
        result = sample_table(data, sample_size=10, seed=42)
        d = result.stats.to_dict()
        assert "total_rows" in d
        assert "sample_size" in d
        assert "sampling_rate" in d
        assert "strategy" in d

    def test_result_to_dict(self):
        data = [{"val": i} for i in range(100)]
        result = sample_table(data, sample_size=10, seed=42)
        d = result.to_dict()
        assert "data_preview" in d
        assert "stats" in d


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


class TestQuickSample:
    def test_small_data_returned_as_is(self):
        data = [{"val": i} for i in range(10)]
        result = quick_sample(data, max_rows=100)
        assert len(result) == 10

    def test_large_data_sampled(self):
        data = [{"val": i} for i in range(20000)]
        result = quick_sample(data, max_rows=1000)
        assert len(result) <= 1000


class TestShouldSample:
    def test_below_threshold(self):
        assert should_sample(10000, threshold=50000) is False

    def test_above_threshold(self):
        assert should_sample(100000, threshold=50000) is True
