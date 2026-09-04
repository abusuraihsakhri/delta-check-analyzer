# Delta Check Analyzer

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Standards:** CAP / CLSI / ISO / Clinical and Laboratory Standards Institute

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)

</div>

---

## What It Does

Delta Check Analyzer detects clinically significant changes between paired lab results using two complementary approaches:

1. **Fixed-limit delta checks** — Common clinical lab thresholds (e.g., Sodium ±4 mEq/L or ±3%)
2. **RCV-based delta checks** — Reference Change Value from biological variation (Fraser's formula)

### Common Delta Check Limits (typical clinical lab values)

| Analyte | Absolute Limit | Percent Limit | Unit |
|---------|---------------|---------------|------|
| Sodium | ±4 | ±3% | mEq/L |
| Potassium | ±0.5 | ±15% | mEq/L |
| Glucose | ±30 | ±20% | mg/dL |
| Hemoglobin | ±1.5 | ±10% | g/dL |
| Creatinine | ±0.3 | ±15% | mg/dL |
| Calcium | ±0.5 | ±5% | mg/dL |

### RCV Formula (Fraser)

```
RCV = sqrt(2) × z × sqrt(CVa² + CVi²)
```

Where:
- **CVa** = analytical coefficient of variation of the assay
- **CVi** = within-subject (intra-individual) biological coefficient of variation
- **z** = standard normal deviate (1.96 for 95%, 2.576 for 99%)
- **sqrt(2)** accounts for the variance of the *difference* between two results

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/delta-check-analyzer.git
cd delta-check-analyzer

# Install dependencies
pip install -r requirements.txt
```

### Optional: Install with web API support

```bash
pip install "delta-check-analyzer[web]"
```

---

## Usage

### Command-Line Interface

#### 1. List Available Analytes
```bash
python cli.py list-analytes
```

#### 2. Combined Delta Check (fixed + RCV)
```bash
python cli.py check --analyte sodium --current 145 --previous 140
python cli.py check --analyte glucose --current 200 --previous 120 --time-hours 6
```

#### 3. Fixed-Limit Check Only
```bash
python cli.py fixed --analyte potassium --current 5.5 --previous 4.0
```

#### 4. RCV-Based Check Only
```bash
python cli.py rcv --analyte creatinine --current 1.5 --previous 1.0 --confidence 0.99
```

#### 5. Batch Process CSV
```bash
python cli.py batch -i sample_data.csv -o results.csv
```

### CLI Parameters

| Parameter | Description | Required |
|:----------|:------------|:---------|
| `--analyte` | Analyte name (e.g., sodium, creatinine, glucose) | Yes |
| `--current` | Current lab result value | Yes |
| `--previous` | Previous lab result value | Yes |
| `--method` | Check method: `fixed`, `rcv`, or `both` | No (default: both) |
| `--time-hours` | Hours between results (for rate delta and time-weighted RCV) | No |
| `--confidence` | RCV confidence level (0.95 or 0.99) | No (default: 0.95) |
| `-i / --input` | Input CSV file path (batch mode) | Yes (batch) |
| `-o / --output` | Output CSV file path (batch mode) | No (default: results.csv) |

### Input CSV Schema (Batch Mode)

| Field | Description | Required |
|:------|:------------|:---------|
| `analyte` | Analyte name | Yes |
| `current` | Current result value | Yes |
| `previous` | Previous result value | Yes |
| `time_hours` | Hours between results | No |

---

## Security Features

### Zero-PHI Outbound Interceptor
Active regex inspection blocking SSNs, MRNs, phone numbers, email addresses, and patient identifiers from outbound data.

### Tamper-Evident HMAC-SHA256 Audit Trail
Chained, cryptographically signed logs for every evaluation. The audit secret key is resolved in priority order:
1. Explicit key passed to `AuditTrail(secret_key=...)`
2. `AUDIT_SECRET_KEY` environment variable
3. Secure random key generated per process (safe default)

**Production deployment:** Always set `AUDIT_SECRET_KEY` to a stable, secrets-manager-provided value.

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## API Server (Optional)

The project includes a FastAPI-based REST API for integration with clinical systems:

```bash
pip install "delta-check-analyzer[web]"
uvicorn agents.api:app --host 0.0.0.0 --port 8000
```

### Endpoints
- `GET /health` — Health check
- `POST /api/audit` — Dispatch task payload for multi-worker evaluation
- `POST /api/chat` — Air-gapped supervisory conversational assistant
- `GET /api/audit/logs` — Retrieve and verify HMAC audit trail

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pip install pytest-cov
pytest -v --cov=delta_check --cov=agents
```

### Expected Test Results
- `test_phi_guard_enforcement` — Validates PHI outbound blocking
- `test_specialized_workers` — Validates QC, Safety, and Protocol workers
- `test_supervisor_consensus_and_audit` — Validates multi-agent consensus and audit integrity
- `test_enrichment_suite_execution` — Validates enrichment feature pipeline
- `test_enrichment_threshold_escalation` — Validates threshold-based alerting

---

## Testing / Simulation

```bash
# Run high-throughput simulation benchmark
python simulator.py 1000
```

---

## Project Structure

```
delta-check-analyzer/
├── delta_check/          # Core delta check algorithms
│   ├── analyzer.py       # Main delta check orchestration
│   ├── core.py           # RCV calculations and biological variation
│   ├── reference_table.py  # CVi/CVa reference values
│   └── cli.py            # Advanced CLI (numpy-based batch processing)
├── agents/               # Enterprise security and multi-agent system
│   ├── base.py           # PHI Guard, HMAC Audit Trail
│   ├── models.py         # Pydantic data schemas
│   ├── workers.py        # Specialized evaluation workers
│   ├── supervisor.py     # Multi-agent orchestrator
│   ├── api.py            # FastAPI REST endpoints
│   ├── metrics.py        # Prometheus metrics exporter
│   ├── streamer.py       # WebSocket telemetry broadcaster
│   └── learning.py       # Bayesian calibration engine
├── tests/                # Pytest test suite
├── sample_data.csv       # Sample longitudinal lab data
├── cli.py                # Main CLI entry point
├── enrichment.py         # Clinical enrichment engines
├── simulator.py          # High-throughput simulation
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project metadata and build config
├── Dockerfile            # Container build
└── docker-compose.yml    # Container orchestration
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Author: Dr. Abu Suraih Sakhri
