"""End-to-end tests of the web UI app: a real server on a free port, runs in a temporary folder.

python -m unittest -v      (no network, no dependencies; add the domain's cases below, with its network mocked)
"""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

TMP = tempfile.mkdtemp(prefix="runs-")
os.environ["RUNS_DIR"] = TMP
os.environ["QUIET"] = "1"

from app import runner, server  # noqa: E402


class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.make_server("127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def get(self, path, raw=False):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            body = r.read().decode("utf-8")
            return (r.status, body) if raw else json.loads(body)

    def post(self, path, data):
        req = urllib.request.Request(self.base + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def wait(self, name, timeout=30):
        t0 = time.time()
        while time.time() - t0 < timeout:
            i = self.get(f"/api/runs/{name}")
            if i["state"] in ("done", "failed"):
                return i
            time.sleep(0.1)
        self.fail(f"run {name} did not finish in {timeout} s")

    def defaults(self, **kw):
        s = {x["name"]: x.get("default") for x in runner.SETTINGS}
        s.update(kw)
        return s

    def test_pages(self):
        for p in ("/", "/architecture", "/health"):
            self.assertEqual(self.get(p, raw=True)[0], 200, p)
        a = self.get("/api/app")
        self.assertEqual(a["title"], runner.TITLE)
        self.assertTrue(a["settings"])

    def test_run_lifecycle(self):
        code, r = self.post("/api/runs", {"settings": self.defaults()})
        self.assertEqual(code, 202, r)
        i = self.wait(r["run"])
        self.assertEqual(i["state"], "done", i.get("error"))
        self.assertTrue(i["results"], "results.json is written")
        self.assertIn(r["run"], [x["run"] for x in self.get("/api/runs")])
        code, html = self.get(f"/run/{r['run']}?embed=1", raw=True)
        self.assertEqual(code, 200)
        self.assertIn(r["run"], html)
        self.assertTrue(os.path.exists(os.path.join(TMP, r["run"], "index.html")), "finished run keeps its page")

    def test_invalid_settings_rejected(self):
        num = next((s for s in runner.SETTINGS if s.get("type") in ("int", "float") and "max" in s), None)
        if not num:
            self.skipTest("no bounded number setting")
        code, r = self.post("/api/runs", {"settings": self.defaults(**{num["name"]: num["max"] + 1})})
        self.assertEqual(code, 400)
        self.assertIn("between", r["error"])

    def test_unknown_run(self):
        with self.assertRaises(urllib.error.HTTPError) as c:
            self.get("/api/runs/999-2000-01-01")
        self.assertEqual(c.exception.code, 404)
        with self.assertRaises(urllib.error.HTTPError):
            self.get("/run/..%2f..%2fetc")

    # --- template example only: delete when the domain changes ---
    def test_example_failure_shows_error(self):
        if not any(o == "fail" for s in runner.SETTINGS for o in s.get("options", [])):
            self.skipTest("example domain replaced")
        _, r = self.post("/api/runs", {"settings": self.defaults(mode="fail")})
        i = self.wait(r["run"])
        self.assertEqual(i["state"], "failed")
        self.assertIn("asked to fail", i["error"])


if __name__ == "__main__":
    unittest.main()
