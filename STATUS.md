# 项目进度（2026-06-14）

真题驱动的 408 选择题刷题机。设计与背景见 Claude 长期记忆 `project-408-study-system` / `project-408-situation`。

## 已完成
- **studio 刷题台**：`bash studio.sh` 一键上线本地网页（127.0.0.1:8408，免代理），和纸界面、侧边今日清单、ABCD 竖排、遗忘曲线、倒计时（今日 187 天）。状态存 `review/state.json`（可多机同步）。
- **切题**：`tools/slice_paper.py` 从真题 PDF 文字层按题号坐标切单题 PNG（含图）。
- **答案**：`tools/extract_answers.py` 已抽取 **2009–2024 全部 16 年**选择题答案 → `answers/*.txt`（含尚无 PDF 的 2024，所以 2024 真题 PDF 一到即可用）。
- **题库现状**：已切 8 年共 305 题 → `bank/`
  - 完整：2011, 2014, 2019, 2020（各 40）
  - 有零星漏抓：2021(缺34)、2022(缺11,19)、2017(缺5-8)、2012(缺1-8)

## 待办
- **OCR 切题**：2009/2010/2013/2015/2016/2018 文字层是坏编码(乱码)、2023/2025 是纯扫描——都需改走 OCR 定位题号来切（重启后的批活，适合 Claude remote）。
- **补切漏题**：上面各年缺的零星题号，手工/半自动补。
- **2024 真题**：用户重启笔记本后通过别的方式传入 `真题pdf/`，再 `python3 tools/slice_paper.py 真题pdf/2024....pdf 2024`（答案已就绪）。
- **章节标签**：见 `tags/README.md`，逐题打 科目+章节，是分块/交错练习的地基。
- **大题**：入库 + 4 条遗忘曲线（按时间排）。
- **参数最终敲定**：每日新题量、间隔阶梯、Nov/Dec 冲刺日期锁定。

## 常用命令
```bash
bash studio.sh                                   # 启动刷题台
python3 tools/slice_paper.py 真题pdf/XXXX.pdf XXXX  # 切某年
python3 tools/extract_answers.py                 # 重抽答案
```
