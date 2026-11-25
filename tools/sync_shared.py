#!/usr/bin/env python3
"""Copy shared/ files into the skills that use them, so every skill folder stays self-contained.

    python tools/sync_shared.py          copy
    python tools/sync_shared.py --check  exit 1 if any copy differs from shared/ (used by CI)

Edit the files under shared/, never the copies inside skills/.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# skill -> shared files it carries (path relative to shared/ == path inside the skill)
USES = {
    "slides": ["scripts/_browser.py", "theme/tokens.css"],
    "diagrams": ["scripts/_browser.py", "theme/tokens.css"],
}


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for skill, files in USES.items():
        for rel in files:
            src, dst = ROOT / "shared" / rel, ROOT / "skills" / skill / rel
            if dst.is_file() and dst.read_bytes() == src.read_bytes():
                continue
            stale.append(dst.relative_to(ROOT))
            if not check:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
    for path in stale:
        print(("out of date: " if check else "updated: ") + str(path))
    if check and stale:
        print("run: python tools/sync_shared.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
