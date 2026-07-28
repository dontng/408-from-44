# Codex Handoff

This repository has two modes of work:

1. Project maintenance: code, scripts, data layout, and documentation.
2. Study speedrun: turning real 408 attempts into usable mechanisms, verification, and transfer.

## Sync discipline

GitHub is the shared source of truth. At the start of any maintenance or speedrun turn, sync the local work copy before making decisions. Do not turn study work into sync management unless the user asks.

All agent-authored code, documentation, knowledge, analysis, layout, and workflow changes stay local by default. Do not infer permission to commit or push from “ready”, a completed subtask, a natural pause, or a switch of topic. Commit or push those changes only when the user explicitly asks to commit, push, sync, or close out the current work. Near a genuine handoff, report uncommitted changes once and offer a handoff commit; do not create one without confirmation.

The scheduled safety net is the sole automatic exception: `tools/autocommit.sh` runs at 02:00 and 20:00 local time. A recovery commit is created only when both conditions hold: a scheduled time has arrived and the worktree has changes. Before committing, it waits for ten minutes without project activity; agents refresh the ignored activity marker with `bash tools/mark-activity.sh` at the start of active project work and before long operations, while direct file edits are detected from their modification time. The wait has a hard cutoff: 04:00 for the 02:00 run and 21:00 for the 20:00 run; at that cutoff it commits even if activity continues, except that an in-progress Git operation must finish first. It then pushes one checkpoint containing all non-ignored changes. Its purpose is off-machine recovery, not normal delivery; agents and workflow commands must not invoke it early or treat a changed worktree as permission for an immediate commit.

## Agent commit standard

Agent-created commits are collaborative records, not opaque user commits. Attribution depends on the publishing path:

- For a local Git commit, keep the configured agent identity as the commit author and add the user as co-author.
- When a connected GitHub interface necessarily records the user as the commit author, do not repeat the user as co-author. Instead, identify the agent in the commit body and add the agent as co-author.

Use the applicable trailer, never both for the same person:

```text
Co-authored-by: dontng <djology.w@icloud.com>
Co-authored-by: Codex <codex@openai.com>
```

For GitHub-interface commits completed by Codex, include `Generated with Codex` immediately before the Codex trailer. This mirrors agent-assisted commit attribution without claiming that Codex is a linked GitHub account.

Every commit message must contain a specific subject and these non-empty sections:

```text
<area>: <completed result>

Implemented:
- files and behavior changed

Why:
- problem or learning/workflow effect addressed

Verified:
- checks run, or why no automated check applies
```

Before committing, inspect the staged diff and stage only work in scope. Install the repository commit policy with `bash tools/setup-git-policy.sh`; it supplies the template and rejects messages without the required implementation, rationale, and verification sections.

## Speedrun architecture

`speedrun/README.md` is the authority for study structure and quality. `speedrun/TEMPLATE.md` fixes the minimum per-question shape; completed daily work lives under `speedrun/sessions/YYYY-MM/MMDD.md`.

For a study turn, read only:

```text
speedrun/README.md
data/results/MMDD.json
src/<month>/MMDD-dayNN.md
speedrun/sessions/YYYY-MM/MMDD.md  # when continuing an existing session
```

The user's first attempt is evidence and must never be overwritten. Independently solve and diagnose before consulting the reference answer. Build only the mechanism needed to read the problem, adjudicate every option, and survive a nearby change of conditions. Use external authority to settle facts or boundaries, not to display research.

After a complete `data/results/MMDD.json` exists, create the daily scaffold with `./speedrun.sh MMDD`. A generated `draft` is not a study state and must not be delivered. After every question is independently closed, run `./speedrun.sh --check MMDD`; treat a passing structural check as necessary but not sufficient, then perform the protocol's content review.

Writing an explanation can advance a problem only to `explained`. Advance it to `verified`, `transferred`, or `automatic` only after the corresponding user performance exists. Never ask whether the user understood; design the cheapest falsifiable check instead.

The tenth problem in a batch receives the same standard as the first. If that quality cannot fit in one pass, split the delivery and preserve explicit progress rather than compressing later problems.
