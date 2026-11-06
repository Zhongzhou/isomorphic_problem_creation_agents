# Conceptual multiple-choice questions

This agent writes a bank of isomorphic multiple-choice questions from one short input file. Each question describes a physical situation and asks the student to choose the equation that correctly expresses a law for it. An example is Newton's second law along the radial direction at one point of a circular path. The questions vary the situation and the asked case, so a student who memorizes one answer cannot reuse it.

## What it generates

- Candidate scenes for each scenario in the input. A critic agent rejects the ones that break the input's specifications, and you choose which of the rest to keep.
- An item tally computed by Python: kept scenes times the variation values you confirmed.
- Figures for each kept scene, drawn by one Python script that you can revise, when the input asks for figures.
- Sample items for you to edit, then the full set of items in the same style, each with feedback that says which forces point with or against the positive direction.
- A review pass, and a problem-bank YAML file when the input asks for one.

## What it does not do

- It does not choose how many scenes to keep. You mark them.
- It does not assign random numbers, solve for a numeric unknown, or rotate which quantity is given. That is the job of the numerical calculation agent, which is under construction.
- It does not run on this website. You download the skill and run it in your own project.

## Workflow

```text
Input file (copied from the template, informal notes are fine)
  -> Agent 1 checks the input
  -> you confirm the input, the correct-answer rule and the variations
  -> Python records the variation axes
  -> repeat until every scenario has candidate scenes:
       Agent 2 writes scenes, Agent 3 keeps or rejects them
  -> you mark the scenes to keep and the backups
  -> Python tallies the items; you confirm
  -> figures; you revise
  -> sample items; you edit
  -> the rest of the items, checked by Python against the tally
  -> Agent 8 reviews; you confirm any physics, figure or choice change
  -> problem-bank YAML
```

The workflow stops for your confirmation at each arrow that says "you". Python, not a model, writes the scene list, the tally, and the item checks.

## Input

Start from `examples/input file design.yaml`. `examples/circular-motion-sample-input.yaml` is a filled example, and `examples/input-form.html` is a form you can open in a browser to write an input file. All three are in the download.

The input names the situation, what every problem states (including the sign convention), what the student decides, the scenarios and their variations, the choice list, and the rule that picks the correct choice.
