#!/usr/bin/env python3
"""Redraw the language bar in the README from what is actually in my repos.

Counts bytes per language across every repo I own that is not a fork, then
rewrites assets/langs.svg and the block between the langs markers in README.md.
Run it with GITHUB_TOKEN set, or plain (unauthenticated) for a quick local check.
"""

import collections
import json
import os
import re
import sys
import urllib.error
import urllib.request

USER = "mason-cao"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_PATH = os.path.join(ROOT, "assets", "langs.svg")
README_PATH = os.path.join(ROOT, "README.md")
START, END = "<!-- langs:start -->", "<!-- langs:end -->"

W, H, GAP, R = 1000, 12, 5, 3
TOP_N = 5
COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178C6", "JavaScript": "#F1E05A",
    "CSS": "#663399", "HTML": "#E34C26", "Java": "#B07219", "C++": "#F34B7D",
    "C": "#555555", "Go": "#00ADD8", "Rust": "#DEA584", "Shell": "#89E051",
    "Jupyter Notebook": "#DA5B0B", "Swift": "#F05138", "Ruby": "#701516",
}
FALLBACK = "#7D8590"


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": f"{USER}-profile-langs"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    """Byte totals per language, skipping forks so I only count my own code."""
    totals, page, repos = collections.Counter(), 1, 0
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        for repo in batch:
            if repo["fork"]:
                continue
            repos += 1
            totals.update(api(f"/repos/{USER}/{repo['name']}/languages"))
        page += 1
    return totals, repos


def shares(totals):
    """Top languages as fractions, with everything else folded into Other."""
    grand = sum(totals.values())
    if not grand:
        sys.exit("no language bytes returned; refusing to write an empty bar")
    top = [(name, count / grand) for name, count in totals.most_common(TOP_N)]
    rest = 1 - sum(frac for _, frac in top)
    if rest > 0.001:
        top.append(("Other", rest))
    return top


def draw(parts):
    span = W - GAP * (len(parts) - 1)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}" role="img">',
           "<title>Language mix across my repositories</title>"]
    x = 0.0
    for name, frac in parts:
        width = max(6.0, span * frac)      # keep the smallest slice visible
        out.append(f'<rect x="{x:.1f}" y="0" width="{width:.1f}" height="{H}" '
                   f'rx="{R}" fill="{COLORS.get(name, FALLBACK)}"/>')
        x += width + GAP
    out.append("</svg>")
    return "\n".join(out) + "\n"


def block(parts, repo_count):
    named = [(n, f) for n, f in parts if n != "Other"]
    alt = ", ".join(f"{n} {f * 100:.0f} percent" for n, f in named)
    legend = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(
        f"{n.upper()} {f * 100:.0f}%" for n, f in named)
    return (
        f"{START}\n"
        f'<img src="assets/langs.svg" width="100%" alt="Language mix across '
        f'{repo_count} repositories: {alt}.">\n\n'
        f"<sub><samp>{legend}</samp></sub>\n"
        f"{END}"
    )


def main():
    try:
        totals, repo_count = collect()
    except urllib.error.HTTPError as err:
        sys.exit(f"GitHub API returned {err.code}: {err.reason}")
    except urllib.error.URLError as err:
        sys.exit(f"could not reach the GitHub API: {err.reason}")
    parts = shares(totals)

    with open(SVG_PATH, "w") as fh:
        fh.write(draw(parts))

    readme = open(README_PATH).read()
    pattern = re.compile(re.escape(START) + ".*?" + re.escape(END), re.S)
    if not pattern.search(readme):
        sys.exit(f"could not find the {START} ... {END} block in README.md")
    updated = pattern.sub(lambda _: block(parts, repo_count), readme)
    with open(README_PATH, "w") as fh:
        fh.write(updated)

    print(f"{repo_count} repos, {sum(totals.values()):,} bytes")
    for name, frac in parts:
        print(f"  {name:<18} {frac * 100:5.1f}%")


if __name__ == "__main__":
    main()
