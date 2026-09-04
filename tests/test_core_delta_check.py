"""
Focused tests for core delta check functionality.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from delta_check.analyzer import (
    absolute_delta,
    percent_delta,
    rate_delta,
    check_fixed_limits,
    check_rcv,
    delta_check,
    FIXED_DELTA_LIMITS,
)
from delta_check.core import (
    rcv_percent,
    rcv_sd_units,
    time_weighted_rcv_percent,
    time_weighted_cvi,
    percent_change,
    probability_of_true_change,
    evaluate_pair,
    DeltaCheckResult,
)


class TestAbsoluteDelta:
    def test_positive_change(self):
        assert absolute_delta(145.0, 140.0) == 5.0

    def test_negative_change(self):
        assert absolute_delta(140.0, 145.0) == 5.0

    def test_no_change(self):
        assert absolute_delta(140.0, 140.0) == 0.0

    def test_decimal_values(self):
        assert absolute_delta(1.5, 1.0) == 0.5


class TestPercentDelta:
    def test_positive_change(self):
        assert percent_delta(145.0, 140.0) == pytest.approx(3.571, rel=1e-2)

    def test_negative_change(self):
        # |140-145|/145 * 100 = 3.448%
        assert percent_delta(140.0, 145.0) == pytest.approx(3.448, rel=1e-2)

    def test_zero_previous_raises(self):
        with pytest.raises(ValueError, match="Previous value is zero"):
            percent_delta(145.0, 0.0)


class TestRateDelta:
    def test_positive_rate(self):
        assert rate_delta(145.0, 140.0, 5.0) == 1.0

    def test_negative_rate(self):
        assert rate_delta(140.0, 145.0, 5.0) == -1.0

    def test_zero_time_raises(self):
        with pytest.raises(ValueError, match="Time between results must be positive"):
            rate_delta(145.0, 140.0, 0.0)

    def test_negative_time_raises(self):
        with pytest.raises(ValueError, match="Time between results must be positive"):
            rate_delta(145.0, 140.0, -1.0)


class TestFixedLimits:
    def test_sodium_within_limits(self):
        result = check_fixed_limits("sodium", 142.0, 140.0)
        assert result["flagged"] is False
        assert result["absolute_flagged"] is False
        assert result["percent_flagged"] is False

    def test_sodium_exceeds_absolute(self):
        result = check_fixed_limits("sodium", 145.0, 140.0)
        assert result["flagged"] is True
        assert result["absolute_flagged"] is True

    def test_potassium_exceeds_percent(self):
        result = check_fixed_limits("potassium", 5.0, 4.0)
        assert result["flagged"] is True
        assert result["percent_flagged"] is True

    def test_unknown_analyte(self):
        result = check_fixed_limits("unknown_analyte", 100.0, 90.0)
        assert result["flagged"] is None
        assert "error" in result

    def test_case_insensitive(self):
        result = check_fixed_limits("Sodium", 142.0, 140.0)
        assert result["flagged"] is False

    def test_space_replacement(self):
        result = check_fixed_limits("total protein", 7.0, 6.8)
        assert result["flagged"] is False


class TestRCV:
    def test_rcv_percent_calculation(self):
        # sodium: CVi=0.6, CVa=0.5, z=1.96 for 95%
        result = rcv_percent(0.6, 0.5, 0.95)
        expected = 1.96 * (2 ** 0.5) * ((0.6 ** 2 + 0.5 ** 2) ** 0.5)
        assert result == pytest.approx(expected, rel=1e-3)

    def test_rcv_unsupported_confidence(self):
        with pytest.raises(ValueError, match="Unsupported confidence level"):
            rcv_percent(0.6, 0.5, 0.80)

    def test_time_weighted_cvi(self):
        # At reference interval, should equal original CVi
        result = time_weighted_cvi(5.0, 24.0, 24.0)
        assert result == pytest.approx(5.0, rel=1e-3)

    def test_time_weighted_cvi_shorter_interval(self):
        # Shorter interval should reduce CVi
        result = time_weighted_cvi(5.0, 6.0, 24.0)
        assert result < 5.0

    def test_time_weighted_cvi_zero_interval_raises(self):
        with pytest.raises(ValueError, match="interval_hours must be positive"):
            time_weighted_cvi(5.0, 0.0, 24.0)


class TestEvaluatePair:
    def test_no_flag_within_rcv(self):
        result = evaluate_pair("sodium", 0.6, 0.5, 140.0, 141.0, confidence=0.95)
        assert isinstance(result, DeltaCheckResult)
        assert result.flagged is False

    def test_flag_exceeds_rcv(self):
        result = evaluate_pair("sodium", 0.6, 0.5, 140.0, 150.0, confidence=0.95)
        assert result.flagged is True

    def test_probability_range(self):
        result = evaluate_pair("sodium", 0.6, 0.5, 140.0, 141.0, confidence=0.95)
        assert 0.0 <= result.probability_true_change <= 1.0

    def test_to_dict(self):
        result = evaluate_pair("sodium", 0.6, 0.5, 140.0, 141.0, confidence=0.95)
        d = result.to_dict()
        assert "analyte" in d
        assert "flagged" in d
        assert "probability_true_change" in d


class TestDeltaCheck:
    def test_combined_check_flagged(self):
        result = delta_check("sodium", 145.0, 140.0, method="both")
        assert result["flagged"] is True
        assert "fixed_limit" in result["flags_triggered"]
        assert "rcv" in result["flags_triggered"]

    def test_combined_check_passed(self):
        result = delta_check("sodium", 141.0, 140.0, method="both")
        assert result["flagged"] is False

    def test_fixed_only(self):
        result = delta_check("sodium", 145.0, 140.0, method="fixed")
        assert "fixed_limit_check" in result
        assert "rcv_check" not in result

    def test_rcv_only(self):
        result = delta_check("sodium", 145.0, 140.0, method="rcv")
        assert "rcv_check" in result
        assert "fixed_limit_check" not in result

    def test_with_time_hours(self):
        result = delta_check("sodium", 145.0, 140.0, time_hours=6.0)
        assert "rate_delta_per_hour" in result
        assert result["time_hours"] == 6.0

    def test_zero_previous_percent_delta(self):
        result = delta_check("sodium", 145.0, 0.0)
        assert isinstance(result["percent_delta"], str)
        assert "undefined" in result["percent_delta"]

    def test_fixed_limits_zero_previous(self):
        result = check_fixed_limits("sodium", 145.0, 0.0)
        assert result["percent_delta"] == "undefined (previous=0)"
        assert result["flagged"] is True  # absolute delta exceeds limit


class TestFixedDeltaLimitsTable:
    def test_all_entries_have_required_keys(self):
        required_keys = {"absolute_limit", "percent_limit", "unit", "within_subject_cv", "analytical_cv"}
        for analyte, info in FIXED_DELTA_LIMITS.items():
            assert required_keys.issubset(info.keys()), f"Missing keys for {analyte}"

    def test_all_limits_positive(self):
        for analyte, info in FIXED_DELTA_LIMITS.items():
            assert info["absolute_limit"] > 0, f"{analyte} absolute_limit must be positive"
            assert info["percent_limit"] > 0, f"{analyte} percent_limit must be positive"
