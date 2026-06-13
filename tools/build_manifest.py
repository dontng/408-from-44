#!/usr/bin/env python3
"""扫描 bank/ 生成网页用的题库清单 web/data.js。

每年的标准答案(可选)放在 bank/<year>/answers.txt，每行 "题号 答案"，如:
    1 D
    2 D
没有答案的题，answer 为 null，网页里走"自判对错"模式。
"""
import os, re, json, glob

BANK = "bank"
OUT = "web/data.js"


def load_answers(year_dir):
    path = os.path.join(year_dir, "answers.txt")
    ans = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            m = re.match(r'\s*(\d{1,2})\s*[\s.:：]\s*([A-Da-d])', line)
            if m:
                ans[int(m.group(1))] = m.group(2).upper()
    return ans


def main():
    items = []
    for year_dir in sorted(glob.glob(os.path.join(BANK, "*"))):
        if not os.path.isdir(year_dir):
            continue
        year = os.path.basename(year_dir)
        ans = load_answers(year_dir)
        for png in sorted(glob.glob(os.path.join(year_dir, "q*.png"))):
            m = re.search(r'q(\d{2})\.png$', png)
            if not m:
                continue
            q = int(m.group(1))
            items.append({
                "id": f"{year}-{q:02d}",
                "year": year,
                "q": q,
                "img": "../" + png.replace("\\", "/"),  # 相对 web/index.html
                "answer": ans.get(q),
            })
    os.makedirs("web", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.QUESTIONS = " + json.dumps(items, ensure_ascii=False, indent=1) + ";\n")
    have = sum(1 for it in items if it["answer"])
    print(f"清单 {len(items)} 题 → {OUT}（其中 {have} 题有答案）")


if __name__ == "__main__":
    main()
