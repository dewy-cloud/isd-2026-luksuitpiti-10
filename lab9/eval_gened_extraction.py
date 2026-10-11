#!/usr/bin/env python3
"""Compare extracted GenEd courses with ground truth and write comparison.csv."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
OCR_DIR = ROOT_DIR / "src" / "ocr_system"
if str(OCR_DIR) not in sys.path:
    sys.path.insert(0, str(OCR_DIR))

import lab7_metrics as metrics


FIELDS = {
    "code": ("Course code", lambda course: course.get("code")),
    "name_th": ("Thai course name", lambda course: course.get("name_th")),
    "credits_total": ("Credits (total)", lambda course: credit_part(course.get("credits"), 0)),
    "lecture_h": ("Lecture hours", lambda course: credit_part(course.get("credits"), 1)),
    "lab_h": ("Lab hours", lambda course: credit_part(course.get("credits"), 2)),
    "self_h": ("Self-study hours", lambda course: credit_part(course.get("credits"), 3)),
}


def credit_part(value: Any, index: int) -> str:
    """Extract total credits or one L-P-S component from a GT credit string."""
    text = str(value or "")
    match = re.search(r"(\d+)\s*\(\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*\)", text)
    if match:
        return match.group(index + 1)
    total = re.match(r"\s*(\d+)", text)
    return total.group(1) if index == 0 and total else ""


def _course_list(data: Any, label: str) -> list[dict[str, Any]]:
    courses = data.get("courses") if isinstance(data, dict) else data
    if not isinstance(courses, list) or any(not isinstance(item, dict) for item in courses):
        raise ValueError(f"{label} must be a JSON list of courses or an object with a 'courses' list")
    return courses


def _index_by_code(courses: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for course in courses:
        code = str(course.get("code") or "").strip()
        if not code:
            raise ValueError(f"{label} contains a course without a code")
        if code in indexed:
            raise ValueError(f"{label} contains duplicate course code: {code}")
        indexed[code] = course
    return indexed


def evaluate_courses(
    ground_truth: list[dict[str, Any]], predictions: list[dict[str, Any]]
) -> dict[str, metrics.FieldStat]:
    """Evaluate only fields present in both GenEd GT and extraction output."""
    gt_by_code = _index_by_code(ground_truth, "Ground truth")
    pred_by_code = _index_by_code(predictions, "Prediction")
    stats = {key: metrics.FieldStat(label) for key, (label, _) in FIELDS.items()}

    for code, reference in gt_by_code.items():
        prediction = pred_by_code.get(code, {})
        for key, (_, getter) in FIELDS.items():
            ref_value = getter(reference)
            pred_value = (
                prediction.get("credits", "")
                if key == "credits_total"
                else prediction.get(key, "")
            )
            stats[key].add(
                ref_value,
                pred_value,
                key=code,
                track_wer=(key == "name_th"),
            )

    for code, prediction in pred_by_code.items():
        if code in gt_by_code:
            continue
        for key in FIELDS:
            pred_value = (
                prediction.get("credits", "")
                if key == "credits_total"
                else prediction.get(key, "")
            )
            stats[key].add(
                "", pred_value, key=code, track_wer=(key == "name_th")
            )

    return stats


def run_evaluation(
    ground_truth_path: Path, prediction_path: Path, output_path: Path
) -> dict[str, metrics.FieldStat]:
    ground_truth_data = json.loads(ground_truth_path.read_text(encoding="utf-8-sig"))
    prediction_data = json.loads(prediction_path.read_text(encoding="utf-8-sig"))
    ground_truth = _course_list(ground_truth_data, "Ground truth")
    predictions = _course_list(prediction_data, "Prediction")
    stats = evaluate_courses(ground_truth, predictions)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.save_csv(
        stats,
        str(output_path),
        extra={"pipeline": "Typhoon OCR + Qwen JSON", "plan": "GenEd"},
    )
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=ROOT_DIR / "data/ground_truth/general_education_ground_truth.json",
        help="Ground-truth GenEd JSON",
    )
    parser.add_argument(
        "--prediction",
        type=Path,
        default=ROOT_DIR / "work/lab7b_run/gened_courses.json",
        help="Extracted GenEd courses JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT_DIR / "work/lab7b_run/gened/comparison.csv",
        help="Destination comparison CSV",
    )
    args = parser.parse_args(argv)

    stats = run_evaluation(args.ground_truth, args.prediction, args.output)
    print(f"Comparison CSV: {args.output}")
    for key, stat in stats.items():
        print(
            f"{key}: exact={stat.n_exact}/{stat.n_items} ({stat.acc:.2%}), "
            f"CER={stat.cer:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
