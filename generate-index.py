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
    title, summary, name = e(a["title"]), e(a["summary"]), e(a["name"])
    if a["status"] == "live":
        badge = f'<span class="count">{e(str(a["version"]))}</span>'
        link = f'<a class="open" href="https://{e(a["host"])}/">Open {e(a["host"])}</a>'
    else:
        badge = '<span class="chip neutral">coming soon</span>'
        link = f'<span class="meta">{e(a["host"])}</span>'
    return f"""      <section class="card app {e(a["status"])}" data-tc-arrange-item="app-{name}" data-tc-collapse="app-{name}" aria-labelledby="app-{name}-h">
        <header>
          <span class="grip" data-tc-arrange-handle tabindex="0" role="button" aria-label="Reorder {title}" title="Drag to reorder">&#10303;</span>
          <h2 id="app-{name}-h" data-tc-collapse-toggle>{title}</h2>
          {badge}
        </header>
        <div class="body" data-tc-collapse-body>
          <p>{summary}</p>
          <p>{link}</p>
        </div>
      </section>"""


def render(apps):
    cards = "\n".join(card(a) for a in apps)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>tcos.app</title>
  <meta name="description" content="Small, open apps from Twin Cities Open Systems.">
  <link rel="canonical" href="https://tcos.app/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="tcos.app">
  <meta property="og:title" content="tcos.app">
  <meta property="og:description" content="Small, open apps from Twin Cities Open Systems.">
  <meta property="og:url" content="https://tcos.app/">
  <meta property="og:locale" content="en_US">
  <meta property="og:image" content="https://tcos.app/og.jpg">
  <meta property="og:image:type" content="image/jpeg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="tcos.app: small, open apps from Twin Cities Open Systems">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="tcos.app">
  <meta name="twitter:description" content="Small, open apps from Twin Cities Open Systems.">
  <meta name="twitter:image" content="https://tcos.app/og.jpg">
  <link rel="stylesheet" href="/css/shell.css">
  <link rel="stylesheet" href="/css/site.css">
  <script>(function(){{var d=document.documentElement;
try{{d.setAttribute("data-fs",localStorage.getItem("tc-fs")||"m");
var t=localStorage.getItem("tc-theme");if(t&&t!=="auto")d.setAttribute("data-theme",t);}}catch(e){{d.setAttribute("data-fs","m");}}}})();</script>
</head>
<body>
<header class="top">
  <span class="brand"><a href="/">tcos.app</a></span>
  <nav aria-label="Main"><a href="/" aria-current="page">Apps</a><a class="ext" href="https://github.com/Twin-Cities-Open-Systems/tcos-app" target="_blank" rel="noopener">Source</a></nav>
  <div class="fontsize-toggle"><span class="fs-label">Aa</span>
    <button class="fontsize-btn" data-size="s"  type="button" aria-pressed="false">S</button>
    <button class="fontsize-btn" data-size="m"  type="button" aria-pressed="true">M</button>
    <button class="fontsize-btn" data-size="l"  type="button" aria-pressed="false">L</button>
    <button class="fontsize-btn" data-size="xl" type="button" aria-pressed="false">XL</button>
    <button class="fontsize-btn" data-size="xxl" type="button" aria-pressed="false">XXL</button>
  </div>
  <div class="theme-toggle">
    <button class="theme-btn" data-theme-choice="light" type="button" aria-pressed="false">Light</button>
    <button class="theme-btn" data-theme-choice="dark"  type="button" aria-pressed="false">Dark</button>
    <button class="theme-btn" data-theme-choice="auto"  type="button" aria-pressed="true">Auto</button>
  </div>
</header>

<main class="wrap">
  <div>
    <h1>tcos.app</h1>
    <p class="lede">Small, open apps from Twin Cities Open Systems.</p>
  </div>
  <div class="cards" data-tc-arrange="apps">
{cards}
  </div>
</main>
<footer class="wrap">
  <p><a href="https://github.com/Twin-Cities-Open-Systems/tcos-app">Source</a></p>
</footer>
<script src="/js/shell.js"></script>
<script src="/js/links.js" defer></script>
<script src="/js/collapse.js" defer></script>
<script src="/js/arrange.js" defer></script>
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
