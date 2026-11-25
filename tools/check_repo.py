#!/usr/bin/env python3
"""Repository checks - run before every commit and in CI.

    python tools/check_repo.py

1. every skills/<name>/SKILL.md follows the Agent Skills spec (https://agentskills.io/specification):
   name == folder, kebab-case <= 64, description 1..1024, only portable frontmatter keys, < 500 lines,
   relative links resolve
2. every skill has a runnable tutorial in tutorials/<name>/
3. shared files are in sync (tools/sync_shared.py --check)
4. all Python compiles
5. nothing that looks like a secret is committed
6. `claude plugin validate .` passes (skipped when the claude CLI is not installed)
"""
from __future__ import annotations

import py_compile
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SECRET_RES = [
    re.compile(p) for p in (
        r"ghp_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{40,}", r"glpat-[A-Za-z0-9_\-]{20,}",
        r"AKIA[0-9A-Z]{16}", r"AIza[0-9A-Za-z_\-]{35}", r"xox[baprs]-[A-Za-z0-9-]{10,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\"private_key\"\s*:\s*\"-----BEGIN",
        r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"][A-Za-z0-9_\-/+=]{20,}['\"]",
    )
]
SKIP_DIRS = {".git", "_out", "__pycache__", "node_modules"}
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def frontmatter(text: str) -> dict[str, str] | None:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    data, key = {}, None
    for line in m.group(1).splitlines():
        if re.match(r"^[A-Za-z][\w-]*:", line):
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip()
        elif key and line.startswith((" ", "\t")):
            data[key] += "\n" + line  # nested (metadata) or folded value
    return data


def check_skill(folder: Path) -> None:
    name = folder.name
    md = folder / "SKILL.md"
    if not md.is_file():
        return err(f"{name}: SKILL.md missing")
    text = md.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm is None:
        return err(f"{name}: SKILL.md has no '---' frontmatter")
    for key in fm:
        if key not in ALLOWED_KEYS:
            err(f"{name}: frontmatter key '{key}' is not in the portable set {sorted(ALLOWED_KEYS)}")
    if fm.get("name") != name:
        err(f"{name}: frontmatter name '{fm.get('name')}' must equal the folder name")
    if not NAME_RE.match(name) or len(name) > 64:
        err(f"{name}: name must be kebab-case a-z0-9, <= 64 chars")
    desc = fm.get("description", "")
    if not 1 <= len(desc) <= 1024:
        err(f"{name}: description length {len(desc)} not in 1..1024")
    if len(fm.get("compatibility", "")) > 500:
        err(f"{name}: compatibility longer than 500 chars")
    for key, val in fm.items():
        if ": " in val and not val.startswith(("'", '"', ">", "|")) and key != "metadata":
            err(f"{name}: unquoted '{key}' contains ': ' - YAML will misread it; quote the value")
    lines = text.count("\n") + 1
    if lines >= 500:
        err(f"{name}: SKILL.md has {lines} lines; keep it under 500 and move detail to references/")
    for target in re.findall(r"\]\(([^)#:]+)\)", text):
        if not (folder / target).exists():
            err(f"{name}: SKILL.md links to missing file {target}")
    tutorials = ROOT / "tutorials" / name
    if not any(tutorials.glob("*.py")):
        err(f"{name}: no runnable tutorial in tutorials/{name}/ (every skill needs one)")


def text_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not (SKIP_DIRS & set(path.relative_to(ROOT).parts)):
            if path.suffix.lower() in {".png", ".pdf", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2"}:
                continue
            yield path


def main() -> int:
    skills = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    for folder in skills:
        check_skill(folder)

    if subprocess.run([sys.executable, str(ROOT / "tools" / "sync_shared.py"), "--check"]).returncode:
        err("shared files out of sync - run: python tools/sync_shared.py")

    for path in text_files():
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True, cfile=None)
            except py_compile.PyCompileError as e:
                err(f"{rel}: does not compile: {e.msg}")
        if rel == "tools/check_repo.py":
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for rx in SECRET_RES:
            if rx.search(content):
                err(f"{rel}: looks like it contains a secret ({rx.pattern[:30]}...)")

    claude = shutil.which("claude")
    if claude:
        res = subprocess.run([claude, "plugin", "validate", str(ROOT)], capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        if res.returncode:
            err("claude plugin validate failed:\n" + (res.stdout + res.stderr).strip())
    else:
        print("note: claude CLI not found - skipped `claude plugin validate`")

    for e in errors:
        print("ERROR " + e)
    print(f"{len(skills)} skills checked, {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
