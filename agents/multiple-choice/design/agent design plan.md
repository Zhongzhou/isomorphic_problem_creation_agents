# Multiple-choice question workflow

Agents create a bank of isomorphic multiple-choice questions from an input copied from [input file design.yaml](input%20file%20design.yaml). A filled example is [circular-motion-sample-input.yaml](circular-motion-sample-input.yaml). Each question asks the student to choose the correct equation for one stated physical situation.

The numerical-calculation workflow stays in [../numerical calculation problems/agent design plan.md](../numerical%20calculation%20problems/agent%20design%20plan.md). This workflow does not assign random numbers, solve for a numeric unknown, or rotate which quantity is given.

[input-file-template.yaml](input-file-template.yaml) and [input-fields-template.md](input-fields-template.md) are an earlier draft. Agents do not read them.

The skill that runs this workflow is [.cursor/skills/multiple-choice-questions/SKILL.md](../../.cursor/skills/multiple-choice-questions/SKILL.md). Python writes the scene sidecar, the tally, and the item checks. The checker and the confirmation stops stay in the main conversation. Agents 2, 3, and 8 are subagents.

## Default stops

These stops are agent behavior. They are not fields in the input.

1. After checking the input, wait for the user to confirm it.
2. After writing candidate scenes, save them and wait. The user marks which scenes to keep and which to hold as backups. The user may keep a different number for each scenario. The agent does not choose that number.
3. After drawing figures, wait for visual revisions.
4. After the sample items, wait. Mirror the user's edits before writing the rest.
5. During review, apply small fixes when the input allows it. List physics, figure, or choice changes and apply those only after the user confirms them.
6. Write the bank YAML only after that review, and only when the input asks for YAML.

Backups are not drawn and do not become items. The item list and the item tally are computed by the agents after the user selects scenes. The input does not contain them.

## Input the agents read

Informal notes are enough. The checker turns equations into LaTeX.

**Question.** `situation` is the physical setup. `given` is what every problem states, including the sign convention and the requirement to define symbols. `ask` is the decision the student makes.

**scenario and variations.** A scenario is a major version of the problem. `common variations` apply to every scenario. A variation listed under one scenario applies only to that scenario. The default grid is every combination of the common variations and that scenario's own variations. `specifications` can say that a combination does not apply. Each scenario has a `description`.

**Diagram.** `need diagram` is Yes or No. `diagram specification` says how to draw a figure. One figure covers every value of a variation that is only a label on the same drawing, such as three positions. A variation that changes the drawing, such as wind direction, gets its own figure.

**Choice Items.** `possible answer` entries are the equations that can be correct. `distractor` entries are never correct. `choice variations` says how the symbols change from one scenario to another. `correct answer` says which possible answer is correct for each variation. The choice order in the input is the choice order in every item.

**Creation Process.**

| Field | What the agent does with it |
| --- | --- |
| `candidates scenes per scenario` | How many scenes to propose for each scenario. |
| `samples per scenario` | How many sample items to write for each scenario before the full grid. |
| `automatic minor fixes` | Yes means small wording and label fixes are applied without asking. |
| `export.convert markdown to YAML` | Yes means the last step writes a bank YAML. |
| `export.YAML template` | The template file. If it is blank, use `Templates/Problem-bank-template-mathjax.yaml`. |

## Agents

Agents propose scenes, drawings, and prose. They take the equations from Choice Items and `choice variations`. They choose the correct one by `correct answer`. They do not invent a new equation for an item.

### 1. Input checker

Read the input and edit it in place.

- Turn choice equations into LaTeX.
- Check that Question has a situation, a given, and an ask.
- Check that every scenario has a description.
- Check that there is at least one possible answer and one distractor, and that `choice variations` says what changes across scenarios.
- If `correct answer` is filled in, use that rule for every item. If it is blank, write a best-guess rule for which possible answer is correct in each variation, show that guess, and wait for the user to confirm or replace it before generating scenes.
- Check that Creation Process gives `candidates scenes per scenario` and `samples per scenario`.
- If `need diagram` is Yes, check that `diagram specification` is present.
- Do not add a field for how many scenes to keep, and do not ask the user for an item tally.

Show the input and stop.

### 2. Scenario candidates

For each scenario, write `candidates scenes per scenario` scenes. Each scene is one or two sentences, is not a repeat, and can carry that scenario's choice list and variations. Follow the description and the specifications.

A variation is an axis, not something to bake into only one scene. A wind-direction variation stays a variation. The scenes are different objects or settings.

Save the scenes in a candidate file next to the input. Include the scenario description, its variations, and its specifications. Then stop.

### 3. Scenario critic

Review each scene against that scenario's description, specifications, and choice variations.

Remove a scene when the choice list does not apply: the constraint force is absent, an extra force would have a component along the asked direction, the object cannot follow the path, or the scene needs two objects. Keep the removed text and the reason.

If a scenario has no scenes left, call Agent 2 again for that scenario only. Stop after 5 rounds and ask the user to loosen the description. When every scenario still has at least one scene, stop and ask the user which scenes to keep.

### 4. Selection

The user marks which scenes to keep and which to hold as backups. The number kept can differ by scenario.

Then compute the tally. For each kept scene, count the combinations of the common variations and that scenario's own variations, and drop any combination the specifications exclude. Report the tally and the combinations. Do not continue until the user confirms the selection.

### 5. Diagrams

Skip this agent when `need diagram` is No.

Draw from `diagram specification`. One figure per kept scene for variations that share a drawing. A separate figure for each value of a variation that changes the drawing. Do not draw backups.

Show the figures and stop. Apply visual revisions to the script and regenerate the set before any problem text is written.

### 6. Sample items

Write `samples per scenario` items for each scenario. Use one kept scene and one value of each variation, and say which values were used.

Each sample contains:

- The scene, plus any condition in the specifications that decides which forces enter the equation.
- The figure, when the scenario has one.
- The question's given and ask, including the sign convention and a definition of every symbol in that item's choices.
- The choice list in the input order, with symbols changed as `choice variations` says.
- The correct possible answer for the variation values used in the sample, chosen by the confirmed `correct answer` rule.
- Feedback that says which forces point with or against the positive direction, states the resulting equation, and says why the distractor is wrong.

Stop. The user edits these samples. Mirror accepted edits onto the other samples before expansion.

### 7. Expansion

After the user accepts the samples, write the rest of the grid: every kept scene, every remaining combination of variations, and the samples' variation values too if a sample is the only copy of that combination.

For a new variation value of the same scene, keep the stem, the figure, the glossary, and the choice order. Change the asked variation, the correct choice, and the feedback. `choice variations` supplies the symbols. `correct answer` supplies which possible answer is correct.

For another kept scene in the same scenario, also change the object name and the glossary wording.

A script checks the expanded file before the review:

- Item count equals the tally from Agent 4.
- Every kept scene that needs a figure has one, and every item points at the figure for its scene and drawing variation.
- No backup scene appears.
- Choice order matches the input.
- The marked correct choice matches `correct answer` for that item's variation values.
- Every symbol in an item's choices is defined in that item.
- Every distractor is marked incorrect.

### 8. Review

Read the full set. When `automatic minor fixes` is Yes, correct small wording, grammar, and label mismatches in place. List anything that changes the physics, the figure, or which choice is correct, and wait. Apply only the confirmed changes, then run the same checks again.

### 9. YAML

When `convert markdown to YAML` is not Yes, stop after the markdown.

When it is Yes, convert the accepted markdown with `YAML template`, or with `Templates/Problem-bank-template-mathjax.yaml` when that field is blank.

- One `multiple_choice` entry per item.
- Question text, choice text, and feedback follow the template. For the default template they are HTML paragraphs, and math uses MathJax `\(...\)`.
- `figure` is the item's image when it has one.
- Choice order stays the input order, with `correct: true` on the mapped choice.
- `feedback.general` is that item's feedback.
- Record the input file, the candidate file, the diagram script, and the markdown source under the bank metadata.

Show the YAML and ask for any metadata the template still needs, such as the bank id and learning objectives.

## Skill

The orchestrator, the subagent prompts, and `scripts/mcq_bank.py` are in [.cursor/skills/multiple-choice-questions/](../../.cursor/skills/multiple-choice-questions/). Diagrams and the bank YAML are still written by the parent agent from the script's figure list and item check.
