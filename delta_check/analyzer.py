#!/usr/bin/env python3
"""
Delta Check Analyzer — Lab Result Change Detection.

Implements multiple delta check approaches:
  1. Fixed-limit delta checks (common clinical lab thresholds)
  2. RCV-based delta checks (Reference Change Value from biological variation)
  3. Absolute, percent, and rate-of-change deltas

Common delta check limits (typical clinical lab values):
  Sodium:     ±4 mEq/L or ±3%
  Potassium:  ±0.5 mEq/L or ±15%
  Glucose:    ±30 mg/dL or ±20%
  Hemoglobin: ±1.5 g/dL or ±10%
  Creatinine: ±0.3 mg/dL or ±15%
  Calcium:    ±0.5 mg/dL or ±5%

RCV formula (Fraser):
  RCV = sqrt(2) × z × sqrt(CVa² + CVi²)

Zero-dependency Python stdlib implementation.
Author: Dr. Abu Suraih Sakhri
License: MIT
"""

import csv
import math
from typing import Dict, Any, Optional

# Import the RCV-based core
from .core import (
    evaluate_pair,
    DeltaCheckResult,
)
from .reference_table import DEFAULT_REFERENCE_TABLE


# ---------------------------------------------------------------------------
# Fixed-Limit Delta Check Table
# ---------------------------------------------------------------------------

# Each entry: (absolute_limit, percent_limit)
# A result is flagged if EITHER the absolute OR percent delta exceeds its limit.
FIXED_DELTA_LIMITS: Dict[str, Dict[str, Any]] = {
    "sodium": {
        "absolute_limit": 4.0,
        "percent_limit": 3.0,
        "unit": "mEq/L",
        "within_subject_cv": 0.6,
        "analytical_cv": 0.5,
    },
    "potassium": {
        "absolute_limit": 0.5,
        "percent_limit": 15.0,
        "unit": "mEq/L",
        "within_subject_cv": 4.8,
        "analytical_cv": 2.0,
    },
    "glucose": {
        "absolute_limit": 30.0,
        "percent_limit": 20.0,
        "unit": "mg/dL",
        "within_subject_cv": 5.7,
        "analytical_cv": 2.5,
    },
    "hemoglobin": {
        "absolute_limit": 1.5,
        "percent_limit": 10.0,
        "unit": "g/dL",
        "within_subject_cv": 2.8,
        "analytical_cv": 1.5,
    },
    "creatinine": {
        "absolute_limit": 0.3,
        "percent_limit": 15.0,
        "unit": "mg/dL",
        "within_subject_cv": 5.9,
        "analytical_cv": 2.2,
    },
    "calcium": {
        "absolute_limit": 0.5,
        "percent_limit": 5.0,
        "unit": "mg/dL",
        "within_subject_cv": 1.9,
        "analytical_cv": 1.0,
    },
    "bun": {
        "absolute_limit": 5.0,
        "percent_limit": 20.0,
        "unit": "mg/dL",
        "within_subject_cv": 12.3,
        "analytical_cv": 3.0,
    },
    "chloride": {
        "absolute_limit": 5.0,
        "percent_limit": 5.0,
        "unit": "mEq/L",
        "within_subject_cv": 1.2,
        "analytical_cv": 1.0,
    },
    "co2": {
        "absolute_limit": 4.0,
        "percent_limit": 10.0,
        "unit": "mEq/L",
        "within_subject_cv": 5.5,
        "analytical_cv": 3.0,
    },
    "wbc": {
        "absolute_limit": 3.0,
        "percent_limit": 20.0,
        "unit": "×10³/µL",
        "within_subject_cv": 9.6,
        "analytical_cv": 3.0,
    },
    "platelets": {
        "absolute_limit": 50.0,
        "percent_limit": 20.0,
        "unit": "×10³/µL",
        "within_subject_cv": 9.1,
        "analytical_cv": 4.0,
    },
    "albumin": {
        "absolute_limit": 0.5,
        "percent_limit": 10.0,
        "unit": "g/dL",
        "within_subject_cv": 3.1,
        "analytical_cv": 2.0,
    },
    "total_protein": {
        "absolute_limit": 0.5,
        "percent_limit": 10.0,
        "unit": "g/dL",
        "within_subject_cv": 2.4,
        "analytical_cv": 2.0,
    },
    "ast": {
        "absolute_limit": 20.0,
        "percent_limit": 30.0,
        "unit": "U/L",
        "within_subject_cv": 12.3,
        "analytical_cv": 5.0,
    },
    "alt": {
        "absolute_limit": 20.0,
        "percent_limit": 30.0,
        "unit": "U/L",
        "within_subject_cv": 19.4,
        "analytical_cv": 5.0,
    },
    "bilirubin": {
        "absolute_limit": 1.0,
        "percent_limit": 30.0,
        "unit": "mg/dL",
        "within_subject_cv": 23.5,
        "analytical_cv": 5.0,
    },
}


# ---------------------------------------------------------------------------
# Delta Calculations
# ---------------------------------------------------------------------------

def absolute_delta(current: float, previous: float) -> float:
    """Absolute delta = |current - previous|."""
    return abs(current - previous)


def percent_delta(current: float, previous: float) -> float:
    """Percent delta = |current - previous| / previous × 100."""
    if previous == 0:
        raise ValueError("Previous value is zero; percent delta is undefined.")
    return abs(current - previous) / abs(previous) * 100.0


def rate_delta(current: float, previous: float, time_hours: float) -> float:
    """Rate delta = (current - previous) / time_between_results (per hour)."""
    if time_hours <= 0:
        raise ValueError("Time between results must be positive.")
    return (current - previous) / time_hours


# ---------------------------------------------------------------------------
# Fixed-Limit Delta Check
# ---------------------------------------------------------------------------

def check_fixed_limits(
    analyte: str,
    current: float,
    previous: float,
) -> Dict[str, Any]:
    """
    Check delta against fixed clinical lab limits.

    Returns dict with deltas, limits, and flag status.
    """
    analyte_key = analyte.strip().lower().replace(" ", "_")

    if analyte_key not in FIXED_DELTA_LIMITS:
        return {
            "analyte": analyte,
            "current": current,
            "previous": previous,
            "error": f"Unknown analyte '{analyte}'. Available: {', '.join(sorted(FIXED_DELTA_LIMITS.keys()))}",
            "flagged": None,
        }

    limits = FIXED_DELTA_LIMITS[analyte_key]
    abs_delta = absolute_delta(current, previous)

    # Handle zero previous value: percent delta is undefined
    try:
        pct_delta = percent_delta(current, previous)
    except ValueError:
        pct_delta = None

    abs_flagged = abs_delta > limits["absolute_limit"]
    pct_flagged = pct_delta is not None and pct_delta > limits["percent_limit"]
    flagged = abs_flagged or pct_flagged

    result = {
        "analyte": analyte,
        "current": current,
        "previous": previous,
        "unit": limits["unit"],
        "absolute_delta": round(abs_delta, 3),
        "percent_delta": round(pct_delta, 3) if pct_delta is not None else "undefined (previous=0)",
        "absolute_limit": limits["absolute_limit"],
        "percent_limit": limits["percent_limit"],
        "absolute_flagged": abs_flagged,
        "percent_flagged": pct_flagged,
        "flagged": flagged,
    }

    if pct_delta is not None:
        result["interpretation"] = (
            f"DELTA CHECK FAILED: {analyte} changed by {abs_delta:.2f} {limits['unit']} "
            f"({pct_delta:.1f}%). Exceeds limit of ±{limits['absolute_limit']} {limits['unit']} "
            f"or ±{limits['percent_limit']}%. Possible specimen error, patient change, or treatment effect."
            if flagged else
            f"Delta check passed: {analyte} change ({abs_delta:.2f} {limits['unit']}, "
            f"{pct_delta:.1f}%) within acceptable limits."
        )
    else:
        result["interpretation"] = (
            f"DELTA CHECK: {analyte} changed by {abs_delta:.2f} {limits['unit']} "
            f"(percent delta undefined — previous value was zero). "
            f"{'Absolute delta exceeds limit.' if abs_flagged else 'Absolute delta within limit.'}"
        )

    return result


# ---------------------------------------------------------------------------
# RCV-Based Delta Check (wraps delta_check.core)
# ---------------------------------------------------------------------------

def check_rcv(
    analyte: str,
    current: float,
    previous: float,
    confidence: float = 0.95,
    interval_hours: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Check delta using Reference Change Value (RCV) from biological variation.

    Uses the RCV formula: RCV = sqrt(2) × z × sqrt(CVa² + CVi²)
    """
    analyte_key = analyte.strip().lower().replace(" ", "_")

    # Try to find in reference table
    table = DEFAULT_REFERENCE_TABLE
    if analyte_key not in table:
        # Try common aliases
        aliases = {
            "bun": "urea",
            "co2": "bicarbonate",
            "hemoglobin": "hemoglobin",
            "hgb": "hemoglobin",
            "wbc": "wbc",
            "plt": "platelets",
            "bilirubin": "total_bilirubin",
        }
        analyte_key = aliases.get(analyte_key, analyte_key)

    if analyte_key not in table:
        return {
            "analyte": analyte,
            "error": f"Analyte '{analyte}' not in biological variation database.",
            "flagged": None,
        }

    cvi, cva = table[analyte_key]

    # Handle zero previous value: percent change is undefined
    if previous == 0:
        return {
            "analyte": analyte,
            "current": current,
            "previous": previous,
            "error": "Previous value is zero; percent change is undefined for RCV evaluation.",
            "flagged": None,
        }

    result = evaluate_pair(
        analyte=analyte,
        cvi=cvi,
        cva=cva,
        prior_value=previous,
        current_value=current,
        confidence=confidence,
        interval_hours=interval_hours,
    )

    return {
        "analyte": result.analyte,
        "current": result.current_value,
        "previous": result.prior_value,
        "absolute_delta": round(result.absolute_change, 3),
        "percent_delta": round(result.percent_change, 3),
        "rcv_percent": round(result.rcv_percent, 3),
        "confidence": result.confidence,
        "interval_hours": result.interval_hours,
        "flagged": result.flagged,
        "probability_true_change": round(result.probability_true_change, 4),
        "interpretation": (
            f"RCV FLAG: {analyte} changed {result.percent_change:.1f}% "
            f"(RCV threshold: {result.rcv_percent:.1f}% at {confidence*100:.0f}% confidence). "
            f"Probability of true change: {result.probability_true_change:.1%}."
            if result.flagged else
            f"RCV passed: {analyte} change ({result.percent_change:.1f}%) within RCV "
            f"({result.rcv_percent:.1f}% at {confidence*100:.0f}% confidence)."
        ),
    }


# ---------------------------------------------------------------------------
# Combined Delta Check
# ---------------------------------------------------------------------------

def delta_check(
    analyte: str,
    current: float,
    previous: float,
    time_hours: Optional[float] = None,
    confidence: float = 0.95,
    method: str = "both",
) -> Dict[str, Any]:
    """
    Perform delta check using specified method(s).

    Args:
        analyte: Analyte name
        current: Current result
        previous: Previous result
        time_hours: Hours between results (for rate delta)
        confidence: RCV confidence level (0.95 or 0.99)
        method: 'fixed', 'rcv', or 'both'

    Returns:
        Comprehensive delta check result
    """
    result = {
        "analyte": analyte,
        "current": current,
        "previous": previous,
        "absolute_delta": round(absolute_delta(current, previous), 3),
    }

    try:
        result["percent_delta"] = round(percent_delta(current, previous), 3)
    except ValueError as e:
        result["percent_delta"] = str(e)

    if time_hours is not None:
        result["rate_delta_per_hour"] = round(rate_delta(current, previous, time_hours), 3)
        result["time_hours"] = time_hours

    if method in ("fixed", "both"):
        result["fixed_limit_check"] = check_fixed_limits(analyte, current, previous)

    if method in ("rcv", "both"):
        result["rcv_check"] = check_rcv(analyte, current, previous, confidence, time_hours)

    # Overall flag
    flags = []
    if method in ("fixed", "both") and result.get("fixed_limit_check", {}).get("flagged"):
        flags.append("fixed_limit")
    if method in ("rcv", "both") and result.get("rcv_check", {}).get("flagged"):
        flags.append("rcv")

    result["flagged"] = len(flags) > 0
    result["flags_triggered"] = flags

    if result["flagged"]:
        result["recommendation"] = (
            f"Delta check ALERT for {analyte}: flagged by {', '.join(flags)}. "
            "Verify specimen identity, check for clotted sample, "
            "review patient clinical status, and consider recollection if specimen error suspected."
        )
    else:
        result["recommendation"] = f"Delta check passed for {analyte}. No action required."

    return result


# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------

def process_batch(input_csv: str, output_csv: str, method: str = "both", confidence: float = 0.95) -> int:
    """
    Process a CSV of paired lab results.

    Expected columns: analyte, current, previous
    Optional: time_hours
    """
    with open(input_csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    out_fields = fieldnames + [
        "absolute_delta", "percent_delta", "flagged", "flags_triggered", "recommendation",
    ]
    out_rows = []

    for r in rows:
        try:
            analyte = r.get("analyte", "unknown")
            current = float(r["current"])
            previous = float(r["previous"])
            time_h = float(r["time_hours"]) if r.get("time_hours") else None

            result = delta_check(analyte, current, previous, time_h, confidence, method)

            row_dict = dict(r)
            row_dict["absolute_delta"] = result["absolute_delta"]
            row_dict["percent_delta"] = result.get("percent_delta", "")
            row_dict["flagged"] = result["flagged"]
            row_dict["flags_triggered"] = ", ".join(result["flags_triggered"])
            row_dict["recommendation"] = result["recommendation"]
        except (ValueError, KeyError) as e:
            row_dict = dict(r)
            row_dict["absolute_delta"] = f"ERROR: {e}"
            row_dict["percent_delta"] = ""
            row_dict["flagged"] = ""
            row_dict["flags_triggered"] = ""
            row_dict["recommendation"] = ""

        out_rows.append(row_dict)

    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    return len(out_rows)
