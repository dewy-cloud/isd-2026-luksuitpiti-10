"""Qwen text-to-SQL adapter that reuses Lab 8B's Ollama helper."""

import json
import re
from types import ModuleType
from typing import Any

import requests

from .config import Settings
from .database import CurriculumDatabase


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


class QwenTextToSQL:
    def __init__(self, config: Settings, lab8b: ModuleType):
        self.config = config
        self.lab8b = lab8b

    def available(self) -> bool:
        try:
            return requests.get(
                f"{self.config.ollama_url}/api/tags", timeout=3
            ).ok
        except requests.RequestException:
            return False

    def _chat(self, prompt: str, schema: dict) -> dict:
        # MODEL INTEGRATION POINT: เปลี่ยนฟังก์ชันนี้หากไม่ใช้ Ollama/Qwen
        # เรียกฟังก์ชัน Ollama ของ Lab 8B โดยตรง เพื่อไม่สร้าง client ซ้ำใน Lab 10
        raw = self.lab8b.ollama_generate(
            prompt, fmt=schema, timeout=self.config.request_timeout,
            model=self.config.ollama_model, num_ctx=4096, num_predict=256,
        )
        return self.lab8b.parse_json_loose(raw)

    def make_sql(
        self,
        question: str,
        schema: str,
        repair_error: str | None = None,
        regulation_labels: list[dict[str, str]] | None = None,
    ) -> str:
        sql, _ = self.lab8b.generate_sql(
            question,
            repair_error=repair_error,
            timeout=self.config.request_timeout,
            model=self.config.ollama_model,
            schema=schema,
            regulation_labels=regulation_labels,
        )
        return sql

    def summarize(self, question: str, rows: list[dict[str, Any]]) -> str:
        prompt = f"""ตอบภาษาไทยจากผลฐานข้อมูลเท่านั้น
คำถาม: {question}
ผลฐานข้อมูล: {json.dumps(rows[:40], ensure_ascii=False)}
ตอบ JSON ที่มี key ชื่อ answer และห้ามเพิ่มข้อมูลที่ไม่มีในผล"""
        
        return str(self._chat(prompt, ANSWER_SCHEMA).get("answer", "")).strip()

    def extract_sources(self, database: CurriculumDatabase, question: str, sql: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        seen = set()

        # 1. ตรวจสอบข้อมูลข้อบังคับ (regulations) จาก rows
        for r in rows:
            if any(k in r for k in ("article_no", "condition_desc", "penalty_action", "source_page")):
                title = str(r.get("topic") or r.get("category") or "ข้อบังคับสถาบันฯ").strip()
                art = r.get("article_no")
                spage = r.get("source_page")
                key = f"reg:{title}:{art}"
                if key not in seen:
                    seen.add(key)
                    sources.append({
                        "type": "regulation",
                        "title": title,
                        "article_no": art,
                        "printed_pages": str(spage) if spage else None,
                        "pdf_pages": None,
                    })

        # 2. ตรวจสอบข้อมูลรายวิชา (course) จาก rows หรือ question
        codes_found: list[str] = []
        for r in rows:
            for k in ("code", "requires"):
                val = str(r.get(k) or "").strip()
                if re.match(r"^\d{8}$", val) and val not in codes_found:
                    codes_found.append(val)
            for v in r.values():
                for c in re.findall(r"\b\d{8}\b", str(v)):
                    if c not in codes_found:
                        codes_found.append(c)

        for c in re.findall(r"\b\d{8}\b", question):
            if c not in codes_found:
                codes_found.append(c)

        if codes_found:
            try:
                conn = self.lab8b.open_db(database.path, readonly=True)
                cols = [col[1] for col in conn.execute("PRAGMA table_info(course)").fetchall()]
                for code in codes_found[:6]:
                    row = conn.execute("SELECT * FROM course WHERE code = ?", (code,)).fetchone()
                    if row:
                        name_th = row["name_th"]
                        printed = row["printed_pages"] if "printed_pages" in cols else None
                        pdf_p = row["pdf_pages"] if "pdf_pages" in cols else None
                        key = f"course:{code}"
                        if key not in seen:
                            seen.add(key)
                            sources.append({
                                "type": "course",
                                "code": code,
                                "title": f"{code} {name_th}" if name_th else code,
                                "printed_pages": printed,
                                "pdf_pages": pdf_p,
                            })
                conn.close()
            except Exception:
                pass

        # 3. หากไม่พบแหล่งอ้างอิงที่มีเลขหน้าจริง ไม่ต้องใส่ fallback หมวดที่ฮาร์ดโค้ด
        return sources

    def ask(self, database: CurriculumDatabase, question: str) -> dict:
        sql = ""
        rows: list[dict[str, Any]] = []
        repair_error = None
        schema_conn = self.lab8b.open_db(database.path, readonly=True)
        try:
            schema = self.lab8b.get_live_schema(schema_conn)
            regulation_labels = self.lab8b.get_live_regulation_labels(schema_conn)
        finally:
            schema_conn.close()

        for attempt in range(2):
            try:
                sql = self.make_sql(
                    question,
                    repair_error=repair_error,
                    schema=schema,
                    regulation_labels=regulation_labels,
                )
                sql, rows = database.query_from_model(sql)
            except Exception as exc:
                if attempt == 1:
                    raise
                repair_error = (
                    f"{type(exc).__name__}: {exc}\nSQL เดิม: {sql}"
                )
                continue

            if rows or attempt == 1:
                break
            repair_error = (
                "SQL รันสำเร็จแต่ได้ 0 rows โปรดตรวจสอบ schema และเงื่อนไขให้ตรงคำถาม "
                "แก้ SQL เฉพาะเมื่อพบสาเหตุ และห้ามตัดเงื่อนไขหลักสูตร/แผนที่ผู้ใช้ระบุ "
                f"SQL เดิม: {sql}"
            )

        answer = self.summarize(question, rows) if rows else "ไม่พบข้อมูลนี้ในฐานข้อมูลหลักสูตร"
        answer = self.lab8b.ensure_answer_matches_rows(answer, rows)
        sources = self.extract_sources(database, question, sql, rows)
        return {"question": question, "sql": sql, "rows": rows, "answer": answer, "sources": sources}
