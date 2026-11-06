"""Copy an agent's form into .cursor/skills/ of this clone, for development.

    python scripts/install_local.py multiple-choice [--form cursor] [--force]

The copy has the same layout as the download: the form's files, with the agent's examples/
beside them, at .cursor/skills/<install_name>/. That directory is git-ignored, so the copy
is never published. Draft agents can be installed this way too.
"""

import argparse
import shutil
import sys

from check_catalog import ROOT, load_catalog

IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("agent", help="agent id, the folder name under agents/")
    p.add_argument("--form", default="cursor")
    p.add_argument("--force", action="store_true", help="replace an existing copy")
    args = p.parse_args(argv)
    agent = next((a for a in load_catalog() if a.get("id") == args.agent), None)
    if agent is None:
        print(f"no agent '{args.agent}' under agents/", file=sys.stderr)
        return 1
    form = next((f for f in agent.get("forms") or [] if f.get("id") == args.form), None)
    if form is None or not form.get("install_name"):
        print(f"agent '{args.agent}' has no '{args.form}' form with an install_name",
              file=sys.stderr)
        return 1
    target = ROOT / ".cursor" / "skills" / form["install_name"]
    if target.exists():
        if not args.force:
            print(f"{target.relative_to(ROOT)} exists; pass --force to replace it",
                  file=sys.stderr)
            return 1
        shutil.rmtree(target)
    shutil.copytree(agent["dir"] / "forms" / args.form, target, ignore=IGNORE)
    if (agent["dir"] / "examples").is_dir():
        shutil.copytree(agent["dir"] / "examples", target / "examples", ignore=IGNORE)
    print(target.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
