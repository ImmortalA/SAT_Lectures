# clean_all_lectures.py — HTML + MathML SAFE cleaner for all_lectures.json
import json, re, os, sys

IN_PATH = "all_lectures.json"
OUT_PATH = "all_lectures.cleaned.json"

MOJIBAKE_MAP = (
    ("â€”","—"),("â€“","–"),("â€˜","‘"),("â€™","’"),("â€œ","“"),("â€�","”"),
    ("â€¢","•"),("Â·","·"),("Â±","±"),("Ã—","×"),("â†’","→"),("â‡’","⇒"),
    ("â‰≥","≥"),("â‰¥","≥"),("â‰≤","≤"),("â‰ ","≠"),("â‰","≠"),("âˆ’","−"),("â‰ˆ","≈"),
)
UNIT_FIXES = (("≠ˆ","≈"),("≠¤","≤"),("â†”","↔"))

def _collapse_hr(html:str)->str:
    return re.sub(r"(?:\s*<hr\s*/?>\s*){2,}", "<hr />", html, flags=re.I)

def _rm_empty_code(html:str)->str:
    return re.sub(r"<pre><code[^>]*>\s*</code></pre>", "", html, flags=re.I)

def _rm_orphan_periods(html:str)->str:
    html = re.sub(r"\s*\.\s*<br\s*/?>", "<br />", html, flags=re.I)
    html = re.sub(r"<p>\s*\.\s*</p>", "", html, flags=re.I)
    return html

def _debackslash_math(html:str)->str:
    # Remove accidental backslashes before <math>
    return re.sub(r"\\+(?=<math\b)", "", html)

def _fake_bullets_to_ul(html:str)->str:
    # Convert <p>- a<br>- b</p> to <ul><li>a</li><li>b</li></ul>
    def repl(m):
        inner = m.group(1)
        parts = re.split(r"(?:<br\s*/?>|\r?\n)", inner)
        lines = [p.strip() for p in parts if p.strip()]
        if lines and all(l.startswith("- ") for l in lines):
            lis = "".join(f"<li>{l[2:]}</li>" for l in lines)
            return f"<ul>{lis}</ul>"
        return m.group(0)
    return re.sub(r"<p>(.*?)</p>", repl, html, flags=re.I|re.S)

def _cap_br(html:str)->str:
    # Limit 3+ <br> in a row to two
    return re.sub(r"(?:(?:<br\s*/?>)\s*){3,}", "<br />\n<br />", html, flags=re.I)

def clean_html(html:str)->str:
    for bad, good in MOJIBAKE_MAP: html = html.replace(bad, good)
    for bad, good in UNIT_FIXES:    html = html.replace(bad, good)
    html = _debackslash_math(html)
    html = _collapse_hr(html)
    html = _rm_empty_code(html)
    html = _rm_orphan_periods(html)
    html = _fake_bullets_to_ul(html)
    html = _cap_br(html)
    return html

def main():
    with open(IN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    changed = 0
    if isinstance(data, list):
        for obj in data:
            if isinstance(obj, dict) and "content" in obj:
                before = obj["content"]
                after  = clean_html(before)
                if after != before: changed += 1
                obj["content"] = after
    elif isinstance(data, dict) and "content" in data:
        before = data["content"]
        after  = clean_html(before)
        if after != before: changed += 1
        data["content"] = after
    else:
        print("Unexpected JSON top-level shape; expected list of objects.")
        sys.exit(2)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Cleaned objects: {changed}")
    print(f"Wrote: {OUT_PATH}")

if __name__ == "__main__":
    main()
