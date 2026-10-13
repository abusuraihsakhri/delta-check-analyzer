"""Regression tests for numerical validation and audit-log integrity."""
import math
import pytest

from agents.base import AuditTrail
from delta_check.analyzer import delta_check, check_fixed_limits
from delta_check.core import evaluate_pair, rcv_percent, time_weighted_cvi


def test_hmac_verifier_recomputes_signatures():
    trail = AuditTrail(secret_key="test-only-secret")
    trail.log("tester", "internal", "event", {"status": "OK"})
    assert trail.verify_integrity()
    # A copy is returned; callers must not alter the real trail.
    trail.get_trail()[0]["actor"] = "attacker"
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "attacker"
    assert not trail.verify_integrity()


def test_hmac_verifier_detects_replaced_hash():
    trail = AuditTrail(secret_key="test-only-secret")
    trail.log("tester", "internal", "first", {"status": "OK"})
    trail.log("tester", "internal", "second", {"status": "OK"})
    trail.logs[0]["current_hash"] = "0" * 64
    trail.logs[1]["prev_hash"] = "0" * 64
    assert not trail.verify_integrity()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_lab_values_are_rejected(value):
    with pytest.raises(ValueError):
        delta_check("sodium", value, 140)
    with pytest.raises(ValueError):
        check_fixed_limits("sodium", 140, value)
    with pytest.raises(ValueError):
        evaluate_pair("sodium", 0.6, 0.5, 140, value)


def test_unsupported_method_and_incomplete_evaluation():
    with pytest.raises(ValueError):
        delta_check("sodium", 145, 140, method="noop")
    result = delta_check("troponin_t", 0.5, 0.1)
    assert result["flagged"] is None
    assert result["fully_evaluated"] is False
    assert "incomplete" in result["recommendation"]


def test_zero_previous_rcv_is_not_a_pass():
    result = delta_check("sodium", 0, 0, method="both")
    assert result["flagged"] is None
    assert result["fully_evaluated"] is False


@pytest.mark.parametrize("cvi,cva", [(-1,1),(1,-2),(float("nan"),2),(1,float("inf"))])
def test_invalid_cv_is_rejected(cvi,cva):
    with pytest.raises(ValueError):
        rcv_percent(cvi,cva)


@pytest.mark.parametrize("hours", [0,-1,float("nan"),float("inf")])
def test_invalid_reference_interval_is_rejected(hours):
    with pytest.raises(ValueError):
        time_weighted_cvi(5,6,reference_interval_hours=hours)


def test_timed_significance_uses_timed_variability():
    result = evaluate_pair("urea",12.3,3.0,100,120,interval_hours=6)
    untimed = evaluate_pair("urea",12.3,3.0,100,120)
    assert result.probability_true_change != untimed.probability_true_change
    assert result.to_dict()["two_sided_p_value"] == pytest.approx(
        round(1 - result.probability_true_change,4)
    )
