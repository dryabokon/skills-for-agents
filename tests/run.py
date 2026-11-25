#!/usr/bin/env python3
"""Run the test cases of every skill and keep the results in runs/001, runs/002, ...

    python tests/run.py                      every skill
    python tests/run.py --skill slides gcp   some skills
    python tests/run.py --case "*plan*"      cases whose id matches
    python tests/run.py --clean              only remove out/ and __pycache__/ left in skill folders (runs do it themselves)
    python tests/run.py --offline            skip cases that need the network
    python tests/run.py --open               open the report when done

Cases live next to each skill in skills/<name>/tests/cases.json. A case runs one or more commands from the
skill's folder - the same commands as SKILL.md and examples/ - and checks the exit code and the output:

    {"id": "dry-run-prices-a-big-query", "title": "...",
     "steps": ["python scripts/bq.py query 'SELECT ...' --dry-run"],
     "needs": ["gcloud"],                     chrome | node | gcloud | network | an env variable such as GH_TOKEN
     "env": {"AZURE_DEVOPS_PAT": ""},         extra environment for this case
     "expect": {"exit": 0, "contains": ["258"], "contains_any": [...], "not_contains": ["Traceback"]},
     "artifacts": ["out/streaming.pdf"]}      files or folders copied into the case folder

Earlier steps must exit 0; `exit` is the last step's code; `contains` looks at the output of all steps. A case whose needs are not met is skipped, not
failed. The run folder holds index.html (open it), results.json and one folder per case with the commands,
their output (tokens from .env are masked) and the artifacts. Exit code 1 if any case failed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
SECRET_NAME = re.compile(r"(TOKEN|PAT|SECRET|PASSWORD|KEY)$")


def load_dotenv() -> None:
    env = ROOT / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(?:export\s+)?([A-Za-z_]\w*)\s*=\s*(.*?)\s*$", line)
            if m and not line.lstrip().startswith("#"):
                v = m.group(2)
                v = v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"" else v
                os.environ.setdefault(m.group(1), v)


def secrets_to_mask() -> list[str]:
    return sorted({v for k, v in os.environ.items() if SECRET_NAME.search(k) and len(v) >= 8}, key=len, reverse=True)


def mask(text: str, secrets: list[str]) -> str:
    for s in secrets:
        text = text.replace(s, "***")
    return text


# ------------------------------------------------------------------ environment probes

def find_bash() -> str | None:
    if os.name == "nt":  # `bash` on Windows PATH is often WSL; the examples are meant for Git Bash
        for p in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"):
            if Path(p).is_file():
                return p
    return shutil.which("bash")


def have_chrome() -> bool:
    sys.path.insert(0, str(ROOT / "skills" / "slides" / "scripts"))
    try:
        import _browser  # noqa: PLC0415
        _browser.find_browser()
        return True
    except SystemExit:
        return False
    finally:
        sys.path.pop(0)


def have_gcloud() -> bool:
    exe = shutil.which("gcloud")
    if not exe:
        return False
    try:
        out = subprocess.run([exe, "config", "get-value", "account"], capture_output=True, text=True, timeout=60).stdout
        return bool(out.strip())
    except (OSError, subprocess.TimeoutExpired):
        return False


PROBES = {"chrome": have_chrome, "node": lambda: bool(shutil.which("npx")), "gcloud": have_gcloud,
          "bash": lambda: bool(find_bash())}


def unmet(needs: list[str], offline: bool, cache: dict) -> list[str]:
    missing = []
    for n in needs:
        if n == "network":
            if offline:
                missing.append("network")
            continue
        if n in PROBES:
            if n not in cache:
                cache[n] = PROBES[n]()
            if not cache[n]:
                missing.append(n)
        elif not os.environ.get(n):
            missing.append(n)
    return missing


# ------------------------------------------------------------------ running

def argv_for(cmd: str, bash: str | None) -> list[str]:
    """`python ...` runs with this interpreter, anything else (bash examples/x.sh, pipes) through bash."""
    if re.match(r"^python3?\s", cmd) and not re.search(r"[|&;<>]|\$\(", cmd):
        return [sys.executable, *shlex.split(cmd)[1:]]
    if not bash:
        raise RuntimeError("bash not found")
    return [bash, "-c", cmd]


def run_case(skill_dir: Path, case: dict, case_dir: Path, secrets: list[str], bash: str | None) -> dict:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "MSYS_NO_PATHCONV": "1", "PYTHONDONTWRITEBYTECODE": "1", **case.get("env", {})}
    start = time.time()
    log, last = [], None
    for i, cmd in enumerate(case["steps"]):
        try:
            res = subprocess.run(argv_for(cmd, bash), cwd=skill_dir, env=env, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=case.get("timeout", 600))
            code, out, err = res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired as e:
            code, out, err = -1, (e.stdout or "") if isinstance(e.stdout, str) else "", f"timed out after {e.timeout}s"
        except RuntimeError as e:
            code, out, err = -1, "", str(e)
        out, err = mask(out, secrets), mask(err, secrets)
        log.append({"command": cmd, "exit": code, "stdout": out, "stderr": err})
        last = log[-1]
        if i < len(case["steps"]) - 1 and code != 0:
            break
    seconds = round(time.time() - start, 1)

    exp = case.get("expect", {})
    text = "\n".join(s["stdout"] + "\n" + s["stderr"] for s in log)  # what to look for: anywhere in the case
    checks = []
    early_fail = next((s for s in log[:-1] if s["exit"] != 0), None)
    if early_fail or len(log) < len(case["steps"]):
        checks.append({"check": "earlier steps succeed", "ok": False,
                       "detail": f"stopped at: {log[-1]['command']} (exit {log[-1]['exit']})"})
    want = exp.get("exit", 0)
    checks.append({"check": f"exit code {want}", "ok": last["exit"] == want, "detail": f"got {last['exit']}"})
    for s in exp.get("contains", []):
        checks.append({"check": f"output contains {s!r}", "ok": s in text, "detail": ""})
    if exp.get("contains_any"):
        hit = [s for s in exp["contains_any"] if s in text]
        checks.append({"check": f"output contains one of {exp['contains_any']}", "ok": bool(hit), "detail": ", ".join(hit)})
    for s in exp.get("not_contains", []) + ["Traceback (most recent call last)"]:
        checks.append({"check": f"output lacks {s!r}", "ok": s not in text, "detail": ""})

    case_dir.mkdir(parents=True)
    with open(case_dir / "commands.txt", "w", encoding="utf-8") as f:
        for s in log:
            f.write(f"$ {s['command']}\n# exit {s['exit']}\n\n")
    (case_dir / "output.txt").write_text("\n\n".join(
        f"$ {s['command']}\n{s['stdout']}" + (f"\n[stderr]\n{s['stderr']}" if s["stderr"].strip() else "") for s in log),
        encoding="utf-8")
    kept = []
    for pattern in case.get("artifacts", []):
        for src in sorted(skill_dir.glob(pattern)):
            dst = case_dir / src.name
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)
            kept += [p.relative_to(case_dir).as_posix() for p in ([dst] if dst.is_file() else sorted(dst.rglob("*")))
                     if p.is_file()]
    return {"status": "pass" if all(c["ok"] for c in checks) else "fail", "seconds": seconds, "checks": checks,
            "artifacts": kept, "exit": last["exit"]}


# ------------------------------------------------------------------ report (rendered by the report skill)

sys.path.insert(0, str(ROOT / "skills" / "report" / "scripts"))
import report as report_skill  # noqa: E402

STATUS = {"pass": "good", "fail": "bad", "skip": "note"}


def _counts(results: list[dict]) -> dict:
    return {s: sum(r["status"] == s for r in results) for s in ("pass", "fail", "skip")}


def _case_item(r: dict, run_dir: Path) -> dict:
    it = {"status": STATUS[r["status"]], "title": r["title"], "sub": r["id"], "open": r["status"] == "fail",
          "right": r.get("reason") or f"{r.get('seconds')} s"}
    if r["status"] == "skip":
        it["text"] = (f"Skipped: {r['reason']}. Set it up (see the skill's .env.example) and run "
                      f"python tests/run.py --skill {r['skill']}")
        return it
    folder = r["folder"]
    it["checks"] = [{"ok": c["ok"], "text": c["check"], "detail": c["detail"]} for c in r["checks"]]
    imgs = [a for a in r["artifacts"] if a.lower().endswith((".png", ".jpg", ".svg"))][:6]
    it["images"] = [{"src": f"{folder}/{a}", "caption": a} for a in imgs]
    it["links"] = [{"text": "commands", "href": f"{folder}/commands.txt"}, {"text": "full output", "href": f"{folder}/output.txt"}] + \
                  [{"text": a, "href": f"{folder}/{a}"} for a in r["artifacts"] if a not in imgs][:8]
    lines = (run_dir / folder / "output.txt").read_text(encoding="utf-8").splitlines()
    it["code"] = "\n".join(lines[:120]) + ("\n…" if len(lines) > 120 else "")
    return it


def report(run_dir: Path, results: list[dict], meta: dict) -> None:
    """runs/NNN/index.html (this run), results.json, and runs/index.html (every run so far)."""
    (run_dir / "results.json").write_text(json.dumps({"meta": meta, "cases": results}, indent=1, ensure_ascii=False),
                                          encoding="utf-8")
    c, total = _counts(results), len(results)
    skills = sorted({r["skill"] for r in results})
    spec = {
        "title": f"Run {run_dir.name}",
        "crumbs": [{"text": "All runs", "href": "../index.html"}, {"text": run_dir.name}],
        "meta": [meta["when"], f"commit {meta['commit']}", f"{meta['seconds']} s"] + (["offline"] if meta["offline"] else []),
        "verdict": {"status": "bad", "text": f"✗ {c['fail']} failed"} if c["fail"] else {"status": "good", "text": "✓ All passed"},
        "bar": {"good": c["pass"], "bad": c["fail"], "note": c["skip"]},
        "groups": [],
        "sections": [],
    }
    for skill in skills:
        rows = [r for r in results if r["skill"] == skill]
        sc = _counts(rows)
        summary = f"{sc['pass']}/{len(rows)} passed" + (f", {sc['fail']} failed" if sc["fail"] else "") + \
                  (f", {sc['skip']} skipped" if sc["skip"] else "")
        spec["groups"].append({"name": skill, "href": f"#{skill}", "summary": summary,
                               "dots": [STATUS[r["status"]] for r in rows]})
        rows.sort(key=lambda r: {"fail": 0, "skip": 1, "pass": 2}[r["status"]])  # failures first
        spec["sections"].append({"title": skill, "id": skill, "note": summary,
                                 "blocks": [{"type": "items", "items": [_case_item(r, run_dir) for r in rows]}]})
    report_skill.write(spec, run_dir / "index.html")
    history()


def history() -> None:
    """runs/index.html: one row per run, newest first."""
    rows, last = [], None
    for d in sorted((p for p in RUNS.iterdir() if p.is_dir() and (p / "results.json").is_file()), reverse=True):
        data = json.loads((d / "results.json").read_text(encoding="utf-8"))
        c, total, m = _counts(data["cases"]), len(data["cases"]), data["meta"]
        last = last or (c, total)
        result = {"text": f"{c['fail']} failed", "status": "bad"} if c["fail"] else {"text": "passed", "status": "good"}
        rows.append([{"text": d.name, "href": f"{d.name}/index.html"}, result, f"{c['pass']}/{total}",
                     c["skip"] or "", m["when"], m["commit"], f"{m['seconds']:.0f} s"])
    spec = {"title": "Skill test runs", "meta": ["python tests/run.py", f"{len(rows)} runs", "newest first"],
            "sections": [{"title": "Runs", "blocks": [{"type": "table", "num": [3, 4, 7],
                                                       "columns": ["Run", "Result", "Passed", "Skipped", "When", "Commit", "Time"],
                                                       "rows": rows}]}]}
    if last:
        c, total = last
        spec["verdict"] = {"status": "bad", "text": f"Latest: {c['fail']} failed"} if c["fail"] else \
            {"status": "good", "text": "Latest: all passed"}
    report_skill.write(spec, RUNS / "index.html")


def new_run_dir(tag: str) -> Path:
    RUNS.mkdir(exist_ok=True)
    nums = [int(p.name[:3]) for p in RUNS.iterdir() if p.is_dir() and p.name[:3].isdigit()]
    d = RUNS / f"{(max(nums) + 1 if nums else 1):03d}"  # 001, 002, ...: date and commit are in the report
    d.mkdir()
    return d


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--skill", nargs="*", help="only these skills")
    p.add_argument("--case", help="only cases whose id matches this glob")
    p.add_argument("--offline", action="store_true", help="skip cases that need the network")
    p.add_argument("--open", action="store_true", help="open the report when done")
    p.add_argument("--clean", action="store_true", help="only remove out/ and __pycache__/ from skill folders")
    a = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if a.clean:
        print(f"removed {len(clean())} folder(s)")
        return 0
    load_dotenv()
    secrets, cache, bash = secrets_to_mask(), {}, find_bash()

    plan = []
    for f in sorted(ROOT.glob("skills/*/tests/cases.json")):
        skill = f.parent.parent.name
        if a.skill and skill not in a.skill:
            continue
        for case in json.loads(f.read_text(encoding="utf-8")):
            if not a.case or fnmatch.fnmatch(case["id"], a.case):
                plan.append((skill, f.parent.parent, case))
    if not plan:
        sys.exit("no cases matched")

    run_dir = new_run_dir("tests")
    print(f"{len(plan)} cases -> {run_dir.relative_to(ROOT)}")
    start, results = time.time(), []
    for n, (skill, skill_dir, case) in enumerate(plan, 1):
        folder = f"{n:02d}-{skill}-{case['id']}"
        row = {"skill": skill, "id": case["id"], "title": case.get("title", case["id"]), "folder": folder}
        missing = unmet(case.get("needs", []), a.offline, cache)
        if missing:
            row.update(status="skip", reason="needs " + ", ".join(missing), checks=[], artifacts=[])
        else:
            row.update(run_case(skill_dir, case, run_dir / folder, secrets, bash))
        results.append(row)
        mark = {"pass": "ok  ", "fail": "FAIL", "skip": "skip"}[row["status"]]
        print(f"  {mark} {skill:<13} {case['id']:<40} {row.get('reason') or str(row.get('seconds')) + ' s'}")
        for c in row.get("checks", []):
            if not c["ok"]:
                print(f"         ✗ {c['check']} {c['detail']}")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    meta = {"when": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "commit": commit or "-", "offline": a.offline,
            "seconds": round(time.time() - start, 1)}
    report(run_dir, results, meta)
    clean()  # artifacts are already in the run folder
    failed = sum(r["status"] == "fail" for r in results)
    skipped = sum(r["status"] == "skip" for r in results)
    print(f"\n{len(results) - failed - skipped} passed, {failed} failed, {skipped} skipped · report: {(run_dir / 'index.html').relative_to(ROOT)}")
    if a.open:
        webbrowser.open((run_dir / "index.html").as_uri())
    return 1 if failed else 0


def clean() -> list[Path]:
    """Remove what runs leave inside skill folders (out/, __pycache__/), so a skill folder can be copied as is."""
    gone = [*ROOT.glob("skills/*/out"), *ROOT.glob("skills/**/__pycache__"), *ROOT.glob("tests/__pycache__")]
    for d in gone:
        shutil.rmtree(d, ignore_errors=True)
    return gone


if __name__ == "__main__":
    sys.exit(main())
