#!/usr/bin/env python3
"""把一份 408 真题 PDF 的单项选择题(01~40)切成单题 PNG。

用法: python3 tools/slice_paper.py 真题pdf/2022年计算机408统考真题.pdf 2022
输出: bank/<year>/qNN.png
依赖文字层中的题号坐标定位切割点；纯扫描无文字层的年份(2023/2025)用本脚本切不了。
"""
import sys, re, os
import fitz  # pymupdf

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

    先找"单项选择题"标题作起点、"综合应用题/二、"作终点，只在此区间内
    收集左边距的题号行；容忍个别题号 OCR 漏抓(跳号)，单调递增即接受。
    """
    started = False
    last = 0
    markers = []
    for pno in range(len(doc)):
        page = doc[pno]
        pw = page.rect.width
        for y0, x0, text in line_groups(page):
            s = text.lstrip()
            if not started:
                if "单项选择题" in text:
                    started = True
                continue
            if "综合应用题" in text or re.match(r'二[、.]', s):
                return markers, _missing(markers)
            if x0 > pw * 0.22:
                continue
            m = re.match(r'0?(\d{1,2})[.．、)]', s)
            if not m:
                continue
            num = int(m.group(1))
            if last < num <= 40:        # 单调递增、容忍跳号
                markers.append((num, pno, y0))
                last = num
                if num == 40:
                    return markers, _missing(markers)
    return markers, _missing(markers)


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
        # 下边界: 同页下一题的题号y；跨页则切到本页底
        if i + 1 < len(markers) and markers[i + 1][1] == pno:
            y1 = markers[i + 1][2]
        else:
            y1 = ph
        top = max(0, y0 - 4)
        clip = fitz.Rect(0, top, pw, y1)
        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
        path = os.path.join(outdir, f"q{qnum:02d}.png")
        pix.save(path)
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
