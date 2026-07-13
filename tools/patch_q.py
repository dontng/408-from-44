#!/usr/bin/env python3
"""手工补切单题：OCR/文字层切题漏抓的零星题号(题号被扫描糊掉时)，用这个补。

两步用法：
  1) 扫描某页、列出左边距所有行的 y 比例，找到缺题真正的起止位置：
       python3 tools/patch_q.py 2009 scan 1
  2) 按页号+上下边界比例(0~1)切出该题：
       python3 tools/patch_q.py 2009 cut 5 1 0.40 0.62
     → 覆盖写 bank/2009/q05.png
"""
import sys, os, subprocess, tempfile
import fitz
from imgtrim import trim_file, remove_page_gap_file

DPI = 200
ZOOM = DPI / 72.0


def open_year(year):
    import glob
    pdfs = glob.glob(f"past_papers/{year}*.pdf")
    if not pdfs:
        sys.exit(f"找不到 past_papers/{year}*.pdf")
    return fitz.open(pdfs[0])


def scan(year, pno):
    doc = open_year(year)
    page = doc[pno]
    pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
    ph = pix.height
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp = f.name
    pix.save(tmp)
    out = subprocess.run(["tesseract", tmp, "stdout", "-l", "chi_sim+eng", "tsv"],
                         capture_output=True, text=True).stdout
    os.unlink(tmp)
    groups = {}
    for row in out.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12 or not c[11].strip():
            continue
        groups.setdefault((c[2], c[3], c[4]), []).append((int(c[6]), int(c[7]), c[11].strip()))
    lines = []
    for ws in groups.values():
        ws.sort(key=lambda t: t[0])
        lines.append((min(w[1] for w in ws), min(w[0] for w in ws),
                      "".join(w for _, _, w in ws)))
    lines.sort()
    print(f"页 {pno} 高 {ph}px，左边距各行 (y比例 | 文本):")
    for top, left, text in lines:
        if left < pix.width * 0.30:
            print(f"  {top/ph:0.3f} | {text[:46]}")


def cut(year, qnum, pno, y0f, y1f):
    doc = open_year(year)
    page = doc[pno]
    ph = page.rect.height
    pw = page.rect.width
    clip = fitz.Rect(0, ph * y0f, pw, ph * y1f)
    pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
    outdir = os.path.join("bank", year)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"q{int(qnum):02d}.png")
    pix.save(path)
    trim_file(path)
    print(f"已切 → {path}")


def _clip_png(page, y0f, y1f):
    ph, pw = page.rect.height, page.rect.width
    clip = fitz.Rect(0, ph * y0f, pw, ph * y1f)
    return page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)


def cut2(year, qnum, p0, a0, a1, p1, b0, b1):
    """跨页题：p0 的 [a0,a1] 与 p1 的 [b0,b1] 竖向拼成一张。"""
    from PIL import Image
    import io
    doc = open_year(year)
    top = Image.open(io.BytesIO(_clip_png(doc[p0], a0, a1).tobytes("png")))
    bot = Image.open(io.BytesIO(_clip_png(doc[p1], b0, b1).tobytes("png")))
    w = max(top.width, bot.width)
    out = Image.new("RGB", (w, top.height + bot.height), "white")
    out.paste(top, (0, 0)); out.paste(bot, (0, top.height))
    outdir = os.path.join("bank", year); os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"q{int(qnum):02d}.png")
    out.save(path)
    remove_page_gap_file(path, min_gap=120)   # 去掉页码+页边距留白带
    trim_file(path)
    print(f"已切(跨页) → {path}")


def main():
    year, mode = sys.argv[1], sys.argv[2]
    if mode == "scan":
        scan(year, int(sys.argv[3]))
    elif mode == "cut":
        cut(year, sys.argv[3], int(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]))
    elif mode == "cut2":
        cut2(year, sys.argv[3], int(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]),
             int(sys.argv[7]), float(sys.argv[8]), float(sys.argv[9]))
    else:
        sys.exit("mode 须为 scan / cut / cut2")


if __name__ == "__main__":
    main()
