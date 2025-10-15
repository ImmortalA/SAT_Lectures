import json
import os
import re
from typing import Dict, List, Tuple

ROOT = os.path.join('data', 'units_processed')

MOJIBAKE_PATTERNS = [
    '—','â€“','â€˜','â€™','â€œ','â€','â€','â€¢','Â·','Â±','×','â†’','⇒','≠≥','≠¥','≠≤','≠ ','≠','Â','−','≠ˆ'
]

LATEX_ESCAPES = [r'\\\$', r'\\\(', r'\\\)']

def find_json_files() -> List[str]:
    found: List[str] = []
    for dirpath, _, filenames in os.walk(ROOT):
        for name in filenames:
            if name.endswith('.json'):
                found.append(os.path.join(dirpath, name))
    found.sort()
    return found

def load_json(path: str) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def has_mojibake(html: str) -> List[str]:
    hits = []
    for token in MOJIBAKE_PATTERNS:
        if token and token in html:
            hits.append(token)
    return hits

def has_latex_escapes(html: str) -> List[str]:
    hits = []
    for pat in LATEX_ESCAPES:
        if re.search(pat, html):
            hits.append(pat)
    return hits

def has_empty_code_block(html: str) -> bool:
    return re.search(r'<pre>\s*<code[^>]*>\s*</code>\s*</pre>', html, flags=re.IGNORECASE) is not None

def has_redundant_hr(html: str) -> bool:
    return re.search(r'(?:\s*<hr\s*/?>\s*){2,}', html, flags=re.IGNORECASE) is not None

def has_fake_bullets(html: str) -> bool:
    for m in re.finditer(r'<p>([\s\S]*?)</p>', html, flags=re.IGNORECASE):
        inner = m.group(1)
        parts = re.split(r'(?:<br\s*/?>|\r?\n)', inner)
        lines = [p.strip() for p in parts if p.strip()]
        if len(lines) >= 2 and all(re.match(r'^-+\s+', L) for L in lines):
            return True
    return False

def has_legacy_case_heading(html: str) -> bool:
    return re.search(r'<h[1-6]>\s*Case\s+\d+[^<]*</h[1-6]>', html, flags=re.IGNORECASE) is not None

def rw_item_structure_issues(html: str) -> List[str]:
    issues: List[str] = []
    # Each rw-item should have ul.choices with exactly four li data-choice=A-D
    for block in re.findall(r'<div class="rw-item"[\s\S]*?</div>', html):
        # choices
        ul = re.search(r'<ul class="choices">([\s\S]*?)</ul>', block)
        if not ul:
            issues.append('rw-item: missing choices list')
            continue
        lis = re.findall(r'<li[^>]*data-choice="([A-D])"[^>]*>', ul.group(1))
        if len(lis) != 4 or lis != ['A','B','C','D']:
            issues.append('rw-item: choices not exactly A–D in order')
    return issues

def validate_file(path: str) -> List[str]:
    problems: List[str] = []
    obj = load_json(path)
    content = obj.get('content', '')
    if not isinstance(content, str):
        problems.append('content: not a string')
        return problems

    # Global checks
    moj = has_mojibake(content)
    if moj:
        problems.append(f"mojibake: {' '.join(sorted(set(moj)))}")
    if has_latex_escapes(content):
        problems.append('latex-escapes: present')
    if has_empty_code_block(content):
        problems.append('empty-code-block: present')
    if has_redundant_hr(content):
        problems.append('redundant-hr: present')
    if has_fake_bullets(content):
        problems.append('fake-bullets: present')
    if has_legacy_case_heading(content):
        problems.append('legacy-case-heading: present')

    # Section-specific
    section = (obj.get('section') or '').lower()
    if 'reading' in section:
        rw_issues = rw_item_structure_issues(content)
        problems.extend(rw_issues)

    return problems

def main() -> None:
    files = find_json_files()
    any_issues = False
    for path in files:
        issues = validate_file(path)
        if issues:
            any_issues = True
            print(f"[ISSUES] {path}")
            for i in issues:
                print(f"  - {i}")
    if not any_issues:
        print('All lectures appear clean based on validator checks.')

if __name__ == '__main__':
    main()



