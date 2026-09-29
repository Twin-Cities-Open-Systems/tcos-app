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

A live app's version is never hand-typed: `version: latest` resolves to the highest
`prod/<repo>/vX.Y.Z` tag via `git ls-remote --tags` when the index is regenerated
(`./deploy.sh lab` does that). `--check` reads the versions already in the committed
page, so CI is offline; a newer tag only warns unless `TCOS_APP_STRICT_VERSIONS=1`.
`TCOS_APP_TAG_SOURCE` redirects the tag source, which is how `tests/test_versions.py`
runs against local bare repos. A regenerate that cannot read a tag refuses rather
than guessing.

## The shared shell, and how a child app inherits it

`tcos-app` owns the look and the behavior every `*.tcos.app` app shares. The files
are listed once, in `shell.manifest`:

| file | what it is |
|---|---|
| `css/shell.css` | tokens, light/dark/auto themes, text sizes, cards, controls, chips, collapse/arrange/table/freshness styles, print. Derived from `fleet-ops/view/assets/view.css` minus the operator-only parts |
| `js/shell.js` | the header (hamburger menu under 40rem, text-size and theme toggles, storage-guarded) and three reusable pieces, below |
| `js/collapse.js` `arrange.js` `table.js` `links.js` `freshness.js` | copies of `human-execution-engine/library/js`, byte for byte (`tests/test_shell.py` fails when they drift, where an HEE checkout exists) |

Three components live in the shell because any `*.tcos.app` app can use them; put a new
one here when a second app could, not in the app. Each is CSS in `shell.css` plus, where it
needs behavior, a small API in `shell.js` (no new files, so no payload list in any repo grows):

| component | markup and API |
|---|---|
| flip card | `.tc-flip[data-flipped]` > `.tc-flip-in` > `.tc-face.tc-front` + `.tc-face.tc-back`; `TC.flip.set/all`; `[data-tc-flip]` buttons and `[data-tc-flipall="back\|front"][data-target]` work with no page script; `.tc-fit` sizes a card to its visible face |
| way back | `nav.tc-jump` with `[data-tc-to=group\|panel\|top]` buttons; `TC.wayback.init(nav, {scope, heading, groups, strip})` |
| dock | `.tc-dock` (+ `.tc-dock-n`): a bar that rides the bottom edge while its section is on screen; the pill lifts above it |

`hovercard.js` is not in the shell: it calls `api.github.com`, and a public app is
same-origin only. Edit these here, never in a child.

Readability is a gated property of the shell, not a style preference. `css/shell.css`
carries the colour tokens (light, system-dark and explicit-dark, designed separately)
and `tests/test_contrast.py` computes the WCAG ratio of every token pair in both
themes: body text 7:1, UI text 4.5:1, borders and icons 3:1, cards lifted from the
page. `python3 tests/test_contrast.py --table` prints the palette. `--edge` is the
3:1 component boundary; `--rule` is a decorative hairline and must never carry meaning.
A child app that adds its own tokens adds its own pairs to a test like this one.

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
