"""The domain of this app - the only file a new app has to change.

TITLE     name in the top bar
SETTINGS  the Settings form; the server validates a run's settings against it
run()     does the work: run(settings, out, log) -> results (saved as results.json, drawn on the Run tab)

results keys (all optional): headline, verdict (good|warn|bad|info), metrics [{label, value, status?, hint?}],
chart {title, x: [...], series: [{name, values: [...]}]}, table {columns: [...], rows: [[...]]}, notes [str].

The example below is a placeholder (a seeded random walk); replace it with the real domain.
"""
from __future__ import annotations

import random

TITLE = "Web UI app"

SETTINGS = [
    {"name": "steps", "label": "Steps", "type": "int", "default": 30, "min": 1, "max": 1000, "help": "length of the walk"},
    {"name": "seed", "label": "Seed", "type": "int", "default": 1, "help": "same seed, same result"},
    {"name": "drift", "label": "Drift", "type": "float", "default": 0.1, "min": -1, "max": 1},
    {"name": "mode", "label": "Mode", "type": "choice", "default": "walk", "options": ["walk", "fail"],
     "help": "fail: shows how a failed run looks"},
]


def run(settings: dict, out, log) -> dict:
    if settings["mode"] == "fail":
        raise RuntimeError("asked to fail (mode = fail)")
    rnd = random.Random(settings["seed"])
    x, values = 0.0, []
    for i in range(settings["steps"]):
        x += settings["drift"] + rnd.uniform(-1, 1)
        values.append(round(x, 3))
    log(f"walked {len(values)} steps")
    end = values[-1]
    last = values[-10:]
    return {
        "headline": f"Ended at {end:+.2f} after {len(values)} steps",
        "verdict": "good" if end >= 0 else "warn",
        "metrics": [{"label": "end", "value": f"{end:+.2f}"}, {"label": "max", "value": f"{max(values):+.2f}"},
                    {"label": "min", "value": f"{min(values):+.2f}"}],
        "chart": {"title": "Position by step", "x": list(range(1, len(values) + 1)),
                  "series": [{"name": "position", "values": values}]},
        "table": {"columns": ["step", "position"], "rows": [[i + 1, v] for i, v in enumerate(last, len(values) - len(last))]},
        "notes": ["Placeholder domain: replace app/runner.py."],
    }
