#!/usr/bin/env python3
"""
Conservative cleanup for extracted question markdown files.
Only applies changes that are unambiguously safe.
"""

import re
from pathlib import Path

QUESTIONS_DIR = Path("/home/djology/408-from-44/questions")


def clean_line(line: str) -> str:

    # ── SAFE: remove leading ，or , immediately after option marker ─────────
    # "- A. ，text"  →  "- A. text"
    # "- B.，text"   →  "- B. text"
    line = re.sub(r'^(- [A-D]\. )[，,]\s*', r'\1', line)
    line = re.sub(r'^(- [A-D]\.)[，,]\s*', r'\1 ', line)

    # ── SAFE: fix 二又X → 二叉X (OCR misreads 叉 as 又) ─────────────────────
    # Only in the specific compound words; never standalone 又
    line = re.sub(r'二又(树|排序|搜索|查找|堆|链|叉)', r'二叉\1', line)

    # ── SAFE: collapse 3+ consecutive spaces to 1 (OCR spacing artifacts) ───
    # Only between non-empty characters, not leading spaces
    line = re.sub(r'(?<=\S)  +(?=\S)', ' ', line)

    return line


def clean_markdown(text: str) -> str:
    lines = text.split('\n')
    return '\n'.join(clean_line(line) for line in lines)


def process_file(path: Path) -> int:
    original = path.read_text(encoding='utf-8')
    cleaned = clean_markdown(original)
    changed = sum(1 for a, b in zip(original.split('\n'), cleaned.split('\n')) if a != b)
    if cleaned != original:
        path.write_text(cleaned, encoding='utf-8')
    return changed


def main():
    files = sorted(QUESTIONS_DIR.glob('ch*.md'))
    total = 0
    for f in files:
        n = process_file(f)
        total += n
        print(f"  {f.name}: {n} 行变更")
    print(f"\n合计 {total} 行")


if __name__ == '__main__':
    main()
