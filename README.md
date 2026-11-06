# Isomorphic problem-bank agents

This repository is an open catalog of AI agents that generate isomorphic physics problem banks: collections of problems that test the same learning objectives, with variations that change the solution and not only the numbers. It also holds the PHY I Mechanics banks as worked examples of the bank format.

**Browse and download the agents at <https://zhongzhou.github.io/isomorphic_problem_creation_agents/>.** Agents are downloaded and installed in your own project. They are not installed in this repository, and the site does not run them.

## Agents

| Agent | Status | Forms |
| --- | --- | --- |
| [Conceptual multiple-choice questions](agents/multiple-choice/) | published, 0.1.0 | Cursor skill |
| [Numerical calculation problems](agents/numerical-calculation/) | under construction, not offered for download | Cursor skill |

Each agent lives in one folder:

```text
agents/<id>/
  agent.yaml        # title, summary, version, status, authors, forms, samples
  README.md         # the body of the agent's page on the site
  CHANGELOG.md
  examples/         # input templates and filled examples; shipped in every zip
  design/           # design notes; not shipped
  samples/          # optional small generated banks
  forms/<form>/     # one folder per form: cursor, codex, chatgpt or gui
    README.md       # the unified form README (front matter + fixed sections)
    ...             # the skill or app itself
```

`status` in `agent.yaml` decides publication. `active` and `deprecated` agents get a card, a page and a download. `draft` agents stay in the repository and are only named on the site under "Under construction".

## Versioning

Every agent and every form uses [semantic versions](https://semver.org), `MAJOR.MINOR.PATCH`:

- **MAJOR**: an existing input file no longer runs, or a workflow step changes meaning.
- **MINOR**: a new form, a new optional input field, or another backward-compatible capability.
- **PATCH**: prompt, script or documentation fixes that leave inputs and outputs compatible.

The agent version and each form's version live only in `agent.yaml`. A form version may lag the agent version. A form with the same MAJOR as its agent reads that agent's current input files. Each form README repeats `version` and `agent_version` in its front matter, and `CHANGELOG.md` has a `## [x.y.z] - YYYY-MM-DD` heading ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/)) for the current version. `scripts/check_catalog.py` fails the build when any of these drift.

The site always offers the version on `main`. To keep a downloadable copy of a release, push a tag: `multiple-choice/v0.1.0` for an agent release, or `multiple-choice-cursor/v0.1.0` for one form. The workflow attaches the zips to a GitHub Release. Draft agents get no Release.

## Adding or updating an agent

1. Copy an existing agent folder's shape into `agents/<new-id>/` and fill in `agent.yaml`. Start with `status: draft`.
2. Give every form a `README.md` with the shared front matter (`agent`, `form`, `version`, `agent_version`, `authors`, `license`, `updated`) and sections: what this form is, requirements, install, how to run, input files, version, authors, license.
3. Bump the version in `agent.yaml`, the form README front matter, and `CHANGELOG.md`.
4. Check and preview locally:

```bash
python -m pip install -r scripts/requirements.txt
python scripts/check_catalog.py
python scripts/build_site.py          # packages the zips and writes _site/
python -m http.server -d _site        # then open http://localhost:8000
```

5. Set `status: active` when the agent is ready to download, and push to `main`. GitHub Actions checks the catalog, packages the zips, and deploys the site.

To work on a skill inside this clone, `python scripts/install_local.py multiple-choice` copies its Cursor form to `.cursor/skills/multiple-choice-questions/`, which git ignores.

## Problem banks

[PHY I Mechanics](./PHY%20I%20Mechanics/) is organized by unit. [Topics.csv](./PHY%20I%20Mechanics/Topics.csv) lists the topics typically included in the course. The banks were developed with generative-AI assistance and are split out from [ESTELA-physics-problem-bank](https://github.com/Zhongzhou/ESTELA-physics-problem-bank), which keeps the exam builder.

Each unit folder contains one or more problem-bank folders. A bank folder usually contains:

* A YAML file (`.yml` or `.yaml`) with the problems and bank metadata.
* A QTI `.zip` that can be imported into a Canvas New Quiz item bank.
* Optional figure or image archives, and optional folders of drafts, scripts, or older versions.

Banks, YAML files, and QTI packages use this name:

```text
Subject-Unit-Abbreviation_of_title-mmddyy
```

For example, `PHY1-F-1DKINT-091525` is Physics 1, Forces, 1D kinematics with non-constant acceleration, created on 09-15-2025. Some earlier folders still use older names. [Templates](./Templates/) has the bank YAML templates.

## License

[LICENSE](./LICENSE) is the Creative Commons Attribution-NonCommercial 4.0 International license text carried over with the problem banks. The license for this repository will be revised later.
