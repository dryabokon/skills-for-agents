"""Run folders: runs/NNN-YYYY-MM-DD/ with config.json, status.json, log.txt, results.json, index.html.

The folder is the only state: the app reads status and results from it, so a restart, another tab or another
instance always sees the truth. RUNS_DIR overrides the location (Cloud Run mounts the bucket at /app/runs).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_NAME = re.compile(r"^\d{3,}-\d{4}-\d{2}-\d{2}$")
_LOCK = threading.Lock()


def runs_dir() -> Path:
    d = Path(os.environ.get("RUNS_DIR") or ROOT / "runs")
    d.mkdir(parents=True, exist_ok=True)
    return d


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def read(d: Path, name: str, default=None):
    f = d / name
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write(d: Path, name: str, data) -> None:
    """Atomic: readers see the old or the new file, never half of one. On Windows a replace fails while a reader
    has the file open, so retry briefly."""
    tmp = d / f".{name}.{threading.get_ident()}.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for attempt in range(50):
        try:
            tmp.replace(d / name)
            return
        except PermissionError:
            if attempt == 49:
                raise
            time.sleep(0.02)


def new_run(settings: dict) -> Path:
    """Next number, today's date. The lock keeps two quick starts from taking the same number."""
    with _LOCK:
        base = runs_dir()
        nums = [int(p.name.split("-")[0]) for p in base.iterdir() if p.is_dir() and RUN_NAME.match(p.name)]
        d = base / f"{(max(nums) + 1 if nums else 1):03d}-{dt.date.today().isoformat()}"
        d.mkdir()
    write(d, "config.json", {"settings": settings, "created": now()})
    write(d, "status.json", {"state": "queued", "created": now()})
    return d


def find(name: str) -> Path | None:
    if not RUN_NAME.match(name or ""):
        return None
    d = runs_dir() / name
    return d if d.is_dir() else None


def info(d: Path, full: bool = False) -> dict:
    st = read(d, "status.json", {"state": "unknown"})
    res = read(d, "results.json", {}) or {}
    out = {"run": d.name, "state": st.get("state"), "started": st.get("started") or st.get("created"),
           "seconds": st.get("seconds"), "error": st.get("error"), "headline": res.get("headline"),
           "verdict": res.get("verdict"), "settings": (read(d, "config.json", {}) or {}).get("settings", {})}
    if full:
        out["results"] = res
        log = d / "log.txt"
        out["log"] = log.read_text(encoding="utf-8")[-20000:] if log.exists() else ""
    return out


def listing() -> list[dict]:
    ds = [p for p in runs_dir().iterdir() if p.is_dir() and RUN_NAME.match(p.name)]
    return [info(d) for d in sorted(ds, key=lambda p: int(p.name.split("-")[0]), reverse=True)[:200]]


def execute(d: Path, fn, settings: dict, on_done=None) -> None:
    """Run fn(settings, out, log) -> results in this thread, keeping status.json and log.txt current."""
    t0 = time.time()
    logf = d / "log.txt"

    def log(msg: str) -> None:
        with logf.open("a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now():%H:%M:%S} {msg}\n")

    started = now()
    write(d, "status.json", {"state": "running", "started": started})
    try:
        results = fn(settings, d, log) or {}
        write(d, "results.json", results)
        write(d, "status.json", {"state": "done", "started": started,
                                 "finished": now(), "seconds": round(time.time() - t0, 1)})
        log("done")
    except Exception as ex:  # the run fails, the server does not
        log("failed: " + "".join(traceback.format_exception_only(type(ex), ex)).strip())
        (d / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        write(d, "status.json", {"state": "failed", "started": started, "error": f"{type(ex).__name__}: {ex}", "finished": now(),
                                 "seconds": round(time.time() - t0, 1)})
    if on_done:
        try:
            on_done(d)
        except Exception:  # the page can be drawn later on request; never leave the thread with an error
            log("could not write index.html: " + traceback.format_exc(limit=1).strip().splitlines()[-1])


def start(fn, settings: dict, on_done=None) -> Path:
    d = new_run(settings)
    threading.Thread(target=execute, args=(d, fn, settings, on_done), daemon=True, name=d.name).start()
    return d
