import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
OCR_DIR = ROOT_DIR / "src" / "ocr_system"
for search_path in (ROOT_DIR, OCR_DIR):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

import lab7_metrics as metrics
from lab9.step1_eval_all_curricula import combine_stats


class CombineCurriculaStatsTests(unittest.TestCase):
    def test_combines_raw_counts_before_calculating_pooled_metrics(self):
        first = metrics.FieldStat("Course name")
        first.add("ABC", "ABC")
        first.add("DEF", "DE")
        second = metrics.FieldStat("Course name")
        second.add("GHI", "GHI")

        combined = combine_stats([{"name": first}, {"name": second}])
        result = combined["name"]

        self.assertEqual(result.n_items, 3)
        self.assertEqual(result.n_exact, 2)
        self.assertEqual(result.c_ref, 9)
        self.assertEqual(result.c_err, 1)
        self.assertAlmostEqual(result.cer, 1 / 9)


if __name__ == "__main__":
    unittest.main()
