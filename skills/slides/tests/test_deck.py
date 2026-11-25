"""Offline checks of the slides helpers. Run from the skill folder: python -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import _browser  # noqa: E402
import deck  # noqa: E402


class SlideCount(unittest.TestCase):
    def test_ignores_sections_inside_comments(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.html"
            f.write_text('<!-- <section class="slide layout-x"> example -->\n'
                         '<section class="slide layout-title"></section>\n<section class="slide layout-bullets"></section>',
                         encoding="utf-8")
            self.assertEqual(deck.slide_count(f), 2)

    def test_template_has_exactly_the_title_slide(self):
        self.assertEqual(deck.slide_count(deck.TEMPLATE), 1)


class Theme(unittest.TestCase):
    def setUp(self):
        self.cwd, self.env = os.getcwd(), os.environ.pop("AGENT_THEME", None)
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()
        if self.env is not None:
            os.environ["AGENT_THEME"] = self.env

    def test_bundled_default(self):
        self.assertEqual(_browser.resolve_theme(None), _browser.BUNDLED_THEME)
        self.assertEqual(_browser.theme_vars()["accent"], "#1f5fbf")

    def test_custom_theme_overrides_only_what_it_sets(self):
        Path("mine.css").write_text(":root { --accent: #0f766e; }", encoding="utf-8")
        v = _browser.theme_vars("mine.css")
        self.assertEqual(v["accent"], "#0f766e")
        self.assertEqual(v["ink"], "#1c1c1c")

    def test_local_agent_theme_file_is_picked_up(self):
        Path(".agent-theme.css").write_text(":root { --accent: #123456; }", encoding="utf-8")
        self.assertEqual(_browser.theme_vars()["accent"], "#123456")

    def test_missing_theme_file_is_an_error(self):
        with self.assertRaises(SystemExit):
            _browser.resolve_theme("nope.css")


class NewDeck(unittest.TestCase):
    def test_title_is_escaped_and_content_inserted(self):
        with tempfile.TemporaryDirectory() as d:
            content = Path(d) / "c.html"
            content.write_text('<section class="slide layout-bullets"><h2>Two</h2></section>', encoding="utf-8")
            out = Path(d) / "d.html"
            args = type("A", (), dict(deck=str(out), force=False, theme=None, title="A <b> & C", subtitle=None,
                                      kicker=None, meta=None, content=str(content)))
            deck.cmd_new(args)
            page = out.read_text(encoding="utf-8")
            self.assertIn("A &lt;b&gt; &amp; C", page)
            self.assertEqual(deck.slide_count(out), 2)
            self.assertNotIn("{{", page)


if __name__ == "__main__":
    unittest.main()
