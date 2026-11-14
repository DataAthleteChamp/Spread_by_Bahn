"""Fetch roster.json for saved runs that lack it (ended worlds stay readable)."""
from pathlib import Path
import json
from spread.client import Client
from .runner import ROOT, load_env
load_env(); c = Client()
for d in (ROOT / "data/runs").iterdir():
    if d.is_dir() and not (d / "roster.json").exists():
        (d / "roster.json").write_text(json.dumps(c.world(d.name).roster())); print("roster", d.name)
