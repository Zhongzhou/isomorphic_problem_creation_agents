"""Check the agent catalog before anything is packaged or published.

    python scripts/check_catalog.py

Reads agents/<id>/agent.yaml for every agent folder and fails (exit 1) when:
  - agent.yaml is missing a required field, or its id is not the folder name
  - status is missing or not one of draft, active, deprecated
  - the agent version or a form version is not MAJOR.MINOR.PATCH
  - a listed form has no forms/<id>/ directory, or a forms/ directory is not listed
  - a form README's front matter version or agent_version disagrees with agent.yaml
  - CHANGELOG.md has no heading for the current agent version
  - a sample path does not exist

The other scripts import load_catalog() from here, so they all read the catalog the same way.
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
STATUSES = ("draft", "active", "deprecated")
PUBLISHED = ("active", "deprecated")
FORM_IDS = ("cursor", "codex", "chatgpt", "gui")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
REQUIRED = ("id", "title", "summary", "problem_type", "version", "status", "authors",
            "license", "forms")


def front_matter(path):
    """The YAML front matter of a markdown file, or {} if it has none."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    return (yaml.safe_load(match.group(1)) or {}) if match else {}


def sample_path(agent_dir, path):
    """A sample path is relative to the agent folder, or else to the repository root."""
    for base in (agent_dir, ROOT):
        if (base / path).exists():
            return base / path
    return None


def load_catalog():
    """Every agent as a dict from its agent.yaml, plus 'dir', sorted by id."""
    agents = []
    for path in sorted(AGENTS.glob("*/agent.yaml")):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data["dir"] = path.parent
        agents.append(data)
    return sorted(agents, key=lambda a: str(a.get("id", "")))


def published(agents):
    return [a for a in agents if a.get("status") in PUBLISHED]


def problems(agent):
    """Everything wrong with one agent, as sentences."""
    out = []
    where = agent["dir"].relative_to(ROOT).as_posix()
    for field in REQUIRED:
        if not agent.get(field):
            out.append(f"{where}/agent.yaml: '{field}' is missing")
    if agent.get("id") and agent["id"] != agent["dir"].name:
        out.append(f"{where}/agent.yaml: id '{agent['id']}' is not the folder name")
    if agent.get("status") not in STATUSES:
        out.append(f"{where}/agent.yaml: status must be one of {', '.join(STATUSES)}")
    version = str(agent.get("version", ""))
    if not SEMVER.match(version):
        out.append(f"{where}/agent.yaml: version '{version}' is not MAJOR.MINOR.PATCH")

    listed = set()
    for form in agent.get("forms") or []:
        fid = form.get("id")
        listed.add(fid)
        if fid not in FORM_IDS:
            out.append(f"{where}: form id '{fid}' is not one of {', '.join(FORM_IDS)}")
        if not SEMVER.match(str(form.get("version", ""))):
            out.append(f"{where}: form '{fid}' version '{form.get('version')}' is not "
                       f"MAJOR.MINOR.PATCH")
        if fid == "cursor" and not form.get("install_name"):
            out.append(f"{where}: form 'cursor' needs an install_name")
        form_dir = agent["dir"] / "forms" / str(fid)
        if not form_dir.is_dir():
            out.append(f"{where}: form '{fid}' is listed but forms/{fid}/ does not exist")
            continue
        readme = form_dir / "README.md"
        if not readme.exists():
            out.append(f"{where}/forms/{fid}: README.md is missing")
            continue
        meta = front_matter(readme)
        if str(meta.get("version")) != str(form.get("version")):
            out.append(f"{where}/forms/{fid}/README.md: version {meta.get('version')} does "
                       f"not match agent.yaml ({form.get('version')})")
        if str(meta.get("agent_version")) != version:
            out.append(f"{where}/forms/{fid}/README.md: agent_version "
                       f"{meta.get('agent_version')} does not match agent.yaml ({version})")
        if meta.get("agent") != agent.get("id") or meta.get("form") != fid:
            out.append(f"{where}/forms/{fid}/README.md: front matter must name agent "
                       f"'{agent.get('id')}' and form '{fid}'")
    if (agent["dir"] / "forms").is_dir():
        for d in sorted((agent["dir"] / "forms").iterdir()):
            if d.is_dir() and d.name not in listed:
                out.append(f"{where}: forms/{d.name}/ exists but is not listed in agent.yaml")

    changelog = agent["dir"] / "CHANGELOG.md"
    if not changelog.exists():
        out.append(f"{where}: CHANGELOG.md is missing")
    elif not re.search(rf"^## \[{re.escape(version)}\]", changelog.read_text(encoding="utf-8"),
                       re.M):
        out.append(f"{where}/CHANGELOG.md: no '## [{version}]' heading")
    if not (agent["dir"] / "README.md").exists():
        out.append(f"{where}: README.md is missing")
    for sample in agent.get("samples") or []:
        if not sample_path(agent["dir"], sample.get("path", "")):
            out.append(f"{where}: sample '{sample.get('path')}' does not exist")
    return out


def main():
    agents = load_catalog()
    if not agents:
        print("no agents found under agents/", file=sys.stderr)
        return 1
    found = [p for a in agents for p in problems(a)]
    for p in found:
        print(p, file=sys.stderr)
    if found:
        return 1
    for a in agents:
        print(f"{a['id']} {a['version']} {a['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
