"""Offline checks of the skill itself: what SKILL.md promises exists in the template, and the domain contract."""
import importlib
import re
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL / "template"
KINDS = {"int", "float", "text", "choice", "bool"}


class SkillTest(unittest.TestCase):
    def test_files_named_in_skill_md_exist(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        named = set(re.findall(r"`((?:app|docs|tests)/[\w./]+\.\w+|deploy\.sh|Dockerfile|\.gcloudignore)`", text))
        self.assertTrue(named)
        for f in named:
            self.assertTrue((TEMPLATE / f).exists(), f"SKILL.md names {f}, missing in template/")

    def test_template_has_what_a_project_needs(self):
        for f in ("README.md", ".gitignore", ".env.example", ".github/workflows/ci.yml", "app/report/scripts/report.py",
                  "app/report/assets/report.css", "app/static/index.html", "app/static/architecture.html"):
            self.assertTrue((TEMPLATE / f).exists(), f)

    def test_report_copy_is_current(self):
        """app/report/ is a copy of the report skill; keep it identical so result pages look like every report."""
        src = SKILL.parent / "report"
        if not src.exists():
            self.skipTest("report skill not next to this one (copied alone into a project)")
        for f in ("scripts/report.py", "assets/report.css", "assets/report.js"):
            a = (src / f).read_bytes().replace(b"\r\n", b"\n")
            b = (TEMPLATE / "app" / "report" / f).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(a, b, f"template/app/report/{f} differs from skills/report/{f}: copy it again")

    def test_runner_contract(self):
        sys.path.insert(0, str(TEMPLATE))
        try:
            runner = importlib.import_module("app.runner")
        finally:
            sys.path.pop(0)
        self.assertIsInstance(runner.TITLE, str)
        names = [s["name"] for s in runner.SETTINGS]
        self.assertEqual(len(names), len(set(names)), "setting names are unique")
        for s in runner.SETTINGS:
            self.assertIn(s.get("type", "text"), KINDS, s)
            if s.get("type") == "choice":
                self.assertIn(s["default"], s["options"], s)
        res = runner.run({s["name"]: s["default"] for s in runner.SETTINGS}, Path("."), lambda m: None)
        self.assertIsInstance(res, dict)


if __name__ == "__main__":
    unittest.main()
