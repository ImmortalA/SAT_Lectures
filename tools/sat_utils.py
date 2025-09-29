from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple


def parse_is_correct(value: str) -> int:
    """Parse correctness-like values into 0 or 1.

    Accepts numeric strings and common boolean-like strings.
    """
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
    """Detect domain, correctness, and section columns from CSV headers.

    Returns (domain_col, correct_col, section_col or None).
    """
    if not fieldnames:
        return ("domain", "is_correct", None)

    normalized = [name.strip() for name in fieldnames]

    domain_candidates = [
        "domain",
        "Domain",
        "subject",
        "Subject",
        "category",
        "Category",
    ]
    correct_candidates = [
        "is_correct",
        "accuracy",
        "correct",
        "isCorrect",
        "IsCorrect",
        "label",
        "Label",
    ]
    section_candidates = [
        "section",
        "Section",
        "module",
        "Module",
        "area",
        "Area",
        "subject_area",
        "Subject_Area",
    ]

    domain_col = next((c for c in domain_candidates if c in normalized), None)
    correct_col = next((c for c in correct_candidates if c in normalized), None)
    section_col = next((c for c in section_candidates if c in normalized), None)

    # Fallback to lowercase matches
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
    """Aggregate per-domain accuracy across one or more CSV files.

    Returns a list of tuples: (section, domain, domain_accuracy, domain_correct, domain_total, section_accuracy),
    sorted by section then domain ascending.
    """
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


def _load_conversion_table(conversion_csv: Optional[Path]) -> Tuple[Dict[int, Tuple[int, int]], Dict[int, Tuple[int, int]]]:
    """Load optional raw→(lower, upper) mappings for R&W and Math.

    Expected CSV columns: raw,rw_lower,rw_upper,math_lower,math_upper
    Returns: (rw_table, math_table)
    """
    rw: Dict[int, Tuple[int, int]] = {}
    math: Dict[int, Tuple[int, int]] = {}
    if not conversion_csv or not conversion_csv.exists():
        return rw, math
    with conversion_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                raw = int(str(row.get("raw", "").strip()))
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



