import importlib.util
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("generate_index", ROOT / "generate-index.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def git(*args, cwd=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.org", GIT_CONFIG_GLOBAL="/dev/null")
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


def make_source(root, repo, tags):
    """A bare repo under <root>/<repo> carrying the given tags (annotated, like deploy.sh makes)."""
    work = Path(root) / (repo + ".work")
    work.mkdir()
    git("init", "-q", cwd=work)
    git("commit", "-q", "--allow-empty", "-m", "c", cwd=work)
    for t in tags:
        git("tag", "-a", "-m", t, t, cwd=work)
    git("clone", "-q", "--bare", str(work), str(Path(root) / repo), cwd=root)
    shutil.rmtree(work)


class LatestProdVersion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        os.environ["TCOS_APP_TAG_SOURCE"] = self.tmp
        self.addCleanup(os.environ.pop, "TCOS_APP_TAG_SOURCE", None)

    def test_highest_semver_wins_not_the_latest_or_the_lexical_last(self):
        make_source(self.tmp, "ham-tcos-app", [
            "prod/ham-tcos-app/v1.2.0", "prod/ham-tcos-app/v1.10.0", "prod/ham-tcos-app/v1.9.9",
            "v2.0.0", "lab-abc", "prod/other-app/v9.9.9", "prod/ham-tcos-app/v3.0.0-rc1",
        ])
        self.assertEqual(gen.latest_prod_version("ham-tcos-app"), "v1.10.0")

    def test_no_prod_tag_fails_loudly(self):
        make_source(self.tmp, "ham-tcos-app", ["v1.0.0"])
        with self.assertRaises(RuntimeError):
            gen.latest_prod_version("ham-tcos-app")

    def test_unreachable_remote_fails_loudly(self):
        with self.assertRaises(RuntimeError):
            gen.latest_prod_version("no-such-repo")


class Regeneration(unittest.TestCase):
    """Runs the real script against a scratch copy of the repo."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.src = Path(self.tmp) / "src"
        make_source(self.src.parent, "src", [])  # placeholder so the dir exists
        shutil.rmtree(self.src)
        self.src.mkdir()
        self.repo = Path(self.tmp) / "repo"
        self.repo.mkdir()
        for f in ("generate-index.py", "apps.yaml", "index.html"):
            shutil.copy(ROOT / f, self.repo / f)

    def run_gen(self, *args, strict=False):
        env = dict(os.environ, TCOS_APP_TAG_SOURCE=str(self.src))
        env.pop("TCOS_APP_STRICT_VERSIONS", None)
        if strict:
            env["TCOS_APP_STRICT_VERSIONS"] = "1"
        return subprocess.run(["python3", "generate-index.py", *args], cwd=self.repo, env=env,
                              capture_output=True, text=True, check=False)

    def shown(self):
        return re.search(r'<span class="count">([^<]*)</span>', (self.repo / "index.html").read_text()).group(1)

    def test_regenerating_picks_up_a_new_release_with_no_edit(self):
        make_source(self.src, "ham-tcos-app", ["prod/ham-tcos-app/v1.2.0"])
        self.assertEqual(self.run_gen().returncode, 0)
        self.assertEqual(self.shown(), "v1.2.0")
        shutil.rmtree(self.src / "ham-tcos-app")
        make_source(self.src, "ham-tcos-app", ["prod/ham-tcos-app/v1.2.0", "prod/ham-tcos-app/v1.3.0"])
        self.assertEqual(self.run_gen().returncode, 0)
        self.assertEqual(self.shown(), "v1.3.0")

    def test_check_stays_green_when_a_child_releases_but_warns(self):
        make_source(self.src, "ham-tcos-app", ["prod/ham-tcos-app/v1.2.0"])
        self.run_gen()
        shutil.rmtree(self.src / "ham-tcos-app")
        make_source(self.src, "ham-tcos-app", ["prod/ham-tcos-app/v1.2.0", "prod/ham-tcos-app/v1.3.0"])
        r = self.run_gen("--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("WARNING", r.stderr)
        self.assertIn("v1.3.0", r.stderr)

    def test_strict_check_fails_on_a_stale_version_and_on_an_unreachable_remote(self):
        make_source(self.src, "ham-tcos-app", ["prod/ham-tcos-app/v1.2.0"])
        self.run_gen()
        shutil.rmtree(self.src / "ham-tcos-app")
        make_source(self.src, "ham-tcos-app", ["prod/ham-tcos-app/v1.2.0", "prod/ham-tcos-app/v1.3.0"])
        self.assertEqual(self.run_gen("--check", strict=True).returncode, 2)
        shutil.rmtree(self.src / "ham-tcos-app")
        self.assertEqual(self.run_gen("--check").returncode, 0)
        self.assertEqual(self.run_gen("--check", strict=True).returncode, 2)

    def test_check_still_catches_a_hand_edited_page(self):
        make_source(self.src, "ham-tcos-app", ["prod/ham-tcos-app/v1.2.0"])
        self.run_gen()
        page = self.repo / "index.html"
        page.write_text(page.read_text().replace("Open ham.tcos.app", "Open somewhere else"))
        self.assertEqual(self.run_gen("--check").returncode, 2)

    def test_regenerate_refuses_when_the_tag_cannot_be_read(self):
        r = self.run_gen()
        self.assertEqual(r.returncode, 2)
        self.assertIn("could not be resolved", r.stderr)

    def test_a_literal_version_is_a_pin(self):
        apps = self.repo / "apps.yaml"
        apps.write_text(apps.read_text().replace("version: latest", "version: v0.9.0"))
        self.assertEqual(self.run_gen().returncode, 0)
        self.assertEqual(self.shown(), "v0.9.0")


if __name__ == "__main__":
    unittest.main()
