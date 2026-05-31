#!/usr/bin/env python3
"""Extract single-choice questions from 组成原理 PDF, output per-section Markdown files."""

import subprocess
import re
import os
import sys
from pathlib import Path

PDF_PATH = "/home/djology/408-from-44/27计算机组成原理_高清带书签版.pdf"
OUTPUT_DIR = "/home/djology/408-from-44/questions/computer_organization"
TMP_DIR = "/tmp/pdf_ocr_co"

# Chapter structure: {chapter_name: [(section_title, start_page, end_page), ...]}
# PDF page numbers (1-based). Page offset: PDF page = book page + 12.
# End page is inclusive. Parser stops at '答案与解析' and similar markers.
CHAPTERS = {
    "ch01_计算机系统概述": [
        ("1.2 计算机系统层次结构", 20, 21),
        ("1.3 计算机的主要性能指标", 25, 27),
    ],
    "ch02_数据的表示和运算": [
        ("2.1 数制与编码", 37, 41),
        ("2.2 运算方法和运算电路", 56, 59),
        ("2.3 浮点数的表示与运算", 73, 77),
    ],
    "ch03_存储系统": [
        ("3.2 主存储器", 99, 103),
        ("3.3 主存储器与CPU的连接", 111, 112),
        ("3.4 外部存储器", 117, 118),
        ("3.5 高速缓冲存储器", 129, 133),
        ("3.6 虚拟存储器", 147, 152),
    ],
    "ch04_指令系统": [
        ("4.1 指令系统", 163, 164),
        ("4.2 指令寻址方式", 172, 177),
        ("4.3 程序的机器级代码表示", 193, 201),
    ],
    "ch05_中央处理器": [
        ("5.1 CPU的功能和基本结构", 209, 210),
        ("5.2 指令执行过程", 216, 216),
        ("5.3 数据通路的功能和基本结构", 225, 232),
        ("5.4 控制器的功能和工作原理", 246, 253),
        ("5.6 指令流水线", 267, 271),
        ("5.7 多处理器的基本概念", 282, 282),
    ],
    "ch06_总线": [
        ("6.1 总线概述", 290, 291),
        ("6.2 总线操作和定时", 298, 299),
    ],
    "ch07_输入输出系统": [
        ("7.2 IO接口", 307, 308),
        ("7.3 IO方式", 321, 335),
    ],
}


def ocr_pages(start: int, end: int, tmp_prefix: str) -> str:
    """Convert PDF pages to images and OCR them. end is inclusive."""
    os.makedirs(TMP_DIR, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-f", str(start), "-l", str(end), "-r", "150",
         PDF_PATH, f"{TMP_DIR}/{tmp_prefix}"],
        capture_output=True, check=True
    )
    texts = []
    for i in range(start, end + 1):
        img = f"{TMP_DIR}/{tmp_prefix}-{i:03d}.ppm"
        if not os.path.exists(img):
            continue
        print(f"    OCR p{i}...", end="", flush=True)
        result = subprocess.run(
            ["tesseract", img, "stdout", "-l", "chi_sim", "--psm", "4"],
            capture_output=True, text=True
        )
        print(f" {len(result.stdout)} chars", flush=True)
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

    nums = []
    rest_start = 0
    num_pat = re.compile(r'^(\d{1,2})[S5s]?[.．，]?\s*$')
    garbled_pat = re.compile(r'^\d{3,}[.．，]?\s*$')
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


def section_filename(section_title: str) -> str:
    """Convert '1.2 计算机系统层次结构' -> '1.2_计算机系统层次结构'."""
    return section_title.strip().replace(" ", "_") + ".md"


def process_chapter(ch_name: str, sections: list) -> None:
    ch_dir = Path(OUTPUT_DIR) / ch_name
    ch_dir.mkdir(parents=True, exist_ok=True)

    for section_title, start, end in sections:
        print(f"  处理 {section_title} (PDF p{start}-{end})...", flush=True)
        tmp_prefix = f"co_{ch_name}_{start}"
        try:
            raw = ocr_pages(start, end, tmp_prefix)
            questions = parse_questions(raw)
            md = questions_to_markdown(section_title, questions)
            out_path = ch_dir / section_filename(section_title)
            out_path.write_text(md, encoding="utf-8")
            print(f"    识别到 {len(questions)} 道题 → {out_path.name}")
        except Exception as e:
            print(f"    失败: {e}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    filter_ch = sys.argv[1] if len(sys.argv) > 1 else None

    for ch_name, sections in CHAPTERS.items():
        if filter_ch and not ch_name.startswith(filter_ch):
            continue
        print(f"\n=== {ch_name} ===")
        process_chapter(ch_name, sections)

    print("\n全部完成！")


if __name__ == "__main__":
    main()
