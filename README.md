# Delta Check Analyzer — Lab Result Change Detection

A zero-dependency Python tool for detecting clinically significant changes between consecutive laboratory results, using both fixed-limit thresholds and Reference Change Value (RCV) from biological variation theory.

## Delta Check Methods

### 1. Fixed-Limit Delta Checks

Common clinical lab thresholds:

| Analyte | Absolute Limit | Percent Limit | Unit |
|---------|---------------|---------------|------|
| Sodium | ±4.0 | ±3% | mEq/L |
| Potassium | ±0.5 | ±15% | mEq/L |
| Glucose | ±30 | ±20% | mg/dL |
| Hemoglobin | ±1.5 | ±10% | g/dL |
| Creatinine | ±0.3 | ±15% | mg/dL |
| Calcium | ±0.5 | ±5% | mg/dL |

A result is flagged if **either** the absolute or percent delta exceeds its limit.

### 2. Reference Change Value (RCV)

Based on Fraser's biological variation theory:

```
RCV = √2 × z × √(CVa² + CVi²)
```

Where:
- **CVi** = within-subject (intra-individual) biological coefficient of variation
- **CVa** = analytical coefficient of variation of the assay
- **z** = standard normal deviate (1.96 for 95%, 2.576 for 99%)

### 3. Rate Delta

```
Rate = (current - previous) / time_between_results
```

Useful for monitoring rapid changes (e.g., glucose in DKA, potassium in renal failure).

## Quick Start

```bash
# Combined delta check (fixed + RCV)
python cli.py check --analyte sodium --current 145 --previous 140

# Fixed-limit only
python cli.py fixed --analyte potassium --current 5.5 --previous 4.0

# RCV-based with time weighting
python cli.py rcv --analyte creatinine --current 1.5 --previous 1.0 --confidence 0.99

# List all analytes with limits
python cli.py list-analytes

# Batch processing
python cli.py batch -i lab_pairs.csv -o results.csv
```

### Python API

```python
from delta_check import delta_check, check_fixed_limits, check_rcv

# Combined check
result = delta_check("sodium", 145, 140, method="both")
print(result["flagged"])           # True
print(result["flags_triggered"])   # ['fixed_limit', 'rcv']

# Fixed limits only
result = check_fixed_limits("potassium", 5.5, 4.0)
print(result["flagged"])           # True

# RCV-based
result = check_rcv("creatinine", 1.3, 1.0, confidence=0.95)
print(result["flagged"])           # True
print(result["probability_true_change"])  # ~0.97
```

## Running Tests

```bash
python -m pytest test_delta_check.py -v
```

## License

MIT License.
