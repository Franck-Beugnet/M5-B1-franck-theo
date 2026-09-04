"""Fixtures pytest — évaluation continue (M5-B2).

Ajoute scripts/ au sys.path pour que `import evaluate_model` fonctionne
quand pytest est lancé depuis la racine du repo (`pytest tests`).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
