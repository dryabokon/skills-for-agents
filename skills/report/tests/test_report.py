"""Offline checks of report.py. Run from the skill folder: python -m unittest discover -s tests -v"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import report  # noqa: E402


class Statuses(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual([report.st(s) for s in ("pass", "FAIL", "skip", "error", "warning", None, "odd")],
                         ["good", "bad", "note", "bad", "warn", "neutral", "neutral"])


class Render(unittest.TestCase):
    def test_example_uses_every_block_and_both_themes(self):
        page = report.render(report.EXAMPLE)
        for needle in ("class='sbar'", "class='kpis'", "<table>", "details class='item'", "id='theme'",
                       'html[data-theme="dark"]', "prefers-color-scheme"):
            self.assertIn(needle, page)

    def test_output_cannot_break_the_page(self):
        evil = "<script>alert(1)</script> & </pre>"
        page = report.render({"title": evil, "sections": [{"title": "s", "blocks": [
            {"type": "code", "text": evil}, {"type": "items", "items": [{"status": "fail", "title": evil, "code": evil}]},
            {"type": "table", "columns": ["a"], "rows": [[evil]]}]}]})
        self.assertNotIn("<script>alert", page)
        self.assertEqual(len(re.findall(r"<script>", page)), 1)  # only the theme script

    def test_failed_items_can_open_and_show_checks(self):
        page = report.render({"title": "t", "sections": [{"blocks": [{"type": "items", "items": [
            {"status": "fail", "title": "x", "open": True, "checks": [{"ok": False, "text": "exit 0", "detail": "got 1"}]}]}]}]})
        self.assertIn("<details class='item' open>", page)
        self.assertIn("✗", page)
        self.assertIn("got 1", page)

    def test_bar_widths_add_up(self):
        page = report.render({"title": "t", "bar": {"pass": 3, "fail": 1}})
        widths = [float(w) for w in re.findall(r"width:([\d.]+)%", page)]
        self.assertAlmostEqual(sum(widths), 100, places=1)

    def test_unknown_block_is_an_error(self):
        with self.assertRaises(SystemExit):
            report.render({"title": "t", "sections": [{"blocks": [{"type": "chart"}]}]})


if __name__ == "__main__":
    unittest.main()
