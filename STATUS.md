# 项目进度（2026-06-15）

真题驱动的 408 选择题刷题机。设计与背景见 Claude 长期记忆 `project-408-study-system` / `project-408-situation`。

## 已完成
- **studio 刷题台**：`bash studio.sh` 一键上线本地网页（127.0.0.1:8408，免代理），和纸界面、侧边今日清单、ABCD 竖排、遗忘曲线、倒计时。状态存 `review/state.json`（可多机同步）。无官方答案的题自动转**自判模式**，不会误判。
- **题库：17 年全部完整，680 题（2009–2025 各 40 题）** → `bank/<年>/qNN.png`。
- **三套切题工具**（`tools/`）：
  - `slice_paper.py` — 文字层按题号坐标切题（适用文字层正常的年份）。
  - `slice_paper_ocr.py` — OCR 定位题号坐标切题（适用坏编码/纯扫描/图片页年份）。OCR 只用来找题号，题面成品仍是原始渲染图，正文 OCR 错误不影响结果。平局取靠后起点，避开"考生须知 1~5"污染。
  - `patch_q.py` — 手工补切漏题：`scan` 列某页左边距行的 y 比例，`cut` 按页+上下比例切单题，`cut2` 跨页题竖向拼接（依赖 Pillow）。
- **答案**：`answers/2009–2024.txt` 已就位（16 年）。

## 待办
- **2025 答案**：`answers/2025.txt` 尚缺（无官方答案 PDF）。到手后放入即可自动判分；在此之前 2025 题走自判模式。不要凭记忆编答案。
- **章节标签**：见 `tags/README.md`，逐题打 科目+章节，解锁分块/交错练习（studio 已读 `tags/<年>.tsv`，缺则忽略）。
- **大题**：入库 + 4 条遗忘曲线（按时间排）。
- **参数最终敲定**：每日新题量、间隔阶梯、Nov/Dec 冲刺日期锁定（都在 `studio.py` 顶部）。
- 个别跨页题成品图中间夹着原 PDF 页脚（如 2013 q34 / 2024 q11），不影响作答。

## 常用命令
```bash
bash studio.sh                                       # 启动刷题台
python3 tools/slice_paper.py     真题pdf/XXXX.pdf XXXX   # 文字层切某年
python3 tools/slice_paper_ocr.py 真题pdf/XXXX.pdf XXXX   # OCR 切某年(扫描/坏编码)
python3 tools/patch_q.py XXXX scan <页>                 # 找漏题的 y 坐标
python3 tools/patch_q.py XXXX cut  <题号> <页> <y0> <y1>          # 补切单题
python3 tools/patch_q.py XXXX cut2 <题号> <页> <y0> 1.0 <页+1> 0 <y1>  # 跨页题
```
