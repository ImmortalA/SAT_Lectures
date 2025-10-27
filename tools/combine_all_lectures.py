#!/usr/bin/env python3
"""
Combine all lectures from units_processed/M and units_processed/V into all_lectures.json
"""
import json
import os
from pathlib import Path

def main():
    project_root = Path(__file__).parent.parent
    m_dir = project_root / "data" / "units_processed" / "M"
    v_dir = project_root / "data" / "units_processed" / "V"
    output_file = project_root / "data" / "units_processed" / "all_lectures.json"
    
    all_lectures = []
    
    # Process Math units (M directory)
    if m_dir.exists():
        print(f"Reading Math units from {m_dir}")
        for json_file in sorted(m_dir.glob("*.strict.json")):
            print(f"  Loading {json_file.name}")
            with open(json_file, 'r', encoding='utf-8') as f:
                lecture = json.load(f)
                all_lectures.append(lecture)
        print(f"  Added {len(list(m_dir.glob('*.strict.json')))} Math lectures")
    else:
        print(f"Warning: {m_dir} does not exist")
    
    # Process Verbal units (V directory)
    if v_dir.exists():
        print(f"Reading Verbal units from {v_dir}")
        for json_file in sorted(v_dir.glob("*.cleaned.json")):
            print(f"  Loading {json_file.name}")
            with open(json_file, 'r', encoding='utf-8') as f:
                lecture = json.load(f)
                all_lectures.append(lecture)
        print(f"  Added {len(list(v_dir.glob('*.cleaned.json')))} Verbal lectures")
    else:
        print(f"Warning: {v_dir} does not exist")
    
    # Write combined file
    print(f"\nWriting {len(all_lectures)} total lectures to {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_lectures, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully created {output_file}")
    print(f"  Total lectures: {len(all_lectures)}")
    
    # Summary by section
    by_section = {}
    for lecture in all_lectures:
        section = lecture.get('section', 'Unknown')
        by_section[section] = by_section.get(section, 0) + 1
    
    print("\nBreakdown by section:")
    for section, count in sorted(by_section.items()):
        print(f"  {section}: {count} lectures")

if __name__ == "__main__":
    main()
