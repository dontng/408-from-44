#!/usr/bin/env python3
"""从 answers/<year>答案.pdf 抽取选择题(1~40)标准答案 → answers/<year>.txt。

优先用逐题"N.【正确答案】X"，回退到顶部答案总表"N．X"。
"""
import re, glob, os, subprocess


def pdftext(path):
    return subprocess.run(["pdftotext", "-layout", path, "-"],
                          capture_output=True, text=True).stdout


def extract(text):
    ans = {}
    # 首选：逐题【正确答案】
    for m in re.finditer(r'(\d{1,2})\s*[.．、]\s*【\s*正确答案\s*】\s*([A-Da-d])', text):
        q = int(m.group(1))
        if 1 <= q <= 40:
            ans[q] = m.group(2).upper()
    if len(ans) >= 35:
        return ans
    # 回退：顶部总表（在"单项选择题"之后、"二、"之前找 N．X）
    head = text
    mstart = re.search(r'单项选择题', text)
    if mstart:
        head = text[mstart.end():]
    mend = re.search(r'二\s*[、.]', head)
    if mend:
        head = head[:mend.start()]
    for m in re.finditer(r'(?<!\d)(\d{1,2})\s*[.．、]\s*([A-Da-d])(?![A-Za-z])', head):
        q = int(m.group(1))
        if 1 <= q <= 40 and q not in ans:
            ans[q] = m.group(2).upper()
    if len(ans) >= 35:
        return ans
    # 再回退：按顺序抓"解答：X"（选择题在前，前40个单字母即Q1~40）
    seq = re.findall(r'解\s*答\s*[:：]\s*([A-Da-d])(?![A-Za-z])', text)
    if len(seq) >= 40:
        return {i + 1: seq[i].upper() for i in range(40)}
    return ans


def main():
    for pdf in sorted(glob.glob("answers/*答案.pdf")):
        m = re.search(r'(\d{4})', os.path.basename(pdf))
        if not m:
            continue
        year = m.group(1)
        text = pdftext(pdf)
        if not text.strip():
            print(f"{year}: ⚠ 无文字层(扫描件)，跳过")
            continue
        ans = extract(text)
        missing = [q for q in range(1, 41) if q not in ans]
        out = f"answers/{year}.txt"
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"# {year} 408 选择题答案（自动抽取自答案PDF）\n")
            for q in range(1, 41):
                if q in ans:
                    f.write(f"{q} {ans[q]}\n")
        flag = "✅" if not missing else f"⚠ 缺{missing}"
        print(f"{year}: 抽到 {len(ans)}/40  {flag} → {out}")


if __name__ == "__main__":
    main()
