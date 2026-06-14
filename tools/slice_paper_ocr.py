#!/usr/bin/env python3
"""OCR 版切题：用 tesseract 定位选择题 01~40 的题号坐标，再切单题 PNG。

用于文字层是坏编码/纯扫描/图片页的年份(2009/10/12页0/13/15/16/18/2023/2025)。
OCR 只用来找题号的 y 坐标——题面成品仍是原始渲染图，正文 OCR 错误不影响结果。

用法: python3 tools/slice_paper_ocr.py 真题pdf/2015年计算机408统考真题.pdf 2015
输出: bank/<year>/qNN.png  (与 slice_paper.py 同格式，可混用)
"""
import sys, re, os, subprocess, tempfile
import fitz  # pymupdf
from slice_paper import crop, _missing  # 复用切割逻辑(PDF坐标)

DPI = 200
ZOOM = DPI / 72.0


def ocr_lines(pix):
    """对一张渲染好的 pixmap 跑 tesseract，返回行: [(top_px, left_px, text)]。

    把同 (block,par,line) 的词拼成一行，行的 left 取最左词的 left。
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp = f.name
    try:
        pix.save(tmp)
        out = subprocess.run(
            ["tesseract", tmp, "stdout", "-l", "chi_sim+eng", "tsv"],
            capture_output=True, text=True,
        ).stdout
    finally:
        os.unlink(tmp)

    groups = {}
    for row in out.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12:
            continue
        txt = c[11].strip()
        if not txt:
            continue
        blk, par, ln = c[2], c[3], c[4]
        left, top = int(c[6]), int(c[7])
        groups.setdefault((blk, par, ln), []).append((left, top, txt))
    lines = []
    for ws in groups.values():
        ws.sort(key=lambda t: t[0])
        text = "".join(w for _, _, w in ws)
        left = min(w[0] for w in ws)
        top = min(w[1] for w in ws)
        lines.append((top, left, text))
    lines.sort(key=lambda t: t[0])
    return lines


def find_markers(doc):
    """OCR 每页，收集左边距的"数字." 候选，取最长严格递增序列。

    坐标换算回 PDF 空间(像素/ZOOM)，以便复用 slice_paper.crop()。
    """
    cand = []
    for pno in range(len(doc)):
        page = doc[pno]
        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
        pw_px = pix.width
        for top, left, text in ocr_lines(pix):
            if left > pw_px * 0.23:        # 题号在左边距
                continue
            m = re.match(r'0?(\d{1,2})\s*[.．、)，,]', text.lstrip())
            if not m:
                continue
            num = int(m.group(1))
            if 1 <= num <= 40:
                cand.append((num, pno, top / ZOOM))   # → PDF 坐标

    best = []
    for i in range(len(cand)):
        run = [cand[i]]
        last = cand[i][0]
        for j in range(i + 1, len(cand)):
            if cand[j][0] > last:
                run.append(cand[j])
                last = cand[j][0]
                if last == 40:
                    break
        # 平局取靠后起点：考生须知(也是1~5编号)永远在正题之前，故真题串胜出
        if len(run) >= len(best):
            best = run
    return best, _missing(best)


def main():
    pdf, year = sys.argv[1], sys.argv[2]
    doc = fitz.open(pdf)
    markers, missing = find_markers(doc)
    nums = [m[0] for m in markers]
    print(f"[OCR] 检测到题号 {len(markers)} 个: {nums}")
    if missing:
        print(f"⚠ 漏抓(需手工补切): {missing}")
    outdir = os.path.join("bank", year)
    n = crop(doc, markers, outdir)
    print(f"已切出 {n} 张 → {outdir}/")


if __name__ == "__main__":
    main()
