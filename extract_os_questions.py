#!/usr/bin/env python3
"""Extract single-choice questions from OS PDF and output per-chapter Markdown files."""

import subprocess
import re
import os
import sys
from pathlib import Path

PDF_PATH = "/home/djology/408-from-44/27操作系统-高清带书签.pdf"
OUTPUT_DIR = "/home/djology/408-from-44/questions"

# Chapter structure: {chapter_name: [(section_title, start_page, end_page), ...]}
# PDF page numbers (1-based). Page offset: PDF page = book page + 12.
# End page is inclusive (last page to OCR). Parser stops at '答案与解析' marker.
CHAPTERS = {
    "ch09_计算机系统概述": [
        ("1.1 操作系统的基本概念", 17, 18),
        ("1.2 操作系统的发展历程", 22, 23),
        ("1.3 操作系统的运行环境", 31, 34),
        ("1.6 虚拟机", 43, 44),
    ],
    "ch10_进程与线程": [
        ("2.1 进程与线程简介", 63, 88),
        ("2.2 CPU调度", 90, 98),
        ("2.3 同步与互斥", 120, 138),
        ("2.4 死锁", 169, 186),
    ],
    "ch11_内存管理": [
        ("3.1 内存管理概念", 203, 224),
        ("3.2 虚拟内存管理", 238, 248),
    ],
    "ch12_文件管理": [
        ("4.1 文件系统概述", 268, 282),
        ("4.2 目录与文件", 283, 293),
        ("4.3 文件系统", 305, 316),
    ],
    "ch13_输入输出管理": [
        ("5.1 IO管理概述", 326, 339),
        ("5.2 设备管理", 341, 345),
        ("5.3 磁盘和固态硬盘", 360, 370),
    ],
}


def ocr_pages(start: int, end: int, tmp_prefix: str) -> str:
    """Convert PDF pages to images and OCR them. end is inclusive."""
    os.makedirs("/tmp/pdf_ocr_os", exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-f", str(start), "-l", str(end), "-r", "200",
         PDF_PATH, f"/tmp/pdf_ocr_os/{tmp_prefix}"],
        capture_output=True, check=True
    )
    texts = []
    for i in range(start, end + 1):
        img = f"/tmp/pdf_ocr_os/{tmp_prefix}-{i:03d}.ppm"
        if not os.path.exists(img):
            continue
        result = subprocess.run(
            ["tesseract", img, "stdout", "-l", "chi_sim", "--psm", "4"],
            capture_output=True, text=True
        )
        texts.append(repair_separated_columns(result.stdout))
    return "\n".join(texts)


def split_two_column_opts(line: str) -> list[tuple[str, str]]:
    """Split a line like 'A. xxx    B. yyy' into pairs."""
    results = []
    parts = re.split(r'(?<!\w)([ABCD])[．.、，,]', line)
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
    """Fix OCR output where question numbers appear before their text."""
    lines = [l.strip() for l in raw_text.splitlines()]

    # Match book page numbers (1-3 digit standalone lines), 3+ digit codes, chapter headers, etc.
    # Use \s* to handle OCR-spaced headers like "第 2 章"
    header_pat = re.compile(r'^(\d{1,3}\s*$|\d{3,}|第\s*\d+\s*章|2027|购买王道)')
    skip_until = 0
    for i, line in enumerate(lines):
        if not line:
            continue
        if header_pat.match(line):
            skip_until = i + 1
        else:
            break

    lines_to_search = lines[skip_until:]

    # Find a cluster of >= 3 consecutive isolated question numbers (may appear after table content).
    # Allow skipping garbled 3-digit lines (e.g. "256." = misread "26.") within a cluster.
    nums = []
    rest_start = 0
    num_pat = re.compile(r'^(\d{1,2})[S5s]?[.．，]?\s*$')
    garbled_pat = re.compile(r'^\d{3,}[.．，]?\s*$')  # 3+ digit lines in a cluster = garbled num
    in_cluster = False
    for i, line in enumerate(lines_to_search):
        if not line:
            continue
        m = num_pat.match(line)
        if m and len(nums) < 30:
            nums.append(int(m.group(1)))
            rest_start = skip_until + i + 1
            in_cluster = True
        elif in_cluster and garbled_pat.match(line):
            # Skip garbled number lines within the cluster; rest_start stays at last good position
            continue
        elif in_cluster:
            rest_start = skip_until + i
            break

    if len(nums) < 3:
        return raw_text

    rest_lines = lines[rest_start:]

    def _block_has_D(block):
        for l in block:
            if l.startswith('D') and re.match(r'^D[.．，]', l):
                return True
            if re.search(r'(?<![A-Za-z])D[.．，]', l) and re.match(r'^[ABCD][.．，]', l):
                return True
        return False

    blocks = []
    current_block = []
    for line in rest_lines:
        if not line:
            continue
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
    stop_markers = ['答案与解析', '归纳总结', '思维拓展', '二、综合应用题', '综合应用题']
    for marker in stop_markers:
        idx = raw_text.find(marker)
        if idx != -1:
            raw_text = raw_text[:idx]

    # Note: per-page repair is already done in ocr_pages; skip second call here.
    lines = [l.rstrip() for l in raw_text.splitlines()]
    questions = []
    current_q = None
    current_opt = None
    in_question_section = False

    q_start = re.compile(r'^(\d[S5s]?\d?)[．.、，]\s*(.+)')
    single_opt = re.compile(r'^([ABCD])[．.、，]\s*(.+)')

    section_markers = ('项选择', '本选择', '元选择', '习题精选')
    skip_prefixes = ('本节试题', '购买王道', '2027 年', '一、', '二、')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if any(m in line for m in section_markers):
            in_question_section = True
            continue

        if not in_question_section:
            continue

        if any(line.startswith(p) for p in skip_prefixes):
            continue

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
    display_name = ch_name[5:].replace("_", " ")
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
