# Codex Handoff

This repository has two modes of work:

1. Project maintenance: code, scripts, data layout, and documentation.
2. Study coaching: processing one current 408 problem after the user has answered the daily roster.

## Sync discipline

GitHub is the shared source of truth. At the start of any maintenance or coaching turn, sync the local work copy before making decisions. Do not turn coaching into sync management unless the user asks.

Do not keep Codex-created state private to one machine. If you create or update workflow files, commit and push them when ready unless the user explicitly asks not to. Local-only files are limited to ignored machine logs and preferences such as `.sync.log`, `.autopull.log`, and `.studio-theme`.

## Coach architecture

`coach/CONSTITUTION.md` is the authority for coaching structure and quality. It defines the ownership of:

- `coach/knowledge/`: 408 textbook-style knowledge by subject and chapter.
- `coach/analysis/`: direct, question-specific reasoning and option elimination by year/question.
- `coach/ability/`: evidence-backed personal problem-solving ability.
- `coach/notes/<month>/`: downstream daily notes, parallel to `src/<month>/`.

For study coaching, start from the narrow handoff:

```text
coach/CONSTITUTION.md
coach/ENTRY.md
coach/current.md
```

Do not bulk-read queues, notes, or the three asset layers. Read only the sections required by the current problem.

A `pass` is the completed delivery of a problem: the problem is understood and valuable output is no longer trapped in chat context or old-paper annotations. `revisit` and `pin` remain future relationship markers; do not create directories, queues, or standalone notes for them.

If `coach/current.md` says there is no open item, tell the user to answer today's roster and complete the answer card first, or run:

```bash
python3 tools/coach_next.py --date MMDD
```
