#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List


ROOT = Path(__file__).resolve().parents[1]
UNITS_DIR = ROOT / "data" / "units_processed"
OUTPUT_FILE = UNITS_DIR / "all_lectures.json"


def is_target_file(path: Path) -> bool:
    name = path.name
    # Include cleaned files from M and V
    return name.endswith(".cleaned.json")


def collect_objects() -> List[Any]:
    results: List[Any] = []
    for path in sorted(UNITS_DIR.rglob("*.json")):
        if not is_target_file(path):
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                results.append(data)
        except Exception as e:
            print(f"[skip] {path}: {e}")
            continue
    return results


def main() -> None:
    items = collect_objects()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


