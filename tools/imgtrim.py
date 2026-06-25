#!/usr/bin/env python3
"""裁掉题面图四周的纯空白，让核心内容尽量铺满。切题/补切后调用，幂等。

  python3 tools/imgtrim.py                    # 裁全库 bank/**/q*.png
  python3 tools/imgtrim.py bank/2014          # 只裁某年
  python3 tools/imgtrim.py --degap bank/2013/q34.png  # 去除跨页拼接留白
"""
import sys, glob, os
import numpy as np
from PIL import Image

PAD = 14        # 裁紧后四周留一点呼吸边
THRESH = 236    # 亮于此视为背景白


def trim_file(path, pad=PAD, thresh=THRESH):
    im = Image.open(path).convert("RGB")
    gray = im.convert("L")
    mask = gray.point(lambda x: 255 if x < thresh else 0)   # 暗像素=内容
    bbox = mask.getbbox()
    if not bbox:
        return False
    w, h = im.size
    box = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
           min(w, bbox[2] + pad), min(h, bbox[3] + pad))
    if box == (0, 0, w, h):
        return False
    im.crop(box).save(path)
    return True


def remove_page_gap(img, min_gap=60, white_thresh=245, white_ratio=0.93,
                    edge_pad=8, min_content=25):
    """删除跨页拼接图中间的页边距+页码留白带。

    关键阈值 white_ratio=0.93：
    - 纯白行（行间距）：white_ratio ≈ 1.00  → 算入缝隙 ✓
    - 页码行("第N/M页")：white_ratio ≈ 0.94–0.99 → 算入缝隙 ✓
    - 真实内容行：white_ratio ≈ 0.61–0.91     → 不算缝隙 ✓

    min_content：缝隙上方和下方各须有至少这么多非稀疏行，
    否则视为"图片尾部留白"假阳性，跳过。
    """
    arr = np.array(img.convert('L'))
    n = len(arr)
    if n == 0:
        return img, 0

    is_sparse = (arr >= white_thresh).mean(axis=1) >= white_ratio

    to_remove = np.zeros(n, dtype=bool)
    i = 0
    while i < n:
        if is_sparse[i]:
            j = i
            while j < n and is_sparse[j]:
                j += 1
            if j - i >= min_gap:
                # 缝隙两侧须各有足够内容行，否则是图片边缘留白，跳过
                content_above = int((~is_sparse[:i]).sum())
                content_below = int((~is_sparse[j:]).sum())
                if content_above >= min_content and content_below >= min_content:
                    to_remove[i + edge_pad: j - edge_pad] = True
            i = j
        else:
            i += 1

    removed = int(to_remove.sum())
    if removed == 0:
        return img, 0
    keep = np.where(~to_remove)[0]
    return Image.fromarray(np.array(img)[keep]), removed


def remove_page_gap_file(path, **kw):
    im = Image.open(path).convert("RGB")
    result, removed = remove_page_gap(im, **kw)
    if removed:
        result.save(path)
    return removed


def main():
    args = sys.argv[1:]
    degap = "--degap" in args
    args = [a for a in args if a != "--degap"]

    roots = args or ["bank"]
    files = []
    for r in roots:
        if os.path.isfile(r):
            files.append(r)
        else:
            files += glob.glob(os.path.join(r, "**", "q*.png"), recursive=True)
            files += glob.glob(os.path.join(r, "q*.png"))
    files = sorted(set(files))

    if degap:
        n = sum(1 for f in files if remove_page_gap_file(f))
        print(f"去页缝完成：{n}/{len(files)} 张有变化")
    else:
        n = sum(trim_file(f) for f in files)
        print(f"裁白完成：{n}/{len(files)} 张有变化")


if __name__ == "__main__":
    main()
