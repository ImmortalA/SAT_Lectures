#!/usr/bin/env python3
import io
import json
import os
import sys

from clean_content import clean_content_html


def check_idempotent(path: str) -> bool:
    with io.open(path, 'r', encoding='utf-8') as f:
        txt = f.read()
    obj = json.loads(txt)
    if not isinstance(obj.get('content'), str):
        print(f'FAIL {path}: missing string content')
        return False
    fname = os.path.basename(path)
    # map ...cleaned.json back to original name for micro-patches
    base = fname.replace('.cleaned.json', '.json') if fname.endswith('.cleaned.json') else fname
    again = clean_content_html(obj['content'], base)
    if again != obj['content']:
        print(f'FAIL {path}: not idempotent')
        return False
    print(f'OK {path}: idempotent')
    return True


def main(argv):
    if len(argv) < 2:
        print('Usage: python tools/validate_cleaned.py path1.cleaned.json [path2 ...]')
        return 2
    ok = True
    for p in argv[1:]:
        ok = check_idempotent(p) and ok
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))




