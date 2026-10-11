import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = ROOT / "work" / "lab8b_run" / "gold_questions.json"
LABEL_PATH = ROOT / "lab9" / "query_complexity_labels.json"

EXPECTED_REGULATION_QUESTIONS = {
    "ภาคการศึกษาปกติต้องลงทะเบียนอย่างน้อยกี่หน่วยกิต": 9,
    "ภาคการศึกษาปกติลงทะเบียนได้สูงสุดกี่หน่วยกิต": 22,
    "กรณีพิเศษเพื่อขอจบลงทะเบียนได้สูงสุดกี่หน่วยกิต": 27,
    "ภาคการศึกษาพิเศษฤดูร้อนลงทะเบียนได้สูงสุดกี่หน่วยกิต": 9,
    "ทุจริตในการสอบครั้งแรกได้รับโทษอะไร": "พักการเรียน 1 ภาคการศึกษาถัดไป",
    "ทุจริตในการสอบซ้ำมากกว่า 3 ครั้งได้รับโทษอะไร": "พ้นสภาพการเป็นนักศึกษา",
    "GPA สะสมสูงสุดที่ยังถือว่าติดภาคทัณฑ์คือเท่าไร": 1.99,
    "GPA สะสมสูงสุดตามเกณฑ์พ้นสภาพนักศึกษาคือเท่าไร": 0.99,
    "เกียรตินิยมอันดับ 1 เหรียญทองต้องมี GPA สะสมอย่างน้อยเท่าไร": 3.75,
    "เกียรตินิยมอันดับ 1 ต้องมี GPA สะสมอย่างน้อยเท่าไร": 3.5,
}


class RegulationGoldQuestionTests(unittest.TestCase):
    def test_gold_questions_do_not_contain_duplicate_question_text(self):
        questions = json.loads(GOLD_PATH.read_text(encoding="utf-8-sig"))
        texts = [item["question"] for item in questions]

        self.assertEqual(len(texts), len(set(texts)))

    def test_gold_set_contains_ten_regulation_questions_with_verified_answers(self):
        questions = json.loads(GOLD_PATH.read_text(encoding="utf-8-sig"))
        actual = {
            item["question"]: item["expect"]["value"]
            for item in questions
            if item["question"] in EXPECTED_REGULATION_QUESTIONS
        }

        self.assertEqual(actual, EXPECTED_REGULATION_QUESTIONS)
        self.assertEqual(len(questions), 189)

    def test_new_regulation_questions_are_prelabelled_level_4(self):
        labels = json.loads(LABEL_PATH.read_text(encoding="utf-8-sig"))

        self.assertEqual(
            {str(number): labels.get(str(number)) for number in range(180, 190)},
            {str(number): 4 for number in range(180, 190)},
        )


if __name__ == "__main__":
    unittest.main()
