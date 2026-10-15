import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ocr_system import lab8b_curriculum_db as lab8b  # noqa: E402
from lab10_fastapi.curriculum_app.config import Settings  # noqa: E402
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL  # noqa: E402
from lab10_fastapi.curriculum_app.database import CurriculumDatabase  # noqa: E402


def sql_json(sql: str) -> str:
    return json.dumps({"sql": sql})


def answer_json(answer: str) -> str:
    return json.dumps({"answer": answer}, ensure_ascii=False)


class SharedNL2SQLPromptTests(unittest.TestCase):
    """Lab 9 (lab8b.ask) and Lab 10 (/api/ask) must run the same NL2SQL pipeline."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "nl2sql-test.db"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE program (program_id TEXT, total_credits INTEGER, years INTEGER)"
            )
            conn.executemany(
                "INSERT INTO program VALUES (?, ?, ?)",
                [("DSBA", 132, 4), ("IT", 129, 4), ("AIT", 120, 4), ("BIT", 126, 4)],
            )
            conn.execute(
                "CREATE TABLE regulation (id INTEGER PRIMARY KEY, category TEXT, topic TEXT, "
                "max_credits INTEGER, article_no TEXT, source_page INTEGER)"
            )
            conn.executemany(
                "INSERT INTO regulation (category, topic, max_credits, article_no, source_page) "
                "VALUES (?, ?, ?, ?, ?)",
                [("เกณฑ์การลงทะเบียน", "ภาคปกติ", 22, "ข้อ 11", 89),
                 ("การทุจริตในการสอบ", "ทุจริตครั้งแรก", None, "ข้อ 30", 94)],
            )
            conn.execute("CREATE TABLE many (n INTEGER)")
            conn.executemany("INSERT INTO many VALUES (?)", [(i,) for i in range(150)])
        self.database = CurriculumDatabase(lab8b, self.db_path)
        self.service = QwenTextToSQL(Settings(), lab8b)
        self.service.extract_sources = lambda *args: []

    def tearDown(self):
        self.temp_dir.cleanup()

    def labels(self):
        conn = lab8b.open_db(self.db_path, readonly=True)
        try:
            return lab8b.get_live_regulation_labels(conn)
        finally:
            conn.close()

    # ── prompt ─────────────────────────────────────────────────────────

    def test_context_window_fits_the_sql_prompt(self):
        self.assertEqual(lab8b.NUM_CTX, 8192)

    def test_prompt_contains_schema_examples_and_question(self):
        prompt = lab8b.build_sql_prompt("หลักสูตร IT ปี 1 เทอม 1 เรียนกี่หน่วยกิต")

        self.assertIn("CREATE TABLE IF NOT EXISTS program", prompt)
        self.assertIn("CREATE VIEW IF NOT EXISTS v_semester_credits", prompt)
        self.assertIn("คำถาม: ปี 1 เทอม 1 เรียนกี่หน่วยกิต", prompt)
        self.assertIn("คำถาม: หลักสูตร IT ปี 1 เทอม 1 เรียนกี่หน่วยกิต\nSQL:", prompt)
        self.assertTrue(prompt.endswith('ตอบเป็น JSON รูปแบบ {"sql": "SELECT ..."} เท่านั้น'))

    def test_every_question_type_uses_the_same_prompt_template(self):
        questions = [
            "หลักสูตร IT มีทั้งหมดกี่หน่วยกิต",
            "หลักสูตร IT ใช้เวลาเรียนกี่ปี",
            "ทุจริตในการสอบครั้งแรกได้รับโทษอะไร",
            "วิชา 06026201 ต้องเรียนวิชาใดมาก่อน",
        ]
        def template(prompt: str) -> str:
            # ทุกอย่างก่อน "คำถาม:" สุดท้าย ต้องเหมือนกันทุกคำถาม
            return prompt.rsplit("\nคำถาม: ", 1)[0]

        prompts = [lab8b.build_sql_prompt(q) for q in questions]

        for question, prompt in zip(questions, prompts):
            with self.subTest(question=question):
                self.assertNotIn("Focused prompt", prompt)
                self.assertTrue(prompt.rstrip().endswith(
                    f'คำถาม: {question}\nSQL:\nตอบเป็น JSON รูปแบบ {{"sql": "SELECT ..."}} เท่านั้น'))
                self.assertEqual(template(prompt), template(prompts[0]))

    def test_prompt_lists_live_regulation_labels_from_the_database(self):
        prompt = lab8b.build_sql_prompt("ทุจริตครั้งแรกโดนอะไร", regulation_labels=self.labels())

        self.assertIn("- category='เกณฑ์การลงทะเบียน' topic='ภาคปกติ'", prompt)
        self.assertIn("- category='การทุจริตในการสอบ' topic='ทุจริตครั้งแรก'", prompt)
        self.assertNotIn("{regulation_labels}", prompt)

    def test_regulation_examples_use_the_stored_category_names(self):
        prompt = lab8b.build_sql_prompt("q")

        self.assertNotIn("'เกณฑ์การทุจริตในการสอบ'", prompt)
        self.assertNotIn("'เกณฑ์ภาคทัณฑ์'", prompt)
        self.assertIn("category = 'การทุจริตในการสอบ'", prompt)
        self.assertIn("category = 'เกณฑ์การภาคทัณฑ์'", prompt)
        self.assertIn(
            "WHERE category = 'เกณฑ์การลงทะเบียน' AND topic = 'ภาคปกติ' LIMIT 1", prompt)

    def test_repair_prompt_appends_the_error_to_the_same_prompt(self):
        base = lab8b.build_sql_prompt("q", regulation_labels=self.labels())
        repair = lab8b.build_sql_prompt("q", "no such column: x", regulation_labels=self.labels())
        tail = '\nตอบเป็น JSON รูปแบบ {"sql": "SELECT ..."} เท่านั้น'

        self.assertTrue(repair.startswith(base[: -len(tail)]))
        self.assertIn("SQL ที่ลองไปแล้วมีข้อผิดพลาด: no such column: x\nเขียนใหม่ให้ถูก", repair)

    # ── lab8b.ask (CLI / Lab 9 benchmark) ──────────────────────────────

    def ask_cli(self, outputs, question="หลักสูตร DSBA มีกี่หน่วยกิต"):
        conn = lab8b.open_db(self.db_path, readonly=True)
        try:
            with patch.object(lab8b, "ollama_generate", side_effect=outputs) as gen:
                result = lab8b.ask(conn, question, verbose=False)
        finally:
            conn.close()
        return result, gen

    def test_every_model_call_uses_num_ctx(self):
        result, gen = self.ask_cli([
            sql_json("SELECT total_credits FROM program WHERE program_id = 'DSBA'"),
            answer_json("132 หน่วยกิต"),
        ])

        self.assertEqual(result["answer"], "132 หน่วยกิต")
        self.assertEqual(gen.call_count, 2)
        for call in gen.call_args_list:
            self.assertEqual(call.kwargs["num_ctx"], lab8b.NUM_CTX)

    def test_cli_repairs_once_after_sql_error(self):
        result, gen = self.ask_cli([
            sql_json("SELECT missing_column FROM program"),
            sql_json("SELECT total_credits FROM program WHERE program_id = 'DSBA'"),
            answer_json("132"),
        ])

        self.assertEqual(result["rows"], [{"total_credits": 132}])
        self.assertIsNone(result["error"])
        self.assertIn("no such column: missing_column", gen.call_args_list[1].args[0])

    def test_cli_gives_up_after_second_sql_error(self):
        result, gen = self.ask_cli([
            sql_json("SELECT missing_column FROM program"),
            sql_json("SELECT still_missing FROM program"),
        ])

        self.assertEqual(gen.call_count, 2)
        self.assertEqual(result["rows"], [])
        self.assertIn("still_missing", result["error"])
        self.assertEqual(result["answer"], "ไม่สามารถตอบคำถามนี้ได้ กรุณาตรวจสอบเอง")

    def test_cli_does_not_retry_when_query_returns_no_rows(self):
        result, gen = self.ask_cli([
            sql_json("SELECT total_credits FROM program WHERE program_id = 'MISSING'"),
        ])

        self.assertEqual(gen.call_count, 1)
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["answer"], "ไม่พบข้อมูลนี้ในเล่มหลักสูตร")

    def test_cli_rejects_write_sql_and_repairs(self):
        result, gen = self.ask_cli([
            sql_json("DROP TABLE program"),
            sql_json("SELECT total_credits FROM program WHERE program_id = 'IT'"),
            answer_json("129"),
        ])

        self.assertEqual(result["rows"], [{"total_credits": 129}])
        self.assertIn("SELECT หรือ WITH", gen.call_args_list[1].args[0])

    def test_cli_uses_rows_fallback_when_synthesis_claims_no_data(self):
        result, _ = self.ask_cli([
            sql_json("SELECT total_credits FROM program WHERE program_id = 'DSBA'"),
            answer_json("ไม่พบข้อมูลนี้ในเล่มหลักสูตร"),
        ])

        self.assertEqual(result["answer"], "ผลจากฐานข้อมูล: total_credits = 132")

    # ── Lab 10 web service ─────────────────────────────────────────────

    def test_web_delegates_to_lab8b_ask_with_settings(self):
        fake = {"sql": "SELECT 1 LIMIT 200", "rows": [{"1": 1}], "answer": "1",
                "error": None, "sql_model_output": "{}"}
        with patch.object(lab8b, "ask", return_value=fake) as ask:
            result = self.service.ask(self.database, "q")

        ask.assert_called_once()
        self.assertEqual(ask.call_args.kwargs["model"], self.service.config.ollama_model)
        self.assertEqual(ask.call_args.kwargs["timeout"], self.service.config.request_timeout)
        self.assertEqual(result["sql"], "SELECT 1 LIMIT 200")
        self.assertEqual(result["answer"], "1")

    def test_web_and_cli_return_the_same_result_for_the_same_model_output(self):
        outputs = [
            sql_json("SELECT missing_column FROM program"),
            sql_json("SELECT total_credits FROM program WHERE program_id = 'BIT'"),
            answer_json("126 หน่วยกิต"),
        ]
        cli, _ = self.ask_cli(list(outputs), "หลักสูตร BIT มีกี่หน่วยกิต")
        with patch.object(lab8b, "ollama_generate", side_effect=list(outputs)):
            web = self.service.ask(self.database, "หลักสูตร BIT มีกี่หน่วยกิต")

        self.assertEqual(web["sql"], cli["sql"])
        self.assertEqual(web["rows"], cli["rows"])
        self.assertEqual(web["answer"], cli["answer"])

    def test_web_does_not_retry_when_query_returns_no_rows(self):
        with patch.object(lab8b, "ollama_generate", side_effect=[
            sql_json("SELECT total_credits FROM program WHERE program_id = 'MISSING'"),
        ]) as gen:
            result = self.service.ask(self.database, "ถามข้อมูลที่ไม่มี")

        self.assertEqual(gen.call_count, 1)
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["answer"], "ไม่พบข้อมูลนี้ในเล่มหลักสูตร")

    def test_web_limits_rows_to_max_rows(self):
        with patch.object(lab8b, "ollama_generate", side_effect=[
            sql_json("SELECT n FROM many"), answer_json("มีหลายแถว"),
        ]):
            result = self.service.ask(self.database, "list")

        self.assertEqual(len(result["rows"]), self.database.max_rows)

    def test_web_returns_empty_sql_string_when_both_attempts_fail(self):
        with patch.object(lab8b, "ollama_generate", side_effect=[
            sql_json("DROP TABLE program"), sql_json("DELETE FROM program"),
        ]):
            result = self.service.ask(self.database, "q")

        self.assertIsInstance(result["sql"], str)
        self.assertEqual(result["rows"], [])

    def test_web_raises_connection_error_when_ollama_is_down(self):
        with patch.object(lab8b, "ollama_generate",
                          side_effect=requests.ConnectionError("refused")):
            with self.assertRaises(requests.ConnectionError):
                self.service.ask(self.database, "q")

    # ── citations for regulation answers ───────────────────────────────

    def sources(self, sql, rows=None):
        service = QwenTextToSQL(Settings(), lab8b)  # real extract_sources (setUp stubs it)
        return [s for s in service.extract_sources(self.database, "q", sql, rows or [])
                if s["type"] == "regulation"]

    def test_regulation_citation_is_found_from_the_sql_filters(self):
        found = self.sources(
            "SELECT max_credits FROM regulation WHERE category = 'เกณฑ์การลงทะเบียน' "
            "AND topic = 'ภาคปกติ' LIMIT 1", [{"max_credits": 22}])

        self.assertEqual(found, [{"type": "regulation", "title": "ภาคปกติ",
                                  "article_no": "ข้อ 11", "printed_pages": "89",
                                  "pdf_pages": None}])

    def test_regulation_citation_supports_like_filters(self):
        found = self.sources(
            "SELECT penalty_action FROM regulation WHERE category LIKE '%ทุจริต%' LIMIT 1")

        self.assertEqual([(s["article_no"], s["printed_pages"]) for s in found], [("ข้อ 30", "94")])

    def test_no_regulation_citation_without_category_or_topic_filter(self):
        self.assertEqual(self.sources("SELECT MAX(max_credits) FROM regulation"), [])

    def test_no_regulation_citation_for_other_tables(self):
        self.assertEqual(self.sources("SELECT total_credits FROM program WHERE program_id = 'IT'"), [])

    def test_no_regulation_citation_when_filters_match_nothing(self):
        self.assertEqual(self.sources(
            "SELECT max_credits FROM regulation WHERE topic = 'ไม่มีหัวข้อนี้'"), [])

    def test_penalty_rows_without_page_still_get_a_citation(self):
        found = self.sources(
            "SELECT penalty_action FROM regulation WHERE category = 'การทุจริตในการสอบ' "
            "AND topic = 'ทุจริตครั้งแรก' LIMIT 1",
            [{"penalty_action": "พักการเรียน 1 ภาคการศึกษาถัดไป"}])

        self.assertEqual([(s["title"], s["article_no"], s["printed_pages"]) for s in found],
                         [("ทุจริตครั้งแรก", "ข้อ 30", "94")])

    def test_regulation_citation_from_rows_is_not_duplicated(self):
        found = self.sources(
            "SELECT article_no, source_page, topic FROM regulation WHERE topic = 'ภาคปกติ'",
            [{"article_no": "ข้อ 11", "source_page": 89, "topic": "ภาคปกติ"}])

        self.assertEqual(len(found), 1)

    def test_web_reports_missing_database(self):
        missing = CurriculumDatabase(lab8b, Path(self.temp_dir.name) / "missing.db")
        with self.assertRaises(FileNotFoundError):
            self.service.ask(missing, "q")


if __name__ == "__main__":
    unittest.main()
