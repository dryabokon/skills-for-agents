"""Offline checks of bq.py. Run from the skill folder: python -m unittest discover -s tests -v"""
import argparse
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import bq  # noqa: E402


def ns(**kw):
    base = dict(project="demo-project", timeout=5, max_gb=1.0, json=False)
    return argparse.Namespace(**{**base, **kw})


class Money(unittest.TestCase):
    def test_price(self):
        self.assertEqual(bq.price(0), "$0")
        self.assertEqual(bq.price(1), "~$0.0001")             # 10 MB minimum
        self.assertEqual(bq.price(1024 ** 4), "~$6.25")       # one TiB on demand
        self.assertEqual(bq.price(258 * 1024 ** 3), "~$1.57")

    def test_human_bytes(self):
        self.assertEqual(bq.human_bytes(0), "0 B")
        self.assertEqual(bq.human_bytes(2650191), "2.5 MB")
        self.assertEqual(bq.human_bytes(258 * 1024 ** 3), "258.0 GB")


class Refs(unittest.TestCase):
    def setUp(self):
        os.environ["GOOGLE_OAUTH_ACCESS_TOKEN"] = "test-token"  # no gcloud call

    def tearDown(self):
        os.environ.pop("GOOGLE_OAUTH_ACCESS_TOKEN", None)

    def test_split_fills_in_the_billing_project(self):
        b = bq.BQ(ns())
        self.assertEqual(b.split("ds", 2), ["demo-project", "ds"])
        self.assertEqual(b.split("other.ds.t", 3), ["other", "ds", "t"])
        self.assertEqual(b.split("`p.ds.t`", 3), ["p", "ds", "t"])
        with self.assertRaises(SystemExit):
            b.split("a.b.c.d", 3)

    def test_statements_that_change_data_are_refused_before_any_call(self):
        for sql in ("DELETE FROM d.t WHERE true", "  insert into d.t values (1)", "DROP TABLE d.t", "MERGE d.t USING x ON true"):
            with self.assertRaises(SystemExit) as e:
                bq.cmd_query(ns(sql=sql, file=None, allow_write=False, dry_run=False, limit=5))
            self.assertIn("only reads", str(e.exception))


class Rows(unittest.TestCase):
    def test_rows_of(self):
        r = {"schema": {"fields": [{"name": "a"}, {"name": "b"}]},
             "rows": [{"f": [{"v": "1"}, {"v": None}]}, {"f": [{"v": "x"}, {"v": [{"v": "1"}]}]}]}
        self.assertEqual(bq.rows_of(r), [{"a": "1", "b": None}, {"a": "x", "b": '[{"v": "1"}]'}])

    def test_flat_fields_nested(self):
        f = bq.flat_fields([{"name": "r", "type": "RECORD", "mode": "REPEATED", "fields": [{"name": "x", "type": "INT64"}]}])
        self.assertEqual([c["column"] for c in f], ["r", "r.x"])
        self.assertEqual(f[0]["type"], "RECORD[]")


if __name__ == "__main__":
    unittest.main()
