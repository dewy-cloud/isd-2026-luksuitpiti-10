#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_gened.py — สกัดหมวดวิชาศึกษาทั่วไป (GenEd) ด้วย Two-Stage Architecture:
Stage 1: Typhoon-OCR 1.5 (scb10x/typhoon-ocr1.5-3b) อ่านหน้าเอกสารเป็น Markdown (.md)
         *แปลง PDF เป็น PNG bytes ในหน่วยความจำโดยตรง ไม่มีการบันทึกไฟล์ภาพลงดิสก์*
Stage 2: LLM (qwen3:4b หรือ llama3.2:3b) สกัดข้อมูลเป็น JSON ตาม Schema ผ่าน Ollama
พร้อมบันทึกลง JSON และอัปเดตฐานข้อมูล SQLite (ตาราง course)

วิชา 06026240 การพัฒนาระบบอัจฉริยะ (ISD 2026: Luksuitpiti)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

# ปรับ Encoding คอนโซลสำหรับ Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import requests
except ImportError:
    print("❌ กรุณาติดตั้ง requests: pip install requests")
    sys.exit(1)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ความละเอียด DPI สำหรับเรนเดอร์ PDF เป็นภาพในหน่วยความจำ
DPI = 150

# ==============================================================================
# JSON Schema สำหรับส่งให้ Ollama กำกับโครงสร้าง Output ใน Stage 2
# ==============================================================================
COURSE_SCHEMA = {
    "type": "object",
    "properties": {
        "courses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "name_th": {"type": "string"},
                    "name_en": {"type": ["string", "null"]},
                    "credits": {"type": "integer"},
                    "lecture_h": {"type": "integer"},
                    "lab_h": {"type": "integer"},
                    "self_h": {"type": "integer"},
                    "description_th": {"type": ["string", "null"]}
                },
                "required": ["code", "name_th", "credits", "lecture_h", "lab_h", "self_h"]
            }
        }
    },
    "required": ["courses"]
}

SYSTEM_PROMPT = """You are an automated curriculum extractor. 
Extract all course information from the provided Markdown into JSON adhering strictly to the schema.
Do NOT think or reason. Immediately output the JSON object following the schema.

Extraction Rules:
1. code: 8-digit course code (starting with 90 or 96).
2. name_th: Thai course name only. Strip any trailing credit numbers and brackets.
3. name_en: English course name (uppercase or title case).
4. credits, lecture_h, lab_h, self_h: numbers from credit format X(lec-lab-self).
5. description_th: Thai course description only. Do NOT include English description.
6. Extract ONLY courses that appear in the text. Do not invent any courses."""

TYPHOON_OCR_PROMPT = """Extract all text from the image.

Instructions:
- Only return the clean Markdown.
- Do not include any explanation or extra text.
- You must include all information on the page.

Formatting Rules:
- Tables: Render tables using <table>...</table> in clean HTML format.
- Equations: Render equations using LaTeX syntax with inline ($...$) and block ($$...$$).
- Images/Charts/Diagrams: Wrap any clearly defined visual areas in <figure>
- Page Numbers: Wrap page numbers in <page_number>...</page_number>.
- Checkboxes: Use ☐ for unchecked and ☑ for checked boxes."""


def parse_page_range(spec: str) -> list[int]:
    """แปลงข้อความช่วงหน้า เช่น '153-156' หรือ '153,155,160' เป็น list ของเลขหน้า"""
    pages = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            s, e = part.split("-")
            pages.extend(range(int(s), int(e) + 1))
        elif part.isdigit():
            pages.append(int(part))
    return sorted(list(set(pages)))


# ==============================================================================
# Stage 1: แปลงหน้าเอกสารเป็น Markdown ด้วย Typhoon-OCR 1.5 (In-Memory Bytes)
# ==============================================================================
def render_pdf_page_to_bytes(pdf_path: Path, page_num: int, dpi: int = DPI) -> bytes:
    """เรนเดอร์หน้า PDF (1-indexed) เป็น bytes PNG ในหน่วยความจำโดยตรง ไม่บันทึกลงดิสก์"""
    if fitz is None:
        raise ImportError("ไม่พบไลบรารี PyMuPDF (fitz) กรุณาติดตั้ง: pip install pymupdf")

    doc = fitz.open(str(pdf_path))
    if page_num < 1 or page_num > len(doc):
        doc.close()
        raise ValueError(f"เลขหน้า {page_num} อยู่นอกช่วงของเอกสาร (มีทั้งหมด {len(doc)} หน้า)")

    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = doc[page_num - 1].get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def get_page_markdown_via_typhoon(
    pdf_or_img_path: Path,
    page_num: int,
    md_cache_dir: Path | None = None,
    ollama_url: str = "http://127.0.0.1:11434",
    ocr_model: str = "scb10x/typhoon-ocr1.5-3b:latest"
) -> str:
    """สกัดหน้าเอกสารเป็น Markdown โดยใช้ Typhoon-OCR 1.5 ผ่าน in-memory bytes"""
    # ตรวจสอบแคชข้อความ Markdown (ถ้ามี)
    md_cache_file = None
    if md_cache_dir is not None:
        md_cache_file = md_cache_dir / f"page_{page_num:03d}.md"
        if md_cache_file.exists() and md_cache_file.stat().st_size > 10:
            return md_cache_file.read_text(encoding="utf-8")

    # ดึงข้อมูลภาพเป็น bytes ในหน่วยความจำ (In-Memory)
    if pdf_or_img_path.suffix.lower() == ".pdf":
        img_bytes = render_pdf_page_to_bytes(pdf_or_img_path, page_num, dpi=DPI)
    else:
        img_bytes = pdf_or_img_path.read_bytes()

    # แปลง bytes เป็น Base64 สำหรับส่งเข้า API
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    payload = {
        "model": ocr_model,
        "messages": [
            {
                "role": "user",
                "content": TYPHOON_OCR_PROMPT,
                "images": [img_b64]
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.6,
            "repeat_penalty": 1.1
        }
    }

    res = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=300)
    res.raise_for_status()
    md_text = res.json().get("message", {}).get("content", "")

    # บันทึกเฉพาะไฟล์ข้อความ Markdown เก็บไว้ใช้งานซ้ำ
    if md_cache_file is not None:
        md_cache_dir.mkdir(parents=True, exist_ok=True)
        md_cache_file.write_text(md_text, encoding="utf-8")

    return md_text


# ==============================================================================
# Stage 2: สกัด Markdown เป็น JSON ด้วย LLM (Qwen / Llama) + JSON Schema
# ==============================================================================
def extract_courses_from_markdown_llm(
    md_text: str,
    model: str = "qwen3:4b",
    host: str = "http://127.0.0.1:11434",
    timeout: int = 180
) -> list[dict]:
    """ส่งข้อความ Markdown เข้า LLM พร้อม JSON Schema เพื่อสกัดรายวิชา"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract all courses from this Markdown into JSON:\n\n{md_text}"}
        ],
        "format": COURSE_SCHEMA,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_ctx": 4096
        }
    }

    res = requests.post(f"{host}/api/chat", json=payload, timeout=timeout)
    res.raise_for_status()

    content = res.json().get("message", {}).get("content", "{}")
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    data = json.loads(content)
    if isinstance(data, dict):
        return data.get("courses", [])
    elif isinstance(data, list):
        return data
    return []


# ==============================================================================
# นำเข้าฐานข้อมูล SQLite (ตาราง course)
# ==============================================================================
def save_to_database(db_path: Path, courses: list[dict]) -> int:
    """นำเข้าหรืออัปเดตข้อมูลลงตาราง course ของ SQLite"""
    if not db_path.exists():
        raise FileNotFoundError(f"ไม่พบฐานข้อมูล SQLite: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    count = 0
    for c in courses:
        cur.execute("""
            INSERT INTO course (code, name_th, name_en, credits, lecture_h, lab_h, self_h, description_th, pdf_pages, printed_pages)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name_th = excluded.name_th,
                name_en = coalesce(excluded.name_en, course.name_en),
                credits = excluded.credits,
                lecture_h = excluded.lecture_h,
                lab_h = excluded.lab_h,
                self_h = excluded.self_h,
                description_th = coalesce(excluded.description_th, course.description_th),
                pdf_pages = excluded.pdf_pages,
                printed_pages = excluded.printed_pages
        """, (
            c["code"],
            c["name_th"],
            c.get("name_en"),
            c["credits"],
            c.get("lecture_h", 3),
            c.get("lab_h", 0),
            c.get("self_h", 6),
            c.get("description_th"),
            c.get("pdf_pages"),
            c.get("printed_pages")
        ))
        count += 1
    conn.commit()
    conn.close()
    return count


# ==============================================================================
# Main CLI
# ==============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="สกัดหมวดวิชาศึกษาทั่วไป (GenEd) ด้วย Two-Stage Architecture: Typhoon-OCR 1.5 -> LLM JSON Schema"
    )
    parser.add_argument("-i", "--input", default="data/input/fulldoc_dsba.pdf",
                        help="พาธไฟล์นำเข้า: ไฟล์ PDF (เช่น data/input/fulldoc_dsba.pdf) หรือ JSON OCR เดิม")
    parser.add_argument("-o", "--output", default="work/lab8b_run/gened_courses.json",
                        help="พาธไฟล์ JSON ผลลัพธ์ (ค่าเริ่มต้น: work/lab8b_run/gened_courses.json)")
    parser.add_argument("--out-md", default="work/lab8b_run/gened_combined.md",
                        help="พาธไฟล์ Markdown รวมทุกหน้าเข้าเป็นไฟล์เดียว (ค่าเริ่มต้น: work/lab8b_run/gened_combined.md)")
    parser.add_argument("-d", "--database", default=None,
                        help="พาธ SQLite database (เช่น work/lab8b_run/curriculum.db)")
    parser.add_argument("--pages", default="153-227",
                        help="ช่วงหน้า PDF ที่ต้องการสกัด เช่น '153-154' สำหรับทดสอบ หรือ '153-227' สำหรับทั้งหมวด")
    parser.add_argument("--ocr-model", default="scb10x/typhoon-ocr1.5-3b:latest",
                        help="โมเดล Typhoon-OCR สำหรับ Stage 1 (ค่าเริ่มต้น: scb10x/typhoon-ocr1.5-3b:latest)")
    parser.add_argument("--model", default="qwen3:4b",
                        help="โมเดล LLM สำหรับ Stage 2 (ค่าเริ่มต้น: qwen3:4b หรือระบุ llama3.2:3b)")
    parser.add_argument("--md-dir", default="work/lab8b_run/markdown_pages",
                        help="โฟลเดอร์เก็บไฟล์แคช Markdown จาก Typhoon-OCR (ค่าเริ่มต้น: work/lab8b_run/markdown_pages)")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434",
                        help="URL ของ Ollama Service (ค่าเริ่มต้น: http://127.0.0.1:11434)")

    args = parser.parse_args()

    in_path = Path(args.input)
    # ถ้าระบุค่าเริ่มต้นเป็น pdf แต่ไม่พบ ให้ลองหา outputs/fulldoc_dsba_ocr.json เป็นตัวสำรอง
    if not in_path.exists():
        fallback_json = Path("outputs/fulldoc_dsba_ocr.json")
        if fallback_json.exists():
            print(f"ℹ ไม่พบ {in_path} -> สลับมาใช้ {fallback_json} แทน")
            in_path = fallback_json
        else:
            print(f"❌ ไม่พบไฟล์ input: {in_path}")
            sys.exit(1)

    wanted_pages = set(parse_page_range(args.pages))
    md_dir = Path(args.md_dir) if args.md_dir else None

    print("=" * 70)
    print("  ระบบสกัดหมวดวิชาศึกษาทั่วไป (GenEd) — Typhoon-OCR + LLM JSON Schema")
    print("=" * 70)
    print(f"  • ไฟล์นำเข้า    : {in_path}")
    print(f"  • ช่วงหน้า      : {args.pages} ({len(wanted_pages)} หน้า)")
    print(f"  • Stage 1 (OCR) : {args.ocr_model} (In-Memory Image Rendering)")
    print(f"  • Stage 2 (LLM) : {args.model} ({args.ollama_url})")
    if md_dir:
        print(f"  • Markdown Dir : {md_dir}")
    if args.out_md:
        print(f"  • รวม Markdown : {args.out_md}")
    print(f"  • ไฟล์ส่งออก    : {args.output}")
    if args.database:
        print(f"  • ฐานข้อมูล     : {args.database}")
    print("=" * 70)

    target_pages_data = []
    is_pdf = in_path.suffix.lower() == ".pdf"

    if is_pdf:
        for p in sorted(list(wanted_pages)):
            target_pages_data.append({"page": p, "pdf_path": in_path})
    else:
        # กรณีส่งไฟล์ JSON เข้ามา
        json_data = json.loads(in_path.read_text(encoding="utf-8"))
        for p in json_data.get("pages", []):
            if p.get("page", 0) in wanted_pages:
                target_pages_data.append(p)

    print(f"\n[*] เริ่มการสกัดข้อมูลจำนวน {len(target_pages_data)} หน้า ...\n")

    all_courses: list[dict] = []
    seen_codes: set[str] = set()
    combined_md_sections: list[str] = []
    t_start = time.time()

    for idx, p_info in enumerate(target_pages_data):
        page_num = p_info["page"]
        print(f"  [{idx + 1:2d}/{len(target_pages_data)}] หน้า {page_num:3d} ... ", end="", flush=True)
        t0 = time.time()

        try:
            # 1. Stage 1: แปลงภาพเป็น bytes ในหน่วยความจำ แล้วส่งเข้า Typhoon-OCR
            if is_pdf:
                md_text = get_page_markdown_via_typhoon(
                    pdf_or_img_path=in_path,
                    page_num=page_num,
                    md_cache_dir=md_dir,
                    ollama_url=args.ollama_url,
                    ocr_model=args.ocr_model
                )
            else:
                md_text = p_info.get("text", "")

            if md_text:
                combined_md_sections.append(
                    f"<!-- ========================================== -->\n"
                    f"<!-- PDF Page {page_num} (หน้าที่พิมพ์ {max(1, page_num - 4)}) -->\n"
                    f"<!-- ========================================== -->\n\n"
                    f"{md_text.strip()}\n"
                )

            # 2. Stage 2: ส่ง Markdown เข้า LLM แปลงเป็น JSON ตาม Schema
            page_courses = extract_courses_from_markdown_llm(
                md_text=md_text,
                model=args.model,
                host=args.ollama_url
            )
            for c in page_courses:
                c["pdf_pages"] = str(page_num)
                c["printed_pages"] = str(max(1, page_num - 4))
            elapsed = time.time() - t0
            print(f"✓ ได้ {len(page_courses)} วิชา ({elapsed:.1f} วิ)")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในหน้า {page_num}: {e}")
            page_courses = []

        for c in page_courses:
            code = c.get("code")
            if code and code not in seen_codes:
                seen_codes.add(code)
                all_courses.append(c)

    # บันทึกไฟล์ Markdown รวมทุกหน้าเป็นไฟล์เดียว
    if args.out_md and combined_md_sections:
        out_md_path = Path(args.out_md)
        out_md_path.parent.mkdir(parents=True, exist_ok=True)
        header_text = (
            f"# เอกสารหลักสูตรหมวดวิชาศึกษาทั่วไป (GenEd)\n"
            f"# วันที่สกัด: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"# แหล่งข้อมูล: {in_path.name} (ช่วงหน้า: {args.pages})\n\n"
        )
        full_md_content = header_text + "\n\n---\n\n".join(combined_md_sections)
        out_md_path.write_text(full_md_content, encoding="utf-8")

    # บันทึกไฟล์ JSON
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(all_courses, ensure_ascii=False, indent=2), encoding="utf-8")

    total_time = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"✓ สกัดข้อมูลเสร็จสิ้นใน {total_time:.1f} วินาที!")
    print(f"  • จำนวนวิชาทั้งหมดที่ได้: {len(all_courses)} วิชา")
    if args.out_md:
        print(f"  • บันทึกรวม Markdown ทุกหน้า: {args.out_md}")
    print(f"  • บันทึกลงไฟล์ JSON: {out_path}")

    # นำเข้า SQLite
    if args.database:
        db_path = Path(args.database)
        print(f"\n[*] กำลังบันทึกข้อมูลเข้าตาราง 'course' ใน SQLite: {db_path} ...")
        inserted = save_to_database(db_path, all_courses)
        print(f"✓ อัปเดตตาราง 'course' สำเร็จ: {inserted} วิชา")
    print("=" * 70)


if __name__ == "__main__":
    main()
