# Codex Handoff

This repository has two modes of work:

1. Project maintenance: code, scripts, data layout, and documentation.
2. Study coaching: helping process the current 408 problem after the user has answered the daily roster.

For project maintenance, inspect the relevant files normally.

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
