# 项目地图

这份地图描述仓库**现在实际存在并运行的结构**。它不是未来架构设想；目录定位发生变化时，应先更新这里，再决定是否移动文件。

## 主流程

[真题原卷](past_papers/) → [题目切图](bank/) → [能力线定义](data/ability_lines.json) → [能力线题单](src/) → [作答与判分](data/) → [TLDR 解析与验证](tldr/)

日常学习只需要从下面三个入口进入：

- [src/](src/)：当前 40 条能力线题单，是做题入口。
- [tldr/](tldr/)：题目解析、纠错、迁移验证和后续回看。
- [navigator/](navigator/)：时间与现实约束的管理系统，不参与题目判分。

## 可点击目录树

- [`408-from-44/`](./)：408 提分项目
  - [src/](src/)：当前题单；`0731.md` 至 `0908.md` 构成连续的能力线链
  - [tldr/](tldr/)：当前解析协议及已生成的 TLDR
  - [data/](data/)：程序读取和生成的机器数据
    - [ability_lines.json](data/ability_lines.json)：能力线的源定义
    - [question_chain.json](data/question_chain.json)：由能力线编译出的链表关系
    - [rosters/](data/rosters/)：答题卡读取的节点题目
    - [answers/](data/answers/)：你的作答记录
    - [results/](data/results/)：判分结果
    - [progress/](data/progress/)：不可覆盖的进度事件及其派生状态
    - [reference/answers/](data/reference/answers/)：判分程序读取的标准答案
  - [tools/](tools/)：构建、答题、判分和维护脚本；目前没有再划分 `runtime/`、`build/`
  - [tests/](tests/)：能力线链和 TLDR 工具的自动检查
  - [navigator/](navigator/)：独立的时间助理子系统
  - [archive/](archive/)：已经从当前程序中切除的旧题单、旧调度和历史设计

<details>
<summary>原始材料：日常不必直接进入</summary>

- [past_papers/](past_papers/)：2009—2025 年真题原卷。
- [bank/](bank/)：从原卷切出的 680 道选择题图片，题单通过相对路径引用。
- [data/reference/answers/](data/reference/answers/)：按年份保存的选择题标准答案。它已从根目录折叠到机器数据层，日常不必直接进入。

</details>

<details>
<summary>根目录命令：日常实际操作</summary>

- [`./today.sh MMDD`](today.sh)：显示指定能力线节点。
- [`./answer.sh MMDD`](answer.sh)：打开答题卡并记录作答。
- [`./tldr.sh MMDD`](tldr.sh)：从判分结果建立 TLDR。
- [`./tldr.sh --check MMDD`](tldr.sh)：检查 TLDR 结构是否完整。

</details>

## `tools/` 内部职责

下面的 `runtime` 和 `build` 是职责分类，不是已经存在的子目录。

- 当前运行链：[show_question_node.py](tools/show_question_node.py)、[answer.py](tools/answer.py)、[grade_today.py](tools/grade_today.py)、[progress.py](tools/progress.py)、[new_tldr.py](tools/new_tldr.py)、[check_tldr.py](tools/check_tldr.py)。
- 题库与能力线构建：[slice_paper.py](tools/slice_paper.py)、[slice_paper_ocr.py](tools/slice_paper_ocr.py)、[extract_answers.py](tools/extract_answers.py)、[build_question_chain.py](tools/build_question_chain.py)。
- 图片与仓库维护：[imgtrim.py](tools/imgtrim.py)、[patch_q.py](tools/patch_q.py) 及 Git 辅助脚本。

旧 `select_today`、`studio`、固定配额策略及其测试已经整体移入
[archive/scheduler-v1/](archive/scheduler-v1/)，当前程序不再兼容这套调度。

## 整理原则

1. `src/` 与 `tldr/` 是当前学习主线，整理不能改变它们的入口。
2. 大量题单已经引用 `bank/`，因此题图暂不移动；不直接使用的标准答案收在 `data/reference/`。
3. `archive/` 是冻结区，不承担运行兼容；当前代码不得反向依赖归档内容。
4. 项目结构以是否降低学习摩擦为标准；没有运行收益的目录重命名不优先。