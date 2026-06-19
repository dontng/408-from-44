#!/usr/bin/env python3
"""重切 OCR/文字层漏抓的题：先定位邻题坐标，再均分间隔切出缺题。
用法:
  python3 tools/fill_missing.py 2009          # 单年
  python3 tools/fill_missing.py 2009 2010     # 多年
  python3 tools/fill_missing.py               # 全部年份
"""
import sys, re, os, glob, subprocess, tempfile
import fitz
from PIL import Image
from imgtrim import trim_file

DPI    = 200
ZOOM   = DPI / 72.0
REPO   = os.path.join(os.path.dirname(__file__), "..")


def open_pdf(year):
    pdfs = glob.glob(os.path.join(REPO, f"真题pdf/{year}*.pdf"))
    return fitz.open(pdfs[0]) if pdfs else None


def ocr_page_markers(page):
    """对单页 OCR，返回左边距题号候选: [(num, y_pdf)]"""
    pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp = f.name
    pix.save(tmp)
    out = subprocess.run(
        ["tesseract", tmp, "stdout", "-l", "chi_sim+eng", "tsv"],
        capture_output=True, text=True).stdout
    os.unlink(tmp)
    groups = {}
    for row in out.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12 or not c[11].strip(): continue
        groups.setdefault((c[2],c[3],c[4]),[]).append((int(c[6]),int(c[7]),c[11].strip()))
    results = []
    for ws in groups.values():
        ws.sort(key=lambda t: t[0])
        left = min(w[0] for w in ws)
        top  = min(w[1] for w in ws)
        text = "".join(w for _,_,w in ws)
        if left > pix.width * 0.26: continue
        m = re.match(r'0?(\d{1,2})\s*[.．、)，,]', text.lstrip())
        if m:
            num = int(m.group(1))
            if 1 <= num <= 40:
                results.append((num, top / ZOOM))
    return results


def detect_markers(doc):
    """全文档检测，返回 {qnum: (pno, y_pdf)}，取最长递增序列。"""
    cand = []
    for pno in range(len(doc)):
        for num, y in ocr_page_markers(doc[pno]):
            cand.append((num, pno, y))
    best = []
    for i in range(len(cand)):
        run = [cand[i]]; last = cand[i][0]
        for j in range(i+1, len(cand)):
            if cand[j][0] > last:
                run.append(cand[j]); last = cand[j][0]
                if last == 40: break
        if len(run) >= len(best): best = run
    return {m[0]: (m[1], m[2]) for m in best}


def stitch_cut(doc, ranges, outpath):
    """ranges = [(pno, y0, y1), ...]，竖向拼接后保存。"""
    pieces = []
    for pno, y0, y1 in ranges:
        if y1 <= y0: continue
        page = doc[pno]
        clip = fitz.Rect(0, y0, page.rect.width, y1)
        pix  = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
        pieces.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
    if not pieces: return False
    if len(pieces) == 1:
        pieces[0].save(outpath)
    else:
        w = max(p.width for p in pieces)
        h = sum(p.height for p in pieces)
        out = Image.new("RGB", (w, h), (255,255,255))
        yoff = 0
        for p in pieces:
            out.paste(p, (0, yoff)); yoff += p.height
        out.save(outpath)
    trim_file(outpath)
    return True


def fill_year(year, doc, markers):
    outdir = os.path.join(REPO, "bank", year)
    ph = {pno: doc[pno].rect.height for pno in range(len(doc))}

    # 把所有检测到的题排成有序列表，计算每题的"全局 y"（累积页高+页内 y）
    def global_y(pno, y):
        return sum(ph[p] for p in range(pno)) + y

    sorted_markers = sorted(markers.items())   # [(qnum, (pno, y)), ...]

    repaired = 0
    for n in range(1, 41):
        if n in markers:
            continue  # 已检测到，跳过

        # 找前后最近的已检测题
        prev_n = max((k for k in markers if k < n), default=None)
        next_n = min((k for k in markers if k > n), default=None)
        if prev_n is None or next_n is None:
            print(f"  {year} Q{n:02d}: 边缘缺失，无法自动定位，跳过")
            continue

        gap = next_n - prev_n - 1   # 这段空白里缺几道题

        # 区间从 prev_n 的起始 到 next_n 的起始，共包含 gap+1 道题
        # 均分该区间，取第 (n-prev_n) 段（1-indexed）
        prev_pno, prev_y = markers[prev_n]
        end_pno,  end_y  = markers[next_n]

        g_start = global_y(prev_pno, prev_y)
        g_end   = global_y(end_pno,  end_y)
        if g_end <= g_start:
            print(f"  {year} Q{n:02d}: 区间异常，跳过"); continue

        total_parts = gap + 1
        seg = n - prev_n          # 1-indexed：prev_n=1, first missing=2, ...
        g0  = g_start + (seg - 1) * (g_end - g_start) / total_parts
        g1  = g_start +  seg      * (g_end - g_start) / total_parts

        # 反算回 (pno, y_pdf)
        def from_global(g):
            acc = 0
            for pno in range(len(doc)):
                if acc + ph[pno] > g:
                    return pno, g - acc
                acc += ph[pno]
            return len(doc)-1, ph[len(doc)-1]

        s_pno, s_y = from_global(max(0, g0 - 4))
        e_pno, e_y = from_global(g1)

        # 构造跨页 ranges
        ranges = []
        for pno in range(s_pno, e_pno + 1):
            y0 = s_y if pno == s_pno else 0
            y1 = e_y if pno == e_pno else ph[pno]
            ranges.append((pno, y0, y1))

        outpath = os.path.join(outdir, f"q{n:02d}.png")
        if stitch_cut(doc, ranges, outpath):
            print(f"  {year} Q{n:02d}: 补切 p{s_pno}[{s_y:.0f}..] → p{e_pno}[..{e_y:.0f}] ✓")
            repaired += 1
        else:
            print(f"  {year} Q{n:02d}: 切出失败")

    return repaired


def process_year(year):
    doc = open_pdf(year)
    if not doc:
        print(f"{year}: 找不到 PDF"); return
    print(f"\n{year}: 检测题号…")
    markers = detect_markers(doc)
    missing = [n for n in range(1,41) if n not in markers]
    if not missing:
        print(f"  ✓ 40/40 已检测")
        return
    print(f"  检测 {len(markers)}/40，缺 {missing}")
    n = fill_year(year, doc, markers)
    print(f"  共补切 {n} 题")


def main():
    os.chdir(REPO)
    years = sys.argv[1:] if sys.argv[1:] else \
            sorted(d for d in os.listdir("bank") if os.path.isdir(f"bank/{d}"))
    for y in years:
        process_year(y)


if __name__ == "__main__":
    main()
