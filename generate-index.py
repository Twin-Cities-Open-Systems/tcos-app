#!/usr/bin/env python3
"""Regenerate index.html from apps.yaml.

The output is deterministic (no timestamps, no commit hash), so a rebuild on
any commit reproduces the committed page byte for byte -- what `hee release
-promote` relies on.

Usage: python3 generate-index.py [--check]
  --check   exit 2 if index.html is not what apps.yaml generates
"""
import html
import pathlib
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
STATUSES = {"planned", "live"}
REQUIRED = ("name", "title", "host", "repo", "summary", "status")


def load(path):
    apps = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("apps") or []
    seen = set()
    for a in apps:
        missing = [k for k in REQUIRED if not a.get(k)]
        if missing:
            sys.exit(f"CRITICAL apps.yaml: {a.get('name', '?')} lacks {', '.join(missing)}")
        if a["status"] not in STATUSES:
            sys.exit(f"CRITICAL apps.yaml: {a['name']} status {a['status']!r} is not one of {sorted(STATUSES)}")
        if a["status"] == "live" and not a.get("version"):
            sys.exit(f"CRITICAL apps.yaml: {a['name']} is live but has no version")
        if not a["host"].endswith(".tcos.app"):
            sys.exit(f"CRITICAL apps.yaml: {a['name']} host {a['host']!r} is not under tcos.app")
        if a["name"] in seen:
            sys.exit(f"CRITICAL apps.yaml: duplicate app {a['name']}")
        seen.add(a["name"])
    return apps


def card(a):
    e = html.escape
    title, summary = e(a["title"]), e(a["summary"])
    if a["status"] == "live":
        head = f'<a href="https://{e(a["host"])}/">{title}</a>'
        meta = f'{e(a["host"])} &middot; {e(str(a["version"]))}'
    else:
        head = title
        meta = f'{e(a["host"])} &middot; coming soon'
    return (f'    <li class="app {e(a["status"])}"><h2>{head}</h2>\n'
            f'      <p>{summary}</p>\n      <p class="meta">{meta}</p></li>')


def render(apps):
    cards = "\n".join(card(a) for a in apps)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>tcos.app</title>
  <meta name="description" content="Small, open apps from Twin Cities Open Systems.">
  <link rel="stylesheet" href="/css/site.css">
</head>
<body>
  <main>
    <h1>tcos.app</h1>
    <p>Small, open apps from Twin Cities Open Systems.</p>
    <ul class="apps">
{cards}
    </ul>
  </main>
  <footer>
    <p><a href="https://github.com/Twin-Cities-Open-Systems/tcos-app">Source</a></p>
  </footer>
</body>
</html>
"""


def main(argv):
    out = HERE / "index.html"
    text = render(load(HERE / "apps.yaml"))
    if "--check" in argv:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print("CRITICAL index.html is not what apps.yaml generates -- run python3 generate-index.py", file=sys.stderr)
            return 2
        return 0
    out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
