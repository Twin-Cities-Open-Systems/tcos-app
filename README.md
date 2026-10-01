# tcos-app

The base of the apps on [tcos.app](https://tcos.app): the registry of which apps
live there, the release procedure every app follows, and (as it grows) the shared
app shell, all built in the open with [`hee`](https://github.com/Twin-Cities-Open-Systems/human-execution-engine).

`apps.yaml` is the source of truth for what is on the domain. `index.html` is
generated from it and never edited by hand.

## Develop

    python3 generate-index.py            # apps.yaml -> index.html
    python3 generate-index.py --check    # what CI runs (offline, deterministic)
    python3 -m unittest discover -s tests

A live app's version is not typed anywhere: `version: latest` in `apps.yaml` means
the highest `prod/<repo>/vX.Y.Z` tag on the app's repo. Regenerating reads the tags
(`./deploy.sh lab` does), so a child's release reaches the card on the next
regeneration with no edit. `--check` compares against the versions in the committed
page, so CI never depends on the network; a newer tag is a warning, and
`TCOS_APP_STRICT_VERSIONS=1` makes it an error. A literal `version: vX.Y.Z` pins.

Serve `.` with any static file server to preview.

## Release

Lab first, then the release PR, then promote. Each step is one `hee release` call
driven by `release.card.v1.yaml`:

    hee release -lab       # wait until the lab serves main (lab-pull installs it), for review
    hee release -cut -yes  # release commit and PR; merging it is the sign-off
    hee release -promote -yes  # deploy tcos.app from the release commit, signed tag

## Add an app

1. Create the app's repo (`<name>-tcos-app`), releasing through the same card shape.
2. Add it to `apps.yaml` as `planned`, then `live` (`version: latest`, taken from its prod tag) once it ships.
3. Release this repo.

## License

GPL-3.0, see `LICENSE`.

## Shared shell: the base of every TCOS web page

tcos-app is the org's primary home for web pages: the shell, the widgets and the
tools every TCOS page shares live here, and a UI improvement made for one site
lands here first. The children are the `*.tcos.app` apps, view.lab, the tcos.us
site and its lab mirror, and the media hubs (the table is in `CLAUDE.md`).

`shell.manifest` lists the CSS and JS a child inherits: the theme selector (auto,
light, dark and four named themes, every color pair measured to WCAG), the
text-size control, the small-screen menu, collapsible and re-arrangeable cards,
flip cards, the way-back pill that follows the reader down a long page, and the
dock. This repo owns them; a
child copies them at the same paths and checks for drift in its own CI. The recipe
is in `CLAUDE.md`, "The shared shell, and how a child app inherits it".
