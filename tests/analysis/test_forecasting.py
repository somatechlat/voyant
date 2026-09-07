"""Tests for apps.analysis.lib.forecasting — pure forecasting engine."""


import pytest

from apps.analysis.lib.forecasting import (
    ExponentialSmoothingForecaster,
    ForecastPoint,
    ForecastResult,
    LinearTrendForecaster,
    MovingAverageForecaster,
    NaiveForecaster,
    detect_trend,
    forecast,
    get_available_methods,
)

# ---------------------------------------------------------------------------
# ForecastPoint
# ---------------------------------------------------------------------------


class TestForecastPoint:
    def test_to_dict(self):
        p = ForecastPoint(period=1, value=10.5, lower_bound=8.0, upper_bound=13.0)
        d = p.to_dict()
        assert d["period"] == 1
        assert d["value"] == 10.5
        assert d["lower_bound"] == 8.0
        assert d["upper_bound"] == 13.0

    def test_to_dict_with_date(self):
        p = ForecastPoint(period=1, value=10.0, lower_bound=8.0, upper_bound=12.0, date="2024-01-01")
        d = p.to_dict()
        assert d["date"] == "2024-01-01"


# ---------------------------------------------------------------------------
# ForecastResult
# ---------------------------------------------------------------------------


class TestForecastResult:
    def test_to_dict(self):
        result = ForecastResult(
            predictions=[ForecastPoint(1, 10.0, 8.0, 12.0)],
            method="naive",
            periods=1,
            confidence_level=0.95,
            stats={"last_value": 10.0},
        )
        d = result.to_dict()
        assert d["method"] == "naive"
        assert d["periods"] == 1
        assert len(d["predictions"]) == 1


# ---------------------------------------------------------------------------
# NaiveForecaster
# ---------------------------------------------------------------------------


class TestNaiveForecaster:
    def test_repeats_last_value(self):
        f = NaiveForecaster()
        result = f.forecast([1.0, 2.0, 3.0, 4.0, 5.0], periods=3)
        assert len(result.predictions) == 3
        for p in result.predictions:
            assert p.value == 5.0

    def test_empty_values(self):
        f = NaiveForecaster()
        result = f.forecast([], periods=3)
        assert result.predictions == []

    def test_confidence_intervals_widen(self):
        f = NaiveForecaster(confidence_level=0.95)
        result = f.forecast([1.0, 2.0, 3.0], periods=5)
        # Uncertainty should grow with horizon
        widths = [p.upper_bound - p.lower_bound for p in result.predictions]
        assert widths[-1] > widths[0]

    def test_method_name(self):
        assert NaiveForecaster().method_name == "naive"


# ---------------------------------------------------------------------------
# MovingAverageForecaster
# ---------------------------------------------------------------------------


class TestMovingAverageForecaster:
    def test_basic_forecast(self):
        f = MovingAverageForecaster(window=3)
        result = f.forecast([1.0, 2.0, 3.0, 4.0, 5.0], periods=2)
        assert len(result.predictions) == 2
        # Average of last 3: (3+4+5)/3 = 4.0
        assert abs(result.predictions[0].value - 4.0) < 0.01

    def test_window_larger_than_data(self):
        f = MovingAverageForecaster(window=100)
        result = f.forecast([1.0, 2.0, 3.0], periods=1)
        # Should use all available values
        assert abs(result.predictions[0].value - 2.0) < 0.01

    def test_insufficient_data(self):
        f = MovingAverageForecaster()
        result = f.forecast([1.0], periods=3)
        assert result.predictions == []

    def test_method_name(self):
        assert MovingAverageForecaster().method_name == "sma"


# ---------------------------------------------------------------------------
# ExponentialSmoothingForecaster
# ---------------------------------------------------------------------------


class TestExponentialSmoothingForecaster:
    def test_basic_forecast(self):
        f = ExponentialSmoothingForecaster(alpha=0.3)
        result = f.forecast([10.0, 20.0, 30.0, 40.0, 50.0], periods=3)
        assert len(result.predictions) == 3
        assert result.stats["alpha"] == 0.3

    def test_alpha_clamping(self):
        f = ExponentialSmoothingForecaster(alpha=0.0)
        assert f.alpha == 0.01
        f2 = ExponentialSmoothingForecaster(alpha=1.0)
        assert f2.alpha == 0.99

    def test_insufficient_data(self):
        f = ExponentialSmoothingForecaster()
        result = f.forecast([1.0], periods=3)
        assert result.predictions == []

    def test_high_alpha_weights_recent(self):
        f = ExponentialSmoothingForecaster(alpha=0.9)
        result = f.forecast([10.0, 10.0, 10.0, 10.0, 100.0], periods=1)
        # With high alpha, should be close to last value
        assert result.predictions[0].value > 50.0

    def test_method_name(self):
        assert ExponentialSmoothingForecaster().method_name == "ema"


# ---------------------------------------------------------------------------
# LinearTrendForecaster
# ---------------------------------------------------------------------------


class TestLinearTrendForecaster:
    def test_linear_trend(self):
        f = LinearTrendForecaster()
        values = [float(i * 2) for i in range(20)]  # y = 2x
        result = f.forecast(values, periods=5)
        assert len(result.predictions) == 5
        # Slope should be approximately 2
        assert abs(result.stats["slope"] - 2.0) < 0.1

    def test_decreasing_trend(self):
        f = LinearTrendForecaster()
        values = [float(100 - i) for i in range(20)]
        result = f.forecast(values, periods=3)
        assert result.stats["trend"] == "decreasing"

    def test_insufficient_data(self):
        f = LinearTrendForecaster()
        result = f.forecast([1.0, 2.0], periods=3)
        assert result.predictions == []

    def test_method_name(self):
        assert LinearTrendForecaster().method_name == "linear"

    def test_flat_trend(self):
        f = LinearTrendForecaster()
        values = [5.0] * 20
        result = f.forecast(values, periods=3)
        assert result.stats["trend"] == "flat"


# ---------------------------------------------------------------------------
# forecast (main API)
# ---------------------------------------------------------------------------


class TestForecastAPI:
    def test_naive_method(self):
        result = forecast([1.0, 2.0, 3.0], periods=2, method="naive")
        assert result.method == "naive"

    def test_sma_method(self):
        result = forecast([1.0, 2.0, 3.0, 4.0, 5.0], periods=2, method="sma")
        assert result.method == "sma"

    def test_ema_method(self):
        result = forecast([1.0, 2.0, 3.0, 4.0, 5.0], periods=2, method="ema")
        assert result.method == "ema"

    def test_linear_method(self):
        result = forecast([1.0, 2.0, 3.0, 4.0, 5.0], periods=2, method="linear")
        assert result.method == "linear"

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown method"):
            forecast([1.0, 2.0], method="nonexistent")

    def test_with_dates(self):
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        result = forecast([1.0, 2.0, 3.0], periods=2, method="naive", dates=dates)
        assert result.method == "naive"


# ---------------------------------------------------------------------------
# get_available_methods
# ---------------------------------------------------------------------------


class TestGetAvailableMethods:
    def test_returns_all_methods(self):
        methods = get_available_methods()
        assert "naive" in methods
        assert "sma" in methods
        assert "ema" in methods
        assert "linear" in methods


# ---------------------------------------------------------------------------
# detect_trend
# ---------------------------------------------------------------------------


class TestDetectTrend:
    def test_increasing_trend(self):
        values = [float(i) for i in range(20)]
        result = detect_trend(values)
        assert result["direction"] == "up"
        assert result["slope"] > 0

    def test_decreasing_trend(self):
        values = [float(20 - i) for i in range(20)]
        result = detect_trend(values)
        assert result["direction"] == "down"
        assert result["slope"] < 0

    def test_flat_trend(self):
        values = [5.0] * 20
        result = detect_trend(values)
        assert result["direction"] == "flat"

    def test_too_few_values(self):
        result = detect_trend([1.0, 2.0])
        assert result["direction"] == "flat"
        assert result["slope"] == 0

    def test_strength_range(self):
        values = [float(i) for i in range(20)]
        result = detect_trend(values)
        assert 0.0 <= result["strength"] <= 1.0
