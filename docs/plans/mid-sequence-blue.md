# Plan: Blue Hat steps in the middle of a sequence

Status: plan only, nothing implemented. Needed for the "strategic planning" preset, which de Bono-style
summaries show with Blue between phases (the order is from a secondary source; check it against the book first).

## Today
Blue opens (framing) and closes (report) every run. `sequence` holds only the five coloured hats.
`SequenceOverride`, `Framing` and the presets reject `blue`.

## Design
1. **Allow `blue` as an inner step.** `ThinkingHatName` stays five hats; add `SequenceStep = ThinkingHatName | "blue"`.
   Step keys follow the existing rule (`blue`, `blue#2`). Blue-Open and Blue-Close remain implicit and are not listed.
2. **A new node action, `blue_checkpoint`,** run by the `sequential` node when it reaches a `blue` step.
   It gets the question, the framing and the earlier hats' outputs (same delimited, size-capped block as now).
   Output schema `BlueCheckpoint`: `progress` (what has been covered, max 3 points), `gaps` (what is missing, max 3),
   `next_focus` (one line passed to the next hat as extra instruction). It has **no power to change the sequence** in v1.
3. **Next hat sees the checkpoint.** The following hat's user message gains a `<blue_checkpoint>` data block
   (treated as data, escaped like `earlier_hats`).
4. **Report.** `FinalReport.checkpoints: list[BlueCheckpoint]`; rendered as "Blue checkpoint after <hat>".
   Blue-Close receives them as input.
5. **Rules in code.** No blue as the first or last step (Open and Close already do that); no two blues in a row;
   max 8 steps still counts blue steps.
6. **Failure.** A failed checkpoint is skipped and recorded like any failed step. It never aborts the run.

## Later (v2, only if wanted)
Let a checkpoint propose to insert or drop a hat, bounded to the 8-step cap and validated by code.
This is a real change to the "the model proposes, code decides" rule, so it needs its own decision.

## Work breakdown
| # | Task | Size |
|---|---|---|
| 1 | Schema: `SequenceStep`, `BlueCheckpoint`, `FinalReport.checkpoints` | S |
| 2 | Rules in `sequence.py` (no first/last/adjacent blue) + tests | S |
| 3 | Prompt `blue_checkpoint.md` v1 (data-block handling, length limits) + prompt tests | S |
| 4 | `make_sequential` handles blue steps; pass checkpoint to next hat | M |
| 5 | Render + JSON + Blue-Close input | S |
| 6 | Add `strategic_planning` preset once its order is confirmed from the book | S |
| 7 | CLI `--sequence` accepts `blue`; docs; live test on Claude and llama.cpp | S |

## Risks
- Small local models may ignore the 3-point limit: reuse `trim_to`.
- Prompt injection through earlier hat text: the checkpoint reads model output, so it uses the same data-block escaping.
- Extra model call per blue step: counts toward the cost report (see progress/cost work).
