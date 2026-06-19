#!/usr/bin/env python3
"""把一份 408 真题 PDF 的单项选择题(01~40)切成单题 PNG。

用法: python3 tools/slice_paper.py 真题pdf/2022年计算机408统考真题.pdf 2022
输出: bank/<year>/qNN.png
依赖文字层中的题号坐标定位切割点；纯扫描无文字层的年份(2023/2025)用本脚本切不了。
"""
import sys, re, os
import fitz  # pymupdf
from PIL import Image
from imgtrim import trim_file

DPI = 200
ZOOM = DPI / 72.0


def line_groups(page):
    """返回该页的文本行: [(y0, x0, text)]，按阅读顺序(y升序)。"""
    words = page.get_text("words")  # x0,y0,x1,y1,word,block,line,wno
    groups = {}
    for x0, y0, x1, y1, w, b, l, wn in words:
        groups.setdefault((b, l), []).append((x0, y0, w))
    lines = []
    for key, ws in groups.items():
        ws.sort(key=lambda t: t[0])
        text = "".join(w for _, _, w in ws)
        x0 = min(w[0] for w in ws)
        y0 = min(w[1] for w in ws)
        lines.append((y0, x0, text))
    lines.sort(key=lambda t: t[0])
    return lines


def find_markers(doc):
    """定位选择题 1..40 的题号。返回 (markers, missing)。

    不依赖标题锚点：收集所有左边距的"数字." 候选(阅读顺序)，再取最长的
    严格递增序列——考生须知那段只到 5，正题能到 40，自然胜出；也能跳过
    任何假开头。容忍个别题号 OCR 漏抓(跳号)。
    """
    cand = []
    for pno in range(len(doc)):
        page = doc[pno]
        pw = page.rect.width
        for y0, x0, text in line_groups(page):
            if x0 > pw * 0.23:           # 题号在左边距
                continue
            m = re.match(r'0?(\d{1,2})[.．、)]', text.lstrip())
            if not m:
                continue
            num = int(m.group(1))
            if 1 <= num <= 40:
                cand.append((num, pno, y0))

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
        if len(run) > len(best):
            best = run
    return best, _missing(best)


def _missing(markers):
    got = {m[0] for m in markers}
    return [n for n in range(1, 41) if n not in got]


def crop(doc, markers, outdir):
    os.makedirs(outdir, exist_ok=True)
    saved = 0
    for i, (qnum, pno, y0) in enumerate(markers):
        page = doc[pno]
        ph = page.rect.height
        pw = page.rect.width
        top = max(0, y0 - 4)
        path = os.path.join(outdir, f"q{qnum:02d}.png")

        # 确定下边界：下一题的题号位置
        if i + 1 < len(markers):
            next_pno, next_y0 = markers[i + 1][1], markers[i + 1][2]
        else:
            next_pno, next_y0 = pno, ph

        if next_pno == pno:
            # 同页：直接截
            clip = fitz.Rect(0, top, pw, next_y0)
            doc[pno].get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip).save(path)
        else:
            # 跨页：分段渲染后竖向拼接
            pieces = []

            # 当前页：题号到页底
            clip = fitz.Rect(0, top, pw, ph)
            pix = doc[pno].get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
            pieces.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))

            # 中间整页（极少见，一题跨3页以上时出现）
            for mid in range(pno + 1, next_pno):
                p = doc[mid]
                clip = fitz.Rect(0, 0, p.rect.width, p.rect.height)
                pix = p.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
                pieces.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))

            # 下一题所在页：页顶到下题题号
            np = doc[next_pno]
            clip = fitz.Rect(0, 0, np.rect.width, next_y0)
            pix = np.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
            pieces.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))

            # 竖向拼接
            total_h = sum(p.height for p in pieces)
            max_w = max(p.width for p in pieces)
            stitched = Image.new("RGB", (max_w, total_h), (255, 255, 255))
            y_off = 0
            for p in pieces:
                stitched.paste(p, (0, y_off))
                y_off += p.height
            stitched.save(path)

        trim_file(path)
        saved += 1
    return saved


def main():
    pdf, year = sys.argv[1], sys.argv[2]
    doc = fitz.open(pdf)
    markers, missing = find_markers(doc)
    nums = [m[0] for m in markers]
    print(f"检测到题号 {len(markers)} 个: {nums}")
    if missing:
        print(f"⚠ 漏抓(需手工补切): {missing}")
    outdir = os.path.join("bank", year)
    n = crop(doc, markers, outdir)
    print(f"已切出 {n} 张 → {outdir}/")


if __name__ == "__main__":
    main()
