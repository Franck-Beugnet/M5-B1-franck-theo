from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "lending_club_holdout.csv"
DEFAULT_OUTPUT = ROOT / "data" / "reference_set.csv"


def build_balanced_reference_set(df: pd.DataFrame, target_col: str, size: int) -> pd.DataFrame:
    """Build a class-balanced reference set with deterministic sampling."""
    if size % 2 != 0:
        raise ValueError("size must be even for balanced sampling")

    positives = df[df[target_col] == "Charged Off"]
    negatives = df[df[target_col] == "Fully Paid"]
    per_class = size // 2

    if len(positives) < per_class or len(negatives) < per_class:
        raise ValueError(
            "Not enough rows to sample balanced classes "
            f"(need {per_class} each, got {len(positives)} and {len(negatives)})"
        )

    # Fixed seeds guarantee a stable output file across runs.
    pos_sample = positives.sample(n=per_class, random_state=42)
    neg_sample = negatives.sample(n=per_class, random_state=43)
    combined = pd.concat([pos_sample, neg_sample], ignore_index=True)
    return combined.sample(frac=1.0, random_state=44).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a stable reference_set.csv from lending_club_holdout.csv"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--size", type=int, default=500)
    parser.add_argument("--target-column", default="loan_status")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    df = pd.read_csv(args.input)
    if args.target_column not in df.columns:
        raise SystemExit(
            f"Target column '{args.target_column}' not found in source data. "
            f"Columns: {', '.join(df.columns)}"
        )

    ref = build_balanced_reference_set(df, args.target_column, args.size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ref.to_csv(args.output, index=False)

    counts = ref[args.target_column].value_counts().to_dict()
    print(f"Wrote {args.output} with {len(ref)} rows")
    print(f"Class distribution: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
