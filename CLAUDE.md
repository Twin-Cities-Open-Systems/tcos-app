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

## tcos-app is the home of every TCOS web page

Operator, 2026-10-01: tcos-app is the org's **primary go-to for all things web
page**. It holds, and will keep gaining, the widgets, tools and resources every
page shares. A UI/UX improvement made for one site lands **here first**, then
reaches the others by sync; it is never re-derived in a child. That covers more
than `*.tcos.app`:

| child | served at | repo | how it takes the shell |
|---|---|---|---|
| ham | `ham.tcos.app` | `ham-tcos-app` | `sync-shell.sh`, committed copy, CI `--check` |
| tcos.app itself | `tcos.app` | this repo | owner |
| view.lab | `view.lab.tcos.us` | `fleet-ops` (`view/`) | `view/build.sh` copies `css/shell.css` + `js/shell.js` at build time; `view.css` imports it |
| mf.lab, store.lab | `mf.lab.tcos.us`, `store.lab.tcos.us` | `fleet-ops` (`tools/*/web`) | their `build.sh` copies `view.css` + `shell.css` |
| tcos.us and its lab mirror | `tcos.us`, `lab.tcos.us` | `tcos-www` | `sync-shell.sh` (same as ham) |
| media hubs | `media.tcos.us`, `media.lab.tcos.us`, `<who>.media...` | `resume` | `sync-shell.sh` (same as ham) |

A new shared piece goes here when a second page could use it. A child that needs
the shell to behave differently asks for an opt-in attribute here (as
`data-tc-print="theme"` below) rather than overriding a token in its own CSS.

## The shared shell, and how a child inherits it

`tcos-app` owns the look and the behavior every TCOS web page shares. The files
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
| way back | `nav.tc-jump` with `[data-tc-to=group\|panel\|top]` buttons; `TC.wayback.init(nav, {scope, heading, groups, strip})`. Init adds a `[data-tc-to=here]` anchor (no markup): its href links the section being read, a plain click copies it and sets the address bar without scrolling; headings without an id get one from their text, in document order, at init |
| dock | `.tc-dock` (+ `.tc-dock-n`): a bar that rides the bottom edge while its section is on screen; the pill lifts above it |

Print is paper by default (white, black ink). A page whose own export promises
the screen's look sets `<html data-tc-print="theme">` and prints in the reader's
theme, dark included; view.lab's PDF button does.

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
