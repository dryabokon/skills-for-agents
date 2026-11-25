"""Offline checks of ado.py. Run from the skill folder: python -m unittest discover -s tests -v"""
import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ado  # noqa: E402


class Urls(unittest.TestCase):
    def test_pull_request(self):
        u = ado.parse_url("https://dev.azure.com/osy/Proj%20X/_git/My%20Repo/pullrequest/605?_a=files")
        self.assertEqual((u["org_url"], u["project"], u["kind"], u["repo"], u["id"]),
                         ("https://dev.azure.com/osy", "Proj X", "pr", "My Repo", 605))

    def test_build(self):
        u = ado.parse_url("https://dev.azure.com/o/p/_build/results?buildId=4109&view=logs")
        self.assertEqual((u["kind"], u["id"]), ("build", 4109))

    def test_work_item_both_forms(self):
        self.assertEqual(ado.parse_url("https://dev.azure.com/o/p/_workitems/edit/754")["id"], 754)
        self.assertEqual(ado.parse_url("https://dev.azure.com/o/p/_boards/board/t/T/Stories?workitem=754")["id"], 754)

    def test_wiki(self):
        u = ado.parse_url("https://dev.azure.com/o/p/_wiki/wikis/P.wiki/530/Some-Page")
        self.assertEqual((u["kind"], u["wiki"], u["id"]), ("wiki", "P.wiki", 530))

    def test_old_style_org(self):
        self.assertEqual(ado.parse_url("https://org.visualstudio.com/p/_build/results?buildId=1")["org_url"],
                         "https://org.visualstudio.com")

    def test_not_azure_devops(self):
        with self.assertRaises(SystemExit):
            ado.parse_url("https://github.com/o/r/pull/1")


class Helpers(unittest.TestCase):
    def test_branch_and_time(self):
        self.assertEqual(ado.branch("refs/heads/feature/x"), "feature/x")
        self.assertEqual(ado.branch("refs/pull/774/merge"), "pull/774/merge")
        self.assertEqual(ado.when("2026-11-25T10:31:07.123Z"), "2026-11-25 10:31")
        self.assertEqual(ado.when(None), "-")

    def test_strip_html(self):
        self.assertEqual(ado.strip_html("<p>a &amp; b</p><div>c</div>"), "a & b\nc")

    def test_error_lines(self):
        hit = lambda s: bool(ado.ERROR_LINE.search(s)) and not ado.NOISE_LINE.search(s)
        self.assertTrue(hit("##[error]Bash exited with code '1'."))
        self.assertTrue(hit('"error": "build input missing: infrastructure/Dockerfile"'))
        self.assertFalse(hit('"errors": [],'))
        self.assertFalse(hit("Build succeeded. 0 errors"))
        self.assertFalse(hit("##[section]Finishing: Build"))


class Config(unittest.TestCase):
    def setUp(self):
        self.cwd, self.saved = os.getcwd(), {k: os.environ.pop(k, None) for k in
                                               ("AZURE_DEVOPS_ORG", "AZURE_DEVOPS_ORG_URL", "AZURE_DEVOPS_PROJECT", "X_KEEP")}
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()
        for k, v in self.saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def test_dotenv_found_upwards_quotes_comments_and_no_override(self):
        Path(".env").write_text('# c\nexport AZURE_DEVOPS_ORG="my org"\nAZURE_DEVOPS_PROJECT=P # note\nX_KEEP=file\n',
                                encoding="utf-8")
        Path("sub").mkdir()
        os.chdir("sub")
        os.environ["X_KEEP"] = "shell"
        ado.load_dotenv()
        self.assertEqual(os.environ["AZURE_DEVOPS_ORG"], "my org")
        self.assertEqual(os.environ["AZURE_DEVOPS_PROJECT"], "P")
        self.assertEqual(os.environ["X_KEEP"], "shell")

    def test_no_org_is_a_clear_error(self):
        a = argparse.Namespace(org=None, project=None, timeout=5)
        with self.assertRaises(SystemExit) as e:
            ado.Client(a)
        self.assertIn("AZURE_DEVOPS_ORG", str(e.exception))

    def test_url_overrides_settings(self):
        os.environ["AZURE_DEVOPS_ORG"] = "other"
        c = ado.Client(argparse.Namespace(org=None, project=None, timeout=5),
                       ado.parse_url("https://dev.azure.com/osy/OsyFly/_build/results?buildId=1"))
        self.assertEqual((c.org_url, c.project), ("https://dev.azure.com/osy", "OsyFly"))


if __name__ == "__main__":
    unittest.main()
