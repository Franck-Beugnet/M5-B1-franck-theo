from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "evaluate_model.py"
BASELINE_PATH = ROOT / "data" / "reference_baseline.json"


def _run_eval(args: list[str], tracking_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["MLFLOW_TRACKING_URI"] = tracking_dir.as_uri()
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)


def _parse_last_json(stdout: str) -> dict:
    lines = [line for line in stdout.splitlines() if line.strip()]
    for i in range(len(lines)):
        chunk = "\n".join(lines[i:])
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            continue
    raise AssertionError(f"No JSON payload found in output:\n{stdout}")


def test_reference_run_matches_baseline_and_returns_zero(tmp_path: Path):
    result = _run_eval(["--release-tag", "pytest-reference"], tmp_path / "mlruns")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _parse_last_json(result.stdout)
    assert payload["release_blocked"] is False
    assert payload["violations"] == []
    assert set(payload["metrics"]) == {
        "f1_macro",
        "f1_default",
        "roc_auc",
        "recall_default",
    }
    for delta in payload["deltas_vs_baseline"].values():
        assert abs(float(delta)) < 1e-9


def test_degrade_run_returns_non_zero_and_lists_violations(tmp_path: Path):
    result = _run_eval(
        ["--release-tag", "pytest-degrade", "--degrade"],
        tmp_path / "mlruns",
    )
    assert result.returncode != 0, result.stdout + result.stderr

    payload = _parse_last_json(result.stdout)
    assert payload["release_blocked"] is True
    assert len(payload["violations"]) >= 1


def test_missing_baseline_file_fails_with_explicit_message(tmp_path: Path):
    backup_path = tmp_path / "reference_baseline_backup.json"
    BASELINE_PATH.replace(backup_path)
    try:
        result = _run_eval(["--release-tag", "pytest-no-baseline"], tmp_path / "mlruns")
        assert result.returncode != 0
        assert "--freeze-baseline" in (result.stdout + result.stderr)
    finally:
        backup_path.replace(BASELINE_PATH)
