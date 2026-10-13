"""Built-in, editable CVi/CVa reference table for common analytes.

Values are representative within-subject (CVi) and analytical (CVa)
coefficients of variation, in percent, compiled from published
biological variation literature (Fraser CG, "Biological Variation: From
Principles to Practice", 2001; and the EFLM Biological Variation
Database, biologicalvariation.eu). They are typical, rounded figures
suitable for demonstration and testing -- a real laboratory must
replace CVa with the value from its own current method validation, and
CVi with the value appropriate to its patient population, before using
this tool for clinical delta-check decisions.

The table is editable at three levels:
  1. Edit the DEFAULT_REFERENCE_TABLE dict below directly.
  2. Pass --reference-table with a CSV of analyte,cvi_percent,cva_percent
     to the CLI to add or override entries without touching this file.
  3. Call load_reference_table(path) from Python.
"""
import csv
import math

# analyte_key -> (CVi_percent, CVa_percent)
DEFAULT_REFERENCE_TABLE = {
    "sodium": (0.6, 0.5),
    "potassium": (4.8, 2.0),
    "chloride": (1.2, 1.0),
    "bicarbonate": (5.5, 3.0),
    "glucose": (5.7, 2.5),
    "urea": (12.3, 3.0),
    "creatinine": (5.9, 2.2),
    "calcium": (1.9, 1.0),
    "magnesium": (3.6, 2.0),
    "phosphate": (8.0, 3.0),
    "albumin": (3.1, 2.0),
    "total_protein": (2.4, 2.0),
    "alt": (19.4, 5.0),
    "ast": (12.3, 5.0),
    "alp": (6.4, 4.0),
    "total_bilirubin": (23.5, 5.0),
    "hemoglobin": (2.8, 1.5),
    "hematocrit": (3.0, 1.5),
    "wbc": (9.6, 3.0),
    "platelets": (9.1, 4.0),
    "troponin_i": (17.0, 10.0),
    "tsh": (19.7, 5.0),
    "inr": (4.1, 3.0),
    "crp": (44.0, 6.0),
    "amylase": (8.6, 4.0),
    "lactate": (11.5, 4.0),
}


def load_reference_table(path: str = None) -> dict:
    """Return the built-in reference table, optionally overlaid with
    entries from a user-supplied CSV (columns: analyte,cvi_percent,cva_percent).
    Entries in the CSV add new analytes or override built-in ones.
    """
    table = dict(DEFAULT_REFERENCE_TABLE)
    if path:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            required = {"analyte", "cvi_percent", "cva_percent"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError("Reference CSV requires analyte,cvi_percent,cva_percent columns")
            for line, row in enumerate(reader, start=2):
                key = (row["analyte"] or "").strip().lower().replace(" ", "_")
                if not key:
                    raise ValueError(f"Reference CSV line {line}: analyte cannot be empty")
                try:
                    cvi = float(row["cvi_percent"])
                    cva = float(row["cva_percent"])
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Reference CSV line {line}: invalid CVi/CVa") from exc
                if any(not math.isfinite(cv) or cv < 0 for cv in (cvi, cva)):
                    raise ValueError(f"Reference CSV line {line}: CVi/CVa must be finite and non-negative")
                table[key] = (cvi, cva)
    return table


def save_reference_table(table: dict, path: str) -> None:
    """Write a reference table to CSV in the format load_reference_table expects."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["analyte", "cvi_percent", "cva_percent"])
        for analyte, (cvi, cva) in sorted(table.items()):
            writer.writerow([analyte, cvi, cva])
