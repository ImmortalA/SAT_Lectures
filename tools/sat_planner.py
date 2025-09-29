from __future__ import annotations

import argparse
import csv
import json
import sys
import re
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Optional, Mapping


# ---------------------------
# Accuracy computation (from questions CSV)
# ---------------------------

def parse_is_correct(value: str) -> int:
    if value is None:
        return 0
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y"}:
        return 1
    if text in {"0", "false", "f", "no", "n"}:
        return 0
    try:
        return 1 if float(text) >= 0.5 else 0
    except Exception:
        return 0


def _detect_columns(fieldnames: List[str]) -> Tuple[str, str, Optional[str]]:
    if not fieldnames:
        return ("domain", "is_correct", None)
    normalized = [name.strip() for name in fieldnames]
    domain_candidates = ["domain", "Domain", "subject", "Subject", "category", "Category"]
    correct_candidates = [
        "is_correct",
        "accuracy",
        "correct",
        "isCorrect",
        "IsCorrect",
        "label",
        "Label",
    ]
    section_candidates = ["section", "Section", "module", "Module", "area", "Area", "subject_area", "Subject_Area"]
    domain_col = next((c for c in domain_candidates if c in normalized), None)
    correct_col = next((c for c in correct_candidates if c in normalized), None)
    section_col = next((c for c in section_candidates if c in normalized), None)
    lower_map = {n.lower(): n for n in normalized}
    if domain_col is None and "domain" in lower_map:
        domain_col = lower_map["domain"]
    if correct_col is None:
        for lc in ["is_correct", "accuracy", "correct"]:
            if lc in lower_map:
                correct_col = lower_map[lc]
                break
    if section_col is None:
        for lc in ["section", "module", "area", "subject_area"]:
            if lc in lower_map:
                section_col = lower_map[lc]
                break
    if domain_col is None or correct_col is None:
        missing = []
        if domain_col is None:
            missing.append("domain")
        if correct_col is None:
            missing.append("is_correct/accuracy")
        raise ValueError(
            f"CSV is missing required columns: {', '.join(missing)}. Found: {', '.join(fieldnames)}"
        )
    return (domain_col, correct_col, section_col)


def _normalize_domain_name(domain_name: str) -> str:
    text = domain_name.strip().lower()
    text = text.replace("&", "and").replace("-", " ")
    text = " ".join(text.split())
    return text


def _infer_section_from_domain(domain_name: str) -> str:
    normalized = _normalize_domain_name(domain_name)
    reading_domains = {
        "expression of ideas",
        "information and ideas",
        "craft and structure",
        "standard english conventions",
        "information ideas",
        "craft structure",
    }
    math_domains = {
        "algebra",
        "advanced math",
        "problem solving and data analysis",
        "geometry trig",
        "geometry and trig",
        "geometry",
    }
    if normalized in reading_domains:
        return "Reading & Writing"
    if normalized in math_domains:
        return "Math"
    if any(key in normalized for key in ["english", "writing", "rhetorical", "text", "words", "evidence"]):
        return "Reading & Writing"
    if any(key in normalized for key in ["algebra", "math", "equations", "data", "functions", "variable", "systems"]):
        return "Math"
    return "Unknown"


def calculate_accuracy_by_domain(csv_paths: Iterable[Path]) -> List[Tuple[str, str, float, int, int, float]]:
    sd_counts: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    section_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    for csv_path in csv_paths:
        if not csv_path.exists():
            continue
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            domain_col, correct_col, section_col = _detect_columns(reader.fieldnames or [])
            for row in reader:
                domain_value = (row.get(domain_col) or "").strip()
                if domain_value == "":
                    continue
                is_correct_value = parse_is_correct(row.get(correct_col))
                if section_col:
                    section_value = (row.get(section_col) or "").strip() or _infer_section_from_domain(domain_value)
                else:
                    section_value = _infer_section_from_domain(domain_value)
                sd_counts[(section_value, domain_value)]["total"] += 1
                sd_counts[(section_value, domain_value)]["correct"] += int(is_correct_value == 1)
                section_counts[section_value]["total"] += 1
                section_counts[section_value]["correct"] += int(is_correct_value == 1)
    results: List[Tuple[str, str, float, int, int, float]] = []
    for (section_name, domain_name), counts in sd_counts.items():
        d_total = counts["total"]
        d_correct = counts["correct"]
        d_accuracy = (d_correct / d_total) if d_total > 0 else 0.0
        sc = section_counts.get(section_name, {"correct": 0, "total": 0})
        s_total = sc["total"]
        s_correct = sc["correct"]
        s_accuracy = (s_correct / s_total) if s_total > 0 else 0.0
        results.append((section_name, domain_name, d_accuracy, d_correct, d_total, s_accuracy))
    results.sort(key=lambda x: (x[0], x[1]))
    return results


# ---------------------------
# Score estimation and table printing
# ---------------------------

def _load_conversion_table(conversion_csv: Optional[Path]) -> Tuple[Dict[int, Tuple[int, int]], Dict[int, Tuple[int, int]]]:
    rw: Dict[int, Tuple[int, int]] = {}
    math: Dict[int, Tuple[int, int]] = {}
    if not conversion_csv or not conversion_csv.exists():
        return rw, math
    with conversion_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                raw = int(str(row.get("raw", "")).strip())
            except Exception:
                continue
            def _parse_int(name: str) -> Optional[int]:
                try:
                    v = row.get(name)
                    if v is None or str(v).strip() == "":
                        return None
                    return int(str(v).strip())
                except Exception:
                    return None
            rw_l = _parse_int("rw_lower"); rw_u = _parse_int("rw_upper")
            m_l = _parse_int("math_lower"); m_u = _parse_int("math_upper")
            if rw_l is not None and rw_u is not None:
                rw[raw] = (rw_l, rw_u)
            if m_l is not None and m_u is not None:
                math[raw] = (m_l, m_u)
    return rw, math


def _estimate_from_table(raw: int, table: Mapping[int, Tuple[int, int]], mode: str = "mid") -> Optional[int]:
    if not table:
        return None
    if raw in table:
        low, up = table[raw]
    else:
        keys = sorted(table.keys())
        if not keys:
            return None
        lower_keys = [k for k in keys if k <= raw]
        upper_keys = [k for k in keys if k >= raw]
        if not lower_keys or not upper_keys:
            k = lower_keys[-1] if lower_keys else upper_keys[0]
            low, up = table[k]
        else:
            k1, k2 = lower_keys[-1], upper_keys[0]
            l1, u1 = table[k1]; l2, u2 = table[k2]
            if k2 == k1:
                low, up = l1, u1
            else:
                t = (raw - k1) / (k2 - k1)
                low = int(round(l1 + t * (l2 - l1)))
                up = int(round(u1 + t * (u2 - u1)))
    if mode == "lower":
        return low
    if mode == "upper":
        return up
    return int(round((low + up) / 2))


def _estimate_linear(percent_correct: float) -> int:
    percent_clamped = max(0.0, min(1.0, percent_correct))
    return int(round(200 + 600 * percent_clamped))


def print_table(results: List[Tuple[str, str, float, int, int, float]], conversion_csv: Optional[Path] = None, estimate_mode: str = "mid") -> Dict[str, int]:
    headers = ["section", "domain", "accuracy", "correct", "total", "section_accuracy"]
    string_rows: List[List[str]] = []
    section_totals: Dict[str, Dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    for section_name, domain_name, d_accuracy, d_correct, d_total, s_accuracy in results:
        section_totals[section_name]["correct"] += d_correct
        section_totals[section_name]["total"] += d_total
    rw_table, math_table = _load_conversion_table(conversion_csv)
    section_to_score: Dict[str, int] = {}
    for section_name, totals in section_totals.items():
        raw_correct = totals["correct"]; total = totals["total"]
        percent = (raw_correct / total) if total > 0 else 0.0
        if section_name.lower().startswith("reading"):
            est = _estimate_from_table(raw_correct, rw_table, estimate_mode)
        elif section_name.lower().startswith("math"):
            est = _estimate_from_table(raw_correct, math_table, estimate_mode)
        else:
            est = None
        if est is None:
            est = _estimate_linear(percent)
        section_to_score[section_name] = est
    for section_name, domain_name, d_accuracy, d_correct, d_total, s_accuracy in results:
        string_rows.append([str(section_name), str(domain_name), f"{d_accuracy:.4f}", str(d_correct), str(d_total), f"{s_accuracy:.4f}"])
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
        rw_score = None; math_score = None
        for name, score in sorted(section_to_score.items()):
            sys.stdout.write(f"{name} Section Score: {score}\n")
            lname = name.lower()
            if rw_score is None and lname.startswith("reading"):
                rw_score = score
            if math_score is None and lname.startswith("math"):
                math_score = score
        total_score = (rw_score or 0) + (math_score or 0) if (rw_score is not None or math_score is not None) else sum(section_to_score.values())
        sys.stdout.write(f"Total Score: {total_score}\n")
    return section_to_score


def read_rubric_spec(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_units_by_domain(lectures_json: dict, domain_keywords: Dict[str, List[str]]) -> Dict[str, List[int]]:
    # Build regex patterns per domain
    domain_to_regex: Dict[str, Optional[re.Pattern[str]]] = {}
    for domain, words in domain_keywords.items():
        if not words:
            domain_to_regex[domain] = None
        else:
            domain_to_regex[domain] = re.compile("|".join(re.escape(w) for w in words), flags=re.I)
    domain_to_units: Dict[str, List[int]] = defaultdict(list)
    for unit in lectures_json.get("units", []):
        unit_no = unit.get("unitNumber")
        try:
            unit_no_int = int(unit_no)
        except Exception:
            continue
        text_parts: List[str] = []
        for lec in unit.get("lectures", []):
            title = str(lec.get("title", ""))
            content = str(lec.get("contentHtml", ""))
            text_parts.append(title)
            text_parts.append(content)
        blob = "\n".join(text_parts)
        for domain, pattern in domain_to_regex.items():
            if pattern is None:
                continue
            if pattern.search(blob):
                if unit_no_int not in domain_to_units[domain]:
                    domain_to_units[domain].append(unit_no_int)
    # Sort unit lists
    for k in list(domain_to_units.keys()):
        domain_to_units[k].sort()
    return domain_to_units


def _compute_section_scores(
    results: List[Tuple[str, str, float, int, int, float]],
    conversion_csv: Optional[Path],
    estimate_mode: str,
) -> Dict[str, int]:
    section_totals: Dict[str, Dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    for section_name, _domain_name, _d_accuracy, d_correct, d_total, _s_accuracy in results:
        section_totals[section_name]["correct"] += d_correct
        section_totals[section_name]["total"] += d_total
    rw_table, math_table = _load_conversion_table(conversion_csv)
    section_to_score: Dict[str, int] = {}
    for section_name, totals in section_totals.items():
        raw_correct = totals["correct"]; total = totals["total"]
        percent = (raw_correct / total) if total > 0 else 0.0
        if section_name.lower().startswith("reading"):
            est = _estimate_from_table(raw_correct, rw_table, estimate_mode)
        elif section_name.lower().startswith("math"):
            est = _estimate_from_table(raw_correct, math_table, estimate_mode)
        else:
            est = None
        if est is None:
            est = _estimate_linear(percent)
        section_to_score[section_name] = est
    return section_to_score


def _units_for_domain(baseline_accuracy: float) -> int:
    # Heuristic: lower accuracy → more units required to master domain
    if baseline_accuracy < 0.4:
        return 3
    if baseline_accuracy < 0.6:
        return 2
    return 1


def _expected_points_per_domain(initial_section_score: int) -> int:
    # Assumptions from rubric:
    # - If initial section score < 600: finishing a domain yields ~30–50 points → use midpoint 40
    # - If initial > 700: suggest diagnostic; we won't compute units here
    # - Else (600–700): steady gains; use a conservative midpoint 25
    if initial_section_score < 600:
        return 40
    if initial_section_score > 700:
        return 0
    return 25


def print_readable_units_plan(
    section_name: str,
    target_improvement: int,
    results: List[Tuple[str, str, float, int, int, float]],
    spec: dict,
    conversion_csv: Optional[Path],
    estimate_mode: str,
    domain_to_units: Optional[Dict[str, List[int]]] = None,
) -> None:
    # Gather unit assumptions
    params = spec.get("parameters", {})
    unit_minutes = int(params.get("unit_duration_minutes", params.get("lesson_duration_minutes", 120)))

    # Section baseline score
    section_scores = _compute_section_scores(results, conversion_csv, estimate_mode)
    baseline_score = section_scores.get(section_name, 0)

    # High-scorer recommendation
    if baseline_score > 700:
        sys.stdout.write(f"{section_name} target +{target_improvement} points\n")
        sys.stdout.write(f"Current estimated score: {baseline_score}\n")
        sys.stdout.write("Recommendation: Take a small domain diagnostic to identify weak skills before planning units.\n")
        return

    # Expected gain per completed domain
    per_domain_points = _expected_points_per_domain(baseline_score)
    if per_domain_points <= 0:
        per_domain_points = 25

    # Domains for this section with baseline accuracies
    section_domains: List[Tuple[str, float]] = []
    for sec, dom, d_acc, _dc, _dt, _sa in results:
        if sec == section_name:
            section_domains.append((dom, d_acc))
    section_domains.sort(key=lambda x: x[1])  # lowest accuracy first

    sys.stdout.write(f"{section_name} target +{target_improvement} points\n")
    sys.stdout.write(f"Current estimated score: {baseline_score}\n")
    sys.stdout.write(f"Assumption: ~{per_domain_points} points per completed domain. Each unit is {unit_minutes} minutes.\n\n")

    cumulative_points = 0
    total_units = 0
    lines: List[str] = []
    for domain_name, acc in section_domains:
        if cumulative_points >= target_improvement:
            break
        units_needed = _units_for_domain(acc)
        units_available = None
        units_list: List[int] = []
        if domain_to_units is not None:
            units_list = list(domain_to_units.get(domain_name, []))
            units_available = len(units_list)
        units_used = units_needed
        if units_available is not None:
            units_used = min(units_needed, units_available)
        # Scale points by fraction of units available if constrained
        points_gain_nominal = per_domain_points
        scale = (units_used / units_needed) if units_needed > 0 else 1.0
        points_gain = int(round(points_gain_nominal * scale))
        cumulative_points += points_gain
        total_units += units_used
        unit_details = f" units={units_used}"
        if units_available is not None:
            unit_details = f" units={units_used}/{units_needed} (avail {units_available})"
        units_str = ""
        if units_list:
            units_str = "; available unit(s): " + ", ".join(str(u) for u in units_list)
        lines.append(
            f"- {domain_name}: baseline accuracy={acc:.2f} →{unit_details}, ~{points_gain} pts (cummulative {cumulative_points}/{target_improvement}){units_str}"
        )

    total_minutes = total_units * unit_minutes
    total_hours = total_minutes / 60.0

    for ln in lines:
        sys.stdout.write(ln + "\n")
    sys.stdout.write("\n")
    sys.stdout.write(f"Estimated total: {total_units} unit(s) ≈ {total_hours:.1f} hours to reach +{target_improvement} points.\n")
    if cumulative_points < target_improvement:
        sys.stdout.write(f"With this practice you can improve to ~+{cumulative_points} points; you need more advanced practice and tests to further improve.\n")

    # Pacing scenarios: assume 1 unit per day
    if total_units > 0:
        sys.stdout.write("\nPacing estimates (1 unit/day):\n")
        scenarios = [
            (2, "1 lesson/day, 2 days/week"),
            (3, "1 lesson/day, 3 days/week"),
            (5, "1 lesson/day, 5 days/week"),
        ]
        for days_per_week, label in scenarios:
            weeks = math.ceil(total_units / days_per_week)
            months = weeks / 4.0
            sys.stdout.write(f"- {label}: ~{weeks} week(s) (~{months:.1f} month)\n")


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="SAT planner: compute accuracies and print lesson plan")
    parser.add_argument("--csv", dest="csv_paths", nargs="+", default=["questions.csv"], help="Input CSVs")
    parser.add_argument("--convert", dest="conversion_csv", default=None)
    parser.add_argument("--mode", dest="estimate_mode", choices=["lower", "upper", "mid"], default="mid")
    parser.add_argument("--target-math", dest="target_math", type=int, default=None, help="Target Math improvement (points)")
    parser.add_argument("--target-rw", dest="target_rw", type=int, default=None, help="Target Reading & Writing improvement (points)")
    parser.add_argument("--spec", dest="spec_file", default="rubric_spec.json", help="Rubric spec JSON")
    args = parser.parse_args(argv)

    # Interactive prompt for targets if not provided and running in a TTY
    def _prompt_int(prompt_text: str) -> Optional[int]:
        try:
            raw = input(prompt_text).strip()
            if raw == "":
                return None
            return int(raw)
        except Exception:
            return None

    if sys.stdin.isatty():
        if args.target_math is None:
            args.target_math = _prompt_int("Enter desired Math improvement in points (leave blank to skip): ")
        if args.target_rw is None:
            args.target_rw = _prompt_int("Enter desired Reading & Writing improvement in points (leave blank to skip): ")

    results = calculate_accuracy_by_domain([Path(p) for p in args.csv_paths])
    conversion_csv = Path(args.conversion_csv) if args.conversion_csv else None
    print_table(results, conversion_csv, args.estimate_mode)

    # Readable units plan based on targets
    if args.target_math or args.target_rw:
        spec = read_rubric_spec(Path(args.spec_file))
        conversion_csv = Path(args.conversion_csv) if args.conversion_csv else None
        # Load lectures and classify units into domains using rubric keywords
        domain_to_units: Optional[Dict[str, List[int]]] = None
        try:
            lectures_path = Path("lectures.json")
            if lectures_path.exists():
                lectures_json = json.loads(lectures_path.read_text(encoding="utf-8"))
                keywords = spec.get("lecture_mapping", {}).get("domain_keywords", {})
                domain_to_units = classify_units_by_domain(lectures_json, keywords)
        except Exception:
            domain_to_units = None
        if args.target_math:
            sys.stdout.write("\n")
            print_readable_units_plan("Math", args.target_math, results, spec, conversion_csv, args.estimate_mode, domain_to_units)
        if args.target_rw:
            sys.stdout.write("\n")
            print_readable_units_plan("Reading & Writing", args.target_rw, results, spec, conversion_csv, args.estimate_mode, domain_to_units)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))





