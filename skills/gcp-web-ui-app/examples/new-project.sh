#!/usr/bin/env bash
# A new project from this skill, the way an agent starts one: an empty folder, the skill in .claude/skills/,
# the template copied in, its tests run, the app started and asked for a run.
# Run from the skill folder:   cd skills/gcp-web-ui-app && bash examples/new-project.sh
# Result: out/my-app/ - a working app; open it with:  cd out/my-app && python -m app
set -e
P=out/my-app
rm -rf "$P" && mkdir -p "$P/.claude/skills/gcp-web-ui-app"
cp SKILL.md "$P/.claude/skills/gcp-web-ui-app/" && cp -r template "$P/.claude/skills/gcp-web-ui-app/"
cd "$P"
cp -rn .claude/skills/gcp-web-ui-app/template/. .        # step 1 of SKILL.md
python -m unittest                                        # the template's own tests
RUNS_DIR=runs QUIET=1 python -m app --port 8097 & PID=$!
trap 'kill $PID 2>/dev/null' EXIT
sleep 2
python - <<'PY'
import json, time, urllib.request
base = "http://127.0.0.1:8097"
req = urllib.request.Request(base + "/api/runs", json.dumps({"settings": {"steps": 10}}).encode(), {"Content-Type": "application/json"})
run = json.load(urllib.request.urlopen(req, timeout=10))["run"]
for _ in range(50):
    i = json.load(urllib.request.urlopen(f"{base}/api/runs/{run}", timeout=10))
    if i["state"] in ("done", "failed"):
        break
    time.sleep(0.1)
print(f"run {run}: {i['state']} - {i['headline']}")
PY
