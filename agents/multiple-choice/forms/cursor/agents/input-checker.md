# Agent 1: input checker

You are the parent agent. Read this file and edit the user's input yourself. Do not spawn a subagent for this step.

The input is the informal YAML described in `problem-creation agents/multiple-choice questions/input file design.yaml`.

## What to do

1. Run `scripts/mcq_bank.py validate` on the input file.
2. Rewrite every choice equation into standard LaTeX. Edit the input file directly.
   - Rewrite fractions and subscripts. `mv^2/r` becomes `\frac{m v^{2}}{r}`. A bare `pi` becomes `\pi`. Keep the user's symbol names.
3. If `errors` is non-empty, ask the user. Do not invent a scenario, a choice, or a variation the user did not write.
4. If `correct_answer_blank` is true, write a best-guess rule for which possible answer is correct in each variation. Show the guess. Do not write it into the file until the user confirms it.
5. From `common variations` and each scenario's own variations, propose the value list a later tally can count. Each axis has an id, the values named in the prose, and `changes_drawing`. A position label on one figure has `changes_drawing` false. A wind direction that changes the arrows has `changes_drawing` true. Show those lists.
6. Show `warnings`, the edited input, the correct-answer rule, and the variation lists. Then stop.

Scene generation does not start until the user confirms this input in a later message.
