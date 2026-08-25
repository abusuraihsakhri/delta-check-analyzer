"""Delta Check Analyzer: flag clinically significant changes between
paired lab results using Reference Change Value (RCV) statistics
and fixed-limit clinical thresholds.
"""
from .core import (
    rcv_percent,
    rcv_sd_units,
    time_weighted_rcv_percent,
    time_weighted_cvi,
    percent_change,
    probability_of_true_change,
    evaluate_pair,
    DeltaCheckResult,
)
from .reference_table import DEFAULT_REFERENCE_TABLE, load_reference_table, save_reference_table
from .analyzer import (
    absolute_delta,
    percent_delta,
    rate_delta,
    check_fixed_limits,
    check_rcv,
    delta_check,
    process_batch,
    FIXED_DELTA_LIMITS,
)

__all__ = [
    # Core RCV
    "rcv_percent",
    "rcv_sd_units",
    "time_weighted_rcv_percent",
    "time_weighted_cvi",
    "percent_change",
    "probability_of_true_change",
    "evaluate_pair",
    "DeltaCheckResult",
    # Reference table
    "DEFAULT_REFERENCE_TABLE",
    "load_reference_table",
    "save_reference_table",
    # Analyzer
    "absolute_delta",
    "percent_delta",
    "rate_delta",
    "check_fixed_limits",
    "check_rcv",
    "delta_check",
    "process_batch",
    "FIXED_DELTA_LIMITS",
]
