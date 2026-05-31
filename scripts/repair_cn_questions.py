#!/usr/bin/env python3
"""Two-pass OCR repair for computer_networks questions.

Uses 300dpi + tesseract chi_sim --psm 4 (vs. 150dpi in original extract).
Applies targeted text corrections for common OCR artifacts.
Falls back to keeping existing question if OCR produces empty/garbled result.
"""

import subprocess
import re
import os
import sys
from pathlib import Path

PDF_PATH = "/home/djology/408-from-44/27计算机网络_高清带书签版.pdf"
OUTPUT_DIR = "/home/djology/408-from-44/questions/computer_networks"
TMP_DIR = "/tmp/pdf_ocr_cn_repair"

CHAPTERS = {
    "ch03_数据链路层": [
        ("3.1 数据链路层的功能", 64, 64),
        ("3.2 组帧", 67, 67),
        ("3.3 差错控制", 71, 72),
        ("3.4 流量控制与可靠传输机制", 79, 83),
        ("3.5 介质访问控制", 95, 96),
        ("3.6 局域网", 112, 117),
        ("3.7 广域网", 127, 127),
        ("3.8 数据链路层设备", 132, 134),
    ],
    "ch04_网络层": [
        ("4.1 网络层的功能", 144, 146),
        ("4.2 IPv4", 163, 176),
        ("4.3 IPv6", 196, 196),
        ("4.4 路由协议", 208, 219),
        ("4.5 多播", 222, 224),
        ("4.6 移动IP", 225, 225),
        ("4.7 网络层设备", 228, 230),
    ],
    "ch05_传输层": [
        ("5.1 传输层提供的服务", 239, 239),
        ("5.2 UDP", 243, 244),
        ("5.3 TCP", 258, 267),
    ],
    "ch02_物理层": [
        ("2.1 通信基础", 47, 51),
        ("2.2 传输介质", 56, 56),
        ("2.3 物理层设备", 59, 59),
    ],
    "ch01_计算机网络体系结构": [
        ("1.1 计算机网络概述", 21, 26),
        ("1.2 网络体系结构与参考模型", 34, 36),
    ],
    "ch06_应用层": [
        ("6.1 网络应用模型", 280, 280),
        ("6.2 域名系统", 285, 286),
        ("6.3 文件传输协议", 290, 291),
        ("6.4 电子邮件", 298, 300),
        ("6.5 万维网", 307, 310),
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# Text correction helpers
# ──────────────────────────────────────────────────────────────────────────────

# OCR confuses "IP" with many similar-looking characters
_IP_SUBS = [
    # standalone IP token before common suffixes
    (re.compile(r'\b(?:了P|JP|耳P|吓P|钙P|肋P|孔P|耻P|痴P|中P|TP|JJP|IJP|I了P|UJP|1P|AP)\b'), 'IP'),
    # IP followed by v4 / v6
    (re.compile(r'(?:了|耳|JP|吓|钙|肋|孔|耻|痴|中|T|JJ|IJ|I了|UJ|1|A)Pv([46])'), r'IPv\1'),
    # leftover "了" before 数据报/分组 (OCR of "IP")
    (re.compile(r'了(?=数据报|分组|地址|首部)'), 'IP'),
    # "P 数据报" with odd prefix
    (re.compile(r'\b[了JP耳吓钙肋孔耻痴中T]{1,2}(?= 数据报| 分组| 地址| 首部)'), 'IP'),
]

# "虚电路" is OCR'd as several variants
_VIRT_CIRCUIT_RE = re.compile(r'(?:庶|康|上庶|上康|[上]?虚)电路')

# bandwidth units
_BW_SUBS = [
    (re.compile(r'(\d+)\s*Mb[Aay]s\b'), r'\1Mb/s'),
    (re.compile(r'Mb[Aay]s\b'), 'Mb/s'),
    (re.compile(r'(\d+)\s*Kb[Aay]s\b'), r'\1kb/s'),
    (re.compile(r'(\d+)\s*kb[Aay]s\b'), r'\1kb/s'),
    (re.compile(r'(\d+)\s*GB[Aay]s\b'), r'\1Gb/s'),
    (re.compile(r'(\d+)\s*Gb[Aay]s\b'), r'\1Gb/s'),
]

# page-header/footer bleeds
_PAGE_HEADER_RE = re.compile(
    r'(?:^|\n)\s*(?:第\s*\d+\s*章\s*[^\n]*\d+|2027\s*年计[算划]机网络[^\n]*|\d{3,4})\s*(?:\n|$)',
    re.MULTILINE,
)

# trailing decoration characters after option text  (e.g.  'B. 提高效率 "')
_TRAILING_JUNK_RE = re.compile(r'[\s"，。、"]+$')

# errant underscore before option letter
_UNDERSCORE_OPT_RE = re.compile(r'^_([ABCD])\.\s*', re.MULTILINE)


def fix_text(text: str) -> str:
    """Apply all targeted OCR corrections to a block of text."""
    # IP variants
    for pat, repl in _IP_SUBS:
        text = pat.sub(repl, text)

    # virtual circuit
    text = _VIRT_CIRCUIT_RE.sub('虚电路', text)

    # bandwidth
    for pat, repl in _BW_SUBS:
        text = pat.sub(repl, text)

    # "计划机" → "计算机"
    text = text.replace('计划机', '计算机')

    # "IKB" / "I KB" → "1KB"  (OCR of "1KB" using capital I)
    text = re.sub(r'\bI\s*KB\b', '1KB', text)
    text = re.sub(r'\bI\s*kb\b', '1kb', text)

    # remove page headers/footers
    text = _PAGE_HEADER_RE.sub('\n', text)

    # trailing decoration on each line
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        # strip trailing junk only from option / stem lines, not blank lines
        if line.strip():
            line = _TRAILING_JUNK_RE.sub('', line)
        cleaned.append(line)
    text = '\n'.join(cleaned)

    # underscore before option letter
    text = _UNDERSCORE_OPT_RE.sub(r'- \1. ', text)

    return text


# ──────────────────────────────────────────────────────────────────────────────
# OCR helpers  (identical logic to extract_cn_questions.py but 300dpi)
# ──────────────────────────────────────────────────────────────────────────────

def ocr_pages(start: int, end: int, tmp_prefix: str) -> str:
    os.makedirs(TMP_DIR, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-f", str(start), "-l", str(end), "-r", "300",
         PDF_PATH, f"{TMP_DIR}/{tmp_prefix}"],
        capture_output=True, check=True,
    )
    texts = []
    for i in range(start, end + 1):
        img = f"{TMP_DIR}/{tmp_prefix}-{i:03d}.ppm"
        if not os.path.exists(img):
            continue
        print(f"    OCR p{i}...", end="", flush=True)
        result = subprocess.run(
            ["tesseract", img, "stdout", "-l", "chi_sim", "--psm", "4"],
            capture_output=True, text=True,
        )
        print(f" {len(result.stdout)} chars", flush=True)
        raw = fix_text(result.stdout)
        texts.append(repair_separated_columns(raw))
    return "\n".join(texts)


def split_two_column_opts(line: str) -> list[tuple[str, str]]:
    results = []
    parts = re.split(r'(?<!\w)([ABCD])[．.、，,]', line)
    prefix = parts[0].strip()
    pm = re.match(r'^([ABCD])[．.、，,]\s*(.+)', prefix)
    if pm:
        results.append((pm.group(1), pm.group(2).strip()))
    i = 1
    while i + 1 < len(parts):
        letter = parts[i].strip()
        content = parts[i + 1].strip()
        if letter in "ABCD" and content:
            results.append((letter, content))
        i += 2
    return results


def repair_separated_columns(raw_text: str) -> str:
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
            if re.match(r'^D[.．，]', l):
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


# ──────────────────────────────────────────────────────────────────────────────
# Question parsing
# ──────────────────────────────────────────────────────────────────────────────

def parse_questions(raw_text: str) -> list[dict]:
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
                current_q["options"][letter] = fix_text(content)
            current_opt = two_col[-1][0]
            continue

        q_match = q_start.match(line)
        opt_match = single_opt.match(line)

        if q_match:
            if current_q:
                questions.append(current_q)
            stem_raw = q_match.group(2).strip().lstrip('，,、．. ')
            current_q = {
                "num": int(q_match.group(1).upper().replace('S', '5').replace('s', '5')),
                "stem": fix_text(stem_raw),
                "options": {},
            }
            current_opt = None
        elif opt_match and current_q:
            letter = opt_match.group(1)
            content = fix_text(opt_match.group(2).strip())
            current_q["options"][letter] = content
            current_opt = letter
        elif current_q:
            if current_opt and current_opt in current_q["options"]:
                current_q["options"][current_opt] += " " + fix_text(line)
            elif not current_q["options"]:
                current_q["stem"] += " " + fix_text(line)

    if current_q:
        questions.append(current_q)

    return questions


# ──────────────────────────────────────────────────────────────────────────────
# Markdown rendering
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# Merge logic: prefer OCR questions but fall back to existing when OCR fails
# ──────────────────────────────────────────────────────────────────────────────

def read_existing_questions(md_path: Path) -> dict[int, dict]:
    """Parse existing markdown file back into question dicts keyed by num."""
    if not md_path.exists():
        return {}
    text = md_path.read_text(encoding="utf-8")
    questions = {}
    stem_re = re.compile(r'^\*\*(\d+)\.\*\*\s+(.+)$')
    opt_re = re.compile(r'^-\s+([ABCD])\.\s+(.+)$')
    current_num = None
    current_stem = None
    current_opts = {}

    for line in text.splitlines():
        sm = stem_re.match(line)
        if sm:
            if current_num is not None:
                questions[current_num] = {"num": current_num, "stem": current_stem, "options": current_opts}
            current_num = int(sm.group(1))
            current_stem = sm.group(2).strip()
            current_opts = {}
        elif opt_re.match(line) and current_num is not None:
            om = opt_re.match(line)
            current_opts[om.group(1)] = om.group(2).strip()
        elif line.startswith('---') and current_num is not None:
            questions[current_num] = {"num": current_num, "stem": current_stem, "options": current_opts}
            current_num = None
            current_stem = None
            current_opts = {}

    if current_num is not None:
        questions[current_num] = {"num": current_num, "stem": current_stem, "options": current_opts}
    return questions


def _q_is_valid(q: dict) -> bool:
    """True if question has a non-empty stem and at least 2 options."""
    if not q.get("stem", "").strip():
        return False
    opts = q.get("options", {})
    return len(opts) >= 2


def merge_questions(ocr_qs: list[dict], existing_qs: dict[int, dict]) -> list[dict]:
    """
    Merge OCR-extracted questions with existing questions.
    - If OCR question is valid → use it (with OCR text fixes already applied)
    - If OCR question is missing/invalid but existing is valid → keep existing
    - Preserve any existing questions not found by OCR (image-heavy, figure questions)
    """
    ocr_by_num: dict[int, dict] = {}
    for q in ocr_qs:
        n = q["num"]
        if n not in ocr_by_num or _q_is_valid(q):
            ocr_by_num[n] = q

    # collect all question numbers
    all_nums = sorted(set(list(ocr_by_num.keys()) + list(existing_qs.keys())))

    merged = []
    for n in all_nums:
        ocr_q = ocr_by_num.get(n)
        ex_q = existing_qs.get(n)

        if ocr_q and _q_is_valid(ocr_q):
            merged.append(ocr_q)
        elif ex_q and _q_is_valid(ex_q):
            # keep existing but apply text fixes
            ex_q_fixed = {
                "num": ex_q["num"],
                "stem": fix_text(ex_q["stem"]),
                "options": {k: fix_text(v) for k, v in ex_q["options"].items()},
            }
            merged.append(ex_q_fixed)
        # if neither is valid, skip (no partial/empty questions)

    return merged


def section_filename(section_title: str) -> str:
    return section_title.strip().replace(" ", "_") + ".md"


# ──────────────────────────────────────────────────────────────────────────────
# Main processing
# ──────────────────────────────────────────────────────────────────────────────

def process_section(ch_name: str, section_title: str, start: int, end: int) -> None:
    ch_dir = Path(OUTPUT_DIR) / ch_name
    ch_dir.mkdir(parents=True, exist_ok=True)
    out_path = ch_dir / section_filename(section_title)

    print(f"  {section_title} (PDF p{start}-{end})...", flush=True)
    tmp_prefix = f"cnr_{ch_name}_{start}"

    try:
        raw = ocr_pages(start, end, tmp_prefix)
    except subprocess.CalledProcessError as e:
        print(f"    pdftoppm failed: {e}")
        return

    ocr_qs = parse_questions(raw)
    existing_qs = read_existing_questions(out_path)
    merged = merge_questions(ocr_qs, existing_qs)

    print(f"    OCR:{len(ocr_qs)} existing:{len(existing_qs)} merged:{len(merged)} → {out_path.name}")

    md = questions_to_markdown(section_title, merged)
    out_path.write_text(md, encoding="utf-8")


def main():
    filter_ch = sys.argv[1] if len(sys.argv) > 1 else None

    for ch_name, sections in CHAPTERS.items():
        if filter_ch and not ch_name.startswith(filter_ch):
            continue
        print(f"\n=== {ch_name} ===")
        for section_title, start, end in sections:
            process_section(ch_name, section_title, start, end)

    print("\n全部完成！")


if __name__ == "__main__":
    main()
