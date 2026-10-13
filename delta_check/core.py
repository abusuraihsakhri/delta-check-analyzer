"""Core Reference Change Value (RCV) delta-check calculations.

Implements the RCV formula from Fraser's biological variation theory
(Fraser CG, "Biological Variation: From Principles to Practice", AACC
Press, 2001):

    RCV = sqrt(2) * z * sqrt(CVa^2 + CVi^2)

where:
  - CVa is the analytical coefficient of variation of the assay,
  - CVi is the within-subject (intra-individual) biological coefficient
    of variation of the analyte,
  - z is the standard normal deviate for the desired confidence level
    (1.96 for 95%, 2.576 for 99%),
  - the leading sqrt(2) accounts for the fact that each result carries
    its own independent analytical + within-subject noise, so the
    variance of the *difference* between two results is twice the
    variance of a single result.

RCV is the smallest percent (or, for near-zero-baseline analytes,
absolute) change between two successive results from the same patient
that is unlikely to be explained by analytical and biological noise
alone, at the chosen confidence level.
"""
import math
from dataclasses import dataclass
from typing import Optional

# Two-tailed critical z-values for common delta-check confidence levels.
Z_SCORES = {
    0.95: 1.96,
    0.99: 2.576,
}

DEFAULT_REFERENCE_INTERVAL_HOURS = 24.0


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function, computed from
    the error function (math.erf) so no external stats library is
    required."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def rcv_sd_units(cvi: float, cva: float) -> float:
    """sqrt(2) * sqrt(CVa^2 + CVi^2): the standard deviation, in percent,
    of the difference between two successive results. Shared by the RCV
    threshold and the probability-of-true-change calculation."""
    return math.sqrt(2.0) * math.sqrt(cva ** 2 + cvi ** 2)


def rcv_percent(cvi: float, cva: float, confidence: float = 0.95) -> float:
    """Reference Change Value, in percent: RCV = sqrt(2) * z * sqrt(CVa^2 + CVi^2)."""
    if confidence not in Z_SCORES:
        raise ValueError(f"Unsupported confidence level {confidence}; use one of {sorted(Z_SCORES)}")
    if not all(math.isfinite(value) and value >= 0 for value in (cvi, cva)):
        raise ValueError("CVi and CVa must be finite, non-negative percentages")
    z = Z_SCORES[confidence]
    return z * rcv_sd_units(cvi, cva)


def time_weighted_cvi(
    cvi: float,
    interval_hours: float,
    reference_interval_hours: float = DEFAULT_REFERENCE_INTERVAL_HOURS,
) -> float:
    """Scale the within-subject CV for the elapsed interval between draws.

    Published CVi values are estimated from samples collected at
    roughly steady-state, day-to-day intervals. Modeling within-subject
    biological fluctuation as an unbiased random walk, its variance
    accumulates in proportion to elapsed time, so the CV grows with
    sqrt(time). An interval shorter than the reference interval
    therefore tightens the effective CVi (and RCV); a longer interval
    widens it, reflecting the greater physiological drift possible over
    a longer gap between draws.
    """
    if not math.isfinite(interval_hours) or interval_hours <= 0:
        raise ValueError("interval_hours must be finite and positive")
    if not math.isfinite(reference_interval_hours) or reference_interval_hours <= 0:
        raise ValueError("reference_interval_hours must be finite and positive")
    if not math.isfinite(cvi) or cvi < 0:
        raise ValueError("CVi must be finite and non-negative")
    return cvi * math.sqrt(interval_hours / reference_interval_hours)


def time_weighted_rcv_percent(
    cvi: float,
    cva: float,
    interval_hours: float,
    confidence: float = 0.95,
    reference_interval_hours: float = DEFAULT_REFERENCE_INTERVAL_HOURS,
) -> float:
    """RCV percent using a CVi scaled for the interval between draws."""
    effective_cvi = time_weighted_cvi(cvi, interval_hours, reference_interval_hours)
    return rcv_percent(effective_cvi, cva, confidence)


def percent_change(prior: float, current: float) -> float:
    if not math.isfinite(prior) or not math.isfinite(current):
        raise ValueError("Prior and current values must be finite")
    if prior == 0:
        raise ValueError("prior value is zero; percent change is undefined (use absolute_change instead)")
    return (current - prior) / prior * 100.0


def probability_of_true_change(observed_percent_change: float, cvi: float, cva: float) -> float:
    """Legacy significance score (1 - two-sided p-value), NOT the posterior
    probability of a true biological change. The function name is retained
    for compatibility. A probability of true change requires a prior model.
    """
    rcv_percent(cvi, cva)  # validate coefficients
    if not math.isfinite(observed_percent_change):
        raise ValueError("Observed change must be finite")
    sd = rcv_sd_units(cvi, cva)
    if sd == 0:
        return 1.0 if observed_percent_change != 0 else 0.0
    z_obs = abs(observed_percent_change) / sd
    p_by_chance = 2.0 * (1.0 - normal_cdf(z_obs))  # two-tailed p-value
    return 1.0 - p_by_chance


@dataclass
class DeltaCheckResult:
    analyte: str
    prior_value: float
    current_value: float
    percent_change: float
    absolute_change: float
    rcv_percent: float
    confidence: float
    interval_hours: Optional[float]
    flagged: bool
    probability_true_change: float

    def to_dict(self) -> dict:
        return {
            "analyte": self.analyte,
            "prior_value": self.prior_value,
            "current_value": self.current_value,
            "percent_change": round(self.percent_change, 3),
            "absolute_change": round(self.absolute_change, 3),
            "rcv_percent": round(self.rcv_percent, 3),
            "confidence": self.confidence,
            "interval_hours": round(self.interval_hours, 3) if self.interval_hours is not None else None,
            "flagged": self.flagged,
            "probability_true_change": round(self.probability_true_change, 4),
            "two_sided_p_value": round(1.0 - self.probability_true_change, 4),
        }


def evaluate_pair(
    analyte: str,
    cvi: float,
    cva: float,
    prior_value: float,
    current_value: float,
    confidence: float = 0.95,
    interval_hours: Optional[float] = None,
    reference_interval_hours: float = DEFAULT_REFERENCE_INTERVAL_HOURS,
) -> DeltaCheckResult:
    """Evaluate one prior/current result pair for a delta-check flag.

    If interval_hours is given, the RCV is time-weighted for the gap
    between draws; otherwise the standard (untimed) RCV is used.
    """
    # The relative RCV model cannot evaluate a zero baseline.
    pct_change = percent_change(prior_value, current_value)
    abs_change = current_value - prior_value
    if interval_hours is not None:
        rcv = time_weighted_rcv_percent(cvi, cva, interval_hours, confidence, reference_interval_hours)
    else:
        rcv = rcv_percent(cvi, cva, confidence)
    flagged = abs(pct_change) > rcv
    effective_cvi = (time_weighted_cvi(cvi, interval_hours, reference_interval_hours)
                     if interval_hours is not None else cvi)
    prob = probability_of_true_change(pct_change, effective_cvi, cva)
    return DeltaCheckResult(
        analyte=analyte,
        prior_value=prior_value,
        current_value=current_value,
        percent_change=pct_change,
        absolute_change=abs_change,
        rcv_percent=rcv,
        confidence=confidence,
        interval_hours=interval_hours,
        flagged=flagged,
        probability_true_change=prob,
    )
