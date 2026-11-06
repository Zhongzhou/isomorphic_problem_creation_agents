"""Build the static catalog site into _site/ from agents/*/agent.yaml and README.md.

    python scripts/build_site.py [--out _site] [--dist dist]

Pages:
  index.html               every active or deprecated agent as a card; draft agents are
                           named under "Under construction" with no link
  agents/<id>/index.html   the agent README, a downloads panel built from agent.yaml,
                           samples, and the current changelog section (published agents only)
  downloads/*.zip          the current zip of every published form, from dist/ (packaged
                           here when dist/ does not have it)

Links to files in the repository go to GitHub. The repository comes from GITHUB_REPOSITORY
in GitHub Actions, or from `git remote get-url origin` locally; the branch from SITE_BRANCH
(default main). Preview: python -m http.server -d _site
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import markdown

from check_catalog import ROOT, load_catalog, problems, published, sample_path
from package_forms import package, zip_name

STYLE = """\
:root {
  color-scheme: light;
  --paper: #fffcf7; --ink: #1c1915; --muted: #5c564e; --line: #d9d3c8; --accent: #1f4b3a;
  --tint: #f4efe6;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--paper); color: var(--ink);
  font: 16px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
.wrap { max-width: 52rem; margin: 0 auto; padding: 0 16px; }
a { color: var(--accent); text-underline-offset: 2px; }
a:focus-visible, .button:focus-visible {
  outline: 3px solid var(--accent); outline-offset: 2px; border-radius: 4px;
}
header.site { border-bottom: 1px solid var(--line); }
header.site .wrap {
  display: flex; justify-content: space-between; align-items: center; gap: 16px;
  min-height: 64px; flex-wrap: wrap;
}
header.site .name { font-weight: 650; color: var(--ink); text-decoration: none; }
main { padding: 32px 0 48px; }
h1 { font-size: 2rem; line-height: 1.2; margin: 0 0 12px; letter-spacing: -0.01em; }
h2 { font-size: 1.3rem; margin: 40px 0 12px; }
h3 { font-size: 1.1rem; margin: 28px 0 8px; }
h4 { font-size: 1rem; margin: 20px 0 6px; }
.lede { font-size: 1.125rem; color: var(--muted); margin: 0 0 8px; }
.muted { color: var(--muted); }
.card {
  border: 1px solid var(--line); border-radius: 8px; padding: 20px; margin: 16px 0;
  background: #fff;
}
.card h3 { margin: 0 0 4px; font-size: 1.2rem; }
.card p { margin: 8px 0; }
.meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; color: var(--muted);
  font-size: 0.95rem; }
.chip { display: inline-block; border: 1px solid var(--line); border-radius: 999px;
  padding: 2px 10px; font-size: 0.875rem; color: var(--ink); background: var(--tint); }
.chip.warn { border-color: #8a5a00; color: #6b4600; background: #fff4dc; }
.button {
  display: inline-flex; align-items: center; min-height: 44px; padding: 0 18px;
  border-radius: 6px; background: var(--accent); color: #fff; text-decoration: none;
  font-weight: 600;
}
.button:hover { background: #173a2d; }
.drafts { list-style: none; padding: 0; margin: 0; }
.drafts li { border-top: 1px solid var(--line); padding: 12px 0; }
.downloads .row { display: flex; flex-wrap: wrap; justify-content: space-between;
  align-items: center; gap: 12px; border-top: 1px solid var(--line); padding: 16px 0; }
.downloads .row:first-of-type { border-top: 0; }
code { font: 0.92em ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--tint); padding: 1px 4px; border-radius: 4px; overflow-wrap: anywhere; }
pre { background: var(--tint); border: 1px solid var(--line); border-radius: 6px;
  padding: 12px 14px; overflow-x: auto; line-height: 1.45; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: 6px 10px; text-align: left; }
footer.site { border-top: 1px solid var(--line); padding: 20px 0 32px; color: var(--muted);
  font-size: 0.95rem; }
"""


def repo_slug():
    slug = os.environ.get("GITHUB_REPOSITORY")
    if slug:
        return slug
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, text=True,
                             capture_output=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "Zhongzhou/isomorphic-bank-creation-skills"
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    return m.group(1) if m else "Zhongzhou/isomorphic-bank-creation-skills"


class Links:
    def __init__(self, slug, branch):
        self.repo = f"https://github.com/{slug}"
        self.branch = branch

    def file(self, path):
        """A repository path (relative to the root) on GitHub, as a folder or a file."""
        kind = "tree" if (ROOT / path).is_dir() else "blob"
        return f"{self.repo}/{kind}/{self.branch}/{quote(Path(path).as_posix())}"


def esc(text):
    return html.escape(str(text), quote=True)


def page(title, body, depth, links, description=""):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<header class="site"><div class="wrap">
<a class="name" href="{up or './'}">Isomorphic problem-bank agents</a>
<a href="{links.repo}">GitHub repository</a>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
<p>Licensed under <a href="{links.file('LICENSE')}">CC BY-NC 4.0</a>. Sample problem banks
illustrate the bank format.</p>
</div></footer>
</body>
</html>
"""


def authors(agent, linked):
    names = []
    for a in agent.get("authors") or []:
        name = esc(a.get("name", ""))
        names.append(f'<a href="{esc(a["url"])}">{name}</a>' if linked and a.get("url")
                     else name)
    return ", ".join(names)


def render_markdown(text, agent_dir, links):
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.S)
    text = re.sub(r"\A\s*# .*\n", "", text)          # the page header already has the title
    out = markdown.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])

    def fix(m):                                        # relative links go to GitHub
        href = html.unescape(m.group(2))
        if re.match(r"^(?:[a-z]+:|#|/)", href):
            return m.group(0)
        target = (agent_dir / href.split("#")[0]).resolve()
        if ROOT not in target.parents and target != ROOT:
            return m.group(0)
        return f'{m.group(1)}"{esc(links.file(target.relative_to(ROOT)))}"'
    return re.sub(r'(<a href=)"([^"]*)"', fix, out)


def changelog_section(agent):
    text = (agent["dir"] / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## \[{re.escape(str(agent['version']))}\].*?(?=^## \[|\Z)", text,
                  re.M | re.S)
    if not m:
        return ""
    section = re.sub(r"^(#{2,5}) ", lambda h: "#" + h.group(1) + " ", m.group(0), flags=re.M)
    return markdown.markdown(section, extensions=["sane_lists"])


def home(agents, links):
    cards = []
    for a in published(agents):
        chips = "".join(f'<span class="chip">{esc(f["title"])}</span>' for f in a["forms"])
        if a["status"] == "deprecated":
            chips += '<span class="chip warn">Deprecated</span>'
        cards.append(f"""<article class="card">
<h3>{esc(a['title'])}</h3>
<div class="meta"><span>Version {esc(a['version'])}</span>{chips}</div>
<p>{esc(a['summary'])}</p>
<p class="muted">By {authors(a, linked=False)}</p>
<a class="button" href="agents/{quote(a['id'])}/">View and download</a>
</article>""")
    drafts = [a for a in agents if a.get("status") == "draft"]
    body = ["""<h1>Isomorphic problem-bank agents</h1>
<p class="lede">An open repository of AI agents that generate isomorphic physics problem
banks: sets of problems that test the same learning objective, with variations that change
the solution and not only the numbers.</p>
<p class="muted">Each agent is downloaded and installed in your own project. This site does
not run them.</p>""",
            "<h2>Agents</h2>",
            "\n".join(cards) or '<p class="muted">No agent is published yet.</p>']
    if drafts:
        body.append("<h2>Under construction</h2>\n<ul class=\"drafts\">" + "".join(
            f"<li><strong>{esc(a['title'])}</strong> <span class=\"chip\">Draft</span>"
            f"<br><span class=\"muted\">{esc(a['summary'])}</span></li>" for a in drafts)
            + "</ul>")
    body.append(f"""<h2>Problem bank format</h2>
<p>Banks, their YAML files and QTI packages are named
<code>Subject-Unit-Abbreviation_of_title-mmddyy</code>, for example
<code>PHY1-F-1DKINT-091525</code>. The <a href="{links.file('PHY I Mechanics')}">PHY I
Mechanics banks</a> are the worked examples of the format, and
<a href="{links.file('PHY I Mechanics/Topics.csv')}">Topics.csv</a> lists the course
topics.</p>""")
    return page("Isomorphic problem-bank agents", "\n".join(body), 0, links,
                "AI agents that generate isomorphic physics problem banks.")


def agent_page(agent, links):
    status = (' <span class="chip warn">Deprecated</span>'
              if agent["status"] == "deprecated" else "")
    rows = []
    for form in agent["forms"]:
        where = (f"<code>.cursor/skills/{esc(form['install_name'])}/</code>"
                 if form["id"] == "cursor" else "")
        rows.append(f"""<div class="row">
<div><strong>{esc(form['title'])}</strong> <span class="muted">version {esc(form['version'])}</span>
{f'<br><span class="muted">Install at</span> {where}' if where else ''}</div>
<a class="button" href="../../downloads/{quote(zip_name(agent, form))}" download>Download
{esc(form['title'])} {esc(form['version'])} (.zip)</a>
</div>""")
    samples = agent.get("samples") or []
    sample_html = ("<ul>" + "".join(
        f'<li><a href="{esc(links.file(sample_path(agent["dir"], s["path"]).relative_to(ROOT)))}">'
        f'{esc(s.get("title") or s["path"])}</a> <span class="muted">'
        f'<code>{esc(Path(s["path"]).name)}</code></span></li>' for s in samples) + "</ul>"
        if samples else '<p class="muted">A sample bank has not been added yet.</p>')
    readme = render_markdown((agent["dir"] / "README.md").read_text(encoding="utf-8"),
                             agent["dir"], links)
    changelog = agent["dir"].relative_to(ROOT) / "CHANGELOG.md"
    body = f"""<h1>{esc(agent['title'])}</h1>
<div class="meta"><span>Version {esc(agent['version'])}</span>{status}
<span>By {authors(agent, linked=True)}</span></div>
<section class="card downloads" aria-labelledby="downloads">
<h2 id="downloads" style="margin-top:0">Download</h2>
{''.join(rows)}
<p class="muted">Unzip into your project so the skill folder sits at the install path, then
ask the platform's agent to run the workflow. Each zip has a README with the full steps.
<a href="{links.repo}/releases">Older versions</a></p>
</section>
{readme}
<h2>Samples</h2>
{sample_html}
<h2>Changelog</h2>
{changelog_section(agent)}
<p><a href="{esc(links.file(changelog))}">Full changelog</a></p>"""
    return page(f"{agent['title']} {agent['version']}", body, 2, links, agent["summary"])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(ROOT / "_site"))
    p.add_argument("--dist", default=str(ROOT / "dist"))
    args = p.parse_args(argv)
    agents = load_catalog()
    bad = [x for a in agents for x in problems(a)]
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    links = Links(repo_slug(), os.environ.get("SITE_BRANCH", "main"))
    out, dist = Path(args.out), Path(args.dist)
    if out.exists():
        shutil.rmtree(out)
    (out / "downloads").mkdir(parents=True)
    (out / "style.css").write_text(STYLE, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "index.html").write_text(home(agents, links), encoding="utf-8")
    for agent in published(agents):
        target = out / "agents" / agent["id"]
        target.mkdir(parents=True)
        (target / "index.html").write_text(agent_page(agent, links), encoding="utf-8")
        for form in agent["forms"]:
            built = dist / zip_name(agent, form)
            if not built.exists():
                dist.mkdir(parents=True, exist_ok=True)
                built = package(agent, form, dist)
            shutil.copy2(built, out / "downloads" / built.name)
    print(f"{out}: {len(published(agents))} agent page(s), "
          f"{sum(1 for _ in (out / 'downloads').iterdir())} download(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
