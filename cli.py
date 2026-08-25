#!/usr/bin/env python3
"""
CLI for Delta Check Analyzer.

Usage:
  python cli.py check --analyte sodium --current 145 --previous 140
  python cli.py check --analyte potassium --current 5.5 --previous 4.0 --method rcv
  python cli.py check --analyte glucose --current 200 --previous 120 --time-hours 6
  python cli.py fixed --analyte sodium --current 145 --previous 140
  python cli.py rcv --analyte creatinine --current 1.5 --previous 1.0 --confidence 0.99
  python cli.py batch -i pairs.csv -o results.csv
"""
import argparse
import json
import sys

from delta_check.analyzer import (
    delta_check,
    check_fixed_limits,
    check_rcv,
    absolute_delta,
    percent_delta,
    rate_delta,
    process_batch,
    FIXED_DELTA_LIMITS,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="delta-check",
        description="Delta Check Analyzer — Lab Result Change Detection",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Combined check
    p_check = subparsers.add_parser("check", help="Perform delta check (combined)")
    p_check.add_argument("--analyte", required=True, help="Analyte name")
    p_check.add_argument("--current", type=float, required=True, help="Current result")
    p_check.add_argument("--previous", type=float, required=True, help="Previous result")
    p_check.add_argument("--time-hours", type=float, default=None, help="Hours between results")
    p_check.add_argument("--confidence", type=float, default=0.95, help="RCV confidence (0.95 or 0.99)")
    p_check.add_argument("--method", choices=["fixed", "rcv", "both"], default="both",
                         help="Delta check method")

    # Fixed limit check
    p_fixed = subparsers.add_parser("fixed", help="Fixed-limit delta check")
    p_fixed.add_argument("--analyte", required=True, help="Analyte name")
    p_fixed.add_argument("--current", type=float, required=True, help="Current result")
    p_fixed.add_argument("--previous", type=float, required=True, help="Previous result")

    # RCV check
    p_rcv = subparsers.add_parser("rcv", help="RCV-based delta check")
    p_rcv.add_argument("--analyte", required=True, help="Analyte name")
    p_rcv.add_argument("--current", type=float, required=True, help="Current result")
    p_rcv.add_argument("--previous", type=float, required=True, help="Previous result")
    p_rcv.add_argument("--confidence", type=float, default=0.95, help="Confidence level")
    p_rcv.add_argument("--time-hours", type=float, default=None, help="Hours between results")

    # List analytes
    subparsers.add_parser("list-analytes", help="List available analytes with delta limits")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV")
    p_batch.add_argument("-i", "--input", required=True, help="Input CSV")
    p_batch.add_argument("-o", "--output", default="results.csv", help="Output CSV")
    p_batch.add_argument("--method", choices=["fixed", "rcv", "both"], default="both")
    p_batch.add_argument("--confidence", type=float, default=0.95)

    args = parser.parse_args(argv)

    if args.command == "check":
        result = delta_check(
            args.analyte, args.current, args.previous,
            args.time_hours, args.confidence, args.method,
        )
        print(json.dumps(result, indent=2))

    elif args.command == "fixed":
        result = check_fixed_limits(args.analyte, args.current, args.previous)
        print(json.dumps(result, indent=2))

    elif args.command == "rcv":
        result = check_rcv(args.analyte, args.current, args.previous,
                           args.confidence, args.time_hours)
        print(json.dumps(result, indent=2))

    elif args.command == "list-analytes":
        print(f"{'Analyte':<20} {'Abs Limit':>10} {'Pct Limit':>10} {'Unit':<10}")
        print("-" * 55)
        for name, info in sorted(FIXED_DELTA_LIMITS.items()):
            print(f"{name:<20} {info['absolute_limit']:>10.2f} {info['percent_limit']:>10.1f}% {info['unit']:<10}")

    elif args.command == "batch":
        n = process_batch(args.input, args.output, args.method, args.confidence)
        print(f"Processed {n} records -> {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
