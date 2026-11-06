"""Write one self-contained zip per form of every published agent.

    python scripts/package_forms.py [--out dist]

For each agent whose status is active or deprecated, and each of its forms, writes
dist/<id>-<form>-<version>.zip. The archive root is the form's install name (for a Cursor
skill, the folder that goes in .cursor/skills/), and holds the form's files, the agent's
examples/ beside them, and LICENSE. Design notes, test caches and __pycache__ stay out.
Draft agents are skipped. The zips are reproducible: entries are sorted and dated
1980-01-01, so the same files give the same bytes.
"""

import argparse
import sys
import zipfile
from pathlib import Path

from check_catalog import ROOT, load_catalog, problems, published

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
EPOCH = (1980, 1, 1, 0, 0, 0)


def zip_name(agent, form):
    return f"{agent['id']}-{form['id']}-{form['version']}.zip"


def _files(folder):
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if path.is_file() and not SKIP_DIRS & set(rel.parts) \
                and path.suffix not in SKIP_SUFFIXES and path.name != ".DS_Store":
            yield path, rel


def _add(archive, path, name):
    info = zipfile.ZipInfo(name, EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, path.read_bytes())


def package(agent, form, out_dir):
    root = form.get("install_name") or f"{agent['id']}-{form['id']}"
    target = out_dir / zip_name(agent, form)
    entries = [(p, f"{root}/{rel.as_posix()}")
               for p, rel in _files(agent["dir"] / "forms" / form["id"])]
    examples = agent["dir"] / "examples"
    if examples.is_dir():
        entries += [(p, f"{root}/examples/{rel.as_posix()}") for p, rel in _files(examples)]
    if (ROOT / "LICENSE").exists():
        entries.append((ROOT / "LICENSE", f"{root}/LICENSE"))
    with zipfile.ZipFile(target, "w") as archive:
        for path, name in sorted(entries, key=lambda e: e[1]):
            _add(archive, path, name)
    return target


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(ROOT / "dist"))
    args = p.parse_args(argv)
    agents = load_catalog()
    bad = [x for a in agents for x in problems(a)]
    if bad:
        print("\n".join(bad), file=sys.stderr)
        print("fix the catalog first: python scripts/check_catalog.py", file=sys.stderr)
        return 1
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for agent in published(agents):
        for form in agent["forms"]:
            print(package(agent, form, out_dir).relative_to(out_dir.parent).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
