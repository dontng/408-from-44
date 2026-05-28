#!/usr/bin/env python3
"""Extract single-choice questions from PDF and output per-chapter Markdown files."""

import subprocess
import re
import os
import sys
from pathlib import Path

PDF_PATH = "/home/djology/408-from-44/27数据结构_高清带书签版.pdf"
OUTPUT_DIR = "/home/djology/408-from-44/questions"

# Chapter structure: {chapter_name: [(section_title, start_page, end_page), ...]}
# Pages are PDF page numbers (1-based). End page is exclusive (= start of next section).
CHAPTERS = {
    "ch01_绪论": [
        ("1.1 数据结构的基本概念", 14, 15),
        ("1.2 算法和算法评价", 17, 19),
    ],
    "ch02_线性表": [
        ("2.1 线性表的定义和基本操作", 25, 26),
        ("2.2 线性表的顺序表示", 29, 31),
        ("2.3 线性表的链式表示", 50, 54),
    ],
    "ch03_栈队列和数组": [
        ("3.1 栈", 78, 80),
        ("3.2 队列", 93, 95),
        ("3.3 栈和队列的应用", 105, 107),
        ("3.4 数组和特殊矩阵", 115, 116),
    ],
    "ch04_串": [
        ("4.2 串的模式匹配", 129, 130),
    ],
    "ch05_树与二叉树": [
        ("5.1 树的基本概念", 137, 139),
        ("5.2 二叉树的概念", 144, 148),
        ("5.3 二叉树的遍历和线索二叉树", 157, 161),
        ("5.4 树、森林", 183, 185),
        ("5.5 树与二叉树的应用", 196, 198),
    ],
    "ch06_图": [
        ("6.1 图的基本概念", 209, 211),
        ("6.2 图的存储及基本操作", 218, 220),
        ("6.3 图的遍历", 230, 232),
        ("6.4 图的应用", 249, 255),
    ],
    "ch07_查找": [
        ("7.2 顺序查找和折半查找", 281, 283),
        ("7.3 树形查找", 303, 307),
        ("7.4 B树和B+树", 320, 326),
        ("7.5 散列表", 332, 337),
    ],
    "ch08_排序": [
        ("8.1 排序的基本概念", 343, 344),
        ("8.2 插入排序", 347, 349),
        ("8.3 交换排序", 355, 357),
        ("8.4 选择排序", 365, 368),
        ("8.5 归并排序基数排序和计数排序", 378, 381),
        ("8.6 各种内部排序算法的比较及应用", 385, 388),
        ("8.7 外部排序", 395, 400),
    ],
}


def ocr_pages(start: int, end: int, tmp_prefix: str) -> str:
    """Convert PDF pages to images and OCR them. end is inclusive."""
    os.makedirs("/tmp/pdf_ocr", exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-f", str(start), "-l", str(end), "-r", "200",
         PDF_PATH, f"/tmp/pdf_ocr/{tmp_prefix}"],
        capture_output=True, check=True
    )
    texts = []
    for i in range(start, end + 1):
        img = f"/tmp/pdf_ocr/{tmp_prefix}-{i:03d}.ppm"
        if not os.path.exists(img):
            continue
        result = subprocess.run(
            ["tesseract", img, "stdout", "-l", "chi_sim", "--psm", "4"],
            capture_output=True, text=True
        )
        texts.append(repair_separated_columns(result.stdout))
    return "\n".join(texts)


def split_two_column_opts(line: str) -> list[tuple[str, str]]:
    """Split a line like 'A. xxx    B. yyy' or 'A， xxx  B. yyy' into pairs."""
    results = []
    # Include Chinese comma ，and ASCII comma in separator set
    parts = re.split(r'(?<!\w)([ABCD])[．.、，,]', line)
    # parts: ['prefix', 'A', 'content_A', 'B', 'content_B', ...]
    # Check if prefix itself starts with an option (e.g. "A， xxx  " before B.)
    prefix = parts[0].strip()
    prefix_opt = re.match(r'^([ABCD])[．.、，,]\s*(.+)', prefix)
    if prefix_opt:
        results.append((prefix_opt.group(1), prefix_opt.group(2).strip()))
    i = 1
    while i + 1 < len(parts):
        letter = parts[i].strip()
        content = parts[i + 1].strip()
        if letter in "ABCD" and content:
            results.append((letter, content))
        i += 2
    return results


def repair_separated_columns(raw_text: str) -> str:
    """
    Fix OCR output where question numbers appear all at once before their text.
    Pattern detected: many bare 'NN.' lines clustered together, then question texts.
    Output: reassembled text with numbers prepended to their questions.
    """
    lines = [l.strip() for l in raw_text.splitlines()]

    # Skip header lines at the start (page numbers, chapter headers)
    header_pat = re.compile(r'^(\d{3,}|第\d+章|2027|购买王道)')
    skip_until = 0
    for i, line in enumerate(lines):
        if not line:
            continue
        if header_pat.match(line):
            skip_until = i + 1
        else:
            break

    lines_to_search = lines[skip_until:]

    # Collect leading isolated numbers (allow OCR noise like "05S.", "0S.")
    nums = []
    rest_start = 0
    for i, line in enumerate(lines_to_search):
        if not line:
            continue
        m = re.match(r'^(\d{1,2})[S5s]?[.．，]?\s*$', line)
        if m and len(nums) < 30:
            nums.append(int(m.group(1)))
            rest_start = skip_until + i + 1
        elif nums:
            rest_start = skip_until + i
            break
        else:
            return raw_text  # no isolated numbers → no repair needed

    if len(nums) < 3:
        return raw_text  # not enough to be sure it's a column issue

    # Remaining lines from original (include headers for context)
    rest_lines = lines[rest_start:]

    # Split rest_lines into question blocks by detecting option patterns
    # A block boundary: previous block had D option (on its own line or within a multi-option line)
    def _block_has_D(block):
        for l in block:
            if l.startswith('D') and re.match(r'^D[.．，]', l):
                return True
            # D option embedded in multi-option line: "A. ... B. ... C. ... D. ..."
            if re.search(r'(?<![A-Za-z])D[.．，]', l) and re.match(r'^[ABCD][.．，]', l):
                return True
        return False

    blocks = []
    current_block = []
    for line in rest_lines:
        if not line:
            continue
        # Skip page-header lines that sneak in between columns
        if re.match(r'^(第\d+章|2027|购买王道|\d{3,})', line):
            continue
        has_D = _block_has_D(current_block)
        is_option = re.match(r'^[ABCD][.．，]', line)
        if has_D and not is_option and current_block:
            blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)

    if not blocks:
        return raw_text

    # Prepend numbers to blocks
    # Determine starting number (might not be 01)
    start_num = min(nums) if nums else 1
    result_lines = []
    for i, block in enumerate(blocks):
        n = nums[i] if i < len(nums) else start_num + i
        result_lines.append(f"{n:02d}. {block[0]}")
        result_lines.extend(block[1:])
        result_lines.append("")
    return "\n".join(result_lines)


def parse_questions(raw_text: str) -> list[dict]:
    """Parse OCR text into list of {num, stem, options} dicts."""
    # Cut off at answer/analysis section
    stop_markers = ['答案与解析', '归纳总结', '思维拓展', '二、综合应用题', '综合应用题']
    for marker in stop_markers:
        idx = raw_text.find(marker)
        if idx != -1:
            raw_text = raw_text[:idx]

    raw_text = repair_separated_columns(raw_text)
    lines = [l.rstrip() for l in raw_text.splitlines()]
    questions = []
    current_q = None
    current_opt = None
    in_question_section = False  # only parse after 单项选择题 header

    q_start = re.compile(r'^(\d[S5s]?\d?)[．.、，]\s*(.+)')
    single_opt = re.compile(r'^([ABCD])[．.、，]\s*(.+)')

    section_markers = ('项选择', '本选择', '元选择')  # handles OCR variants: 单项/音项/单本/单元
    skip_prefixes = ('本节试题', '购买王道', '2027 年', '一、', '二、')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Activate parsing once we hit the question section header
        if any(m in line for m in section_markers):
            in_question_section = True
            continue

        if not in_question_section:
            continue

        if any(line.startswith(p) for p in skip_prefixes):
            continue

        # Two-column options: "A. xxx    B. yyy" or "A. xxx   C. yyy"
        two_col = split_two_column_opts(line)
        if two_col and current_q and len(two_col) >= 2:
            for letter, content in two_col:
                current_q["options"][letter] = content
            current_opt = two_col[-1][0]
            continue

        q_match = q_start.match(line)
        opt_match = single_opt.match(line)

        if q_match:
            if current_q:
                questions.append(current_q)
            stem_raw = q_match.group(2).strip().lstrip('，,、．. ')
            current_q = {
                "num": int(q_match.group(1).upper().replace('S', '5')),
                "stem": stem_raw,
                "options": {}
            }
            current_opt = None
        elif opt_match and current_q:
            letter = opt_match.group(1)
            content = opt_match.group(2).strip()
            current_q["options"][letter] = content
            current_opt = letter
        elif current_q:
            if current_opt and current_opt in current_q["options"]:
                current_q["options"][current_opt] += " " + line
            elif not current_q["options"]:
                current_q["stem"] += " " + line

    if current_q:
        questions.append(current_q)

    return questions


def questions_to_markdown(section_title: str, questions: list[dict]) -> str:
    if not questions:
        return f"### {section_title}\n\n> （未识别到题目）\n\n"

    lines = [f"### {section_title}\n"]
    for q in questions:
        lines.append(f"**{q['num']:02d}.** {q['stem']}\n")
        for letter in "ABCD":
            if letter in q["options"]:
                lines.append(f"- {letter}. {q['options'][letter]}")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def process_chapter(ch_name: str, sections: list) -> str:
    display_name = ch_name[5:].replace("_", " ")  # "ch01_绪论" -> "绪论"
    ch_num = ch_name[2:4]
    md_lines = [f"# 第{ch_num}章 {display_name} — 单项选择题\n"]

    for section_title, start, end in sections:
        print(f"  处理 {section_title} (PDF p{start}-{end})...", flush=True)
        tmp_prefix = f"{ch_name}_{start}"
        try:
            raw = ocr_pages(start, end, tmp_prefix)
            questions = parse_questions(raw)
            md_lines.append(questions_to_markdown(section_title, questions))
            print(f"    识别到 {len(questions)} 道题")
        except Exception as e:
            md_lines.append(f"### {section_title}\n\n> 处理失败: {e}\n\n")
            print(f"    失败: {e}")

    return "\n".join(md_lines)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Allow filtering by chapter: python3 extract_questions.py ch01
    filter_ch = sys.argv[1] if len(sys.argv) > 1 else None

    for ch_name, sections in CHAPTERS.items():
        if filter_ch and not ch_name.startswith(filter_ch):
            continue
        print(f"\n=== {ch_name} ===")
        md = process_chapter(ch_name, sections)
        out_path = Path(OUTPUT_DIR) / f"{ch_name}.md"
        out_path.write_text(md, encoding="utf-8")
        print(f"  已写入 {out_path}")

    print("\n全部完成！")


if __name__ == "__main__":
    main()
