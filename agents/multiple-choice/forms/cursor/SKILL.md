---
name: multiple-choice-questions
description: >-
  Runs the multiple-choice question workflow: check an input copied from
  input file design.yaml, confirm variation values and the correct-answer
  rule, generate and critique scenes, then tally items after the user
  chooses which scenes to keep. Use when the user asks to run the
  multiple-choice question workflow, build a conceptual multiple-choice
  problem bank, or generate isomorphic equation-choice questions from
  that input.
---

# Multiple-choice questions

Orchestrate the workflow below. You talk to the user yourself for Agent 1 and for every confirmation stop. Spawn Agent 2, Agent 3, and Agent 8 with the Task tool (`subagent_type: generalPurpose`). Python is the only writer of `update_count`, the variation tally, the scene status, and the item checks.

Scripts, run from the repo root with the project virtual environment. On Windows that interpreter is `.venv/Scripts/python.exe`. On macOS or Linux it is `.venv/bin/python`. Do not use a system `python` or `py -3`.

```bash
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py validate "INPUT.yaml"
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py init --input "INPUT.yaml"
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py receive --file "INPUT.mcq.yaml"
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py add --file "INPUT.mcq.yaml" --scenario "scenario 1" --text "..."
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py remove --file "INPUT.mcq.yaml" --scenario "scenario 1" --index 0 --reason "..."
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py set-variations --file "INPUT.mcq.yaml" --json-file "axes.json"
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py select --file "INPUT.mcq.yaml" --json-file "selection.json"
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py tally --file "INPUT.mcq.yaml"
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py figures --file "INPUT.mcq.yaml"
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py sample-slots --file "INPUT.mcq.yaml"
.venv/Scripts/python.exe .cursor/skills/multiple-choice-questions/scripts/mcq_bank.py check-items --file "INPUT.mcq.yaml" --json-file "items.json"
```

The environment is the repo-root `.venv` directory, which git ignores. Recreate it with `py -3 -m venv .venv`, then install [requirements.txt](requirements.txt) using that interpreter.

`init` writes `INPUT.mcq.yaml` beside the input. Quote paths that contain spaces. If a sidecar already exists, ask the user before `init --force`.

The input does not say how many scenes to keep. Do not invent that number. `select` records only the indexes the user marked.

`tally` counts kept scenes times the variation values stored by `set-variations`. Do not type an item count into a prompt. Use `items` from the tally JSON.

## Stops

These are not input fields. Do them in order.

1. After checking the input, wait for the user to confirm it.
2. After writing candidate scenes, save them and wait. The user marks which scenes to keep and which to hold as backups.
3. After `tally`, show the count and wait for the user to confirm the selection.
4. After drawing figures, wait for visual revisions. Skip figures when `need_diagram` is false.
5. After the sample items, wait. Mirror the user's edits before writing the rest.
6. During review, apply small fixes only when `automatic_minor_fixes` is true. List physics, figure, or choice changes and apply those only after the user confirms them.
7. Write the bank YAML only after that review, and only when `export_yaml` is true.

## 1. Check the input

Read [agents/input-checker.md](agents/input-checker.md) and follow it. If the user did not name a file, ask which input to use.

After editing, show the input, any validator warnings, the correct-answer rule, and the proposed variation axes. Then stop. Do not run `init`, `receive`, or Agents 2 and 3 in this turn.

## 2. Record axes and generate scenes

Start this section only after the user explicitly confirms the input, the correct-answer rule, and the variation value lists.

```text
- [ ] init the sidecar
- [ ] set-variations
- [ ] receive
- [ ] generate, or stop for selection
- [ ] add the new scenes
- [ ] critique and remove
- [ ] repeat until every scenario has a pending scene or the round limit stops you
```

1. `init --input` the confirmed file. If `correct answer` was blank, write the confirmed rule into the input before `init`.
2. Write `axes.json` from the confirmed value lists. `set-variations --json-file` that path. Every scenario id appears in `by_scenario`. An axis the scenario does not use is an empty list.
3. `receive`. This increments `update_count`.
   - Exit code 2 (`stop: true`): a scenario still has no pending scene after more than 5 rounds. Tell the user. Give them the sidecar path. Ask them to loosen that scenario's description.
   - `ready_for_selection: true`: go to selection.
   - Otherwise spawn Agent 2 once per scenario whose `needed` is greater than 0.
4. Agent 2's prompt is the full text of [agents/scene-generator.md](agents/scene-generator.md) plus that scenario's fields, `choices`, `choice_variations`, `pending_texts`, `rejected`, and `needed` from the receive JSON. Append each returned string with `add --scenario`. One `add` call may take several `--text` flags.
5. Agent 3's prompt is the full text of [agents/scene-critic.md](agents/scene-critic.md) plus the description, specifications, choice list, and `pending_texts`, numbered from 0. Apply the reviews with one `remove` call per scenario. Pass `--index` and `--reason` only for `keep: false`. If every pending scene is kept, run `remove` with no index. If the review count does not match the pending list, run Agent 3 once more. If it still does not match, stop and tell the user.
6. When `ready_for_selection` is true, show the pending scenes and stop. Otherwise go back to `receive`.

Subagents return JSON only. They do not edit the sidecar and they do not call each other.

## 3. Selection and tally

The user marks, in the candidate list, which scene indexes to keep and which to hold as backups. The number kept can differ by scenario.

Write `selection.json` with one object per scenario: `{"keep": [0], "backup": [1, 2]}`. Every scene index appears in exactly one list. `select --json-file` that path.

`tally`. Show `items` and the combinations. Backups are excluded. Stop until the user confirms the selection.

## 4. Diagrams

Skip this section when `need_diagram` is false.

`figures` lists one drawing per kept scene, and a separate drawing for each value of an axis with `changes_drawing: true`. Do not draw backups.

Write one Python script from `diagram_specification` and generate those figures. Show them and stop. Apply visual revisions to the script and regenerate the set before any problem text is written.

## 5. Samples

`sample-slots` lists `samples_per_scenario` items per scenario that still has a kept scene. Each slot names the scene index and the variation values.

Write those items. Each one contains:

- The scene, plus any condition in the specifications that decides which forces enter the equation.
- The figure for that scene and drawing, when the bank has figures.
- The question's given and ask, including a definition of every symbol in that item's choices.
- The choice list in the input order, with symbols changed as `choice_variations` says.
- The correct possible answer chosen by `correct_answer`.
- Feedback that says which forces point with or against the positive direction, states the resulting equation, and says why the distractor is wrong.

Save the samples in a markdown file next to the input. Stop. Mirror the user's edits onto the other samples before expansion.

## 6. Expansion and review

After the user accepts the samples, write the rest of the grid. For a new variation value of the same scene, keep the stem, the figure, the glossary, and the choice order. Change the asked variation, the correct choice, and the feedback.

Write `items.json` with one object per item:

```json
{
  "items": [
    {
      "scenario": "scenario 1",
      "scene_index": 0,
      "values": {"position": "top"},
      "choices": ["...", "..."],
      "correct_index": 0,
      "choice_symbols": ["T", "m"],
      "defines_symbols": ["T", "m"],
      "figure": "diagrams/scenario-1-scene-0.png"
    }
  ]
}
```

`correct_index` is the position in `choices`. It must point at a possible answer. Distractor indexes are incorrect. `check-items` compares this file with the tally. Fix the markdown until `ok` is true.

Then spawn Agent 8. Its prompt is the full text of [agents/reviewer.md](agents/reviewer.md) plus the items, `correct_answer`, `choice_variations`, and `automatic_minor_fixes`. When `automatic_minor_fixes` is true, apply each `minor` fix. Show every `major` issue and wait. Apply only the confirmed changes, then run `check-items` again.

## 7. YAML

When `export_yaml` is false, stop after the markdown.

When it is true, convert the accepted markdown with `yaml_template`. For the default template, question text, choice text, and feedback are HTML paragraphs, and math uses MathJax `\(...\)`. One `multiple_choice` entry per item. Choice order stays the input order, with `correct: true` on the mapped choice. `feedback.general` is that item's feedback. `figure` is the item's image when it has one.

Record the input file, the sidecar, the diagram script, and the markdown source under the bank metadata. Show the YAML and ask for any metadata the template still needs, such as the bank id and learning objectives.
