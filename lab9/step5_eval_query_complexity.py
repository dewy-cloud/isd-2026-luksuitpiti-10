"""Evaluate NL2SQL accuracy grouped by deterministic query-complexity levels.

The script reads an existing ``eval_result.json``.  It does not call an LLM
and does not modify the source benchmark.  CSV files use UTF-8 with BOM so
Thai text opens correctly in Excel.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT_DIR / "work" / "lab8b_run" / "eval_result.json"
DEFAULT_DETAIL = ROOT_DIR / "lab9" / "reports" / "query_complexity_detail.csv"
DEFAULT_SUMMARY = ROOT_DIR / "lab9" / "reports" / "query_complexity_summary.csv"

LEVEL_NAMES = {
    1: "Simple Lookup",
    2: "Filter & Aggregate",
    3: "Multi-table Relation",
    4: "Regulation Query",
    5: "Ambiguous Query",
}
PROGRAM_MARKERS = (
    "DSBA",
    "BIT",
    "AIT",
    "IT",
    "ธุรกิจอัจฉริยะ",
    "เทคโนโลยีสารสนเทศ",
    "ปัญญาประดิษฐ์",
)


def _has_explicit_program(question: str) -> bool:
    upper = question.upper()
    return any(marker.upper() in upper for marker in PROGRAM_MARKERS)


def _uses_default_dsba(question: str, sql: str) -> bool:
    normalized_sql = re.sub(r"\s+", " ", sql.upper())
    selects_dsba = bool(
        re.search(r"PROGRAM_ID\s*=\s*['\"]DSBA['\"]", normalized_sql)
    )
    return selects_dsba and not _has_explicit_program(question)


def classify_query(
    row: dict[str, Any], override_level: int | None = None
) -> tuple[int, str]:
    """Return ``(level, reason)`` for one evaluated query.

    Manual labels take priority.  Automatic rules are deliberately ordered:
    ambiguity, regulations, relationships, aggregation/plan filters, lookup.
    """
    if override_level is not None:
        if override_level not in LEVEL_NAMES:
            raise ValueError(f"complexity level must be 1-5, got {override_level}")
        return override_level, "manual_override"

    question = str(row.get("question") or "")
    sql = str(row.get("sql") or "")
    normalized = re.sub(r"\s+", " ", sql.upper()).strip()

    if _uses_default_dsba(question, sql):
        return 5, "ambiguous_default_dsba"

    if re.search(r"\bREGULATION\b", normalized):
        return 4, "regulation_query"

    select_count = len(re.findall(r"\bSELECT\b", normalized))
    if (
        re.search(r"\bJOIN\b", normalized)
        or select_count > 1
        or re.search(r"\bPREREQUISITE\b", normalized)
    ):
        return 3, "multi_table_relation"

    has_aggregate = bool(
        re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", normalized)
        or re.search(r"\b(GROUP BY|HAVING)\b", normalized)
    )
    has_plan_filter = bool(
        re.search(r"\bV_(PLAN|SEMESTER_CREDITS)\b", normalized)
        or (
            re.search(r"\bPLAN_ITEM\b", normalized)
            and len(re.findall(r"\bAND\b", normalized)) >= 2
        )
    )
    if has_aggregate or has_plan_filter:
        return 2, "aggregate_or_plan_filter"

    return 1, "single_table_lookup"


def load_overrides(path: Path | None) -> dict[str, int]:
    """Load optional JSON labels keyed by 1-based row number or question."""
    if path is None:
        return {}
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError("override file must be a JSON object")
    overrides: dict[str, int] = {}
    for key, value in raw.items():
        level = int(value)
        if level not in LEVEL_NAMES:
            raise ValueError(f"override {key!r} must be level 1-5")
        overrides[str(key)] = level
    return overrides


def _override_for(
    row: dict[str, Any], row_number: int, overrides: dict[str, int]
) -> int | None:
    return overrides.get(str(row_number), overrides.get(str(row.get("question") or "")))


def enrich_rows(
    rows: list[dict[str, Any]], overrides: dict[str, int] | None = None
) -> list[dict[str, Any]]:
    labels = overrides or {}
    enriched = []
    for number, row in enumerate(rows, 1):
        level, reason = classify_query(row, _override_for(row, number, labels))
        enriched.append(
            {
                "question_number": number,
                "question": row.get("question", ""),
                "complexity_level": level,
                "level_name": LEVEL_NAMES[level],
                "classification_reason": reason,
                "valid_sql": not bool(row.get("error")),
                "correct": bool(row.get("correct")),
                "error": row.get("error") or "",
                "why": row.get("why") or "",
                "sql": row.get("sql") or "",
            }
        )
    return enriched


def evaluate_by_complexity(
    rows: list[dict[str, Any]], overrides: dict[str, int] | None = None
) -> dict[int, dict[str, Any]]:
    """Calculate Valid SQL and Execution Accuracy for each level."""
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in enrich_rows(rows, overrides):
        grouped[int(row["complexity_level"])].append(row)

    report: dict[int, dict[str, Any]] = {}
    for level in LEVEL_NAMES:
        items = grouped[level]
        total = len(items)
        valid = sum(bool(item["valid_sql"]) for item in items)
        correct = sum(bool(item["correct"]) for item in items)
        report[level] = {
            "level": level,
            "level_name": LEVEL_NAMES[level],
            "total_questions": total,
            "valid_sql_count": valid,
            "valid_sql_rate": round(valid / total * 100, 2) if total else 0.0,
            "correct_answers": correct,
            "execution_accuracy": round(correct / total * 100, 2) if total else 0.0,
        }
    return report


def write_csv_reports(
    rows: list[dict[str, Any]],
    detail_path: Path,
    summary_path: Path,
    overrides: dict[str, int] | None = None,
) -> dict[int, dict[str, Any]]:
    """Write question-level and level-summary CSV reports."""
    detail_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    enriched = enrich_rows(rows, overrides)
    summary = evaluate_by_complexity(rows, overrides)

    detail_fields = [
        "question_number",
        "question",
        "complexity_level",
        "level_name",
        "classification_reason",
        "valid_sql",
        "correct",
        "error",
        "why",
        "sql",
    ]
    with detail_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(enriched)

    summary_fields = [
        "level",
        "level_name",
        "total_questions",
        "valid_sql_count",
        "valid_sql_rate",
        "correct_answers",
        "execution_accuracy",
    ]
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary[level] for level in LEVEL_NAMES)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate Valid SQL and Execution Accuracy by query complexity"
    )
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--labels", type=Path, help="optional JSON manual overrides")
    parser.add_argument("--detail-csv", type=Path, default=DEFAULT_DETAIL)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise ValueError("evaluation input must be a JSON array")
    overrides = load_overrides(args.labels)
    summary = write_csv_reports(
        rows, args.detail_csv, args.summary_csv, overrides
    )

    print("Query Complexity Evaluation")
    print("Level | Questions | Valid SQL | Execution Accuracy")
    for level, metrics in summary.items():
        print(
            f"{level:>5} | {metrics['total_questions']:>9} | "
            f"{metrics['valid_sql_rate']:>8.2f}% | "
            f"{metrics['execution_accuracy']:>17.2f}%"
        )
    print(f"Detail CSV : {args.detail_csv}")
    print(f"Summary CSV: {args.summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
