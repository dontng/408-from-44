# 408-from-44

> 从 44 分到 100+ / 120+。当前主线：每天生成一份 MD 题单，右侧答题卡作答，完成后进入 Codex 单题教练流。

这个项目不再追求维护一套完美题库系统，只服务一个闭环：

```text
生成今日题单 -> 看题作答 -> 完成今日答题 -> 生成 today 过账清单 -> Codex 一题一题处理
```

## 今天怎么用

1. 生成今日题单：`./tod 0705`。不传日期时默认今天：`./tod`。同日期题单生成后即冻结；重复运行会复用原题，不会重新选题或覆盖作答结果。
2. 启动答题卡：`./ans 0705`。
3. 打开当天 MD：`src/july/0705-day01.md`。MD 顶部有“打开答题卡”链接，建议 VS Code 左右分屏：左边看题图，右边点 `A/B/C/D/?`，其中 `?` 表示不会，空着表示还没答。
4. 答完后，在答题卡底部点“完成今日答题”。它会生成结果和教练流入口数据。

生成题单、完成今日答题和逐题教练流程只更新本地工作区；知识正文、文档、代码和布局改动也默认留在本地。除非明确 handoff，否则它们不会立即提交。本地 `.sync.log` / `.autopull.log` 只保留最近 7 天。

另外，Git 安全网会在每天 02:00 与 20:00 检查一次工作区；**仅当“已到该时点”且“存在未提交改动”同时成立**，才创建一个完整恢复点并推送。若项目仍在编辑或讨论，它会等到连续 10 分钟无活动再提交；02:00 最多等到 04:00，20:00 最多等到 21:00，届时直接提交。它不替代正常的 handoff，只避免白天或睡前忘记同步而让工作只能留在一台机器上。

## 关键文件

```text
src/<month>/MMDD-dayNN.md     人看的每日题单
data/rosters/MMDD.json       机器题单
data/answers/MMDD.json       答题卡保存的作答
data/results/MMDD.json       完成今日答题后生成的结果
coach/today/MMDD.json        当天全部题目的过账清单
coach/current.md             Codex 当前只处理的一题
coach/pins/                  考前必须拔掉的长期钉子
```

## 命令

| 命令 | 作用 |
|---|---|
| `./tod 0705` | 生成当天 MD 和机器题单 |
| `./ans 0705` | 启动答题卡服务 |
| `python3 tools/grade_today.py --date 0705` | 手动生成结果和 `coach/today` |
| `python3 tools/coach_next.py --date 0705` | 从 `coach/today` 取下一题生成 `coach/current.md` |
| `python3 tools/coach_mark.py --date 0705 --decision revisit` | 标记当前题为 `pass/revisit/pin` |

答题卡地址固定为 `http://127.0.0.1:8409/?date=0705`，日期换成当天 `MMDD`。

## 题单策略

策略文件是 `data/roster_policy.json`。当前模型：2018-2025 选择题 7 遍主线，2015-2017 选择题 3 遍训练，2013-2014 选择题 1 遍补洞，2009-2012 默认退出主线，只作 reserve。

每日容量：重启期 `10 题 = 7 复习 / 3 新题`；正常日 `20-26` 题；硬上限 `30` 题；低效日 `8-10` 题，只保温。完整模型见 `docs/408重整数学模型-2026-07-05.md`。

## Coach 流

Codex 不应该一次读完整病历。项目给 Codex 的窄入口是 `coach/ENTRY.md` 和 `coach/current.md`。当天全部题都会进入 `coach/today/MMDD.json`，但 Codex 默认只处理 `current.md` 里的当前一题。

每题最终只允许三种处置：

```text
pass < revisit < pin
```

`pass` 表示今晚收口，回正常调度；`revisit` 表示短期回炉，近期必须再出现；`pin` 表示长期悬挂，考前必须拔掉。规则见 `coach/README.md` 和 `AGENTS.md`。

## 资产

`bank/` 是 2009-2025 选择题切图，`answers/` 是答案文本，`review/imgnorm.json` 是题图显示配置。当前入口只有 `bash today.sh` 和 `bash answer.sh`。
