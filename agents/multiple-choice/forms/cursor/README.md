---
agent: multiple-choice
form: cursor
version: 0.1.0
agent_version: 0.1.0
authors:
  - name: Zhongzhou Chen
    role: author
license: CC-BY-NC-4.0
updated: 2026-11-01
---

# Conceptual multiple-choice questions: Cursor skill

## What this form is

A Cursor skill that turns an input file into a bank of isomorphic multiple-choice questions. Cursor's agent runs the workflow in [SKILL.md](SKILL.md); Python scripts in `scripts/` keep the scene list, the item tally and the item checks. The workflow does not choose how many scenes to keep: you mark them after the candidates are written, and the tally is computed from that selection.

## Requirements

- [Cursor](https://cursor.com) with agent mode, in the project where you want to build a bank.
- Python 3.10 or later. The scripts need PyYAML, listed in `requirements.txt`.

## Install

1. Unzip the download into your project so that the skill folder sits at `.cursor/skills/multiple-choice-questions/`. The zip's top folder is `multiple-choice-questions/`, so unzip it inside `.cursor/skills/`.
2. Create a virtual environment at your project root, once, and install the requirements:

```bash
py -3 -m venv .venv
.venv/Scripts/python.exe -m pip install -r .cursor/skills/multiple-choice-questions/requirements.txt
```

On macOS or Linux the interpreter is `.venv/bin/python`. Keep `.venv` out of version control.

## How to run

1. Copy `examples/input file design.yaml` and fill it in. Informal notes are fine. You can also open `examples/input-form.html` in a browser to write the file.
2. In Cursor chat, ask to run the multiple-choice question workflow on that file.
3. Confirm the edited input, the correct-answer rule, and the variation value lists. Scene generation does not start before that confirmation.
4. When the candidates are ready, mark which scenes to keep. The tally, figures, samples, and YAML export follow that choice.

The sidecar is `INPUT.mcq.yaml` next to the input. If it already exists, the workflow asks before replacing it.

## Input files

- `examples/input file design.yaml`: the input template.
- `examples/circular-motion-sample-input.yaml`: a filled example.
- `examples/input-form.html`: a form that writes an input file.

## Version

Form version 0.1.0 of agent version 0.1.0. See the [agent changelog](https://github.com/Zhongzhou/isomorphic-bank-creation-skills/blob/main/agents/multiple-choice/CHANGELOG.md).

## Authors

- Zhongzhou Chen (author)

## License

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). See `LICENSE` in the [repository](https://github.com/Zhongzhou/isomorphic-bank-creation-skills).
