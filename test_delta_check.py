#!/usr/bin/env python3
"""Tests for Delta Check Analyzer — both fixed-limit and RCV-based approaches."""
import math
import os
import tempfile
import unittest

from delta_check.analyzer import (
    absolute_delta,
    percent_delta,
    rate_delta,
    check_fixed_limits,
    check_rcv,
    delta_check,
    process_batch,
    FIXED_DELTA_LIMITS,
)
from delta_check.core import (
    rcv_percent,
    rcv_sd_units,
    time_weighted_rcv_percent,
    probability_of_true_change,
    evaluate_pair,
)
from delta_check.reference_table import DEFAULT_REFERENCE_TABLE, load_reference_table


# ---------------------------------------------------------------------------
# Basic Delta Calculations
# ---------------------------------------------------------------------------

class TestAbsoluteDelta(unittest.TestCase):
    def test_positive_change(self):
        self.assertAlmostEqual(absolute_delta(150, 140), 10.0)

    def test_negative_change(self):
        self.assertAlmostEqual(absolute_delta(130, 140), 10.0)

    def test_no_change(self):
        self.assertAlmostEqual(absolute_delta(140, 140), 0.0)


class TestPercentDelta(unittest.TestCase):
    def test_increase(self):
        self.assertAlmostEqual(percent_delta(110, 100), 10.0)

    def test_decrease(self):
        self.assertAlmostEqual(percent_delta(90, 100), 10.0)

    def test_zero_previous_raises(self):
        with self.assertRaises(ValueError):
            percent_delta(5, 0)


class TestRateDelta(unittest.TestCase):
    def test_rate_basic(self):
        self.assertAlmostEqual(rate_delta(140, 130, 5), 2.0)

    def test_negative_time_raises(self):
        with self.assertRaises(ValueError):
            rate_delta(140, 130, 0)


# ---------------------------------------------------------------------------
# Fixed-Limit Delta Checks
# ---------------------------------------------------------------------------

class TestFixedLimits(unittest.TestCase):
    def test_sodium_within_limits(self):
        result = check_fixed_limits("sodium", 141, 140)
        self.assertFalse(result["flagged"])

    def test_sodium_exceeds_absolute(self):
        # |145 - 140| = 5 > 4 mEq/L limit
        result = check_fixed_limits("sodium", 145, 140)
        self.assertTrue(result["flagged"])
        self.assertTrue(result["absolute_flagged"])

    def test_sodium_exceeds_percent(self):
        # |146 - 140| / 140 * 100 = 4.3% > 3% limit
        result = check_fixed_limits("sodium", 146, 140)
        self.assertTrue(result["flagged"])

    def test_potassium_within_limits(self):
        result = check_fixed_limits("potassium", 4.2, 4.0)
        self.assertFalse(result["flagged"])

    def test_potassium_exceeds_absolute(self):
        # |5.0 - 4.0| = 1.0 > 0.5 limit
        result = check_fixed_limits("potassium", 5.0, 4.0)
        self.assertTrue(result["flagged"])
        self.assertTrue(result["absolute_flagged"])

    def test_glucose_within_limits(self):
        result = check_fixed_limits("glucose", 130, 120)
        self.assertFalse(result["flagged"])

    def test_glucose_exceeds_absolute(self):
        # |200 - 120| = 80 > 30 limit
        result = check_fixed_limits("glucose", 200, 120)
        self.assertTrue(result["flagged"])

    def test_hemoglobin_within_limits(self):
        result = check_fixed_limits("hemoglobin", 12.5, 12.0)
        self.assertFalse(result["flagged"])

    def test_hemoglobin_exceeds(self):
        # |10.0 - 12.0| = 2.0 > 1.5 limit
        result = check_fixed_limits("hemoglobin", 10.0, 12.0)
        self.assertTrue(result["flagged"])

    def test_creatinine_within_limits(self):
        result = check_fixed_limits("creatinine", 1.1, 1.0)
        self.assertFalse(result["flagged"])

    def test_creatinine_exceeds(self):
        # |1.5 - 1.0| = 0.5 > 0.3 limit
        result = check_fixed_limits("creatinine", 1.5, 1.0)
        self.assertTrue(result["flagged"])

    def test_calcium_within_limits(self):
        result = check_fixed_limits("calcium", 9.5, 9.3)
        self.assertFalse(result["flagged"])

    def test_calcium_exceeds(self):
        # |10.5 - 9.5| = 1.0 > 0.5 limit
        result = check_fixed_limits("calcium", 10.5, 9.5)
        self.assertTrue(result["flagged"])

    def test_unknown_analyte(self):
        result = check_fixed_limits("troponin", 0.5, 0.1)
        self.assertIn("error", result)
        self.assertIsNone(result["flagged"])

    def test_interpretation_included(self):
        result = check_fixed_limits("sodium", 145, 140)
        self.assertIn("interpretation", result)


# ---------------------------------------------------------------------------
# RCV-Based Delta Checks
# ---------------------------------------------------------------------------

class TestRCVCheck(unittest.TestCase):
    def test_sodium_small_change_not_flagged(self):
        result = check_rcv("sodium", 141, 140)
        self.assertFalse(result["flagged"])

    def test_sodium_large_change_flagged(self):
        result = check_rcv("sodium", 145, 140)
        self.assertTrue(result["flagged"])

    def test_creatinine_30_percent_flagged(self):
        result = check_rcv("creatinine", 1.3, 1.0)
        self.assertTrue(result["flagged"])

    def test_creatinine_10_percent_not_flagged(self):
        result = check_rcv("creatinine", 1.1, 1.0)
        self.assertFalse(result["flagged"])

    def test_probability_in_result(self):
        result = check_rcv("glucose", 150, 120)
        self.assertIn("probability_true_change", result)

    def test_unknown_analyte(self):
        result = check_rcv("troponin_t", 0.5, 0.1)
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# Combined Delta Check
# ---------------------------------------------------------------------------

class TestCombinedDeltaCheck(unittest.TestCase):
    def test_both_pass(self):
        result = delta_check("sodium", 141, 140, method="both")
        self.assertFalse(result["flagged"])
        self.assertEqual(len(result["flags_triggered"]), 0)

    def test_fixed_flag_rcv_pass(self):
        # Sodium 140→145: absolute delta 5 > 4 (fixed flag), but RCV ~2.16% < 3.57% (RCV flag too)
        result = delta_check("sodium", 145, 140, method="both")
        self.assertTrue(result["flagged"])
        self.assertIn("fixed_limit", result["flags_triggered"])

    def test_method_fixed_only(self):
        result = delta_check("sodium", 141, 140, method="fixed")
        self.assertIn("fixed_limit_check", result)
        self.assertNotIn("rcv_check", result)

    def test_method_rcv_only(self):
        result = delta_check("sodium", 141, 140, method="rcv")
        self.assertNotIn("fixed_limit_check", result)
        self.assertIn("rcv_check", result)

    def test_with_time_hours(self):
        result = delta_check("glucose", 200, 120, time_hours=6, method="both")
        self.assertIn("rate_delta_per_hour", result)
        self.assertTrue(result["flagged"])

    def test_recommendation_on_flag(self):
        result = delta_check("potassium", 6.0, 4.0, method="fixed")
        self.assertTrue(result["flagged"])
        self.assertIn("ALERT", result["recommendation"])


# ---------------------------------------------------------------------------
# RCV Core Tests (from original test suite)
# ---------------------------------------------------------------------------

class TestRCVFormula(unittest.TestCase):
    def test_rcv_percent_matches_fraser_formula(self):
        cvi, cva = DEFAULT_REFERENCE_TABLE["sodium"]
        expected = math.sqrt(2) * 1.96 * math.sqrt(cva ** 2 + cvi ** 2)
        self.assertAlmostEqual(rcv_percent(cvi, cva, confidence=0.95), expected, places=9)

    def test_rcv_99_uses_larger_z(self):
        cvi, cva = DEFAULT_REFERENCE_TABLE["creatinine"]
        self.assertGreater(rcv_percent(cvi, cva, 0.99), rcv_percent(cvi, cva, 0.95))

    def test_rcv_rejects_unsupported_confidence(self):
        with self.assertRaises(ValueError):
            rcv_percent(1.0, 1.0, confidence=0.90)


class TestTimeWeighting(unittest.TestCase):
    def test_shorter_interval_tightens_rcv(self):
        cvi, cva = DEFAULT_REFERENCE_TABLE["urea"]
        rcv_default = rcv_percent(cvi, cva, 0.95)
        rcv_short = time_weighted_rcv_percent(cvi, cva, 6, 0.95, 24)
        self.assertLess(rcv_short, rcv_default)

    def test_longer_interval_widens_rcv(self):
        cvi, cva = DEFAULT_REFERENCE_TABLE["urea"]
        rcv_default = rcv_percent(cvi, cva, 0.95)
        rcv_long = time_weighted_rcv_percent(cvi, cva, 96, 0.95, 24)
        self.assertGreater(rcv_long, rcv_default)


class TestProbabilityOfTrueChange(unittest.TestCase):
    def test_at_rcv95_gives_95_percent(self):
        cvi, cva = DEFAULT_REFERENCE_TABLE["sodium"]
        rcv95 = rcv_percent(cvi, cva, 0.95)
        prob = probability_of_true_change(rcv95, cvi, cva)
        self.assertAlmostEqual(prob, 0.95, places=3)

    def test_zero_change_gives_zero(self):
        cvi, cva = DEFAULT_REFERENCE_TABLE["sodium"]
        self.assertAlmostEqual(probability_of_true_change(0.0, cvi, cva), 0.0, places=9)


class TestReferenceTable(unittest.TestCase):
    def test_default_table_has_expected_analytes(self):
        table = load_reference_table()
        self.assertIn("sodium", table)
        self.assertIn("creatinine", table)

    def test_custom_csv_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "custom.csv")
            with open(path, "w", newline="") as f:
                f.write("analyte,cvi_percent,cva_percent\n")
                f.write("sodium,1.0,1.0\n")
                f.write("digoxin,20.0,8.0\n")
            table = load_reference_table(path)
            self.assertEqual(table["sodium"], (1.0, 1.0))
            self.assertEqual(table["digoxin"], (20.0, 8.0))


# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------

class TestProcessBatch(unittest.TestCase):
    def test_batch_basic(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = os.path.join(tmp, "in.csv")
            out = os.path.join(tmp, "out.csv")
            with open(inp, "w") as f:
                f.write("analyte,current,previous\n")
                f.write("sodium,141,140\n")
                f.write("potassium,6.0,4.0\n")
                f.write("glucose,200,120\n")
            n = process_batch(inp, out, method="fixed")
            self.assertEqual(n, 3)
            with open(out) as f:
                content = f.read()
                self.assertIn("flagged", content)
                self.assertIn("True", content)  # potassium and glucose should flag
                self.assertIn("False", content)  # sodium should not


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    def test_cli_check(self):
        from cli import main
        ret = main(["check", "--analyte", "sodium", "--current", "141", "--previous", "140"])
        self.assertEqual(ret, 0)

    def test_cli_fixed(self):
        from cli import main
        ret = main(["fixed", "--analyte", "potassium", "--current", "5.5", "--previous", "4.0"])
        self.assertEqual(ret, 0)

    def test_cli_rcv(self):
        from cli import main
        ret = main(["rcv", "--analyte", "creatinine", "--current", "1.5", "--previous", "1.0"])
        self.assertEqual(ret, 0)

    def test_cli_list_analytes(self):
        from cli import main
        ret = main(["list-analytes"])
        self.assertEqual(ret, 0)

    def test_cli_batch(self):
        from cli import main
        with tempfile.TemporaryDirectory() as tmp:
            inp = os.path.join(tmp, "in.csv")
            out = os.path.join(tmp, "out.csv")
            with open(inp, "w") as f:
                f.write("analyte,current,previous\nsodium,141,140\n")
            ret = main(["batch", "-i", inp, "-o", out])
            self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
