#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import os
import re
from typing import List, Tuple


ALL_LECTURES = os.path.join('data', 'units_processed', 'all_lectures.json')


MATHML_RE = re.compile(r'<math[\s\S]*?</math>', re.IGNORECASE)
P_TAG_RE = re.compile(r'<p>([\s\S]*?)</p>', re.IGNORECASE)
BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)


def mask_mathml(html: str) -> Tuple[str, List[str]]:
    blocks: List[str] = []

    def sub(m: re.Match) -> str:
        blocks.append(m.group(0))
        return f'__MATHML_{len(blocks)-1}__'

    masked = MATHML_RE.sub(sub, html)
    return masked, blocks


def unmask_mathml(masked: str, blocks: List[str]) -> str:
    for i, b in enumerate(blocks):
        masked = masked.replace(f'__MATHML_{i}__', b)
    return masked


def fix_mojibake_visible(text: str, unit_title: str) -> str:
    repls = [
        ('â€”', '—'), ('â€“', '–'), ('â€˜', '‘'), ('â€™', '’'), ('â€œ', '“'), ('â€�', '”'),
        ('×', '×'), ('âˆ’', '−'), ('⇒', '⇒'),
    ]
    for bad, good in repls:
        text = text.replace(bad, good)

    # â‰ -> ≠ only when it precedes 0 or variables (visible text only)
    text = re.sub(r'â‰(?=\s*[0-9A-Za-z])', '≠', text)

    # Unit 9 specific: replace corrupted token ≠¤ -> ≤
    if 'Unit 9' in unit_title or 'unit 9' in unit_title.lower():
        text = text.replace('≠¤', '≤')
    return text


def collapse_duplicate_next_idea(text: str) -> str:
    # Collapse consecutive duplicate Next idea headers without intervening body
    # e.g., <h3>Next idea</h3><br /><h3>Next idea</h3> => single
    pattern = re.compile(
        r'(?:<h([1-6])>\s*Next\s+idea\s*</h\1>(?:\s|<br\s*/?>)*){2,}',
        re.IGNORECASE,
    )
    return pattern.sub(lambda m: f'<h{m.group(1)}>Next idea</h{m.group(1)}>', text)


def remove_stray_dot_breaks(text: str) -> str:
    # Remove stray " .<br/>" patterns
    text = re.sub(r'\s*\.\s*<br\s*/?>', '<br />', text, flags=re.IGNORECASE)
    # Remove orphan punctuation paragraphs like <p>.  </p>
    text = re.sub(r'<p>\s*[\.,;:!\?]\s*</p>', '', text, flags=re.IGNORECASE)
    # Collapse repeated <br/>
    text = re.sub(r'(?:\s*<br\s*/?>\s*){2,}', '<br />', text, flags=re.IGNORECASE)
    return text


def label_mc_choices(text: str) -> str:
    # Convert unlabeled 4-item bullets into labeled choices A-D using data-choice
    def process_ul(m: re.Match) -> str:
        ul_inner = m.group(1)
        lis = re.findall(r'<li([^>]*)>([\s\S]*?)</li>', ul_inner, flags=re.IGNORECASE)
        if len(lis) != 4:
            return m.group(0)
        # If already labeled with data-choice, do nothing
        if all('data-choice' in attrs.lower() for attrs, _ in lis):
            return m.group(0)
        # If items start with A./A)/B... assume already labeled visually; still add attributes if missing
        letters = ['A', 'B', 'C', 'D']
        rebuilt_items: List[str] = []
        for idx, (attrs, body) in enumerate(lis):
            if 'data-choice' not in attrs.lower():
                attrs = (attrs + f' data-choice="{letters[idx]}"').strip()
            rebuilt_items.append(f'<li{(" " + attrs) if attrs else ""}>{body}</li>')
        return '<ul>' + ''.join(rebuilt_items) + '</ul>'

    return re.sub(r'<ul>([\s\S]*?)</ul>', process_ul, text, flags=re.IGNORECASE)


def dedupe_problem_solution(text: str) -> str:
    # Safe heuristic: remove later duplicate paragraphs for Problem/Solution that exactly repeat
    seen: set[str] = set()
    out_parts: List[str] = []
    last_end = 0
    for m in P_TAG_RE.finditer(text):
        start, end = m.span()
        out_parts.append(text[last_end:start])
        p_html = m.group(0)
        inner = m.group(1).strip()
        key = None
        if re.match(r'<strong>\s*Problem\b', inner, flags=re.IGNORECASE):
            key = ('P:' + re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', inner))).strip()
        elif re.match(r'(?:<strong>\s*)?Solution\b', inner, flags=re.IGNORECASE):
            key = ('S:' + re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', inner))).strip()
        if key and key in seen:
            # drop this duplicate paragraph
            pass
        else:
            if key:
                seen.add(key)
            out_parts.append(p_html)
        last_end = end
    out_parts.append(text[last_end:])
    return ''.join(out_parts)


def clean_content(content: str, unit_title: str) -> str:
    masked, blocks = mask_mathml(content)
    masked = fix_mojibake_visible(masked, unit_title)
    masked = collapse_duplicate_next_idea(masked)
    masked = remove_stray_dot_breaks(masked)
    masked = label_mc_choices(masked)
    masked = dedupe_problem_solution(masked)
    return unmask_mathml(masked, blocks)


def find_all_content_spans(json_text: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    i = 0
    key_re = re.compile(r'"content"\s*:\s*"')
    while True:
        m = key_re.search(json_text, i)
        if not m:
            break
        start_quote = m.end() - 1  # position of the opening quote for value
        pos = start_quote + 1
        while pos < len(json_text):
            ch = json_text[pos]
            if ch == '\\':
                pos += 2
                continue
            if ch == '"':
                end_quote = pos + 1
                spans.append((start_quote, end_quote))
                i = end_quote
                break
            pos += 1
        else:
            # Unterminated string; stop
            break
    return spans


def main() -> None:
    with io.open(ALL_LECTURES, 'r', encoding='utf-8') as f:
        original_text = f.read()
    data = json.loads(original_text)
    if not isinstance(data, list):
        raise SystemExit('Expected top-level JSON array')

    # Prepare cleaned contents in array order (only for specific sections)
    cleaned_contents: List[str] = []
    for obj in data:
        section = str(obj.get('section', ''))
        content = str(obj.get('content', ''))
        unit_title = str(obj.get('unit', ''))
        if section in ('Math', 'Reading and Writing'):
            cleaned_contents.append(clean_content(content, unit_title))
        else:
            cleaned_contents.append(content)

    # Replace content string literals in the original text sequentially
    spans = find_all_content_spans(original_text)
    if len(spans) != len(cleaned_contents):
        # Fallback to JSON dump if mismatch (should not happen with consistent formatting)
        for idx, obj in enumerate(data):
            obj['content'] = cleaned_contents[idx]
        with io.open(ALL_LECTURES, 'w', encoding='utf-8', newline='') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return

    pieces: List[str] = []
    last = 0
    for (start, end), new_html in zip(spans, cleaned_contents):
        pieces.append(original_text[last:start])
        pieces.append(json.dumps(new_html, ensure_ascii=False))
        last = end
    pieces.append(original_text[last:])
    updated_text = ''.join(pieces)

    with io.open(ALL_LECTURES, 'w', encoding='utf-8', newline='') as f:
        f.write(updated_text)
    print(f'Updated {ALL_LECTURES} content fields')


if __name__ == '__main__':
    main()


