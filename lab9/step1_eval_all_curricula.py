#!/usr/bin/env python3
"""Pool Lab 7B extraction metrics across all seven study-plan predictions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
OCR_DIR = ROOT_DIR / "src" / "ocr_system"
if str(OCR_DIR) not in sys.path:
    sys.path.insert(0, str(OCR_DIR))

from lab7b_curriculum import evaluate
import lab7_metrics as metrics


EVALUATION_PAIRS = [
    ("DSBA (coop)", "DSBA", "DSBA", "DSBA_academic_plan_coop.json"),
    ("DSBA (no_coop)", "DSBA_non_coop", "DSBA", "DSBA_academic_plan_no_coop.json"),
    ("BIT (coop)", "BIT", "BIT", "BIT_academic_plan_coop.json"),
    ("BIT (no_coop)", "BIT_non_coop", "BIT", "BIT_academic_plan_no_coop.json"),
    ("IT (coop)", "IT", "IT", "IT_academic_plan_coop.json"),
    ("IT (no_coop)", "IT_non_coop", "IT", "IT_academic_plan_no_coop.json"),
    ("AIT (single)", "AIT", "AIT", "AIT_academic_plan.json"),
]

COUNTERS = (
    "n_items",
    "n_exact",
    "n_missing",
    "n_hallucinated",
    "c_err",
    "c_ref",
    "c_sub",
    "c_del",
    "c_ins",
    "w_err",
    "w_ref",
)


def combine_stats(stat_sets: list[dict[str, metrics.FieldStat]]) -> dict[str, metrics.FieldStat]:
    """Pool raw counters across plans so rates are weighted by their denominators."""
    if not stat_sets:
        raise ValueError("At least one evaluation result is required")

    expected_keys = set(stat_sets[0])
    if any(set(stats) != expected_keys for stats in stat_sets[1:]):
        raise ValueError("All evaluation results must contain the same metric fields")

    combined = {
        key: metrics.FieldStat(stat_sets[0][key].label)
        for key in stat_sets[0]
    }
    for stats in stat_sets:
        for key, stat in stats.items():
            target = combined[key]
            for counter in COUNTERS:
                setattr(target, counter, getattr(target, counter) + getattr(stat, counter))
    return combined


def evaluate_all(output_path: Path) -> dict[str, metrics.FieldStat]:
    """Evaluate all seven saved predictions against their matching ground truths."""
    stat_sets = []
    for plan_name, prediction_dir, program, ground_truth_name in EVALUATION_PAIRS:
        prediction_path = ROOT_DIR / "work" / "lab7b_run" / prediction_dir / "pred_text.json"
        ground_truth_path = ROOT_DIR / "data" / "ground_truth" / program / ground_truth_name
        if not prediction_path.is_file():
            raise FileNotFoundError(f"Prediction not found for {plan_name}: {prediction_path}")
        if not ground_truth_path.is_file():
            raise FileNotFoundError(f"Ground truth not found for {plan_name}: {ground_truth_path}")

        prediction = json.loads(prediction_path.read_text(encoding="utf-8-sig"))
        ground_truth = json.loads(ground_truth_path.read_text(encoding="utf-8-sig"))
        stats, _ = evaluate(prediction, ground_truth)
        stat_sets.append(stats)

    pooled = combine_stats(stat_sets)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.save_csv(
        pooled,
        str(output_path),
        extra={"pipeline": "text", "plan": "All curricula (pooled)"},
    )
    return pooled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT_DIR / "lab9" / "reports" / "all_curricula" / "comparison.csv",
        help="Destination summary CSV (default: lab9/reports/all_curricula/comparison.csv)",
    )
    args = parser.parse_args(argv)

    pooled = evaluate_all(args.output)
    print(f"Pooled metrics CSV: {args.output}")
    for key, stat in pooled.items():
        wer = f"{stat.wer:.4%}" if stat.w_ref else "N/A"
        print(
            f"{key}: items={stat.n_items}, CER={stat.cer:.4%}, "
            f"WER={wer}, Exact Match={stat.acc:.4%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
