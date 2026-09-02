# Delta Check Analyzer

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

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

Command-line interface for the Delta Check Analyzer.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`DeltaCheckResult`** — dedicated module for delta check result evaluation and state verification.

---

## 📐 Mathematical Formulation & Logic

```text
  RCV formula (Fraser):
  return (current - previous) / time_hours
  Uses the RCV formula: RCV = sqrt(2) × z × sqrt(CVa² + CVi²)
  return (
  Implements the RCV formula from Fraser's biological variation theory
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --analyte <value> --current <value> --previous <value> --method <value>
```

### Parameter Reference
- `--analyte`: Specifies input measurement or parameter value.
- `--current`: Specifies input measurement or parameter value.
- `--previous`: Specifies input measurement or parameter value.
- `--method`: Specifies input measurement or parameter value.
- `--time-hours`: Specifies input measurement or parameter value.
- `--confidence`: Specifies input measurement or parameter value.
- `--input`: Specifies input measurement or parameter value.
- `--output`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `suite_name` | Parameter / observation metric | Required |
| `system_slug` | Parameter / observation metric | Required |
| `standard_reference` | Parameter / observation metric | Required |
| `test_cases` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t delta-check-analyzer .
docker run -p 8000:8000 delta-check-analyzer
```
