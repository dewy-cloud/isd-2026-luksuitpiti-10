import csv
import tempfile
import unittest
from pathlib import Path

from lab9.step5_eval_query_complexity import (
    classify_query,
    enrich_rows,
    evaluate_by_complexity,
    write_csv_reports,
)


class QueryComplexityClassifierTests(unittest.TestCase):
    def test_classifies_single_table_lookup_as_level_1(self):
        row = {
            "question": "วิชา 06026200 มีกี่หน่วยกิต",
            "sql": "SELECT credits FROM course WHERE code = '06026200'",
        }
        self.assertEqual(classify_query(row), (1, "single_table_lookup"))

    def test_classifies_aggregate_as_level_2(self):
        row = {
            "question": "IT ปี 1 เทอม 1 เรียนกี่วิชา",
            "sql": (
                "SELECT COUNT(*) FROM v_plan WHERE program_id = 'IT' "
                "AND year = 1 AND semester = 1"
            ),
        }
        self.assertEqual(classify_query(row), (2, "aggregate_or_plan_filter"))

    def test_classifies_join_subquery_and_prerequisite_as_level_3(self):
        rows = [
            {
                "question": "วิชาบังคับก่อนของ Data Engineering คืออะไร",
                "sql": (
                    "SELECT requires FROM prerequisite WHERE code = "
                    "(SELECT code FROM course WHERE name_en LIKE '%Data Engineering%')"
                ),
            },
            {
                "question": "รายชื่อวิชาในแผน IT",
                "sql": "SELECT c.code FROM course c JOIN plan_item p ON p.code = c.code",
            },
        ]
        for row in rows:
            with self.subTest(sql=row["sql"]):
                self.assertEqual(classify_query(row), (3, "multi_table_relation"))

    def test_classifies_regulation_as_level_4_before_other_sql_features(self):
        row = {
            "question": "DSBA เกียรตินิยมอันดับหนึ่งต้องมี GPA เท่าไร",
            "sql": (
                "SELECT r.gpa_min FROM regulation r "
                "JOIN program p ON p.program_id = 'DSBA' LIMIT 1"
            ),
        }
        self.assertEqual(classify_query(row), (4, "regulation_query"))

    def test_classifies_default_dsba_without_program_in_question_as_level_5(self):
        row = {
            "question": "หลักสูตรนี้มีกี่หน่วยกิต",
            "sql": "SELECT total_credits FROM program WHERE program_id = 'DSBA'",
        }
        self.assertEqual(classify_query(row), (5, "ambiguous_default_dsba"))

    def test_explicit_override_has_priority(self):
        row = {
            "question": "หลักสูตรนี้มีกี่หน่วยกิต",
            "sql": "SELECT total_credits FROM program WHERE program_id = 'DSBA'",
        }
        self.assertEqual(
            classify_query(row, override_level=2),
            (2, "manual_override"),
        )


class QueryComplexityEvaluationTests(unittest.TestCase):
    def test_enriched_rows_include_llm_answer_and_expected_answer(self):
        rows = [
            {
                "question": "How many credits?",
                "answer": "132 credits",
                "expect": {"type": "value", "value": 132},
            },
            {
                "question": "Which courses require this?",
                "answer": "A, B",
                "expect": {"type": "set", "value": ["A", "B"]},
            },
            {
                "question": "Unknown course?",
                "answer": "No data found",
                "expect": {"type": "none", "value": None},
            },
        ]

        enriched = enrich_rows(rows)

        self.assertEqual(enriched[0]["llm_answer"], "132 credits")
        self.assertEqual(enriched[0]["expected_answer"], "132")
        self.assertEqual(enriched[0]["expected_answer_type"], "value")
        self.assertEqual(enriched[1]["expected_answer"], "A, B")
        self.assertEqual(enriched[1]["expected_answer_type"], "set")
        self.assertEqual(enriched[2]["expected_answer"], "No result expected")
        self.assertEqual(enriched[2]["expected_answer_type"], "none")

    def test_calculates_valid_sql_and_execution_accuracy_per_level(self):
        rows = [
            {
                "question": "วิชา 06026200 มีกี่หน่วยกิต",
                "sql": "SELECT credits FROM course WHERE code = '06026200'",
                "error": None,
                "correct": True,
            },
            {
                "question": "วิชา 99999999 มีกี่หน่วยกิต",
                "sql": "SELECT credits FROM course WHERE code = '99999999'",
                "error": None,
                "correct": False,
            },
            {
                "question": "IT ปี 1 เทอม 1 เรียนกี่วิชา",
                "sql": "SELECT COUNT(*) FROM v_plan WHERE program_id = 'IT'",
                "error": "syntax error",
                "correct": False,
            },
        ]

        report = evaluate_by_complexity(rows)

        self.assertEqual(report[1]["total_questions"], 2)
        self.assertEqual(report[1]["valid_sql_count"], 2)
        self.assertEqual(report[1]["valid_sql_rate"], 100.0)
        self.assertEqual(report[1]["correct_answers"], 1)
        self.assertEqual(report[1]["execution_accuracy"], 50.0)
        self.assertEqual(report[2]["total_questions"], 1)
        self.assertEqual(report[2]["valid_sql_rate"], 0.0)
        self.assertEqual(report[2]["execution_accuracy"], 0.0)

    def test_writes_detail_and_summary_csv(self):
        rows = [{
            "question": "วิชา 06026200 มีกี่หน่วยกิต",
            "sql": "SELECT credits FROM course WHERE code = '06026200'",
            "error": None,
            "correct": True,
            "why": "ตรง",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            detail_path = Path(tmp) / "detail.csv"
            summary_path = Path(tmp) / "summary.csv"
            write_csv_reports(rows, detail_path, summary_path)

            with detail_path.open(encoding="utf-8-sig", newline="") as f:
                detail = list(csv.DictReader(f))
            with summary_path.open(encoding="utf-8-sig", newline="") as f:
                summary = list(csv.DictReader(f))

        self.assertEqual(detail[0]["complexity_level"], "1")
        self.assertEqual(detail[0]["valid_sql"], "True")
        self.assertEqual(summary[0]["level"], "1")
        self.assertEqual(summary[0]["execution_accuracy"], "100.0")

    def test_detail_csv_includes_llm_and_expected_answers(self):
        rows = [{
            "question": "How many credits?",
            "sql": "SELECT credits FROM course",
            "error": None,
            "correct": True,
            "answer": "3 credits",
            "expect": {"type": "value", "value": 3},
        }]
        with tempfile.TemporaryDirectory() as tmp:
            detail_path = Path(tmp) / "detail.csv"
            summary_path = Path(tmp) / "summary.csv"
            write_csv_reports(rows, detail_path, summary_path)
            with detail_path.open(encoding="utf-8-sig", newline="") as handle:
                detail = list(csv.DictReader(handle))

        self.assertEqual(detail[0]["llm_answer"], "3 credits")
        self.assertEqual(detail[0]["expected_answer"], "3")
        self.assertEqual(detail[0]["expected_answer_type"], "value")


if __name__ == "__main__":
    unittest.main()
