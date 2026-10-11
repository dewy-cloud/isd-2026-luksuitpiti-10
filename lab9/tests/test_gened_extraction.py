import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
OCR_DIR = ROOT_DIR / "src" / "ocr_system"
if str(OCR_DIR) not in sys.path:
    sys.path.insert(0, str(OCR_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from lab9.eval_gened_extraction import evaluate_courses


class GenEdExtractionEvaluationTests(unittest.TestCase):
    def test_compares_available_fields_and_counts_missing_and_spurious_courses(self):
        ground_truth = [
            {
                "code": "90641001",
                "name_th": "วิชาหนึ่ง",
                "credits": "2(1-2-3)",
            },
            {
                "code": "90641002",
                "name_th": "วิชาสอง",
                "credits": "3(3-0-6)",
            },
        ]
        predictions = [
            {
                "code": "90641001",
                "name_th": "วิชาหนึ่ง",
                "credits": 2,
                "lecture_h": 1,
                "lab_h": 2,
                "self_h": 3,
            },
            {
                "code": "90641003",
                "name_th": "วิชาเกิน",
                "credits": 1,
                "lecture_h": 1,
                "lab_h": 0,
                "self_h": 2,
            },
        ]

        stats = evaluate_courses(ground_truth, predictions)

        self.assertEqual(set(stats), {
            "code", "name_th", "credits_total", "lecture_h", "lab_h", "self_h"
        })
        self.assertEqual(stats["code"].n_items, 3)
        self.assertEqual(stats["code"].n_missing, 1)
        self.assertEqual(stats["code"].n_hallucinated, 1)
        self.assertEqual(stats["credits_total"].n_exact, 1)
        self.assertEqual(stats["lecture_h"].n_exact, 1)
        self.assertEqual(stats["lab_h"].n_exact, 1)
        self.assertEqual(stats["self_h"].n_exact, 1)

    def test_credits_breakdown_is_parsed_from_ground_truth(self):
        stats = evaluate_courses(
            [{"code": "90641001", "name_th": "ทดสอบ", "credits": "3 (2-2-5)"}],
            [{
                "code": "90641001", "name_th": "ทดสอบ", "credits": 3,
                "lecture_h": 2, "lab_h": 2, "self_h": 5,
            }],
        )

        for field in ("code", "name_th", "credits_total", "lecture_h", "lab_h", "self_h"):
            self.assertEqual(stats[field].acc, 1.0, field)


if __name__ == "__main__":
    unittest.main()
