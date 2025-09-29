from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Optional

from sat_utils import (
    calculate_accuracy_by_domain,
    _load_conversion_table,
    _estimate_from_table,
    _estimate_linear,
)


def print_table(results: List[Tuple[str, str, float, int, int, float]], conversion_csv: Optional[Path] = None, estimate_mode: str = "mid") -> None:
    headers = ["section", "domain", "accuracy", "correct", "total", "section_accuracy"]
    string_rows: List[List[str]] = []
    section_to_totals: Dict[str, Dict[str, int]] = {}
    for section_name, domain_name, d_accuracy, d_correct, d_total, s_accuracy in results:
        string_rows.append([
            str(section_name),
            str(domain_name),
            f"{d_accuracy:.4f}",
            str(d_correct),
            str(d_total),
            f"{s_accuracy:.4f}",
        ])
        st = section_to_totals.setdefault(section_name, {"correct": 0, "total": 0})
        st["correct"] += d_correct
        st["total"] += d_total

    rw_table, math_table = _load_conversion_table(conversion_csv)
    section_to_score: Dict[str, int] = {}
    for section_name, totals in section_to_totals.items():
        raw_correct = totals["correct"]
        total = totals["total"]
        percent = (raw_correct / total) if total > 0 else 0.0
        lname = section_name.lower()
        if lname.startswith("reading"):
            est = _estimate_from_table(raw_correct, rw_table, estimate_mode)
        elif lname.startswith("math"):
            est = _estimate_from_table(raw_correct, math_table, estimate_mode)
        else:
            est = None
        if est is None:
            est = _estimate_linear(percent)
        section_to_score[section_name] = est

    col_widths = [0 for _ in headers]
    for col_idx, header in enumerate(headers):
        max_data_width = max((len(row[col_idx]) for row in string_rows), default=0)
        col_widths[col_idx] = max(len(header), max_data_width)

    def fmt_row(row: List[str]) -> str:
        section = row[0].ljust(col_widths[0])
        domain = row[1].ljust(col_widths[1])
        accuracy = row[2].rjust(col_widths[2])
        correct = row[3].rjust(col_widths[3])
        total = row[4].rjust(col_widths[4])
        s_accuracy = row[5].rjust(col_widths[5])
        return f"{section}  {domain}  {accuracy}  {correct}  {total}  {s_accuracy}"

    header_line = fmt_row(headers)  # type: ignore[arg-type]
    sep_line = "  ".join("-" * w for w in col_widths)
    sys.stdout.write(header_line + "\n")
    sys.stdout.write(sep_line + "\n")
    for row in string_rows:
        sys.stdout.write(fmt_row(row) + "\n")
    if section_to_score:
        sys.stdout.write("\n")
        for section_name in sorted(section_to_score.keys()):
            sys.stdout.write(f"{section_name} Section Score: {section_to_score[section_name]}\n")
        rw_score = None
        math_score = None
        for name, score in section_to_score.items():
            lname = name.lower()
            if rw_score is None and lname.startswith("reading"):
                rw_score = score
            if math_score is None and lname.startswith("math"):
                math_score = score
        if rw_score is not None or math_score is not None:
            total_score = (rw_score or 0) + (math_score or 0)
        else:
            total_score = sum(section_to_score.values())
        sys.stdout.write(f"Total Score: {total_score}\n")


def print_json(results: List[Tuple[str, str, float, int, int, float]], conversion_csv: Optional[Path] = None, estimate_mode: str = "mid") -> None:
    payload: Dict[str, Dict[str, object]] = {}
    section_totals: Dict[str, Dict[str, int]] = {}
    for section_name, domain_name, d_accuracy, d_correct, d_total, s_accuracy in results:
        s = payload.setdefault(section_name, {"accuracy": s_accuracy, "correct": 0, "total": 0, "domains": {}})
        s["accuracy"] = s_accuracy
        s["correct"] = int(s.get("correct", 0)) + d_correct
        s["total"] = int(s.get("total", 0)) + d_total
        domains = s["domains"]  # type: ignore[assignment]
        assert isinstance(domains, dict)
        domains[domain_name] = {"accuracy": d_accuracy, "correct": d_correct, "total": d_total}
        t = section_totals.setdefault(section_name, {"correct": 0, "total": 0})
        t["correct"] += d_correct
        t["total"] += d_total

    rw_table, math_table = _load_conversion_table(conversion_csv)
    for section_name, totals in section_totals.items():
        raw_correct = totals["correct"]
        total = totals["total"]
        percent = (raw_correct / total) if total > 0 else 0.0
        lname = section_name.lower()
        if lname.startswith("reading"):
            est = _estimate_from_table(raw_correct, rw_table, estimate_mode)
        elif lname.startswith("math"):
            est = _estimate_from_table(raw_correct, math_table, estimate_mode)
        else:
            est = None
        if est is None:
            est = _estimate_linear(percent)
        payload[section_name]["score"] = est
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Compute per-section/domain accuracy and estimate SAT scores")
    parser.add_argument("--csv", dest="csv_paths", nargs="+", default=["questions.csv"], help="One or more CSV paths (default: questions.csv)")
    parser.add_argument("--output", dest="output_format", choices=["table", "json"], default="table", help="Output format: table or json (default: table)")
    parser.add_argument("--convert", dest="conversion_csv", default=None, help="Optional conversion table CSV: raw,rw_lower,rw_upper,math_lower,math_upper")
    parser.add_argument("--mode", dest="estimate_mode", choices=["lower", "upper", "mid"], default="mid", help="If conversion table provided, choose lower/upper/mid estimate (default: mid)")
    args = parser.parse_args(argv)

    csv_paths = [Path(p) for p in args.csv_paths]
    results = calculate_accuracy_by_domain(csv_paths)
    conversion_csv = Path(args.conversion_csv) if args.conversion_csv else None

    if args.output_format == "json":
        print_json(results, conversion_csv, args.estimate_mode)
    else:
        print_table(results, conversion_csv, args.estimate_mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


