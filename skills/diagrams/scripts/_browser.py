"""Headless Chrome / Edge / Chromium helpers and theme lookup (standard library only).

The same file sits in skills/slides and skills/diagrams so each skill works on its own;
keep the two copies identical (CI checks it).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLED_THEME = HERE.parent / "assets" / "theme.css"

_CANDIDATES = {
    "win32": [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    ],
    "darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ],
}
_ON_PATH = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge", "chrome-headless-shell"]
# where `npx @puppeteer/browsers install chrome-headless-shell@stable --path ~/.cache/puppeteer` puts it
# (no root needed - the easy way to get a browser in WSL, a container or CI)
_PUPPETEER_CACHE = Path.home() / ".cache" / "puppeteer"


def find_browser() -> str:
    """Path to a Chromium-based browser; CHROME_PATH wins. Exits with a clear message if none is found."""
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).is_file():
        return env
    for raw in _CANDIDATES.get(sys.platform, []):
        path = Path(os.path.expandvars(raw))
        if path.is_file():
            return str(path)
    for name in _ON_PATH:
        found = shutil.which(name)
        if found:
            return found
    cached = sorted(_PUPPETEER_CACHE.glob("chrome-headless-shell/*/*/chrome-headless-shell"), reverse=True)
    if cached:
        return str(cached[0])
    sys.exit("No Chrome, Edge or Chromium found. Install one, set CHROME_PATH, or (Linux/WSL, no root):\n"
             "  npx @puppeteer/browsers install chrome-headless-shell@stable --path ~/.cache/puppeteer")


def file_url(path: Path, query: str = "") -> str:
    url = Path(path).resolve().as_uri()
    return f"{url}?{query}" if query else url


def run_headless(args: list[str], timeout: int = 90) -> subprocess.CompletedProcess:
    """Run the browser headless with a throwaway profile (so an open browser window never interferes)."""
    with tempfile.TemporaryDirectory(prefix="agent-skills-chrome-") as profile:
        cmd = [
            find_browser(), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--disable-extensions", "--hide-scrollbars", "--allow-file-access-from-files",
            f"--user-data-dir={profile}", *args,
        ]
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def dump_dom(url: str, budget_ms: int = 4000, size: str = "1600,900") -> str:
    """The page's DOM after its scripts ran - how the check scripts read results back from the page."""
    res = run_headless([f"--window-size={size}", f"--virtual-time-budget={budget_ms}", "--dump-dom", url])
    if res.returncode != 0 and not res.stdout:
        sys.exit(f"Browser failed: {res.stderr.strip()[:500]}")
    return res.stdout


def screenshot(url: str, out: Path, width: int, height: int, budget_ms: int = 2500) -> Path:
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    run_headless([f"--window-size={width},{height}", f"--virtual-time-budget={budget_ms}", f"--screenshot={out}", url])
    if not out.is_file():
        sys.exit(f"Screenshot was not written: {out}")
    return out


def print_pdf(url: str, out: Path, budget_ms: int = 4000) -> Path:
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    run_headless(["--no-pdf-header-footer", "--print-to-pdf-no-header", f"--virtual-time-budget={budget_ms}",
                  f"--print-to-pdf={out}", url], timeout=180)
    if not out.is_file():
        sys.exit(f"PDF was not written: {out}")
    return out


def extract_block(dom: str, element_id: str) -> str | None:
    """Text content of <pre id="..."> (or any element) written by an in-page check."""
    m = re.search(rf'<(\w+)[^>]*id="{re.escape(element_id)}"[^>]*>(.*?)</\1>', dom, re.S)
    if not m:
        return None
    import html
    return html.unescape(m.group(2))


# ---------- theme ----------

def resolve_theme(arg: str | None = None) -> Path:
    """--theme > AGENT_THEME > ./.agent-theme.css > bundled default."""
    for source, candidate in (("--theme", arg), ("AGENT_THEME", os.environ.get("AGENT_THEME"))):
        if candidate:
            path = Path(candidate)
            if not path.is_file():
                sys.exit(f"Theme file given by {source} not found: {candidate}")
            return path.resolve()
    local = Path(".agent-theme.css")
    return local.resolve() if local.is_file() else BUNDLED_THEME


def theme_css(arg: str | None = None) -> str:
    """Bundled defaults followed by the chosen theme, so a custom theme may override only some variables."""
    chosen = resolve_theme(arg)
    css = BUNDLED_THEME.read_text(encoding="utf-8")
    if chosen != BUNDLED_THEME:
        css += f"\n/* theme: {chosen.name} */\n" + chosen.read_text(encoding="utf-8")
    return css


def theme_vars(arg: str | None = None) -> dict[str, str]:
    """CSS custom properties as a dict: {'accent': '#1f5fbf', ...}; later definitions win."""
    css = re.sub(r"/\*.*?\*/", "", theme_css(arg), flags=re.S)
    return {k: v.strip() for k, v in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", css)}
