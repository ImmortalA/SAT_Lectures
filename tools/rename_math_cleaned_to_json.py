import os
import sys

TARGET_DIR = os.path.join('data', 'units_processed', 'M')


def main() -> int:
    if not os.path.isdir(TARGET_DIR):
        print(f"[error] Missing directory: {TARGET_DIR}")
        return 1

    renamed = 0
    skipped = 0
    for name in os.listdir(TARGET_DIR):
        if not name.endswith('.student.cleaned.json'):
            continue
        src = os.path.join(TARGET_DIR, name)
        dst = os.path.join(TARGET_DIR, name.replace('.student.cleaned.json', '.json'))
        try:
            if os.path.exists(dst):
                # Avoid overwriting existing .json; skip (caller can handle merges separately)
                print(f"[skip] Exists: {dst}")
                skipped += 1
                continue
            os.replace(src, dst)
            print(f"[renamed] {name} -> {os.path.basename(dst)}")
            renamed += 1
        except OSError as exc:
            print(f"[error] {name}: {exc}")
            skipped += 1

    print(f"Done. Renamed: {renamed}, Skipped: {skipped}")
    return 0


if __name__ == '__main__':
    sys.exit(main())



