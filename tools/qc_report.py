#!/usr/bin/env python3
"""
QC report generator for SAT lesson JSON files.
Scans JSON under data/units_processed/M and data/units_processed/V and produces qc_report.txt.

Rules implemented from the user spec. This tool NEVER modifies files.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from typing import Dict, List, Tuple


WORK_ROOTS = [
    os.path.join('data', 'units_processed', 'M'),
    os.path.join('data', 'units_processed', 'V'),
]


MOJIBAKE_TOKENS = [
    '—', 'â€“', 'â€˜', 'â€™', 'â€œ', 'â€0', 'â€¢', 'Â·', 'Â±', '×', 'â†’', '⇒',
    '≠≥', '≠¥', '≠≤', '≠ ', '≠', 'âˆ−', '−', '≠ˆ', 'â†”'
]


def read_json(path: str) -> Tuple[dict, str]:
    with io.open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    data = json.loads(raw)
    return data, raw


def check_fields(data: dict) -> Tuple[str, List[str]]:
    required = [
        'id', 'section', 'domain', 'related_skills', 'unit', 'description',
        'duration', 'content', 'completed', 'locked', 'progress'
    ]
    issues: List[str] = []
    for k in required:
        if k not in data:
            issues.append(f'missing key: {k}')
    extra_keys = [k for k in data.keys() if k not in required]
    # extras allowed; just note
    if extra_keys:
        issues.append(f'extra keys present: {extra_keys}')
    return ('OK' if not issues else 'ERROR(' + '; '.join(issues) + ')', issues)


def find_regex_positions(text: str, pattern: re.Pattern, limit: int = 5) -> List[Tuple[int, str]]:
    hits: List[Tuple[int, str]] = []
    for m in pattern.finditer(text):
        i = m.start()
        lo = max(0, i - 30)
        hi = min(len(text), i + 30)
        snippet = text[lo:hi]
        hits.append((i, snippet))
        if len(hits) >= limit:
            break
    return hits


def html_checks(content: str) -> Tuple[str, List[str]]:
    issues: List[str] = []
    # Empty code blocks
    empty_code_re = re.compile(r'<pre>\s*<code[^>]*>\s*</code>\s*</pre>', re.IGNORECASE)
    empties = find_regex_positions(content, empty_code_re)
    for idx, snip in empties:
        issues.append(f'Empty code block at ~{idx}: "{snip}"')

    # Duplicate HR sequences
    dup_hr_re = re.compile(r'(?:<hr(?:\s*/?)>\s*){2,}', re.IGNORECASE)
    dhrs = find_regex_positions(content, dup_hr_re)
    for idx, snip in dhrs:
        issues.append(f'Duplicate <hr> sequence at ~{idx}: "{snip}"')

    # Fake bullets paragraphs: lines starting with - separated by <br>
    p_re = re.compile(r'<p>([\s\S]*?)</p>', re.IGNORECASE)
    br_re = re.compile(r'<br\s*/?>', re.IGNORECASE)
    for m in p_re.finditer(content):
        block = m.group(1)
        parts = [x.strip() for x in br_re.split(block)]
        parts = [x for x in parts if x]
        if parts and all(x.lstrip().startswith('- ') for x in parts):
            idx = m.start()
            snip = content[max(0, idx-30): min(len(content), idx+60)]
            issues.append(f'Fake bullets paragraph at ~{idx}: "{snip}"')

    # Orphan punctuation like <p>.</p>
    orphan_punct_re = re.compile(r'<p>\s*[\.,;:!\?]\s*</p>', re.IGNORECASE)
    orphans = find_regex_positions(content, orphan_punct_re)
    for idx, snip in orphans:
        issues.append(f'Orphan punctuation paragraph at ~{idx}: "{snip}"')

    status = 'OK' if not issues else ('WARN/LINT(' + ' | '.join(issues) + ')')
    return status, issues


def mathml_checks(section: str, content: str) -> Tuple[str, List[str]]:
    if section.lower().startswith('reading'):
        return 'OK', []
    issues: List[str] = []
    # Tag balance for <math>
    open_count = len(re.findall(r'<math\b', content, flags=re.IGNORECASE))
    close_count = len(re.findall(r'</math>', content, flags=re.IGNORECASE))
    if open_count != close_count:
        issues.append(f'MathML <math> open/close mismatch: {open_count} vs {close_count}')

    # Simple mis-nesting signals, e.g., ")</msup>"
    if re.search(r'\)\s*</msup>', content, flags=re.IGNORECASE):
        pos = re.search(r'\)\s*</msup>', content, flags=re.IGNORECASE).start()
        snip = content[max(0, pos-30): pos+30]
        issues.append(f'Possible mis-nesting at ~{pos}: "{snip}"')

    # Suspicious entities: look for mojibake within MathML segments
    # Here we just scan content for the mojibake tokens and note if near <math>
    for tok in MOJIBAKE_TOKENS:
        for m in re.finditer(re.escape(tok), content):
            i = m.start()
            # proximity to MathML
            near_math = bool(re.search(r'<math[\s\S]{0,200}$', content[:i], flags=re.IGNORECASE) and re.search(r'^[\s\S]{0,200}</math>', content[i:], flags=re.IGNORECASE))
            if near_math:
                snip = content[max(0, i-30): min(len(content), i+30)]
                issues.append(f'Mojibake inside/near MathML at ~{i}: "{snip}"')

    status = 'OK' if not issues else ('WARN(' + ' | '.join(issues) + ')')
    return status, issues


def mojibake_scan(content: str) -> Tuple[Dict[str, int], List[Tuple[str, int, str]]]:
    counts: Dict[str, int] = {}
    samples: List[Tuple[str, int, str]] = []
    for tok in MOJIBAKE_TOKENS:
        n = content.count(tok)
        if n:
            counts[tok] = n
            # capture first sample occurrence
            i = content.find(tok)
            snip = content[max(0, i-30): min(len(content), i+30)]
            samples.append((tok, i, snip))
    return counts, samples


def structure_checks_math(content: str) -> Tuple[str, List[str]]:
    issues: List[str] = []
    # Extract headings text
    headings = [(m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip(), m.start())
                for m in re.finditer(r'<h([1-6])>([\s\S]*?)</h\1>', content, flags=re.IGNORECASE)]
    required = [
        'Title & Goal', 'Key idea', 'Worked example', 'Quick practice',
        'Next idea', 'Another example', 'More practice', 'Mixed practice set'
    ]
    present = [txt for (_, txt, _) in headings]
    for req in required:
        if req not in present:
            issues.append(f'Missing header: {req}')

    # Duplicate header detection
    header_positions: Dict[str, List[int]] = {}
    for _, txt, pos in headings:
        header_positions.setdefault(txt, []).append(pos)
    for txt, poss in header_positions.items():
        if len(poss) > 1 and txt in ('Next idea', 'Quick practice'):
            issues.append(f'Duplicate header: {txt} at ~offsets {poss}')

    # Empty sections: header followed by next header with no substantial text
    for idx, (level, txt, pos) in enumerate(headings):
        end = headings[idx+1][2] if idx+1 < len(headings) else len(content)
        body = re.sub(r'\s+', ' ', re.sub(r'<h[1-6]>[\s\S]*?</h[1-6]>', '', content[pos:end], flags=re.IGNORECASE)).strip()
        if txt in required and len(body) < 15:
            issues.append(f'Empty section: {txt} at ~{pos}')

    status = 'OK' if not issues else ('ISSUES:\n' + '\n'.join(issues))
    return status, issues


def sat_style_checks(content: str) -> Tuple[str, List[str]]:
    issues: List[str] = []
    # MC answers as bullets: detect <ul> with items starting with A./A)/A-
    for m in re.finditer(r'<ul>([\s\S]*?)</ul>', content, flags=re.IGNORECASE):
        ul = m.group(1)
        lis = re.findall(r'<li>([\s\S]*?)</li>', ul, flags=re.IGNORECASE)
        if lis and all(re.match(r'\s*[A-D](\)|\.|-|\s)', re.sub(r'<[^>]+>', '', li).strip()) for li in lis):
            issues.append(f'MC answers as bullets at ~{m.start()}')

    # Problem/Solution adjacency heuristic: find "Solution" headings not adjacent
    for m in re.finditer(r'(Problem\s*\d+|Q\s*\d+)[\s\S]{0,200}?(?=<h[1-6]|$)', content, flags=re.IGNORECASE):
        block_start = m.start()
        tail = content[m.end(): m.end()+200]
        if 'Solution' not in tail:
            issues.append(f'Possible missing adjacent solution near ~{block_start}')

    status = 'OK' if not issues else ('ISSUES:\n' + '\n'.join(issues))
    return status, issues


def truncation_check(content: str) -> Tuple[str, List[str]]:
    issues: List[str] = []
    # Unclosed <math>
    if len(re.findall(r'<math\b', content, flags=re.IGNORECASE)) != len(re.findall(r'</math>', content, flags=re.IGNORECASE)):
        tail = content[-200:]
        issues.append(f'Unbalanced MathML; tail: "{tail}"')
    # Ends mid-tag
    if content.rstrip().endswith('<'):
        tail = content[-200:]
        issues.append(f'Ends mid-tag; tail: "{tail}"')
    status = 'none' if not issues else ('POSSIBLE (' + ' | '.join(issues) + ')')
    return status, issues


def unit_specific_flags(content: str, filename: str) -> Tuple[List[str], Dict[str, int]]:
    notes: List[str] = []
    counters: Dict[str, int] = {}
    for tok, label in [('≠ˆ', 'Replace "≠ˆ"→"≈" candidates'),
                       ('≠¤', 'Replace "≠¤"→"≤" candidates'),
                       ('â†”', 'Replace "â†”"→"↔" candidates')]:
        n = content.count(tok)
        if n:
            counters[label] = n
    return notes, counters


def build_report(paths: List[str]) -> str:
    lines: List[str] = []
    files_with_errors: List[str] = []
    files_with_warn: List[str] = []
    clean_files: List[str] = []
    mojibake_totals: Dict[str, int] = {}
    bullet_need = 0
    header_issues = 0
    truncations = 0

    for path in paths:
        try:
            data, raw = read_json(path)
        except Exception as e:
            lines.append('QC REPORT')
            lines.append(f'[File] {os.path.basename(path)}')
            lines.append(f'JSON: ERROR({e})')
            lines.append('')
            files_with_errors.append(os.path.basename(path))
            continue

        fname = os.path.basename(path)
        section = str(data.get('section', ''))
        content = str(data.get('content', ''))

        lines.append('QC REPORT')
        lines.append(f'[File] {fname}')

        json_status, json_issues = check_fields(data)
        lines.append(f'JSON: {json_status}')

        html_status, html_issues = html_checks(content)
        lines.append(f'HTML: {html_status}')

        math_status, math_issues = mathml_checks(section, content)
        lines.append(f'MathML: {math_status}')

        counts, samples = mojibake_scan(content)
        total_moji = sum(counts.values())
        # accumulate totals
        for k, v in counts.items():
            mojibake_totals[k] = mojibake_totals.get(k, 0) + v
        lines.append(f'Mojibake: {total_moji}; {counts}')
        for tok, idx, snip in samples:
            lines.append('')
            lines.append(f'"{snip}" (offset ~{idx})')

        # Structure (Math only per spec target)
        structure_status = 'OK'
        struct_issues: List[str] = []
        if section.lower().startswith('math'):
            structure_status, struct_issues = structure_checks_math(content)
            lines.append('')
            lines.append(f'Structure: {structure_status}')
            if struct_issues:
                header_issues += 1
        else:
            lines.append('')
            lines.append('Structure: OK')

        # SAT Style (Math focus but we will scan anyway)
        sat_status, sat_issues = sat_style_checks(content)
        lines.append('')
        lines.append(f'SAT Style: {sat_status}')
        if any('MC answers as bullets' in x for x in sat_issues):
            bullet_need += 1

        # Truncation
        trunc_status, trunc_issues = truncation_check(content)
        lines.append('')
        lines.append(f'Truncation: {trunc_status}')
        if trunc_issues:
            truncations += 1

        # Unit-specific flags
        unit_notes, unit_counts = unit_specific_flags(content, fname)
        lines.append('')
        lines.append('UNIT-SPECIFIC flags (if any):')
        for label, n in unit_counts.items():
            lines.append(f'{label}: {n}')

        # Suggested safe fixes (report only)
        lines.append('')
        lines.append('Suggested SAFE Fixes (REPORT ONLY — not applied):')
        # A) literal tokens to replace
        if counts:
            repls = [f'"{k}"→"<correct>"' for k in counts.keys()]
            lines.append(f'Literal replacements: {repls}')
        else:
            lines.append('Literal replacements: []')

        # bullets
        if any('Fake bullets paragraph' in x for x in html_issues):
            lines.append('Bullet normalization targets: present (convert - lines to <ul><li>)')
        else:
            lines.append('Bullet normalization targets: []')

        # duplicate hr
        if any('Duplicate <hr>' in x for x in html_issues):
            lines.append('Duplicate <hr> collapse: present')
        else:
            lines.append('Duplicate <hr> collapse: []')

        # empty code blocks
        if any('Empty code block' in x for x in html_issues):
            lines.append('Empty <pre><code> removal points: present')
        else:
            lines.append('Empty <pre><code> removal points: []')

        # header normalization
        if section.lower().startswith('math') and struct_issues:
            lines.append('Header restructuring: needed to match template')
        else:
            lines.append('Header restructuring: []')

        lines.append('')

        # classify file status
        has_error = (json_status.startswith('ERROR(')) or ('ERROR(' in html_status) or ('ERROR(' in math_status)
        has_warn = (not has_error) and (html_issues or math_issues or counts or struct_issues)
        if has_error:
            files_with_errors.append(fname)
        elif has_warn:
            files_with_warn.append(fname)
        else:
            clean_files.append(fname)

    # Summary
    lines.append('Summary Totals')
    lines.append(f'- Files with ERRORS: {len(files_with_errors)} ({files_with_errors})')
    lines.append(f'- Files with WARN/LINT only: {len(files_with_warn)} ({files_with_warn})')
    lines.append(f'- Clean files: {len(clean_files)} ({clean_files})')
    lines.append(f'- Totals by issue type:')
    lines.append(f'  mojibake: {mojibake_totals}')
    lines.append(f'  bullet conversions needed (files): {bullet_need}')
    lines.append(f'  header issues (files): {header_issues}')
    lines.append(f'  truncations (files): {truncations}')
    return '\n'.join(lines)


def gather_files() -> List[str]:
    files: List[str] = []
    for root in WORK_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            if name.lower().endswith('.json'):
                files.append(os.path.join(root, name))
    files.sort()
    return files


def main(argv: List[str]) -> int:
    out_path = 'qc_report.txt'
    files = gather_files()
    report = build_report(files)
    with io.open(out_path, 'w', encoding='utf-8', newline='') as f:
        f.write(report)
    print(f'Wrote {out_path} with {len(files)} files scanned')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))


