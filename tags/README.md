# tags — 每题的「科目 + 章节」标签

> 状态：旧方案，当前能力线题单和答题流程均未读取，待退役。

这个目录原本为 `studio` 的分块/交错抽题准备，只完成了 2024、2025
两年。现在的能力线由 `data/ability_lines.json` 定义，不依赖这里的章节标签。

## 格式

每年一个文件 `tags/<年份>.tsv`，每行用 Tab 分隔：

```
题号	科目	章节
1	data_structures	ch05_树与二叉树
2	computer_organization	ch03_存储系统
```

科目取值（与目录一致）：
`data_structures` / `computer_organization` / `operating_systems` / `computer_networks`

## 标准章节表

- **data_structures**：ch01_绪论 / ch02_线性表 / ch03_栈队列和数组 / ch04_串 / ch05_树与二叉树 / ch06_图 / ch07_查找 / ch08_排序
- **computer_organization**：ch01_计算机系统概述 / ch02_数据的表示和运算 / ch03_存储系统 / ch04_指令系统 / ch05_中央处理器 / ch06_总线 / ch07_输入输出系统
- **operating_systems**：ch01_操作系统概述 / ch02_进程与线程 / ch03_内存管理 / ch04_文件管理 / ch05_输入输出管理
- **computer_networks**：ch01_体系结构 / ch02_物理层 / ch03_数据链路层 / ch04_网络层 / ch05_传输层 / ch06_应用层

## 原定打标方式（历史说明）

对 `bank/<年>/qNN.png` 逐张看图，按上面分类输出 `题号 科目 章节`，写入 `tags/<年>.tsv`。
提示词约束：**只按 408 考纲归类，拿不准的章节标 `?` 待人工核**。
原方案计划由 `studio` 读取后用于分块/交错调度；该流程现已不再是项目主线。
