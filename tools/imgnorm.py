#!/usr/bin/env python3
"""算出每张题图在网页上的“显示宽度”，让屏幕上的汉字高度跨年跨题一致。

为什么需要：源 PDF 字号/页宽差异大，imgtrim 又把每张图裁成“最宽那行”的宽度
(700~1500px 不等)。若网页按固定宽度铺满，屏幕字号 = 源字号 × 容器宽/图宽 —— 宽图
字被压小、窄图字被放大，能差一倍。

字号代理：直接用“连通域量出的汉字像素高”(就是用户眼睛看到的字高)，按年取中位数
——同一年同一份 PDF、同一渲染 DPI，字高本就恒定，逐题量反而会被插图/表格带偏，故按
年聚合最稳。再令 显示宽 = 原生宽 × 目标字高 / 该年字高，于是不论怎么裁，屏幕上汉字
都≈ DISP_TEXT_PX 高。结果写 review/imgnorm.json，studio.py 只读不算(保持纯标准库)。

  python3 tools/imgnorm.py            # 全库
  python3 tools/imgnorm.py 2024 2025  # 指定年份(其余沿用旧值)
"""
import sys, re, glob, json, statistics
from collections import deque
from pathlib import Path
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "review" / "imgnorm.json"

DISP_TEXT_PX = 11      # 目标：每张题图在网页上的汉字高(CSS px)，全库一致
DISP_MAX_W = 760       # 单题图最大显示宽(px)；更宽的表格交给 CSS max-width:100% 兜底
DISP_MIN_W = 150       # 极窄题(如一行短选项)允许就显示窄，不撑大字
SAMPLE_PER_YEAR = 6    # 每年采样几题量字高(取中位数即可，无需全量)


def glyph_height(path):
    """连通域量汉字像素高：二值化后取“像字”的连通块高度中位数。纯图返回 None。"""
    im = Image.open(path).convert("L")
    w, h = im.size
    px = im.load()
    dark = [[px[x, y] < 140 for x in range(w)] for y in range(h)]
    seen = [[False] * w for _ in range(h)]
    heights = []
    for y0 in range(h):
        row, srow = dark[y0], seen[y0]
        for x0 in range(w):
            if not row[x0] or srow[x0]:
                continue
            miny = maxy = y0; minx = maxx = x0; n = 0
            dq = deque([(y0, x0)]); srow[x0] = True
            while dq:
                y, x = dq.popleft(); n += 1
                if y < miny: miny = y
                if y > maxy: maxy = y
                if x < minx: minx = x
                if x > maxx: maxx = x
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and dark[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True; dq.append((ny, nx))
            ch, cw = maxy - miny + 1, maxx - minx + 1
            if n >= 15 and 12 <= ch <= 60 and 6 <= cw <= 60:   # 像“一个字”的连通块
                heights.append(ch)
    return statistics.median(heights) if heights else None


def year_glyph_px(ydir):
    """采样若干题量字高，取中位数。优先挑文字多(文件大)的题，量得准。"""
    files = sorted(ydir.glob("q*.png"), key=lambda f: f.stat().st_size, reverse=True)
    vals = []
    for f in files:
        gh = glyph_height(f)
        if gh:
            vals.append(gh)
        if len(vals) >= SAMPLE_PER_YEAR:
            break
    return statistics.median(vals) if vals else None


def main():
    years = set(sys.argv[1:])
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    meta = data.setdefault("_meta", {})
    meta.update(text_px=DISP_TEXT_PX, max_w=DISP_MAX_W, min_w=DISP_MIN_W)
    glyph = data.setdefault("glyph_px", {})
    items = data.setdefault("items", {})

    for ydir in sorted((REPO / "bank").glob("*")):
        if not ydir.is_dir() or (years and ydir.name not in years):
            continue
        yr = ydir.name
        gh = year_glyph_px(ydir)
        if not gh:
            print(f"{yr}: 量不到字高，跳过"); continue
        glyph[yr] = gh
        scale = DISP_TEXT_PX / gh
        for f in sorted(ydir.glob("q*.png")):
            m = re.search(r"q(\d+)\.png$", f.name)
            if not m:
                continue
            nw = Image.open(f).size[0]
            w = max(DISP_MIN_W, min(DISP_MAX_W, round(nw * scale)))
            items[f"{yr}-{int(m.group(1)):02d}"] = w
        print(f"{yr}: 字高 {gh:.0f}px → scale {scale:.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"写入 {len(items)} 题 → {OUT}")


if __name__ == "__main__":
    main()
