#!/usr/bin/env python3
"""Reject incomplete or result-inconsistent speedrun session deliveries."""
import argparse
import json
import re
from pathlib import Path

from new_speedrun import REPO, RESULT_DIR, SESSION_DIR, date_key, pick_label


CORE_HEADINGS = (
    "### 真正要解决的问题",
    "### 最小机制",
    "### 逐项裁决",
    "### 最小验证",
)
PLACEHOLDERS = ("待命名机制", "`draft`", "<验证题>", "<!--", "TODO")


def session_sections(text):
    pattern = re.compile(r"^## (\d{2})｜(\d{4}-\d{2})：.+$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((int(match.group(1)), match.group(2), text[match.start():end]))
    return sections


def check(result, text):
    errors = []
    sections = session_sections(text)
    expected = result["items"]
    if len(sections) != len(expected):
        errors.append(f"question section count {len(sections)} != result count {len(expected)}")

    for position, (item, actual) in enumerate(zip(expected, sections), 1):
        idx, qid, section = actual
        if idx != int(item["idx"]) or qid != item["qid"]:
            errors.append(
                f"section {position}: got {idx:02d}/{qid}, "
                f"expected {int(item['idx']):02d}/{item['qid']}"
            )
        evidence = (
            f"首次作答：{pick_label(item.get('pick'))}；"
            f"正确答案：{item.get('answer') or '待核'}；"
            "当前状态：`explained`"
        )
        if evidence not in section:
            errors.append(f"{item['qid']}: first-attempt evidence or state does not match results")
        for heading in CORE_HEADINGS:
            if heading not in section:
                errors.append(f"{item['qid']}: missing {heading}")
        if "<details>" not in section or "<summary>核对</summary>" not in section:
            errors.append(f"{item['qid']}: missing folded verification answer")
        for placeholder in PLACEHOLDERS:
            if placeholder in section:
                errors.append(f"{item['qid']}: unresolved placeholder {placeholder}")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    key = date_key(args.date)
    result = json.loads((RESULT_DIR / f"{key}.json").read_text(encoding="utf-8"))
    session = SESSION_DIR / result["date"][:7] / f"{key}.md"
    text = session.read_text(encoding="utf-8")
    errors = check(result, text)
    if errors:
        for error in errors:
            print("FAIL", error)
        raise SystemExit(f"speedrun check failed: {len(errors)} issue(s)")
    print(f"PASS {session.relative_to(REPO)}: {len(result['items'])} questions closed")


if __name__ == "__main__":
    main()
