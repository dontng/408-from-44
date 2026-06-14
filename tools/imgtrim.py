#!/usr/bin/env python3
"""裁掉题面图四周的纯空白，让核心内容尽量铺满。切题/补切后调用，幂等。

  python3 tools/imgtrim.py            # 裁全库 bank/**/q*.png
  python3 tools/imgtrim.py bank/2014  # 只裁某年
"""
import sys, glob, os
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


def main():
    roots = sys.argv[1:] or ["bank"]
    files = []
    for r in roots:
        files += glob.glob(os.path.join(r, "**", "q*.png"), recursive=True)
        files += glob.glob(os.path.join(r, "q*.png"))
    files = sorted(set(files))
    n = sum(trim_file(f) for f in files)
    print(f"裁白完成：{n}/{len(files)} 张有变化")


if __name__ == "__main__":
    main()
