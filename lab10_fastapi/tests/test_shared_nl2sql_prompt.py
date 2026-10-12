import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ocr_system import lab8b_curriculum_db as lab8b  # noqa: E402
from lab10_fastapi.curriculum_app.config import Settings  # noqa: E402
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL  # noqa: E402
from lab10_fastapi.curriculum_app.database import CurriculumDatabase  # noqa: E402


class SharedNL2SQLPromptTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "retry-test.db"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE program (program_id TEXT, total_credits INTEGER, years INTEGER)"
            )
            conn.executemany(
                "INSERT INTO program VALUES (?, ?, ?)",
                [("DSBA", 132, 4), ("IT", 129, 4), ("AIT", 120, 4), ("BIT", 126, 4)],
            )
            conn.execute(
                "CREATE TABLE course (code TEXT, name_th TEXT, name_en TEXT, credits INTEGER)"
            )
            conn.executemany(
                "INSERT INTO course VALUES (?, ?, ?, ?)",
                [("06026201", "แคลคูลัส 2", "CALCULUS 2", 3),
                 ("06016401", "วิชา IT", "IT COURSE", 3)],
            )
            conn.execute("CREATE TABLE prerequisite (code TEXT, requires TEXT, kind TEXT)")
            conn.execute("INSERT INTO prerequisite VALUES ('06026201', '06026200', 'pre')")
            conn.execute(
                "CREATE TABLE regulation (category TEXT, topic TEXT, max_credits INTEGER, "
                "article_no TEXT, source_page INTEGER)"
            )
            conn.execute(
                "INSERT INTO regulation VALUES "
                "('Registration', 'Regular semester', 22, 'Article 11', 89)"
            )
            conn.execute(
                "INSERT INTO regulation VALUES "
                "('เกณฑ์การลงทะเบียน', 'ภาคปกติ', 22, 'ข้อ 11', 89)"
            )
            conn.execute("CREATE TABLE study_plan (plan_id TEXT, plan_type TEXT)")
            conn.execute(
                "CREATE TABLE plan_item "
                "(plan_id TEXT, program_id TEXT, year INTEGER, semester INTEGER, "
                "code TEXT, credits INTEGER, alt_group TEXT, note TEXT)"
            )
            conn.execute(
                "CREATE TABLE v_semester_credits "
                "(plan_id TEXT, program_id TEXT, year INTEGER, semester INTEGER, "
                "credits INTEGER, n_courses INTEGER)"
            )
            conn.execute("INSERT INTO study_plan VALUES ('DSBA_NORMAL', 'no_coop')")
            conn.execute("INSERT INTO study_plan VALUES ('DSBA_COOP', 'coop')")
            conn.execute(
                "INSERT INTO v_semester_credits VALUES "
                "('DSBA_NORMAL', 'DSBA', 1, 1, 18, 7), "
                "('DSBA_COOP', 'DSBA', 1, 1, 20, 8)"
            )
            conn.execute(
                "CREATE TABLE v_plan (program_id TEXT, plan_type TEXT, year INTEGER, "
                "semester INTEGER, code TEXT, name_th TEXT, name_en TEXT, credits INTEGER, "
                "alt_group TEXT, note TEXT, is_elective_slot INTEGER)"
            )
            conn.execute(
                "INSERT INTO v_plan VALUES "
                "('BIT', 'no_coop', 1, 1, '06000001', 'วิชาทดสอบ', 'Test Course', 3, NULL, NULL, 0)"
            )
        self.database = CurriculumDatabase(lab8b, self.db_path)
        self.service = QwenTextToSQL(Settings(), lab8b)
        self.service.summarize = lambda question, rows: str(rows[0]["total_credits"])
        self.service.extract_sources = lambda *args: []

    def tearDown(self):
        self.temp_dir.cleanup()

    def get_live_schema(self):
        conn = lab8b.open_db(self.db_path, readonly=True)
        try:
            return lab8b.get_live_schema(conn)
        finally:
            conn.close()

    def test_prompt_highlights_schema_columns_that_are_often_misused(self):
        prompt = lab8b.build_sql_prompt("List courses", schema=self.get_live_schema())

        self.assertIn("CREATE TABLE course", prompt)
        self.assertIn("CREATE TABLE plan_item", prompt)
        self.assertIn("CREATE TABLE v_plan", prompt)
        self.assertIn("Use only tables and columns listed", prompt)

    def test_prerequisite_few_shot_uses_course_code_placeholder(self):
        prompt = lab8b.build_sql_prompt(
            "วิชา 06066102 ต้องเรียนวิชาใดมาก่อน", schema=self.get_live_schema()
        )

        self.assertIn("<COURSE_CODE_FROM_QUESTION>", prompt)
        self.assertNotIn("WHERE p.code = '06046401'", prompt)

    def test_lab8_prompt_includes_live_regulation_labels(self):
        prompts = []
        sql = (
            "SELECT max_credits, article_no, source_page FROM regulation "
            "WHERE category = 'Registration' AND topic = 'Regular semester' LIMIT 1"
        )

        def model_response(prompt, **kwargs):
            prompts.append(prompt)
            if len(prompts) == 1:
                return json.dumps({"sql": sql})
            return json.dumps({"answer": "22 หน่วยกิต"})

        conn = lab8b.open_db(self.db_path, readonly=True)
        try:
            with patch.object(lab8b, "ollama_generate", side_effect=model_response):
                result = lab8b.ask(conn, "Regular semester max credits?", verbose=False)
        finally:
            conn.close()

        self.assertEqual(result["rows"][0]["max_credits"], 22)
        self.assertIn('"category": "Registration"', prompts[0])
        self.assertIn('"topic": "Regular semester"', prompts[0])

    def test_web_prompt_includes_live_regulation_labels(self):
        prompts = []
        sql = (
            "SELECT max_credits, article_no, source_page FROM regulation "
            "WHERE category = 'Registration' AND topic = 'Regular semester' LIMIT 1"
        )

        def model_response(prompt, **kwargs):
            prompts.append(prompt)
            return json.dumps({"sql": sql})

        with (
            patch.object(lab8b, "ollama_generate", side_effect=model_response),
            patch.object(self.service, "summarize", return_value="22 credits"),
        ):
            result = self.service.ask(self.database, "Regular semester max credits?")

        self.assertEqual(result["rows"][0]["max_credits"], 22)
        self.assertIn('"category": "Registration"', prompts[0])
        self.assertIn('"topic": "Regular semester"', prompts[0])

    def test_regulation_query_uses_compact_prompt_with_live_labels(self):
        conn = lab8b.open_db(self.db_path, readonly=True)
        try:
            schema = lab8b.get_live_schema(conn)
            labels = lab8b.get_live_regulation_labels(conn)
        finally:
            conn.close()

        prompt = lab8b.build_sql_prompt(
            "ภาคการศึกษาปกติลงทะเบียนได้สูงสุดกี่หน่วยกิต",
            schema=schema,
            regulation_labels=labels,
        )

        self.assertIn("Regulation matching rules:", prompt)
        self.assertIn('"topic": "ภาคปกติ"', prompt)

    def test_live_semantic_guidance_is_added_to_repair_prompt(self):
        schema = self.get_live_schema()
        guidance = lab8b.get_live_schema_guidance(schema)
        prompt = lab8b.build_sql_prompt(
            "query",
            "OperationalError: no such column: p.plan_type\\nSQL เดิม: SELECT p.plan_type FROM plan_item p",
            schema=schema,
        )

        self.assertIn("program.total_credits", guidance)
        self.assertIn("program.years", guidance)
        self.assertIn("v_semester_credits", guidance)
        self.assertIn("JOIN study_plan", guidance)
        self.assertIn(guidance, prompt)

    def test_prompt_separates_program_totals_duration_and_semester_credits(self):
        schema = self.get_live_schema()
        prompt = lab8b.build_sql_prompt(
            "หลักสูตรนี้มีทั้งหมดกี่หน่วยกิต", schema=schema
        )

        self.assertIn("program.total_credits", prompt)
        self.assertIn("Do not SUM semester credits", prompt)
        self.assertIn("Do not add a plan_type, year, or semester filter", prompt)
        self.assertIn("v_semester_credits.credits", prompt)
        self.assertIn("semester/year", prompt)

    def test_total_curriculum_credit_prompt_excludes_unrelated_few_shot_examples(self):
        prompt = lab8b.build_sql_prompt(
            "หลักสูตรนี้มีหน่วยกิตรวมทั้งหมดเท่าไร", schema=self.get_live_schema()
        )

        self.assertIn("Focused prompt for total curriculum credits", prompt)
        self.assertIn("program.total_credits", prompt)
        self.assertIn("Do not use prerequisite or study-plan rows", prompt)
        self.assertNotIn("SELECT DISTINCT p.requires", prompt)

    def test_plan_prompt_defaults_to_dsba_no_coop_in_generation_and_retry(self):
        schema = self.get_live_schema()
        prompts = [
            lab8b.build_sql_prompt("ปี 1 เทอม 1 เรียนกี่วิชา", schema=schema),
            lab8b.build_sql_prompt(
                "ปี 1 เทอม 1 เรียนกี่วิชา",
                "OperationalError: no such column: plan_type",
                schema=schema,
            ),
        ]

        for prompt in prompts:
            self.assertIn("default program_id = 'DSBA'", prompt)
            self.assertIn("default plan_type = 'no_coop'", prompt)
            self.assertIn("An explicit program_id or plan_type in the question overrides its corresponding default", prompt)
            self.assertIn("do not count or sum across multiple plan_type values", prompt)
            self.assertIn(
                "For semester course counts, SELECT v_semester_credits.n_courses; never use COUNT(*)",
                prompt,
            )
            self.assertIn(
                "Filter v_semester_credits.plan_id with study_plan.plan_type = 'no_coop'",
                prompt,
            )
        base_prompt, retry_prompt = prompts
        question_position = base_prompt.rfind("ปี 1 เทอม 1 เรียนกี่วิชา")
        policy_position = base_prompt.rfind("Plan selection policy for study-plan")
        self.assertLess(question_position, policy_position)
        self.assertLess(policy_position, base_prompt.rfind("\nSQL:"))
        self.assertLess(
            retry_prompt.rfind("Plan selection policy for study-plan"),
            retry_prompt.rfind("User question:"),
        )

    def test_repair_prompt_regenerates_from_question_instead_of_patching_failed_sql(self):
        prompt = lab8b.build_sql_prompt(
            "หลักสูตรนี้มีทั้งหมดกี่หน่วยกิต",
            "OperationalError: no such column: sp.plan_type\\nSQL เดิม: SELECT SUM(credits) FROM v_semester_credits WHERE sp.plan_type = 'no_coop'",
            schema=self.get_live_schema(),
        )

        self.assertIn("Regenerate the SQL from the original user question", prompt)
        self.assertIn("Do not treat the failed SQL as a template", prompt)
        self.assertIn("program.total_credits", prompt)
        self.assertIn("irrelevant plan_type filter to a curriculum-total query", prompt)

    def test_repair_prompt_explains_column_ownership_and_alias_repair(self):
        prompt = lab8b.build_sql_prompt(
            "หลักสูตร IT ใช้เวลาเรียนกี่ปี",
            "OperationalError: no such column: p.plan_type\nSQL เดิม: SELECT p.plan_type FROM plan_item p",
            schema=self.get_live_schema(),
        )

        self.assertIn("p.plan_type", prompt)
        self.assertIn("Verify every qualified column belongs to the relation assigned to that alias.", prompt)
        self.assertIn("Preserve the intended filter by applying it to the joined relation", prompt)

    def test_repair_prompt_maps_missing_qualified_column_to_live_table(self):
        prompt = lab8b.build_sql_prompt(
            "หลักสูตร IT ใช้เวลาเรียนกี่ปี",
            "OperationalError: no such column: p.plan_type\n"
            "SQL เดิม: SELECT p.plan_type FROM plan_item AS p",
            schema=self.get_live_schema(),
        )

        self.assertIn("Alias p -> plan_item", prompt)
        self.assertIn("plan_type ไม่มีใน plan_item", prompt)
        self.assertIn("plan_type มีอยู่ใน study_plan", prompt)
        self.assertIn("JOIN study_plan", prompt)
        self.assertIn("plan_id", prompt)

    def test_unqualified_missing_column_diagnostic_suggests_live_join_key(self):
        schema = self.get_live_schema()
        diagnostic = lab8b.get_sql_repair_diagnostics(
            "OperationalError: no such column: plan_type\n"
            "SQL เดิม: SELECT credits FROM v_semester_credits WHERE plan_type = 'no_coop'",
            schema,
        )

        self.assertIn("JOIN study_plan", diagnostic)
        self.assertIn("plan_id", diagnostic)
        self.assertIn("sp.plan_type", diagnostic)

    def test_live_schema_is_read_from_the_connected_sqlite_database(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE actual_table (actual_column TEXT)")
        conn.execute("CREATE VIEW actual_view AS SELECT actual_column FROM actual_table")

        schema = lab8b.get_live_schema(conn)
        prompt = lab8b.build_sql_prompt("show rows", schema=schema)

        self.assertIn("CREATE TABLE actual_table (actual_column TEXT)", schema)
        self.assertIn("CREATE VIEW actual_view", schema)
        self.assertIn("-- VIEW actual_view columns: actual_column", schema)
        self.assertIn("actual_column", prompt)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS program", prompt)
        conn.close()

    def test_web_uses_schema_from_its_active_database_for_generation(self):
        generated_sql = "SELECT total_credits FROM program WHERE program_id = 'DSBA' LIMIT 1"
        with patch.object(
            lab8b,
            "ollama_generate",
            return_value=json.dumps({"sql": generated_sql}),
        ) as generate:
            result = self.service.ask(self.database, "DSBA total credits")

        self.assertEqual(result["rows"], [{"total_credits": 132}])
        prompt = generate.call_args.args[0]
        self.assertIn("CREATE TABLE program", prompt)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS program", prompt)

    def test_web_retries_once_after_sql_execution_error(self):
        first_sql = "SELECT missing_column FROM program LIMIT 1"
        corrected_sql = "SELECT total_credits FROM program WHERE program_id = 'DSBA' LIMIT 1"
        with patch.object(
            lab8b,
            "generate_sql",
            side_effect=[(first_sql, "bad"), (corrected_sql, "fixed")],
        ) as generate_sql:
            result = self.service.ask(self.database, "หลักสูตร DSBA มีกี่หน่วยกิต")

        self.assertEqual(result["rows"], [{"total_credits": 132}])
        self.assertEqual(generate_sql.call_count, 2)
        self.assertIn("no such column", generate_sql.call_args_list[1].kwargs["repair_error"])
        self.assertIn(first_sql, generate_sql.call_args_list[1].kwargs["repair_error"])

    def test_web_uses_rows_fallback_when_synthesis_claims_no_data(self):
        generated_sql = "SELECT total_credits FROM program WHERE program_id = 'DSBA'"
        with patch.object(lab8b, "generate_sql", return_value=(generated_sql, "sql")):
            with patch.object(self.service, "summarize", return_value="ไม่พบข้อมูลนี้ในเล่มหลักสูตร"):
                result = self.service.ask(self.database, "DSBA total credits")

        self.assertEqual(result["rows"], [{"total_credits": 132}])
        self.assertEqual(result["answer"], "ผลจากฐานข้อมูล: total_credits = 132")

    def test_cli_uses_rows_fallback_when_synthesis_claims_no_data(self):
        conn = lab8b.open_db(self.db_path)
        model_outputs = [
            json.dumps({"sql": "SELECT total_credits FROM program WHERE program_id = 'DSBA'"}),
            json.dumps({"answer": "ไม่พบข้อมูลนี้ในเล่มหลักสูตร"}),
        ]
        with patch.object(lab8b, "ollama_generate", side_effect=model_outputs):
            result = lab8b.ask(conn, "DSBA total credits", verbose=False)
        conn.close()

        self.assertEqual(result["rows"], [{"total_credits": 132}])
        self.assertEqual(result["answer"], "ผลจากฐานข้อมูล: total_credits = 132")

    def test_all_question_types_generate_sql_through_the_llm(self):
        cases = [
            ("วิชา 06026201 คือวิชาอะไร", "SELECT name_th FROM course LIMIT 1"),
            ("หลักสูตรนี้มีหน่วยกิตรวมเท่าไร", "SELECT total_credits FROM program LIMIT 1"),
            ("ปี 1 เทอม 1 เรียนกี่หน่วยกิต", "SELECT credits FROM v_semester_credits LIMIT 1"),
            ("ปี 1 เทอม 1 เรียนวิชาอะไรบ้าง", "SELECT code FROM v_plan LIMIT 1"),
        ]

        for question, model_sql in cases:
            with self.subTest(question=question):
                with patch.object(
                    lab8b,
                    "ollama_generate",
                    return_value=json.dumps({"sql": model_sql}),
                ) as generate:
                    actual_sql, _ = lab8b.generate_sql(
                        question, schema=self.get_live_schema()
                    )

                self.assertEqual(actual_sql, model_sql)
                generate.assert_called_once()

    def test_repair_prompt_is_compact_and_includes_failed_sql_and_schema(self):
        question = "วิชา 06016401 ในหลักสูตร IT มีกี่หน่วยกิต"
        failed_sql = "SELECT credits FROM course WHERE code = '06016401' AND program_id = 'IT'"
        repair_error = f"OperationalError: no such column: program_id\nSQL: {failed_sql}"

        prompt = lab8b.build_sql_prompt(
            question, repair_error, schema=self.get_live_schema()
        )

        self.assertIn(question, prompt)
        self.assertIn(failed_sql, prompt)
        self.assertIn("CREATE TABLE course", prompt)
        self.assertIn("course", prompt)
        self.assertIn("name_th", prompt)
        self.assertIn("no such column: program_id", prompt)
        self.assertNotIn("คำถาม: วิชา 06036100", prompt)

    def test_web_retries_once_after_empty_query_result(self):
        empty_sql = "SELECT total_credits FROM program WHERE program_id = 'MISSING' LIMIT 1"
        corrected_sql = "SELECT total_credits FROM program WHERE program_id = 'DSBA' LIMIT 1"
        with patch.object(
            lab8b,
            "generate_sql",
            side_effect=[(empty_sql, "empty"), (corrected_sql, "fixed")],
        ) as generate_sql:
            result = self.service.ask(self.database, "หลักสูตร DSBA มีกี่หน่วยกิต")

        self.assertEqual(result["rows"], [{"total_credits": 132}])
        self.assertEqual(generate_sql.call_count, 2)
        self.assertIn("0 rows", generate_sql.call_args_list[1].kwargs["repair_error"])

    def test_web_still_abstains_when_retry_also_returns_no_rows(self):
        no_match_sql = "SELECT total_credits FROM program WHERE program_id = 'MISSING' LIMIT 1"
        with patch.object(
            lab8b,
            "generate_sql",
            return_value=(no_match_sql, "empty"),
        ) as generate_sql:
            result = self.service.ask(self.database, "ถามข้อมูลที่ไม่มี")

        self.assertEqual(generate_sql.call_count, 2)
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["answer"], "ไม่พบข้อมูลนี้ในฐานข้อมูลหลักสูตร")

    def test_total_curriculum_credits_is_generated_by_the_llm(self):
        question = "หลักสูตรนี้มีหน่วยกิตรวมทั้งหมดเท่าไร"
        expected_sql = (
            "SELECT total_credits FROM program "
            "WHERE program_id = 'DSBA' LIMIT 1"
        )

        with patch.object(
            lab8b,
            "ollama_generate",
            return_value=json.dumps({"sql": expected_sql}),
        ) as generate:
            actual_sql, _ = lab8b.generate_sql(
                question, schema=self.get_live_schema()
            )

        self.assertEqual(actual_sql, expected_sql)
        generate.assert_called_once()

    def test_recent_query_patterns_use_llm_and_repair_schema_errors(self):
        cases = [
            (
                "หลักสูตรนี้มีทั้งหมดกี่หน่วยกิต",
                "SELECT SUM(credits) FROM v_semester_credits "
                "WHERE program_id = 'DSBA' AND sp.plan_type = 'no_coop'",
                "SELECT total_credits FROM program WHERE program_id = 'DSBA' LIMIT 1",
                {"total_credits": 132},
            ),
            (
                "หลักสูตร IT ใช้เวลาเรียนกี่ปี",
                "SELECT COUNT(DISTINCT p.year) FROM plan_item AS p "
                "WHERE p.is_elective_slot = 0",
                "SELECT years FROM program WHERE program_id = 'IT' LIMIT 1",
                {"years": 4},
            ),
            (
                "วิชา 06016401 ในหลักสูตร IT มีกี่หน่วยกิต",
                "SELECT credits FROM course WHERE code = '06016401' "
                "AND program_id = 'IT'",
                "SELECT credits FROM course WHERE code = '06016401' LIMIT 1",
                {"credits": 3},
            ),
            (
                "ปี 1 เทอม 1 เรียนกี่วิชา",
                "SELECT COUNT(*) FROM v_plan WHERE program_id = 'DSBA' "
                "AND sp.plan_type = 'no_coop' AND is_elective_slot = 0",
                "SELECT v.n_courses FROM v_semester_credits AS v "
                "JOIN study_plan AS sp ON sp.plan_id = v.plan_id "
                "WHERE v.program_id = 'DSBA' AND sp.plan_type = 'no_coop' "
                "AND v.year = 1 AND v.semester = 1 LIMIT 1",
                {"n_courses": 7},
            ),
        ]

        for question, invalid_sql, corrected_sql, expected_row in cases:
            with self.subTest(question=question):
                conn = lab8b.open_db(self.db_path)
                with patch.object(
                    lab8b,
                    "ollama_generate",
                    side_effect=[
                        json.dumps({"sql": invalid_sql}),
                        json.dumps({"sql": corrected_sql}),
                        json.dumps({"answer": "ok"}),
                    ],
                ) as generate:
                    result = lab8b.ask(conn, question, verbose=False)
                conn.close()

                self.assertEqual(result["rows"], [expected_row])
                self.assertIsNone(result["error"])
                self.assertEqual(generate.call_count, 3)
                self.assertIn("no such column", generate.call_args_list[1].args[0])

    def test_course_identity_question_uses_llm_and_executes(self):
        question = "วิชา 06026201 คือวิชาอะไร"
        expected_sql = (
            "SELECT code, name_th, name_en FROM course "
            "WHERE code = '06026201' LIMIT 1"
        )
        with patch.object(
            lab8b,
            "ollama_generate",
            return_value=json.dumps({"sql": expected_sql}),
        ) as generate:
            sql, _ = lab8b.generate_sql(question, schema=self.get_live_schema())

        generate.assert_called_once()
        executed_sql, rows = self.database.query_from_model(sql)
        self.assertEqual(executed_sql, expected_sql)
        self.assertEqual(rows, [{
            "code": "06026201",
            "name_th": "แคลคูลัส 2",
            "name_en": "CALCULUS 2",
        }])

    def test_prerequisite_dependents_query_returns_course_names(self):
        question = "ถ้าไม่ผ่านวิชา 06026200 จะลงวิชาอะไรไม่ได้บ้าง"
        expected_sql = (
            "SELECT DISTINCT p.code, c.name_th, c.name_en "
            "FROM prerequisite AS p JOIN course AS c ON c.code = p.code "
            "WHERE p.requires = '06026200' AND p.kind = 'pre' LIMIT 1"
        )

        def model_follows_prerequisite_example(prompt, **kwargs):
            if "JOIN course AS c ON c.code = p.code" in prompt:
                sql = expected_sql
            else:
                sql = (
                    "SELECT code FROM prerequisite "
                    "WHERE requires = '06026200' AND kind = 'pre' LIMIT 1"
                )
            return json.dumps({"sql": sql})

        with patch.object(
            lab8b, "ollama_generate", side_effect=model_follows_prerequisite_example
        ):
            sql, _ = lab8b.generate_sql(question, schema=self.get_live_schema())
        _, rows = self.database.query_from_model(sql)

        self.assertEqual(rows, [{
            "code": "06026201",
            "name_th": "แคลคูลัส 2",
            "name_en": "CALCULUS 2",
        }])

    def test_semester_credit_query_is_generated_by_llm_using_valid_schema(self):
        question = "ปี 1 เทอม 1 เรียนกี่หน่วยกิต"
        expected_sql = (
            "SELECT v.credits FROM v_semester_credits AS v "
            "JOIN study_plan AS sp ON sp.plan_id = v.plan_id "
            "WHERE v.program_id = 'DSBA' AND sp.plan_type = 'no_coop' "
            "AND v.year = 1 AND v.semester = 1 LIMIT 1"
        )

        with patch.object(
            lab8b,
            "ollama_generate",
            return_value=json.dumps({"sql": expected_sql}),
        ) as generate:
            sql, _ = lab8b.generate_sql(question, schema=self.get_live_schema())
        generate.assert_called_once()
        self.assertEqual(sql, expected_sql)
        _, rows = self.database.query_from_model(sql)

        self.assertEqual(rows, [{"credits": 18}])

    def test_missing_year_semester_course_list_returns_empty_rows_without_error(self):
        question = "ปี 7 เทอม 1 ในหลักสูตร BIT เรียนวิชาอะไรบ้าง"
        with patch.object(
            lab8b,
            "ollama_generate",
            return_value=json.dumps({
                "sql": "SELECT code, name_th, name_en FROM v_plan "
                       "WHERE program_id = 'BIT' AND plan_type = 'no_coop' "
                       "AND year = 7 AND semester = 1 LIMIT 1"
            }),
        ) as generate:
            result = self.service.ask(self.database, question)

        self.assertEqual(generate.call_count, 2)
        self.assertIn("0 rows", generate.call_args_list[1].args[0])
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["answer"], "ไม่พบข้อมูลนี้ในฐานข้อมูลหลักสูตร")
        self.assertIn("FROM v_plan", result["sql"])
        self.assertNotIn("pi.is_elective_slot", result["sql"])

    def test_web_prompt_handles_special_graduation_registration_limit(self):
        question = "กรณีพิเศษเพื่อขอจบลงทะเบียนได้สูงสุดกี่หน่วยกิต"
        expected_sql = (
            "SELECT max_credits FROM regulation "
            "WHERE category = 'เกณฑ์การลงทะเบียน' "
            "AND topic LIKE '%กรณีพิเศษ%' LIMIT 1"
        )
        wrong_sql = (
            "SELECT max_credits, article_no, source_page FROM regulation "
            "WHERE category = 'เกณฑ์การสำเร็จการศึกษา' "
            "AND min_gpa IS NULL LIMIT 1"
        )

        def fake_ollama_generate(prompt, **kwargs):
            # The model fixture follows the explicit few-shot example when the
            # shared Lab 8B prompt is supplied; otherwise it reproduces the
            # incorrect SQL observed from the web prompt.
            sql = expected_sql if "topic LIKE '%กรณีพิเศษ%'" in prompt else wrong_sql
            return json.dumps({"sql": sql}, ensure_ascii=False)

        service = QwenTextToSQL(Settings(), lab8b)
        with patch.object(lab8b, "ollama_generate", side_effect=fake_ollama_generate):
            actual_sql = service.make_sql(
                question, schema=self.get_live_schema()
            )

        self.assertEqual(actual_sql, expected_sql)


if __name__ == "__main__":
    unittest.main()
