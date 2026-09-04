"""Tests pytest pour l'évaluation continue (scripts/evaluate_model.py).

Mini-cours : `08_Evaluation_continue_seuils_essentiel.md`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import joblib
import pandas as pd
import pytest

import evaluate_model as em

ROOT = Path(__file__).parent.parent


def _load_model_and_meta():
    model = joblib.load(em.MODELS_DIR / "pyrenex_risk_v2.joblib")
    meta = json.loads((em.MODELS_DIR / "pyrenex_risk_v2.json").read_text(encoding="utf-8"))
    return model, meta


def test_compute_metrics_returns_the_four_target_metrics():
    model, meta = _load_model_and_meta()
    df = pd.read_csv(em.REFERENCE_SET)

    metrics = em.compute_metrics(model, df, meta)

    assert set(metrics) == {"f1_macro", "f1_default", "roc_auc", "recall_default"}
    assert all(0.0 <= value <= 1.0 for value in metrics.values())


def test_check_thresholds_no_violation_when_metrics_match_baseline():
    baseline = {"f1_macro": 0.60, "f1_default": 0.43, "roc_auc": 0.72, "recall_default": 0.66}

    assert em.check_thresholds(baseline, baseline) == []


def test_check_thresholds_flags_absolute_min_violation():
    baseline = {"f1_macro": 0.60, "f1_default": 0.43, "roc_auc": 0.72, "recall_default": 0.66}
    metrics = {**baseline, "f1_macro": 0.10}  # sous le plancher absolu (0.55)

    violations = em.check_thresholds(metrics, baseline)

    assert any("f1_macro" in v and "plancher absolu" in v for v in violations)


def test_check_thresholds_flags_relative_drop_violation():
    baseline = {"f1_macro": 0.60, "f1_default": 0.43, "roc_auc": 0.90, "recall_default": 0.66}
    metrics = {**baseline, "roc_auc": 0.70}  # au-dessus du plancher, mais chute > tolérance (0.06)

    violations = em.check_thresholds(metrics, baseline)

    assert any("roc_auc" in v and "baiss" in v for v in violations)
    assert not any("roc_auc" in v and "plancher absolu" in v for v in violations)


def test_load_baseline_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(em, "REFERENCE_BASELINE", tmp_path / "missing.json")

    with pytest.raises(SystemExit):
        em.load_baseline()


def test_load_reference_set_rejects_too_few_rows(tmp_path, monkeypatch):
    small = tmp_path / "small.csv"
    pd.DataFrame({"loan_amnt": [1, 2], "loan_status": ["Fully Paid", "Charged Off"]}).to_csv(
        small, index=False
    )
    monkeypatch.setattr(em, "REFERENCE_SET", small)

    with pytest.raises(SystemExit):
        em.load_reference_set()


def test_freeze_baseline_writes_metrics_to_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(em, "REFERENCE_BASELINE", tmp_path / "baseline.json")
    model, meta = _load_model_and_meta()
    df = pd.read_csv(em.REFERENCE_SET)

    result = em.freeze_baseline(model, df, meta)

    written = json.loads((tmp_path / "baseline.json").read_text(encoding="utf-8"))
    assert written == result
    assert written["n_reference"] == len(df)
    assert written["metrics"] == em.compute_metrics(model, df, meta)


def test_script_exits_zero_on_normal_release():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "evaluate_model.py"), "--release-tag", "pytest-ok"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["violations"] == []


def test_script_exits_nonzero_on_degrade():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "evaluate_model.py"),
            "--release-tag",
            "pytest-degrade",
            "--degrade",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["violations"]
