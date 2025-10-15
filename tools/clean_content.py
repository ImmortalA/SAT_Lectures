#!/usr/bin/env python3
"""
Clean SAT lesson JSON files by transforming ONLY the "content" field per rules:
 - Mojibake normalization (A)
 - LaTeX escapes in visible text (B) (never touch MathML)
 - Remove empty <pre><code> blocks (C)
 - Collapse duplicate <hr> (D)
 - Convert fake hyphen bullets into real lists (E)
 - Optionally fold legacy headings to student-facing wrapper (F)
 - Unit-specific micro-patches (by filename)

STRICT CONSTRAINTS
 - Preserve MathML substrings byte-for-byte: never modify content inside <math>...</math>
 - Modify ONLY the JSON value for the "content" key, keep the rest of the file text identical
 - Idempotent: subsequent runs produce no diffs

USAGE
  python tools/clean_content.py path/to/file1.json [path/to/file2.json ...]

Outputs side-by-side files with suffix .cleaned.json in the same directory.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
from typing import Dict, List, Tuple


# --------------------------- JSON content replacement ---------------------------

def _find_content_string_span(json_text: str) -> Tuple[int, int]:
    """Find the start and end indices (inclusive-exclusive) of the JSON string literal
    representing the value for the "content" key. This is a textual scan which preserves
    all other file bytes.

    Returns (start_index_of_open_quote, end_index_past_closing_quote).
    Raises ValueError if not found or malformed.
    """
    # Find the key "content" as a JSON string key, allowing whitespace around colon
    key_pattern = re.compile(r'("content"\s*:\s*)', re.DOTALL)
    key_match = key_pattern.search(json_text)
    if not key_match:
        raise ValueError('"content" key not found')

    pos = key_match.end(1)
    # Skip whitespace until the starting quote of the string value
    while pos < len(json_text) and json_text[pos].isspace():
        pos += 1
    if pos >= len(json_text) or json_text[pos] not in ('"',):
        raise ValueError('"content" value is not a JSON string at expected position')

    start = pos  # position of the opening quote
    pos += 1
    # Scan to find matching closing quote while handling escapes
    while pos < len(json_text):
        ch = json_text[pos]
        if ch == '\\':
            # Skip the escaped character
            pos += 2
            continue
        if ch == '"':
            end = pos + 1
            return start, end
        pos += 1
    raise ValueError('Unterminated JSON string for "content"')


def _replace_content_value_textually(original_json_text: str, new_content: str) -> str:
    """Replace the JSON string literal value of the "content" field with the JSON-encoded
    literal of new_content, preserving all other bytes in the file.
    """
    start, end = _find_content_string_span(original_json_text)
    # Dump the new content as a JSON string literal (including quotes)
    # ensure_ascii=False to keep Unicode characters as-is
    encoded = json.dumps(new_content, ensure_ascii=False)
    return original_json_text[:start] + encoded + original_json_text[end:]


# --------------------------- Content transformations ---------------------------

MATHML_BLOCK_RE = re.compile(r'<math[\s\S]*?</math>', re.IGNORECASE)


def _extract_mathml_blocks(html: str) -> Tuple[str, List[str]]:
    """Replace each MathML <math>...</math> block with a unique placeholder and
    return the transformed html and the list of original blocks in order.
    """
    blocks: List[str] = []

    def _substitute(match: re.Match) -> str:
        blocks.append(match.group(0))
        return f"__MATHML_BLOCK_{len(blocks)-1}__"

    masked = MATHML_BLOCK_RE.sub(_substitute, html)
    return masked, blocks


def _restore_mathml_blocks(masked_html: str, blocks: List[str]) -> str:
    for i, block in enumerate(blocks):
        masked_html = masked_html.replace(f"__MATHML_BLOCK_{i}__", block)
    return masked_html


def _normalize_mojibake(text: str) -> str:
    replacements = [
        ('—', '—'), ('â€“', '–'), ('â€˜', '‘'), ('â€™', '’'), ('â€œ', '“'), ('â€', '”'),
        ('â€¢', '•'), ('Â·', '·'), ('Â±', '±'), ('×', '×'),
        ('â†’', '→'), ('⇒', '⇒'),
        ('≠≥', '≥'), ('≠¥', '≥'), ('≠≤', '≤'), ('≠ ', '≠'), ('≠', '≠'),
        ('−', '−'), ('≠ˆ', '≈'),
    ]
    for bad, good in replacements:
        text = text.replace(bad, good)

    # Remove lone 'Â' when surrounded by whitespace/punctuation
    # Pass 1: replace space-Â-space → single space (idempotent)
    text = re.sub(r'\sÂ\s', ' ', text)
    # Pass 2: remove Â when preceded/followed by boundary punct/space/start/end
    text = re.sub(r'(^|[\s\.,;:!\?\-])Â(?=($|[\s\.,;:!\?\-]))', r'\1', text)
    return text


def _unescape_latex_visible(text: str) -> str:
    # Only outside MathML; caller ensures masking.
    text = text.replace('\\$', '$')
    text = text.replace('\\(', '(')
    text = text.replace('\\)', ')')
    return text


EMPTY_CODE_BLOCK_RE = re.compile(r'<pre>\s*<code[^>]*>\s*</code>\s*</pre>', re.IGNORECASE)


def _remove_empty_code_blocks(text: str) -> str:
    return EMPTY_CODE_BLOCK_RE.sub('', text)


def _collapse_hr(text: str) -> str:
    # Normalize different <hr> syntaxes into runs, then collapse to a single canonical <hr />
    hr_pattern = re.compile(r'(?:<hr(?:\s*/?)>)', re.IGNORECASE)
    # Replace any run of hr tags with a single placeholder, then replace back with canonical form
    def _collapse_runs(m: re.Match) -> str:
        return '<hr />'

    # First, coalesce consecutive hr tags regardless of whitespace
    text = re.sub(r'(?:(?:\s*<hr(?:\s*/?)>\s*){2,})', '<hr />', text, flags=re.IGNORECASE)
    # Then, leave single hr tags as-is, but we can normalize them to <hr /> for consistency
    text = hr_pattern.sub('<hr />', text)
    return text


P_TAG_RE = re.compile(r'<p>([\s\S]*?)</p>', re.IGNORECASE)
BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)


def _convert_fake_bullets(text: str) -> str:
    def _process_paragraph(m: re.Match) -> str:
        inner = m.group(1)
        # Split on <br> variants or newlines to detect lines
        split_lines = BR_RE.split(inner)
        lines = [ln.strip() for ln in split_lines]
        non_empty = [ln for ln in lines if ln.strip()]
        if not non_empty:
            return m.group(0)

        is_bullet = [ln.lstrip().startswith('- ') for ln in non_empty]

        if all(is_bullet):
            items = [ln.lstrip()[2:].strip() for ln in non_empty]
            # Preserve MathML placeholders in items; do not alter
            lis = ''.join(f'<li>{it}</li>' for it in items)
            return f'<ul>{lis}</ul>'

        if any(is_bullet) and not all(is_bullet):
            bullet_items: List[str] = []
            prose_lines: List[str] = []
            for ln in lines:
                stripped = ln.strip()
                if not stripped:
                    # Preserve blank lines as empty breaks in prose
                    prose_lines.append('')
                    continue
                if stripped.lstrip().startswith('- '):
                    bullet_items.append(stripped.lstrip()[2:].strip())
                else:
                    prose_lines.append(stripped)

            # Rebuild prose with <br /> separators where blanks existed
            prose_body = '<br />'.join(prose_lines).strip()
            ul = ''.join(f'<li>{it}</li>' for it in bullet_items)
            ul_block = f'<ul>{ul}</ul>' if bullet_items else ''
            if prose_body:
                return f'<p>{prose_body}</p>{ul_block}'
            else:
                return ul_block or m.group(0)

        return m.group(0)

    # Apply paragraph-wise
    return P_TAG_RE.sub(_process_paragraph, text)


HEADING_TAG_RE = re.compile(r'<h([1-6])>([\s\S]*?)</h\1>', re.IGNORECASE)


def _fold_legacy_headings(text: str) -> str:
    def _replace_heading(m: re.Match) -> str:
        heading_text = m.group(2)
        # Strip HTML tags for matching, but keep original content for reinsertion
        plain = re.sub(r'<[^>]+>', '', heading_text).strip()
        if re.match(r'^(?:Case\s+\d+:|Key\s+rules|Steps|Methods)\b', plain, flags=re.IGNORECASE):
            # Replace heading with student-facing wrapper; keep original title bold
            safe_title = heading_text.strip()
            return (
                '<h3>Next idea</h3>'
                '<p>Build on the previous idea. Notice what changes and what stays the same.</p>'
                f'<p><strong>{safe_title}</strong></p>'
            )
        return m.group(0)

    return HEADING_TAG_RE.sub(_replace_heading, text)


def _apply_unit_micro_patches(text: str, filename: str) -> str:
    name = os.path.basename(filename)
    if name == 'unit-04-rates.json':
        text = text.replace('≠ˆ', '≈')
    elif name == 'unit-09-inequalities.json':
        text = text.replace('≠¤', '≤')
    elif name == 'unit-08-systems-of-equations.json':
        text = text.replace('9/5 . Then y', '9/5. Then y')
    elif name == 'unit-02-percent.json':
        # Replace only the corrupted sentence starting with the lead-in
        text = re.sub(
            r'Example: salary increases[^\n<]*',
            'Example: salary increases $2000 each year → y = 2000t + P',
            text,
        )
    return text


def clean_content_html(original_html: str, filename: str) -> str:
    """Apply ordered fixes (A→F) and micro-patches to the provided HTML content.
    MathML blocks are preserved byte-for-byte.
    """
    masked, math_blocks = _extract_mathml_blocks(original_html)

    # A) Mojibake
    masked = _normalize_mojibake(masked)

    # B) LaTeX escapes (visible text only; MathML masked)
    masked = _unescape_latex_visible(masked)

    # C) Empty <pre><code> blocks
    masked = _remove_empty_code_blocks(masked)

    # D) Redundant <hr>
    masked = _collapse_hr(masked)

    # E) Fake bullets to real lists
    masked = _convert_fake_bullets(masked)

    # F) Fold legacy headings
    masked = _fold_legacy_headings(masked)

    # Unit-specific micro-patches
    masked = _apply_unit_micro_patches(masked, filename)

    # Restore MathML blocks exactly
    cleaned = _restore_mathml_blocks(masked, math_blocks)
    return cleaned


def _load_json_and_get_content(path: str) -> Tuple[str, str]:
    with io.open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    # Parse only to ensure JSON validity and to access the content value
    try:
        data = json.loads(text)
    except Exception as e:
        raise RuntimeError(f'Failed to parse JSON for {path}: {e}')
    if 'content' not in data or not isinstance(data['content'], str):
        raise RuntimeError(f'JSON at {path} missing string "content" field')
    return text, data['content']


def _write_cleaned_json(original_json_text: str, cleaned_content: str, out_path: str) -> None:
    updated = _replace_content_value_textually(original_json_text, cleaned_content)
    with io.open(out_path, 'w', encoding='utf-8', newline='') as f:
        f.write(updated)


def process_file(path: str) -> str:
    base, ext = os.path.splitext(path)
    out_path = f"{base}.cleaned{ext}"
    original_json_text, orig_content = _load_json_and_get_content(path)
    cleaned_content = clean_content_html(orig_content, os.path.basename(path))
    _write_cleaned_json(original_json_text, cleaned_content, out_path)
    return out_path


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print('Usage: python tools/clean_content.py path/to/file1.json [file2.json ...]')
        return 2
    exit_code = 0
    for path in argv[1:]:
        try:
            out_path = process_file(path)
            # Use ASCII arrow to avoid Windows console encoding issues
            print(f'Cleaned {path} -> {out_path}')
        except Exception as e:
            exit_code = 1
            print(f'ERROR cleaning {path}: {e}', file=sys.stderr)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))


