# scripts

## auto_log.py

记录每次 git commit 到 `logs/sessions.txt`，格式为 strace 风格，置顶最近 3 条。

触发方式：Claude Code Stop hook，对话结束时自动执行，无需手动调用。  
配置位置：`.claude/settings.json`

---

## knight.sh（许愿机）

轮询 `wishes/spell/`，发现 `[pending]` 的 wish 后用 `claude -p` 执行，结果写入
`wishes/phantasm/`，每条执行完立即 git push。

**启动（挂后台）**

```bash
nohup bash wishes/knight.sh >> wishes/knight.log 2>&1 &
```

**查看运行日志**

```bash
tail -f wishes/knight.log
```

**停止**

```bash
pkill -f knight.sh
```

**自定义轮询间隔（默认 1800 秒）**

```bash
POLL_INTERVAL=600 nohup bash wishes/knight.sh >> wishes/knight.log 2>&1 &
```

**从另一台电脑提交 wish**

在 `wishes/spell/` 下按日期建文件，例如 `0601.md`：

```
# 0601

--- wish-01 [pending]
对 questions/operating_systems/ch03_内存管理 下所有文件做 OCR 纠错
```

git push 后 knight 会在下次轮询时自动拉取并执行。

wish 状态流转：`[pending]` → `[running]` → `[done]` / `[exhausted]` / `[failed]`

---

## extract_ds_questions.py / extract_os_questions.py

从 PDF 提取单选题，输出为按章节分的 markdown 文件。题目已全部提取完毕，
一般不需要再运行。如需重新提取：

```bash
python3 scripts/extract_ds_questions.py
python3 scripts/extract_os_questions.py
```

## clean_questions.py

对提取出的 markdown 做保守格式清洗。同上，已完成历史使命。
