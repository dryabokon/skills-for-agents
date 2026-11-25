"""Offline checks of the diagrams helpers. Run from the skill folder: python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import _browser  # noqa: E402
import diagram  # noqa: E402

V = _browser.theme_vars()


class StatusClasses(unittest.TestCase):
    def test_adds_classdef_only_for_used_statuses(self):
        out = diagram.with_status_classes("flowchart LR\n  A:::confirmed --> B:::proposed\n", V)
        self.assertIn("classDef confirmed", out)
        self.assertIn("classDef proposed", out)
        self.assertNotIn("classDef unclear", out)

    def test_keeps_user_classdef(self):
        src = "flowchart LR\n  A:::confirmed\n  classDef confirmed fill:#000\n"
        self.assertEqual(diagram.with_status_classes(src, V).count("classDef confirmed"), 1)

    def test_leaves_other_diagram_types_alone(self):
        src = "sequenceDiagram\n  A->>B: hi\n"
        self.assertEqual(diagram.with_status_classes(src, V).strip(), src.strip())

    def test_class_statement_counts_as_use(self):
        out = diagram.with_status_classes("graph TD\n  A --> B\n  class A unclear\n", V)
        self.assertIn("classDef unclear", out)


class Svg(unittest.TestCase):
    def test_theme_is_inlined_into_placeholder(self):
        out = diagram.build_svg('<svg viewBox="0 0 10 10"><style id="theme"/><rect/></svg>', V)
        self.assertIn(V["accent"], out)
        self.assertEqual(out.count('<style id="theme">'), 1)

    def test_theme_is_added_when_there_is_no_placeholder(self):
        out = diagram.build_svg('<svg viewBox="0 0 10 10"><rect/></svg>', V)
        self.assertIn('<style id="theme">', out)

    def test_literal_colours_only(self):
        self.assertNotIn("var(", diagram.svg_theme_css(V))

    def test_size_from_viewbox_or_attributes(self):
        self.assertEqual(diagram.svg_size('<svg viewBox="0 0 960 410">'), (960.0, 410.0))
        self.assertEqual(diagram.svg_size('<svg width="300" height="200">'), (300.0, 200.0))
        with self.assertRaises(SystemExit):
            diagram.svg_size("<svg>")

    def test_starter_uses_every_status(self):
        starter = (Path(diagram.SKILL) / "assets" / "starter.svg").read_text(encoding="utf-8")
        for s in diagram.STATUSES:
            self.assertIn(s, starter)


if __name__ == "__main__":
    unittest.main()
