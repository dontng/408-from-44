# 408-from-44

> 服务于考研总分 350 冲击中的 408 提分。当前主线：每天生成一份 MD 题单，真实作答后进入 speedrun，以题补机制、以验证判掌握。

这个项目不再追求维护一套完美题库系统，只服务一个闭环：

```text
生成今日题单 -> 看题作答 -> 固化首次结果 -> speedrun 逐题闭合 -> 验证与迁移
```

## 今天怎么用

1. 生成今日题单：`./tod 0705`。不传日期时默认今天：`./tod`。同日期题单生成后即冻结；重复运行会复用原题，不会重新选题或覆盖作答结果。
2. 启动答题卡：`./ans 0705`。
3. 打开当天 MD：`src/july/0705-day01.md`。MD 顶部有“打开答题卡”链接，建议 VS Code 左右分屏：左边看题图，右边点 `A/B/C/D/?`，其中 `?` 表示不会，空着表示还没答。
4. 答完后，在答题卡底部点“完成今日答题”。它会固化首次作答和判分结果；随后按 [speedrun 协议](speedrun/README.md)处理当天题目。
5. 执行 `./speedrun.sh MMDD` 生成当天骨架；逐题闭合后执行 `./speedrun.sh --check MMDD`。检查通过只代表达到结构交付线，验证题仍需实际作答。

生成题单、完成今日答题和逐题速通只更新本地工作区；速通正文、文档、代码和布局改动也默认留在本地。除非明确 handoff，否则它们不会立即提交。本地 `.sync.log` / `.autopull.log` 只保留最近 7 天。

另外，Git 安全网会在每天 02:00 与 20:00 检查一次工作区；**仅当“已到该时点”且“存在未提交改动”同时成立**，才创建一个完整恢复点并推送。若项目仍在编辑或讨论，它会等到连续 10 分钟无活动再提交；02:00 最多等到 04:00，20:00 最多等到 21:00，届时直接提交。它不替代正常的 handoff，只避免白天或睡前忘记同步而让工作只能留在一台机器上。

## 关键文件

```text
src/<month>/MMDD-dayNN.md     人看的每日题单
data/rosters/MMDD.json       机器题单
data/answers/MMDD.json       答题卡保存的作答
data/results/MMDD.json       完成今日答题后生成的结果
speedrun/README.md           速通的执行协议与质量门槛
speedrun/TEMPLATE.md         每题不可降级的固定骨架
speedrun/sessions/YYYY-MM/   每日完整速通与验证
```

## 命令

| 命令 | 作用 |
|---|---|
| `./tod 0705` | 生成当天 MD 和机器题单 |
| `./ans 0705` | 启动答题卡服务 |
| `python3 tools/grade_today.py --date 0705` | 手动固化结果并更新题单 |
| `./speedrun.sh 0712` | 从真实判分生成当天 speedrun 骨架 |
| `./speedrun.sh --check 0712` | 核对当天 speedrun 是否达到结构交付线 |

答题卡地址固定为 `http://127.0.0.1:8409/?date=0705`，日期换成当天 `MMDD`。

## 题单策略

策略文件是 `data/roster_policy.json`。当前模型：2018-2025 选择题 7 遍主线，2015-2017 选择题 3 遍训练，2013-2014 选择题 1 遍补洞，2009-2012 默认退出主线，只作 reserve。

每日容量：重启期 `10 题 = 7 复习 / 3 新题`；正常日 `20-26` 题；硬上限 `30` 题；低效日 `8-10` 题，只保温。完整模型见 `docs/408重整数学模型-2026-07-05.md`。

## Speedrun 流

Codex 从 `data/results/MMDD.json` 读取不可覆盖的首次作答，以当天真实题目为入口。每题必须完成：独立诊断、最小闭合机制、全部选项裁决、可证伪验证；不能把“解释写完”或“原题重选正确”算作掌握。

状态只描述证据强度：

```text
diagnosed → grounded → explained → verified → transferred → automatic
```

每日完整交付写入 `speedrun/sessions/YYYY-MM/MMDD.md`。协议见 [speedrun/README.md](speedrun/README.md)，逐题结构见 [speedrun/TEMPLATE.md](speedrun/TEMPLATE.md)。

## 资产

`bank/` 是 2009-2025 选择题切图，`answers/` 是答案文本，`review/imgnorm.json` 是题图显示配置。当前入口只有 `bash today.sh` 和 `bash answer.sh`。
