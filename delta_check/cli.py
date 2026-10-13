"""Command-line interface for the Delta Check Analyzer."""
import argparse
import csv
import sys
from datetime import datetime

from .core import evaluate_pair, DeltaCheckResult
from .reference_table import load_reference_table


def parse_timestamp(value: str) -> datetime:
    """Parse a timestamp in ISO 8601 or a couple of common lab-system
    formats."""
    value = value.strip()
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not parse timestamp: {value!r}")


def cmd_list_analytes(args) -> int:
    table = load_reference_table(args.reference_table)
    print(f"{'analyte':16s} {'CVi%':>8s} {'CVa%':>8s}")
    for analyte, (cvi, cva) in sorted(table.items()):
        print(f"{analyte:16s} {cvi:8.2f} {cva:8.2f}")
    return 0


def _format_result_line(prefix: str, result: DeltaCheckResult) -> str:
    d = result.to_dict()
    flag = "FLAGGED" if d["flagged"] else "ok"
    interval = f", interval={d['interval_hours']}h" if d["interval_hours"] is not None else ""
    return (
        f"[{flag}] {prefix}{d['analyte']}: {d['prior_value']} -> {d['current_value']} "
        f"(delta={d['percent_change']}%, RCV@{int(d['confidence'] * 100)}%={d['rcv_percent']}%{interval}, "
        f"two-sided p={d['two_sided_p_value']})"
    )


def cmd_pair(args) -> int:
    table = load_reference_table(args.reference_table)
    analyte = args.analyte.strip().lower().replace(" ", "_")
    if analyte not in table:
        print(
            f"Unknown analyte '{args.analyte}'. Run 'list-analytes' to see available analytes, "
            f"or supply --reference-table with a CSV that defines it.",
            file=sys.stderr,
        )
        return 1
    cvi, cva = table[analyte]
    result = evaluate_pair(
        analyte,
        cvi,
        cva,
        args.prior,
        args.current,
        confidence=args.confidence,
        interval_hours=args.interval_hours,
        reference_interval_hours=args.reference_interval_hours,
    )
    print(_format_result_line("", result))
    return 0


def cmd_batch(args) -> int:
    table = load_reference_table(args.reference_table)

    rows = []
    with open(args.input, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "patient_id": row["patient_id"].strip(),
                    "analyte": row["analyte"].strip().lower().replace(" ", "_"),
                    "timestamp": parse_timestamp(row["timestamp"]),
                    "value": float(row["value"]),
                }
            )

    groups: dict = {}
    for row in rows:
        groups.setdefault((row["patient_id"], row["analyte"]), []).append(row)

    results = []  # list of (patient_id, prior_ts, current_ts, DeltaCheckResult)
    skipped_unknown = set()
    for (patient_id, analyte), group in groups.items():
        group.sort(key=lambda r: r["timestamp"])
        if analyte not in table:
            skipped_unknown.add(analyte)
            continue
        if len(group) < 2:
            continue
        cvi, cva = table[analyte]

        # Evaluate consecutive chronological observations. No array dependency
        # is required, and zero baselines can be handled per pair.
        for i in range(len(group) - 1):
            prior_row, current_row = group[i], group[i + 1]
            interval_hours = None
            if args.time_weighted:
                delta_hours = (current_row["timestamp"] - prior_row["timestamp"]).total_seconds() / 3600.0
                interval_hours = delta_hours if delta_hours > 0 else None
            if prior_row["value"] == 0:
                print(
                    f"Skipped {patient_id}/{analyte} at {prior_row['timestamp'].isoformat()}: "
                    "percentage change is undefined for zero baseline.",
                    file=sys.stderr,
                )
                continue
            result = evaluate_pair(
                analyte,
                cvi,
                cva,
                prior_row["value"],
                current_row["value"],
                confidence=args.confidence,
                interval_hours=interval_hours,
                reference_interval_hours=args.reference_interval_hours,
            )
            results.append((patient_id, prior_row["timestamp"], current_row["timestamp"], result))

    if skipped_unknown:
        print(
            f"Skipped {len(skipped_unknown)} analyte(s) with no reference values: "
            f"{', '.join(sorted(skipped_unknown))}",
            file=sys.stderr,
        )

    show_all = args.all
    out_rows = []
    for patient_id, t1, t2, result in results:
        if not show_all and not result.flagged:
            continue
        d = result.to_dict()
        d["patient_id"] = patient_id
        d["prior_timestamp"] = t1.isoformat()
        d["current_timestamp"] = t2.isoformat()
        out_rows.append(d)
    out_rows.sort(key=lambda d: (d["patient_id"], d["current_timestamp"]))

    if args.output:
        fieldnames = [
            "patient_id", "analyte", "prior_timestamp", "current_timestamp",
            "prior_value", "current_value", "percent_change", "absolute_change",
            "rcv_percent", "confidence", "interval_hours", "flagged",
            "probability_true_change", "two_sided_p_value",
        ]
        with open(args.output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(out_rows)
        print(f"Wrote {len(out_rows)} row(s) to {args.output}")
    else:
        for row in out_rows:
            flag = "FLAGGED" if row["flagged"] else "ok"
            print(
                f"[{flag}] patient={row['patient_id']} {row['analyte']}: "
                f"{row['prior_value']} -> {row['current_value']} "
                f"(delta={row['percent_change']}%, RCV={row['rcv_percent']}%, "
                f"two-sided p={row['two_sided_p_value']})"
            )

    n_flagged = sum(1 for *_ , r in results if r.flagged)
    print(f"\n{n_flagged} of {len(results)} result pair(s) flagged.", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="delta-check-analyzer",
        description=(
            "Flag clinically significant changes between paired lab results using "
            "Reference Change Value (RCV) statistics (Fraser's biological variation theory)."
        ),
    )
    parser.add_argument(
        "--reference-table",
        help="CSV file of analyte,cvi_percent,cva_percent that adds to or overrides the built-in table",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-analytes", help="List the built-in CVi/CVa reference table")
    p_list.set_defaults(func=cmd_list_analytes)

    p_pair = sub.add_parser("pair", help="Evaluate a single prior/current result pair")
    p_pair.add_argument("analyte", help="Analyte name, e.g. sodium, creatinine, troponin_i")
    p_pair.add_argument("prior", type=float, help="Prior (baseline) result value")
    p_pair.add_argument("current", type=float, help="Current result value")
    p_pair.add_argument(
        "--confidence", type=float, default=0.95, choices=[0.95, 0.99],
        help="Confidence level for the RCV threshold (default: 0.95)",
    )
    p_pair.add_argument(
        "--interval-hours", type=float, default=None,
        help="Hours between the two draws; if given, uses the time-weighted RCV",
    )
    p_pair.add_argument(
        "--reference-interval-hours", type=float, default=24.0,
        help="Interval, in hours, the CVi reference value assumes (default: 24)",
    )
    p_pair.set_defaults(func=cmd_pair)

    p_batch = sub.add_parser(
        "batch", help="Scan a longitudinal lab results CSV for delta-check flags"
    )
    p_batch.add_argument("input", help="Input CSV with columns: patient_id,analyte,timestamp,value")
    p_batch.add_argument("--output", help="Write results to this CSV instead of stdout")
    p_batch.add_argument("--confidence", type=float, default=0.95, choices=[0.95, 0.99])
    p_batch.add_argument(
        "--time-weighted", action="store_true",
        help="Scale the RCV for the elapsed interval between each pair of draws",
    )
    p_batch.add_argument("--reference-interval-hours", type=float, default=24.0)
    p_batch.add_argument(
        "--all", action="store_true", help="Output every evaluated pair, not just flagged ones"
    )
    p_batch.set_defaults(func=cmd_batch)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
