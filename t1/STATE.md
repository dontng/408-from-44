# 408 T1 State

T1 is the training control layer. It compresses repeated, reviewed T0 evidence
into a small number of testable exam actions.

## Boundary

T0 is the source of truth and remains unchanged:

- `src/` records each daily roster.
- `data/results/` records answer outcomes.
- `review/state.json` owns spaced-repetition scheduling.
- `coach/` records the one-question review flow and durable pins.

T1 does not duplicate any of those systems. It cannot create a new daily plan,
change a due date, or promote a one-off wrong answer into a lasting weakness.

## Evidence Standard

Create a fingerprint only when two or more independently reviewed questions
show the same first divergence point. Each item must contain:

| Field | Requirement |
| --- | --- |
| Trigger | The recognizable exam condition. |
| First divergence | The earliest wrong classification, representation, or operation. |
| Corrective action | One short action to execute when the trigger appears. |
| Evidence | At least two question IDs and their reviewed outcomes. |
| Verification | Existing-bank questions or future evidence that could disprove it. |
| Status | `watching`, `active`, or `archived`. |

## Active Fingerprints

None. The existing history has not yet been reviewed against the T1 evidence
standard.

## Operating Rule

T1 has one allowed user-facing output per active fingerprint: either a concise
pre-question action or a same-pattern verification task drawn from `bank/`.
It must train one exam reaction, not present a chapter summary.
