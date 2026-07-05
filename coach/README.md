# Coach Flow

Coach 只做一件事：把当天做过的题逐题过账，给出下一步处置。

它不是自由知识库，不记录所有知识点，不复刻 `cprune`。复杂内容只有在升级为 pin 时才长期保留。

## today

`coach/today/MMDD.json` 是当天过账清单。

来源是当天判分结果。当天做过的每道题都会进入 `today`，不能因为答对就自动跳过。

字段含义：

- `grade`：判分结果，可能是 `right` / `wrong` / `unknown` / `blank` / `self_check`。
- `priority`：处理顺序。`1` 最高，通常是错题、不会、自判；`2` 是答对但仍需检查的新题；`3` 是答对且暂时低风险的题。
- `decision`：Codex 处理后的处置，初始为 `open`。

## current

`coach/current.md` 是当前正在通关的一题或一个问题。

Codex 默认只读 `current.md`，不要一次读完整 `today` 和所有历史。处理完当前题后，再进入下一题。

## pins

`coach/pins/` 是考前必须拔掉的钉子。

只有反复不过、核心题型不稳、同类题连续炸、考场风险高的问题，才升级为 pin。

## decisions

每题最终只允许三种处置：

```text
pass < revisit < pin
```

- `pass`：今晚收口，回正常调度。
- `revisit`：短期回炉，近期必须再出现。
- `pin`：长期悬挂，考前必须拔掉。

答对不是自动 `pass`。Codex 需要判断这题是否真的进入包围圈、是否能说明关键规则、是否还需要短期回炉。
