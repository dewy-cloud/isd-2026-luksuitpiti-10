"""Qwen text-to-SQL adapter that reuses Lab 8B's ask() pipeline."""

import re
from types import ModuleType
from typing import Any

import requests

from .config import Settings
from .database import CurriculumDatabase


# เงื่อนไข category/topic ที่เป็นค่าตัวอักษรตรง ๆ ใน SQL ของโมเดล เช่น topic = 'ภาคปกติ'
REGULATION_FILTER_RE = re.compile(
    r"\b(category|topic)\s*(=|LIKE)\s*'((?:[^']|'')*)'", re.IGNORECASE)


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

    def extract_sources(self, database: CurriculumDatabase, question: str, sql: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        seen = set()

        # 1. ตรวจสอบข้อมูลข้อบังคับ (regulations) จาก rows
        #    แนบเฉพาะแถวที่มีเลขข้อหรือเลขหน้าจริง ถ้าไม่มี ให้ข้อ 1b ค้นจาก SQL แทน
        for r in rows:
            if r.get("article_no") or r.get("source_page"):
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

        # 1b. SQL อ่านตาราง regulation แต่ไม่ได้ SELECT เลขข้อ/เลขหน้ามาด้วย
        #     ค้นซ้ำด้วยเงื่อนไข category/topic เดียวกับที่ใช้หาคำตอบ
        if not any(s["type"] == "regulation" for s in sources):
            sources.extend(self._regulation_sources_from_sql(database, sql, seen))

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

    def _regulation_sources_from_sql(self, database: CurriculumDatabase, sql: str, seen: set) -> list[dict[str, Any]]:
        """หาเลขข้อบังคับและเลขหน้าของแถว regulation ที่ SQL ของโมเดลใช้ตอบ"""
        if not re.search(r"\bregulation\b", sql or "", re.IGNORECASE):
            return []
        filters = REGULATION_FILTER_RE.findall(sql)
        if not filters:
            # ไม่รู้ว่าคำตอบมาจากแถวไหน — ไม่แนบดีกว่าแนบผิด
            return []

        # ชื่อคอลัมน์และ operator มาจาก regex ที่จำกัดค่าไว้แล้ว ส่วนค่าส่งเป็น parameter
        where = " AND ".join(f"{col.lower()} {op.upper()} ?" for col, op, _ in filters)
        params = [value.replace("''", "'") for _, _, value in filters]
        try:
            conn = self.lab8b.open_db(database.path, readonly=True)
            try:
                rows = conn.execute(
                    "SELECT category, topic, article_no, source_page FROM regulation "
                    f"WHERE {where} LIMIT 3", params).fetchall()
            finally:
                conn.close()
        except Exception:
            return []

        sources = []
        for r in rows:
            title = str(r["topic"] or r["category"] or "ข้อบังคับสถาบันฯ").strip()
            key = f"reg:{title}:{r['article_no']}"
            if key in seen:
                continue
            seen.add(key)
            sources.append({
                "type": "regulation",
                "title": title,
                "article_no": r["article_no"],
                "printed_pages": str(r["source_page"]) if r["source_page"] else None,
                "pdf_pages": None,
            })
        return sources

    def ask(self, database: CurriculumDatabase, question: str) -> dict:
        # ใช้ lab8b.ask() ตัวเดียวกับที่ Lab 9 วัดผล — prompt, num_ctx, repair
        # และ guard_sql จึงเหมือนกันทุกอย่าง เว็บเพิ่มแค่ citations และ max_rows
        database._require_db()
        conn = self.lab8b.open_db(database.path, readonly=True)
        try:
            result = self.lab8b.ask(
                conn, question, verbose=False,
                model=self.config.ollama_model,
                timeout=self.config.request_timeout,
            )
        finally:
            conn.close()

        if result["error"] and result["sql_model_output"] is None:
            # โมเดลไม่ตอบเลยทั้งสองรอบ — Ollama ไม่พร้อม ให้ API ตอบ 503
            raise requests.ConnectionError(result["error"])

        sql = result["sql"] or ""
        rows = result["rows"][: database.max_rows]
        answer = result["answer"] or "ไม่พบข้อมูลนี้ในเล่มหลักสูตร"
        sources = self.extract_sources(database, question, sql, rows)
        return {"question": question, "sql": sql, "rows": rows, "answer": answer, "sources": sources}
