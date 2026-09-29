"""Contrast gate for the shared shell's color tokens, both themes.

Every pair the shell paints is listed once, with the target its role earns:
body text 7:1, UI text 4.5:1, borders and icons 3:1 (WCAG 2.x relative
luminance). The test fails under target; `python3 tests/test_contrast.py
--table` prints the same pairs as the markdown palette table for a PR body.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "css" / "shell.css").read_text()
BODY, UI, EDGE = 7.0, 4.5, 3.0
SKINS = {"paper": "light", "contrast": "light", "midnight": "dark", "graphite": "dark"}  # keep in step with KIND in js/shell.js

# (foreground, background, target, where it is used)
PAIRS = [
    ("ink", "bg", BODY, "body text on the page"),
    ("ink", "surface", BODY, "body text in a card"),
    ("ink", "sunk", BODY, "body text in a pill"),
    ("muted", "bg", BODY, "secondary text on the page"),
    ("muted", "surface", BODY, "secondary text in a card"),
    ("muted", "sunk", BODY, "secondary text in a pill"),
    ("accent", "bg", BODY, "link on the page"),
    ("accent", "surface", BODY, "link in a card"),
    ("accent", "sunk", BODY, "link in a pill"),
    ("accent", "accent-soft", UI, "nav link, hovered"),
    ("on-accent", "accent", BODY, "button label"),
    ("good-ink", "good-bg", BODY, "status chip: good"),
    ("warning-ink", "warning-bg", BODY, "status chip: warning"),
    ("serious-ink", "serious-bg", BODY, "status chip: serious"),
    ("critical-ink", "critical-bg", BODY, "status chip: critical"),
    ("good-ink", "surface", UI, "status figure: good"),
    ("critical-ink", "surface", UI, "status figure: critical"),
    ("edge", "bg", EDGE, "card border against the page"),
    ("edge", "surface", EDGE, "control border on a card"),
    ("edge", "sunk", EDGE, "pill border on a card"),
    ("accent", "bg", EDGE, "focus ring on the page"),
    ("accent", "surface", EDGE, "focus ring on a card"),
]


def tokens(block):
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{3,6})", block))


def block(pattern):
    m = re.search(pattern + r"\{(.*?)\n\s*\}|" + pattern + r"\{([^}]*)\}", CSS, re.DOTALL)
    return m.group(1) or m.group(2)


def themes():
    light = tokens(re.search(r"\n:root\{(.*?)\n\}", CSS, re.DOTALL).group(1))
    dark = dict(light)
    dark.update(tokens(re.search(r':root\[data-theme="dark"\]\{(.*?)\n\}', CSS, re.DOTALL).group(1)))
    system = tokens(re.search(r':root:not\(\[data-theme="light"\]\)\{(.*?)\n  \}', CSS, re.DOTALL).group(1))
    out = {"light": light, "dark": dark}
    for name, kind in SKINS.items():
        m = re.search(r':root\[data-skin="%s"\]\{(.*?)\n\}' % name, CSS, re.DOTALL)
        assert m, f"skin {name} missing from shell.css"
        out[name] = {**out[kind], **tokens(m.group(1))}
    return out, system


def lum(hexcolor):
    h = hexcolor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class Contrast(unittest.TestCase):
    def test_every_pair_meets_its_target_in_every_theme(self):
        by_theme, _ = themes()
        for name, t in by_theme.items():
            for fg, bg, target, use in PAIRS:
                r = ratio(t[fg], t[bg])
                self.assertGreaterEqual(r, target, f"{name}: {fg} on {bg} ({use}) is {r:.2f}, needs {target}")

    def test_js_kind_map_matches_skins(self):
        js = (ROOT / "js" / "shell.js").read_text()
        kind = dict(re.findall(r'(\w+): "(light|dark)"', re.search(r"var KIND = \{(.*?)\};", js).group(1)))
        self.assertEqual(kind, SKINS)

    def test_system_dark_matches_explicit_dark(self):
        by_theme, system = themes()
        for k, v in system.items():
            self.assertEqual(v, by_theme["dark"][k], f"--{k}: prefers-color-scheme block drifts from [data-theme=dark]")

    def test_no_pure_white_on_pure_black(self):
        by_theme, _ = themes()
        for name, t in by_theme.items():
            for k in ("bg", "surface", "ink"):
                self.assertNotIn(t[k].lower(), ("#fff", "#ffffff", "#000", "#000000"), f"{name}: --{k} is pure")

    def test_cards_are_lifted_from_the_page(self):
        by_theme, _ = themes()
        for name, t in by_theme.items():
            self.assertGreater(ratio(t["surface"], t["bg"]), 1.1, f"{name}: card vs page tone")
            self.assertGreater(ratio(t["edge"], t["bg"]), 3.0, f"{name}: card edge vs page")


def table():
    by_theme, _ = themes()
    print("| pair | use | target | light | dark |\n|---|---|---|---|---|")
    for fg, bg, target, use in PAIRS:
        print(f"| `{fg}` on `{bg}` | {use} | {target:g}:1 | {ratio(by_theme['light'][fg], by_theme['light'][bg]):.2f} | {ratio(by_theme['dark'][fg], by_theme['dark'][bg]):.2f} |")
    print("\n| token | light | dark |\n|---|---|---|")
    for k in sorted(by_theme["light"]):
        if k not in ("shadow", "fs"):
            print(f"| `--{k}` | `{by_theme['light'][k]}` | `{by_theme['dark'][k]}` |")


if __name__ == "__main__":
    if "--table" in sys.argv:
        table()
    else:
        unittest.main()
