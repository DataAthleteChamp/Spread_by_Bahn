"""Read-only final preflight, runtime identity and a per-checkout single-actor lock."""
from __future__ import annotations

import fcntl
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone

from spread.client import SpreadError

from .bench import parse_variant
from .runner import ROOT, world_map

RUNTIME = ROOT / "results" / "final-runtime"
SOURCE_FILES = (
    "lab/live.py", "lab/readiness.py", "lab/bench.py", "lab/runner.py", "lab/desk.py",
    "lab/notes.py", "lab/train_risk.py", "lab/fit_ref.py", "lab/policies/__init__.py",
    "lab/policies/econ.py", "lab/policies/smart.py", "lab/final_config.json", "requirements.txt",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(variant, cls, params):
    frozen = json.loads((ROOT / "lab/final_config.json").read_text())
    if variant == "FINAL":
        _, frozen_cls, frozen_params = parse_variant(frozen["spec"])
        if cls is not frozen_cls or params != frozen["overrides"] or params != frozen_params:
            raise ValueError("FINAL differs from its frozen policy specification")
    models = {}
    if params.get("risk", cls.DEFAULTS.get("risk")):
        name = params.get("risk_file", cls.DEFAULTS["risk_file"])
        if name != os.path.basename(name):
            raise ValueError("Risk model must be a file in lab/models")
        models[name] = digest(ROOT / "lab/models" / name)
    for flag, name in (("winmodel", "win.json"), ("haz", "hazard.json")):
        if params.get(flag, cls.DEFAULTS.get(flag)):
            models[name] = digest(ROOT / "lab/models" / name)
    if params.get("ref_w", cls.DEFAULTS.get("ref_w", 1)) < 1:
        models["ref.json"] = digest(ROOT / "lab/models/ref.json")
    if variant == "FINAL":
        expected = {**frozen["models_sha256"], "ref.json": frozen["ref_json_sha256"]}
        for name, prefix in expected.items():
            if name not in models or not models[name].startswith(prefix):
                raise ValueError(f"Frozen model fingerprint mismatch: {name}")
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain", "--", "lab", "requirements.txt"],
                            cwd=ROOT, capture_output=True, text=True)
    return {
        "started_at": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(),
        "variant": variant, "policy": cls.NAME, "params": params,
        "params_sha256": hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest(),
        "git": git.stdout.strip() if git.returncode == 0 else None,
        "git_status": "available" if git.returncode == status.returncode == 0 else "unavailable",
        "source_worktree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
        "source_sha256": {path: digest(ROOT / path) for path in SOURCE_FILES},
        "models_sha256": models, "python": sys.version.split()[0],
        "packages": {name: importlib.metadata.version(name)
                     for name in ("spread", "numpy", "scipy", "scikit-learn")},
    }


def verify_files(startup):
    for name, expected in startup["source_sha256"].items():
        if digest(ROOT / name) != expected:
            raise RuntimeError(f"Source changed since startup: {name}; restart the runner before joining")
    for name, expected in startup["models_sha256"].items():
        if digest(ROOT / "lab/models" / name) != expected:
            raise RuntimeError(f"Model changed since startup: {name}; refusing mixed-version execution")


def preflight(client):
    worlds = client.worlds()
    world_map(client)
    try:
        final = client.final()
    except SpreadError as error:
        if error.status != 404:
            raise
        return {"authenticated": True, "known_worlds": len(worlds), "final": None}
    snapshot = client.world(final["worldId"]).snapshot()
    return {
        "authenticated": True, "known_worlds": len(worlds),
        "final": {**final, "ended": snapshot["now"] >= snapshot["endsAt"],
                  "snapshot_now": snapshot["now"], "ends_at": snapshot["endsAt"]},
    }


def write_record(name, data):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    target = RUNTIME / name
    temporary = RUNTIME / f"{name}.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(target)


@contextmanager
def single_runner():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / "runner.lock").open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another lab.live runner already holds this checkout's final lock") from error
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()) + "\n")
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
