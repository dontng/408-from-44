# Codex Handoff

This repository has two modes of work:

1. Project maintenance: code, scripts, data layout, and documentation.
2. Study coaching: helping process the current 408 problem after the user has answered the daily roster.

For project maintenance, inspect the relevant files normally.

## Sync discipline

GitHub is the shared source of truth. At the start of any maintenance or coaching
turn, sync the local work copy before making decisions. The repository has
separate scripts to encourage regular push/pull sync; do not turn coaching into
sync management unless the user asks.

Do not keep Codex-created state private to one machine. If you create or update
files in this repository for the workflow, commit and push them when the work is
ready, unless the user explicitly asks not to. Local-only files are limited to
ignored machine logs and preferences such as `.sync.log`, `.autopull.log`, and
`.studio-theme`.

## Coaching notes

The main coaching output is still one current item at a time. Preserve durable
notes only when they are worth seeing again: the first divergence point, the rule
that fixed it, and any compact pattern that should influence later review. Avoid
turning every solved problem into a long knowledge-base entry.

For study coaching, do not scan the whole repository and do not read the full daily queue by default. Use the narrow coach handoff:

```text
coach/ENTRY.md
coach/current.md
```

The coaching task is one problem at a time. Do not expand into a free-form knowledge base. Do not create broad summaries of all weaknesses unless explicitly asked.

The expected coaching output is a recommendation for the current item:

```text
pass / revisit / pin
```

- `pass`: close it for tonight; return it to normal scheduling.
- `revisit`: short-term return; it should come back soon.
- `pin`: persistent exam-risk issue; it belongs in `coach/pins/`.

If `coach/current.md` says there is no open item, tell the user to answer today's roster and complete the answer card first, or run:

```bash
python3 tools/coach_next.py --date MMDD
```

## T1 world

T1 is the evidence-driven training control layer in `t1/`. It is not a second
question bank, scheduler, note system, or a replacement for one-problem
coaching. Read it only when the user explicitly asks for T1 work.

- T0 remains the source of truth: `src/`, `data/results/`, `review/state.json`,
  and reviewed coaching outcomes.
- Add a T1 fingerprint only after at least two independent, reviewed pieces of
  evidence establish the same first divergence point. A wrong answer alone is
  not sufficient evidence.
- A fingerprint must name one trigger, one first divergence point, one
  corrective action, and its evidence question IDs. It may not be a broad topic
  label such as a course name or chapter.
- T1 can propose verification questions from the existing bank. It must not
  create a parallel daily plan or silently alter the scheduler.
- Archive a fingerprint when it has enough contrary evidence; do not preserve
  it as permanent baggage.
