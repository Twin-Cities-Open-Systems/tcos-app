import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = [ln.strip() for ln in (ROOT / "shell.manifest").read_text().splitlines() if ln.strip()]
HEE_JS = Path.home() / "git" / "human-execution-engine" / "library" / "js"
HEE_OWNED = ("collapse", "arrange", "table", "links", "freshness")


class Shell(unittest.TestCase):
    def test_manifest_is_the_shared_file_list(self):
        self.assertEqual(MANIFEST, [
            "css/shell.css", "js/shell.js", "js/collapse.js", "js/arrange.js",
            "js/table.js", "js/links.js", "js/freshness.js",
        ])

    def test_every_manifest_file_exists_and_ships(self):
        deploy = (ROOT / "deploy.sh").read_text()
        dirs = re.search(r"^ASSET_DIRS=\(([^)]*)\)", deploy, re.MULTILINE).group(1).split()
        for rel in MANIFEST:
            self.assertTrue((ROOT / rel).is_file(), rel)
            self.assertIn(rel.split("/")[0], dirs, f"{rel} is not under a shipped ASSET_DIRS entry")

    def test_index_uses_the_shell(self):
        page = (ROOT / "index.html").read_text()
        for rel in ("/css/shell.css", "/js/shell.js", "/js/collapse.js", "/js/arrange.js", "/js/links.js"):
            self.assertIn(f'"{rel}"', page)
        self.assertIn("data-tc-collapse-toggle", page)
        self.assertIn("data-tc-arrange-handle", page)
        self.assertIn("<title>tcos.app</title>", page)
        self.assertIn('property="og:image"', page)

    def test_page_loads_only_same_origin_assets(self):
        page = (ROOT / "index.html").read_text()
        urls = re.findall(r'<script[^>]+src="([^"]+)"', page) + re.findall(r'<link rel="stylesheet" href="([^"]+)"', page)
        self.assertTrue(urls)
        for url in urls:
            self.assertTrue(url.startswith("/"), url)

    def test_hee_components_match_their_source(self):
        if not HEE_JS.is_dir():
            self.skipTest("human-execution-engine checkout not present")
        for name in HEE_OWNED:
            self.assertEqual((ROOT / "js" / f"{name}.js").read_bytes(), (HEE_JS / f"{name}.js").read_bytes(), name)


if __name__ == "__main__":
    unittest.main()
