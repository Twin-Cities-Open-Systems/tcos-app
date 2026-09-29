# tcos-app

Org governance is canonical in `human-execution-engine`'s
`prompts/PROMPTING_RULES.md`. It is delivered to every session by the
`SessionStart` hook installed from the `dotfiles` repo:

    make claude-hooks

It is deliberately **not** `@import`-ed here. Measured 2026-08-31, with
sentinel strings probed from real sessions:

| mechanism | resolves? |
|---|---|
| `@import` whose path is inside this repo | yes |
| `@import` whose path resolves outside this repo | **no** |
| `.claude/rules/` symlink pointing outside this repo | **no** |
| `@https://` or `@http://` URL | **no** |
| `SessionStart` hook | yes |

All three failures are **silent** -- they look like they worked. So an
import line here would be decoration, not delivery.

The hook also carries no assumption about where your checkouts live. It
honours `HEE_REPO_DIR`, so an operator using `~/projects/` or anything
else works without editing a repo.

If the org rules are not in `/context`, the hook is not installed.

`tcos-app` is generated: `index.html` comes from `apps.yaml` via
`python3 generate-index.py`. Edit the registry, regenerate, commit both. Release
only through `hee release -lab | -cut | -promote`.

## The shared shell, and how a child app inherits it

`tcos-app` owns the look and the behavior every `*.tcos.app` app shares. The files
are listed once, in `shell.manifest`:

| file | what it is |
|---|---|
| `css/shell.css` | tokens, light/dark/auto themes, text sizes, cards, controls, chips, collapse/arrange/table/freshness styles, print. Derived from `fleet-ops/view/assets/view.css` minus the operator-only parts |
| `js/shell.js` | the text-size and theme toggles (storage-guarded) |
| `js/collapse.js` `arrange.js` `table.js` `links.js` `freshness.js` | copies of `human-execution-engine/library/js`, byte for byte (`tests/test_shell.py` fails when they drift, where an HEE checkout exists) |

`hovercard.js` is not in the shell: it calls `api.github.com`, and a public app is
same-origin only. Edit these here, never in a child.

A child inherits by **copying** the files at the same relative paths and serving
them from its own origin (no cross-host `<script src>`; the lab has no egress
guarantee). The child's `sync-shell.sh` copies the manifest from a tcos-app
checkout and `--check` fails when any copy differs, which is what the child's CI
runs against tcos-app `main`. Merge tcos-app first, then sync the child.

Markup contract for a page (see `index.html`): the head bootstrap that sets
`data-fs`/`data-theme` before paint, the `.top` header with the font-size and
theme buttons, and cards as `<section class="card" data-tc-collapse="ID">` with a
`<h2 data-tc-collapse-toggle>` and a `<div class="body" data-tc-collapse-body>`.
Cards built by script call `TC.collapse.init(container)` after inserting them.
