# 408-from-44

> 服务于考研总分 350 冲击中的 408 提分。当前主线：把 2009–2025 年真题组织成能够恢复上下文的能力线，再用 TLDR 完成解析、纠错和迁移验证。

仓库各目录的定位、当前状态和可点击入口见 [项目地图](ARCHITECTURE.md)。

## 两个层次

题单与解析严格分开：

```text
src/MMDD.md                         能力线题单
tldr/sessions/YYYY-MM/MMDD-tldr.md TLDR 解析与验证
```

`src/` 是学习对象。40 份新题单直接位于 `src/` 根目录，从 `0731.md` 连续到 `0908.md`；日期只是链表节点，不是等长配额。每份题单对应一条能力线，内部真题按年份递增，并先给出“故事梗概”解释这些题为什么相连。

`tldr/` 是原 `speedrun/` 的完整更名。它保留真实首次作答、独立诊断、最小闭合机制、全部选项裁决和可证伪验证，不承担题单存放职责。

## 使用

```bash
./today.sh 0731       # 显示 src/0731.md 对应的能力线和题目
./answer.sh 0731      # 启动该节点答题卡
./tldr.sh 0731        # 从判分结果生成 tldr/sessions/.../0731-tldr.md
./tldr.sh --check 0731
```

完整能力线入口是 [src/README.md](src/README.md)。题单已经一次性生成，`today.sh` 不再临时抽题。

## 关键文件

| 路径 | 作用 |
|---|---|
| `data/ability_lines.json` | 40 条能力线、故事梗概和题目归属 |
| `data/question_chain.json` | 编译后的日期、前驱、后继和文件路径 |
| `src/MMDD.md` | 人看的能力线题单 |
| `data/rosters/MMDD.json` | 答题卡读取的机器题单 |
| `tldr/README.md` | TLDR 执行协议与质量门槛 |
| `tldr/TEMPLATE.md` | 每题不可降级的解析骨架 |
| `tldr/sessions/YYYY-MM/MMDD-tldr.md` | 完整解析与验证 |
| `tools/build_question_chain.py` | 生成并校验整条能力线链 |

## 完整性

- 2009–2025 年 680 道选择题全部至少归入一条能力线。
- 40 条能力线对应 40 个连续日期节点。
- 题目在每条能力线内按年份递增。
- 24 道跨机制接口题会在两条或三条能力线中出现；第二次出现只检查接口，不计作新的刷题配额。
- 原等长日题单和动态调度系统已经切出当前主线，统一冻结在 [`archive/`](archive/)。

TLDR 的状态仍只描述证据强度：

```text
diagnosed → grounded → explained → verified → transferred → automatic
```
