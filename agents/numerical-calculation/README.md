# Numerical calculation problems

Under construction. This agent is not offered for download yet.

This agent starts from an equation scheme: the physics relations a problem uses, the quantities that may vary, and how many scenarios to write. It produces a reviewed list of real-world scenarios that fit the scheme, and one calculation function for every equation set. It then pairs every accepted scenario with every equation set.

## What it generates

- A checked input, with formulas rewritten in LaTeX.
- A list of scenarios. A generator agent writes them and a critic agent keeps or rejects them. Python counts the rounds and stops after five.
- Every combination of the input's formula choices, with constants, parameters and computed variables.
- One Python function per equation set, written and checked by Python.
- A table that pairs every accepted scenario with every equation set.

## What it does not do yet

Random numbers, question wording, and versions that rotate which quantity is unknown are not generated yet.

## Workflow

```text
Input scheme YAML
  -> Agent 1 checks and edits the input; you confirm
  -> repeat until the target number of scenarios is reached (at most 5 rounds):
       Agent 2 writes the scenarios still needed, Agent 3 keeps or rejects them
  -> Python expands every formula combination
  -> Agent 4 chooses parameters and computed variables when the input leaves them out
  -> Python writes and checks one function per equation set
  -> Python pairs every accepted scenario with every equation set
```

## Input

Start from `examples/input-scheme.yaml`. Its sidecars, `input-scheme.scenarios.yaml`, `input-scheme.calculations.yaml` and `input-scheme.calculations.py`, show what a run writes.
