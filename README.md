# Delta Check Analyzer

### [Open the Live Application →](https://abusuraihsakhri.github.io/delta-check-analyzer/)

Compare consecutive laboratory results using configurable reference change value (RCV) calculations and illustrative fixed delta limits. The browser application runs locally without a backend. The repository also provides Python APIs, two command-line interfaces, and an optional FastAPI prototype.

## Browser calculator

Open the link above, select an analyte, enter prior/current results, and review absolute/percentage changes and thresholds. CVi and CVa can be changed to match a local validated method. Select fixed limits, RCV or both, then optionally export the single evaluation as CSV.

- RCV = √2 × z × √(CVi² + CVa²); z = 1.96 at 95% or 2.576 at 99% (two-sided).
- Fixed checks flag changes exceeding **either** the configured absolute or percentage limit.
- When a requested method is unavailable or a baseline is zero, results explicitly report an incomplete evaluation.
- No patient identifiers are requested. Input and result data stay in the current browser tab; no backend, analytics, external font requests or persistent browser storage are used.
- The browser runs plain JavaScript implementing the same threshold formulas; no server-side Python or Pyodide is required.

**Clinical limitation:** Built-in biological-variation coefficients and fixed limits are rounded *demonstration values*, not validated universal clinical decision limits. The apparent significance value exposed for backward compatibility as probability_true_change is **1 minus the two-sided p-value**, not the posterior probability that a true biological change occurred. Some Python-only workflows offer exploratory time-weighted CVi based on a random-walk assumption; this is not established as a generally validated RCV adjustment. Units, analytical performance, specimen factors, clinical context, analyte-specific kinetics and local policies must be assessed before laboratory implementation. This tool is not validated for autonomous clinical decisions.

## Python installation

Python 3.10 or newer is required.

~~~bash
git clone https://github.com/abusuraihsakhri/delta-check-analyzer.git
cd delta-check-analyzer
python -m pip install -e .
~~~

The basic calculator uses the Python standard library. Optional API and test dependencies are installed with pip install -e ".[web]" or pip install -e ".[dev]".

## Command-line usage

The installed delta-check command and the repository's python cli.py entry point support fixed, RCV and combined evaluation:

~~~bash
delta-check list-analytes
delta-check check --analyte sodium --previous 140 --current 145
delta-check rcv --analyte creatinine --previous 1.0 --current 1.5 --confidence 0.99
delta-check batch -i paired_results.csv -o results.csv
~~~

For the last command, the input CSV must contain analyte,current,previous and may include time_hours. Bad or unknown records are reported; an incomplete check is not a normal result.

The advanced python -m delta_check CLI provides a longitudinal cohort workflow with analyte-specific CVi/CVa override tables:

~~~bash
python -m delta_check list-analytes
python -m delta_check pair sodium 140 145
python -m delta_check batch sample_data.csv --all --output longitudinal_results.csv
~~~

This **different** batch schema requires patient_id,analyte,timestamp,value. Results are grouped by patient/analyte and sorted chronologically; consecutive observations are compared. Use --time-weighted only when its assumptions have been explicitly evaluated. Do not place identifiable patient information in repositories, issues or publicly shared exports.

## Optional API / Docker

~~~bash
python -m pip install -e ".[web]"
uvicorn agents.api:app --host 127.0.0.1 --port 8000
# Alternatively: docker compose up --build
~~~

The prototype exposes /health, /metrics, /api/audit, /api/chat and /api/audit/logs. Its generic multi-worker thresholds are **not** equivalent to the RCV calculator, and its model provider is currently a deterministic mock. The API has no authentication or production-grade protected-health-information controls. The supplied Docker Compose configuration binds to localhost by default; never expose these endpoints publicly or send actual patient data without a separate security and clinical validation assessment. The regex-based identifier guard is not a guarantee of HIPAA de-identification.

The HMAC-SHA256 audit log detects modified signed entries within an active process. It is in memory, does not survive restart, and is not a persistent or independently anchored audit ledger.

## Testing and development

~~~bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m unittest -q test_delta_check
node --check web/app.js
node --test web/app.test.cjs
~~~

GitHub Actions runs the Python test suites and browser calculation tests against Python 3.10, 3.11, and 3.12. To test the browser locally, open web/index.html or serve the repository root using python -m http.server 8001. Modern Chromium, Firefox, and Safari browsers are targeted; clinical deployment and cross-browser automated end-to-end testing are not claimed.

## License

MIT — see [LICENSE](LICENSE).
