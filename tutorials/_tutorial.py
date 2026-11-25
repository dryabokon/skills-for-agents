"""Tiny helper for the tutorials: print every command exactly as a person (or an agent) would type it, then run it.

Each tutorial runs from the repository root and writes into tutorials/_out/<tutorial>/ (git-ignored).
"""
from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPEN = "--open" in sys.argv


def out_dir(name: str) -> Path:
    path = ROOT / "tutorials" / "_out" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def rel(path) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def step(title: str) -> None:
    print(f"\n=== {title}")


def run(*args, ok_codes=(0,)) -> int:
    """Run `python <script> args...` from the repo root, echoing the command first."""
    shown = ["python"] + [rel(a) if isinstance(a, Path) else str(a) for a in args]
    print("$ " + " ".join(f'"{x}"' if " " in x else x for x in shown))
    sys.stdout.flush()
    code = subprocess.run([sys.executable] + shown[1:], cwd=ROOT).returncode
    if code not in ok_codes:
        sys.exit(f"step failed with exit code {code}")
    return code


def done(*results: Path) -> None:
    print("\nResult:")
    for r in results:
        print(f"  {r}")
    if OPEN:
        for r in results:
            webbrowser.open(Path(r).resolve().as_uri())
    elif results:
        print("(add --open to open the result)")
    os.environ.setdefault("PYTHONUTF8", "1")
