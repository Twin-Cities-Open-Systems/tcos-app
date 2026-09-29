# tcos-app

The base of the apps on [tcos.app](https://tcos.app): the registry of which apps
live there, the release procedure every app follows, and (as it grows) the shared
app shell, all built in the open with [`hee`](https://github.com/Twin-Cities-Open-Systems/human-execution-engine).

`apps.yaml` is the source of truth for what is on the domain. `index.html` is
generated from it and never edited by hand.

## Develop

    python3 generate-index.py            # apps.yaml -> index.html
    python3 generate-index.py --check    # what CI runs

Serve `.` with any static file server to preview.

## Release

Lab first, then the release PR, then promote. Each step is one `hee release` call
driven by `release.card.v1.yaml`:

    hee release -lab       # build and publish to the lab surface for review
    hee release -cut -yes  # release commit and PR; merging it is the sign-off
    hee release -promote -yes  # deploy tcos.app from the release commit, signed tag

## Add an app

1. Create the app's repo (`<name>-tcos-app`), releasing through the same card shape.
2. Add it to `apps.yaml` as `planned`, then `live` with its version once it ships.
3. Release this repo.

## License

GPL-3.0, see `LICENSE`.
