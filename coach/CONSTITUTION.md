# Coach Constitution

Coach 是 408 真题学习资产的根。它把一题的真实处理结果交付给三个实体层，并让每日 notes 呈现当天的最终产出。

## Stable layout

```text
coach/
  CONSTITUTION.md
  ENTRY.md
  current.md
  today/
  knowledge/
  ability/
  analysis/
  notes/<month>/<MMDD>.md
```

- `knowledge/` 是唯一的 408 学科正文。它按科目与章节生长，写成可持续修订的教材，不按年份堆叠。
- `analysis/` 按 `<year>/qNN.md` 保存原题的硬解析。正文直接处理题干、推理与选项；它调用 knowledge，不复制一份课程。
- `ability/` 保存已经由真实题目证实的个人解题能力内容。它不重讲学科知识，也不预建分类树。
- `notes/` 是下游呈现。目录必须与 `src/` 一致，按月份管理；每日 note 引用当天题目沉淀出的 analysis、knowledge、ability，不复制它们的正文。
- `today/` 与 `current.md` 仍是 T0 到 coach 的运行入口。

## Content ownership

一段正文只能有一个主要归宿：

| 内容 | 归宿 |
| --- | --- |
| 脱离原题后仍成立的学科解释 | knowledge |
| 某题如何被直接做出、如何逐项排除选项 | analysis |
| 用户为何未能正确调用知识与解析路径，以及怎样训练 | ability |
| 当天完成了什么、这些实体之间的引用 | notes |

## Pass

`pass` 是一题学习过程的收束与交付，不是一个独立文件或目录，也不要求把一切问题当场解决。

一次 pass 至少保证：本题已经被理解；有价值内容不只留在聊天上下文或原卷空白处；它已被交付给既有或待创建的 knowledge、analysis、ability 实体，并可由当天 note 呈现。

`revisit` 与 `pin` 目前只保留为未来可实现的关系标记。不得为它们新建目录、队列或独立知识正文。

## Analysis rule

analysis 不写“题目档案式”小作文。打开文件后直接解题：能正推就正推，正推成本高时就逐项排除；两种方法都必须调用已有 knowledge。若 knowledge 不足以把题做穿，应补 knowledge 后回到 analysis。

## Context and quality

- 当前题只读取必要的 knowledge 段落、相关 analysis 与少量已证实的 ability 内容；不得批量读取全库。
- 不因措辞漂亮、看似提速或一次偶然失误新建长期内容。
- 所有关于用户的判断必须可回链到真实题目，并允许后续题推翻。
- 任何新增结构必须服务下一道相关题更快、更准地被处理；否则不保留。
