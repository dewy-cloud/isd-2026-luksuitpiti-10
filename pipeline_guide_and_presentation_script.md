# คู่มือการดำเนินงานระบบหลักสูตรอัจฉริยะ (ISD 2026: Luksuitpiti)
## End-to-End CLI Pipeline Guide, Database Architecture & Step-by-Step Spoken Scripts

เอกสารนี้รวบรวมขั้นตอนคำสั่ง Command-Line Interface (CLI) ตั้งแต่เปิดเครื่องคอมพิวเตอร์ ทำการถอดรหัสเอกสาร PDF ด้วย OCR, การสกัดโครงสร้างรายวิชาและข้อบังคับสถาบันฯ ครบทั้ง 4 หลักสูตร (**DSBA / BIT / IT / AIT**), การนำเข้าและตรวจสอบความสอดคล้องของฐานข้อมูล SQLite, ไปจนถึงการเปิดระบบบริการถาม-ตอบผ่าน Web Application **โดยมี "สคริปต์บทพูดพรีเซนต์กำกับอธิบายในทุกๆ ขั้นตอน (Phase 0 – Phase 6)" อย่างละเอียด**

---

## สารบัญ
1. [ภาพรวมสถาปัตยกรรมระบบ (System Architecture)](#1-ภาพรวมสถาปัตยกรรมระบบ-system-architecture)
2. [ข้อมูลและเลขหน้าของทั้ง 4 หลักสูตร](#2-ข้อมูลและเลขหน้าของทั้ง-4-หลักสูตร)
3. [ขั้นตอนการทำงาน CLI ตั้งแต่เปิดเครื่องคอมพิวเตอร์ พร้อมสคริปต์บทพูด](#3-ขั้นตอนการทำงาน-cli-ตั้งแต่เปิดเครื่องคอมพิวเตอร์-พร้อมสคริปต์บทพูด)
   - [Phase 0: การเตรียมความพร้อมสภาพแวดล้อม (Environment & Local Models)](#phase-0-การเตรียมความพร้อมสภาพแวดล้อม-environment--local-models)
   - [Phase 1: การประมวลผล OCR จากเอกสาร PDF ทั้งเล่ม (Lab 1 – 3)](#phase-1-การประมวลผล-ocr-จากเอกสาร-pdf-ทั้งเล่ม-lab-1--3)
   - [Phase 2: การสกัดข้อมูลระดับฟิลด์และประเมินผลเบื้องต้น (Lab 4 – 6)](#phase-2-การสกัดข้อมูลระดับฟิลด์และประเมินผลเบื้องต้น-lab-4--6)
   - [Phase 3: การสกัดแผนการศึกษาและข้อบังคับด้วย Local AI (Lab 7B)](#phase-3-การสกัดแผนการศึกษาและข้อบังคับด้วย-local-ai-lab-7b)
   - [Phase 4: การนำเข้าข้อมูลสู่ฐานข้อมูล SQLite & ตรวจสอบ 7 กฎ (Lab 8B)](#phase-4-การนำเข้าข้อมูลสู่ฐานข้อมูล-sqlite--ตรวจสอบ-7-กฎ-lab-8b)
   - [Phase 5: การทดสอบ Benchmark ทั้งระบบ 4 ขั้นตอน (Lab 9)](#phase-5-การทดสอบ-benchmark-ทั้งระบบ-4-ขั้นตอน-lab-9)
   - [Phase 6: การเปิดใช้งาน Web Application และ API Service (Lab 10)](#phase-6-การเปิดใช้งาน-web-application-และ-api-service-lab-10)
4. [โครงสร้างตารางฐานข้อมูลและการเชื่อมโยง (Database Schema)](#4-โครงสร้างตารางฐานข้อมูลและการเชื่อมโยง-database-schema)

---

## 1. ภาพรวมสถาปัตยกรรมระบบ (System Architecture)

```mermaid
flowchart TD
    subgraph S1["Phase 1: Input & OCR"]
        P1["PDF เล่มหลักสูตร มคอ.2<br/>(DSBA, BIT, IT, AIT)"] --> O1["Tesseract / Paddle Engine<br/>src.ocr_system.pipeline"]
        O1 --> O2["Raw OCR Full-text<br/>outputs/fulldoc_*_ocr.json"]
    end

    subgraph S2["Phase 2: Extraction & Alignment"]
        O2 --> E1["Field Extraction & Alignment<br/>src.ocr_system.field_extraction"]
        E1 --> E2["Multi-level Evaluation<br/>lab6/run_lab6_eval.py"]
        P1 --> E3["Local VLM (Typhoon-OCR 1.5)<br/>+ Qwen3 Extraction (Lab 7B)"]
        E3 --> E4["Structured JSON Plans & Regulations<br/>work/lab7b_run/"]
    end

    subgraph S3["Phase 3: Database & Verification"]
        E4 --> D1["Database Transformer & Loader<br/>run_lab8b.py / lab8b_curriculum_db.py"]
        D1 --> D2[("SQLite Database<br/>work/lab8b_run/curriculum.db")]
        D2 --> D3["7-Rule Consistency Verification<br/>work/lab8b_run/verify.json"]
    end

    subgraph S4["Phase 4: Serving & Evaluation"]
        D2 --> Q1["NL-to-SQL Service (Qwen3:4b)<br/>lab10_fastapi.curriculum_app"]
        Q1 --> Q2["FastAPI Server & Web UI<br/>http://127.0.0.1:8000"]
        D2 --> B1["4-Step Benchmark + Complexity Analysis<br/>run_all_eval.py / step5_eval_query_complexity.py"]
    end
```

---

## 2. ข้อมูลและเลขหน้าของทั้ง 4 หลักสูตร

| หลักสูตร | ชื่อปริญญาและสาขาวิชา | หน่วยกิตรวม | แผนการศึกษา | ช่วงหน้า PDF ของตารางแผน | ช่วงหน้าโครงสร้างเต็ม |
|---|---|:---:|---|:---:|:---:|
| **DSBA** | วท.บ. (วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ) | 132 | แผนปกติ (`no_coop`)<br>แผนสหกิจ (`coop`) | หน้า 26–32<br>หน้า 33–39 | หน้า 22–32<br>หน้า 22–25, 33–39 |
| **BIT** | วท.บ. (เทคโนโลยีสารสนเทศทางธุรกิจ) | 126 | แผนปกติ (`no_coop`)<br>แผนสหกิจ (`coop`) | หน้า 26–30<br>หน้า 31–35 | หน้า 22–30<br>หน้า 22–25, 31–35 |
| **IT** | วท.บ. (เทคโนโลยีสารสนเทศ) | 129 | แผนปกติ (`no_coop`)<br>แผนสหกิจ (`coop`) | หน้า 32–38<br>หน้า 39–45 | หน้า 24–38<br>หน้า 24–31, 39–45 |
| **AIT** | วท.บ. (เทคโนโลยีปัญญาประดิษฐ์) | 120 | แผนเดี่ยว (`single`) | หน้า 23–26 | หน้า 21–26 |
| **หมวดวิชาศึกษาทั่วไป (GenEd)** | หมวดวิชาศึกษาทั่วไป ฉบับปรับปรุง พ.ศ. 2564 | - | ใช้ร่วมกันทั้ง 4 หลักสูตร | หน้า 154–227 | ภาคผนวก ง |
| **ข้อบังคับสถาบันฯ** | ข้อบังคับ สจล. ว่าด้วยการศึกษาระดับปริญญาตรี 2564 | - | ภาคผนวก ก | หน้า 94, 96, 97, 98, 99, 101 | - |

---

## 3. ขั้นตอนการทำงาน CLI ตั้งแต่เปิดเครื่องคอมพิวเตอร์ พร้อมสคริปต์บทพูด

---

### Phase 0: การเตรียมความพร้อมสภาพแวดล้อม (Environment & Local Models)

เมื่อเปิดเครื่องคอมพิวเตอร์ ให้เปิด PowerShell และเข้าไปยังโฟลเดอร์โปรเจกต์:

```powershell
# 1. เข้าสู่ไดเรกทอรีโปรเจกต์
cd C:\Users\thewh\Downloads\isd-2026-luksuitpiti

# 2. สร้างและเปิดใช้งาน Virtual Environment (Python 3.11 หรือ 3.12)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. ติดตั้งไลบรารีที่จำเป็นทั้งหมด
pip install -r requirements.txt
pip install -r lab10_fastapi/curriculum_app/requirements.txt

# 4. สตาร์ท Ollama Local Service (รันในพื้นหลัง หรือเปิดอีกหน้าต่าง Terminal)
ollama serve

# 5. ดึงโมเดล Local AI ที่ใช้ในระบบ (รันออฟไลน์บนเครื่อง ไม่มีค่าใช้จ่าย API)
ollama pull qwen3:4b
ollama pull scb10x/typhoon-ocr1.5-3b
```

🎙️ **สคริปต์บทพูดสำหรับ Phase 0:**
> "ในการเริ่มต้นระบบ เราเริ่มจากการเตรียมสภาพแวดล้อมบนเครื่องคอมพิวเตอร์ โดยสร้าง Python Virtual Environment และติดตั้ง Dependencies ที่จำเป็นทั้งหมด จากนั้นเราสตาร์ทบริการ Ollama บนเครื่อง Local ซึ่งจุดเด่นสำคัญของระบบเราคือ **ทำงานแบบ Offline ภายในเครื่องทั้งหมด** โดยไม่ต้องพึ่งพา Cloud API ภายนอก ทำให้ไม่มีค่าใช้จ่าย และรักษาความปลอดภัยของข้อมูลได้อย่างสมบูรณ์ โดยเราใช้โมเดล **Qwen3 (4B)** สำหรับการประมวลผลข้อความและเขียน SQL และโมเดล **Typhoon-OCR 1.5** สำหรับการอ่านข้อความภาษาไทยจากภาพสแกนครับ"

💡 **นโยบายการกำหนดค่า Temperature (Greedy Decoding vs Controlled Stochasticity Policy)**:
* **`temperature = 0.0` (Zero Randomness / Greedy Decoding - ค่าหลักของระบบ)**:
  * **ใช้ตอนไหน**: ใช้ใน **OCR Stage** (อ่านภาพสแกนด้วย Typhoon-OCR), **NL2SQL Engine** (แปลงภาษาเป็นคำสั่ง SQL ด้วย Qwen3:4b), **Text Pipeline** (จัดโครงสร้างตารางเรียนเป็น JSON) และ **Answer Synthesis** (ตามฟังก์ชัน `ollama_generate()` ในโค้ดจริงที่ล็อกไว้ที่ 0.0)
  * **เหตุผล**: ใช้การถอดรหัสแบบ Greedy Decoding เพื่อ**ลดความแปรปรวนและเพิ่มความทำซ้ำได้ (Reproducibility)** ให้อ่านตัวอักษร/รหัสวิชาตรงตามต้นฉบับมากที่สุด เขียน SQL ได้ถูกต้องตามไวยากรณ์ และช่วยควบคุมการสังเคราะห์คำตอบให้อยู่ในขอบเขตของผลลัพธ์จาก SQL
* **`temperature = 0.1` (Low Stochasticity - กำหนดเฉพาะจุด)**:
  * **ใช้ตอนไหน**: ใช้ใน **Regulation Structuring** (จัดโครงสร้างข้อบังคับร้อยแก้วในภาคผนวก ก) และ **GenEd Stage 2** (สกัดคำอธิบายวิชาศึกษาทั่วไป 74 หน้า)
  * **เหตุผล**: อนุญาตให้มีความยืดหยุ่นทางภาษาเล็กน้อย เพื่อให้การจัดโครงสร้างเนื้อหาข้อความยาวๆ มีความเป็นธรรมชาติและช่วยลดการเกิดอาการติดลูปคำซ้ำภาษาไทย

---

### Phase 1: การประมวลผล OCR จากเอกสาร PDF ทั้งเล่ม (Lab 1 – 3)

การถอดรหัสข้อความทั้งเล่ม (300+ หน้า) จากไฟล์ PDF ออกมาเป็น JSON และ TXT:

```powershell
# 1. รัน OCR เล่ม DSBA
python -m src.ocr_system.pipeline --input data/input/fulldoc_dsba.pdf --output outputs/fulldoc_dsba_ocr.json --engine tesseract

# 2. รัน OCR เล่ม IT
python -m src.ocr_system.pipeline --input data/input/fulldoc_it.pdf --output outputs/fulldoc_it_ocr.json --engine tesseract

# 3. รัน OCR เล่ม AIT
python -m src.ocr_system.pipeline --input data/input/fulldoc_AIT.pdf --output outputs/fulldoc_AIT_ocr.json --engine tesseract

# 4. รัน OCR เล่ม BIT
python -m src.ocr_system.pipeline --input data/input/fulldoc_bit.pdf --output outputs/fulldoc_BIT_ocr.json --engine tesseract
```

📁 **ผลลัพธ์ที่ได้**:
* `outputs/fulldoc_dsba_ocr.json` และ `outputs/fulldoc_dsba_ocr.txt`
* `outputs/fulldoc_it_ocr.json` และ `outputs/fulldoc_it_ocr.txt`
* `outputs/fulldoc_AIT_ocr.json` และ `outputs/fulldoc_AIT_ocr.txt`
* `outputs/fulldoc_BIT_ocr.json` และ `outputs/fulldoc_BIT_ocr.txt`

🎙️ **สคริปต์บทพูดสำหรับ Phase 1:**
> "ขั้นตอนแรกคือการแปลงเอกสารดิบ เล่มหลักสูตร มคอ.2 ทั้ง 4 สาขา ซึ่งมีความหนากว่าเล่มละ 300 หน้า ผ่าน Full-document OCR Pipeline ด้วยคำสั่ง `pipeline` ของระบบ โดยผลลัพธ์จะถูกบันทึกเป็นไฟล์ JSON ที่เก็บทั้งข้อความรวมทั้งเล่ม และข้อความแยกเป็นรายหน้า พร้อมระบุเลขหน้าที่แท้จริง เพื่อเตรียมพร้อมสำหรับการสกัดและอ้างอิงตำแหน่งในขั้นตอนถัดไปครับ"

---

### Phase 2: การสกัดข้อมูลระดับฟิลด์และประเมินผลเบื้องต้น (Lab 4 – 6)

ทำการสกัดรายวิชา (รหัสวิชา, ชื่อไทย, ชื่ออังกฤษ, หน่วยกิต) จากข้อความ OCR และประเมินผล 3 ระดับ:

```powershell
# รันการประเมินผลประสิทธิภาพ 3 ระดับ ครบทั้ง 4 หลักสูตร
python lab6/run_lab6_eval.py
```

📁 **ผลลัพธ์ที่ได้**:
* `lab6/outputs/eval_field_level.json` (รายงานการประเมินความถูกต้องของการสกัดรหัสวิชาและหน่วยกิตเทียบกับ Ground Truth)
* `lab6/outputs/eval_page_level.csv` (รายงานการประเมินตำแหน่งหน้าอ้างอิงจริงเทียบกับ Ground Truth กว่า 1,106 รายการ)
* `lab6/outputs/eval_category_summary.csv` (ตารางสรุปรวมผลการประเมินรายหมวดวิชาและหลักสูตร)

🎙️ **สคริปต์บทพูดสำหรับ Phase 2:**
> "หลังจากได้ข้อความ OCR แล้ว เราทำการประเมินประสิทธิภาพผ่าน Lab 6 ซึ่งเชื่อมโยงโดยตรงจากฟังก์ชันสกัดใน Lab 4 โดยวัดผลครบ 3 มิติ:
> 1. **Field Level**: ตรวจสอบความถูกต้องในการดึงรหัสวิชาและหน่วยกิตเทียบกับ Ground Truth ครบทุกหลักสูตร โดยสามารถสกัดรหัสวิชาและโครงสร้างหน่วยกิตได้อย่างครบถ้วนและสอดคล้องกับเล่มหลักสูตร
> 2. **Page Level**: ตรวจสอบตำแหน่งหน้าที่พิมพ์จริงเทียบกับ Ground Truth กว่า 1,106 รายการ ยืนยันความแม่นยำในการระบุเลขหน้าอ้างอิงของแต่ละรายวิชา
> 3. **Category Level**: สรุปผลแยกตามหมวดวิชาศึกษาทั่วไปและวิชาเฉพาะของแต่ละสาขา ซึ่งผลลัพธ์ทั้งหมดถูกจัดเก็บลงในโฟลเดอร์ `lab6/outputs/` อย่างเป็นระบบครับ"

---

### Phase 3: การสกัดแผนการศึกษาด้วย Text Pipeline (Chunked LLM) และข้อบังคับด้วย Local VLM/LLM (Lab 7B)

สกัดโครงสร้างตารางเรียนด้วย Text Pipeline (Chunked LLM: Qwen3:4b) และสกัดข้อบังคับสถาบันฯ ด้วย Typhoon-OCR และ Qwen3:

```powershell
# 1. สกัดตารางแผนการเรียน DSBA (แผนสหกิจ + กลุ่มวิชาเลือกเฉพาะ: หน้า 19–25, 33–39)
python src/ocr_system/lab7b_curriculum.py -i data/input/fulldoc_dsba.pdf --pages 19-25,33-39 --pipeline text --out work/lab7b_run/DSBA

# 2. สกัดตารางแผนการเรียน BIT (แผนสหกิจ + กลุ่มวิชาเลือกเฉพาะ: หน้า 24–25, 31–35)
python src/ocr_system/lab7b_curriculum.py -i data/input/fulldoc_bit.pdf --pages 24-25,31-35 --pipeline text --out work/lab7b_run/BIT

# 3. สกัดตารางแผนการเรียน IT (แผนสหกิจ + กลุ่มวิชาเลือกเฉพาะ: หน้า 26–30, 39–45)
python src/ocr_system/lab7b_curriculum.py -i data/input/fulldoc_it.pdf --pages 26-30,39-45 --pipeline text --out work/lab7b_run/IT

# 4. สกัดตารางแผนการเรียน AIT (แผนเดี่ยว + กลุ่มวิชาเลือกเฉพาะ: หน้า 21–26)
python src/ocr_system/lab7b_curriculum.py -i data/input/fulldoc_AIT.pdf --pages 21-26 --pipeline text --out work/lab7b_run/AIT

# (หมายเหตุ: หากต้องการสกัดเฉพาะตารางแผนการศึกษา 4 ปีโดยไม่รวมวิชาเลือก สามารถระบุ DSBA: 26-39, BIT: 26-35, IT: 32-45, AIT: 23-26)

# 5. สกัดข้อบังคับสถาบันฯ ภาคผนวก ก หน้า 94, 96–99, 101 (เกณฑ์ลงทะเบียน, ทุจริต, ภาคทัณฑ์, พ้นสภาพ, เกียรตินิยม)
python -c "from src.ocr_system.lab7b_curriculum import run_extract_regulations; run_extract_regulations()"

# 6. สกัดคำอธิบายรายวิชาหมวดศึกษาทั่วไป (GenEd) หน้า 154–227 ด้วย Two-Stage Architecture (Typhoon-OCR 1.5 + Qwen3)
python src/ocr_system/extract_gened.py -i data/input/fulldoc_dsba.pdf --pages 154-227 -o work/lab7b_run/gened_courses.json --out-md work/lab7b_run/gened_combined.md --md-dir work/lab7b_run/markdown_pages
```

📁 **ผลลัพธ์ที่ได้**:
* `work/lab7b_run/DSBA/pred_text.json`
* `work/lab7b_run/BIT/pred_text.json`
* `work/lab7b_run/IT/pred_text.json`
* `work/lab7b_run/AIT/pred_text.json`
* `work/lab7b_run/regulations/regulations.json`
* `work/lab7b_run/regulations/intermediate_regulations_vlm.md`
* `work/lab7b_run/markdown_pages/` (แคช Markdown รายหน้า 74 หน้า)
* `work/lab7b_run/gened_combined.md` (ไฟล์ Markdown รวมหมวดวิชาศึกษาทั่วไปทั้งหมด)
* `work/lab7b_run/gened_courses.json` (ข้อมูลรายวิชา GenEd ครบทั้ง 266 วิชา พร้อมชื่อและคำอธิบายภาษาไทย name_th, description_th และโครงสร้างหน่วยกิตย่อย lecture_h, lab_h, self_h ครบถ้วน 100%)

🎙️ **สคริปต์บทพูดสำหรับ Phase 3:**
> "ใน Phase ที่ 3 มีจุดเด่นด้านวิศวกรรมคือเราแบ่งกลยุทธ์การสกัดออกเป็น 3 รูปแบบอย่างเหมาะสมกับลักษณะข้อมูล:
> 
> 1. **สำหรับตารางแผนการศึกษาทั้ง 4 สาขา (คำสั่งที่ 1–4)**: เราเลือกใช้ **`--pipeline text`** ซึ่งเป็นการดึงข้อความดิจิทัลจากเล่มโดยตรง (Digital Text Layer) แล้วส่งประมวลผลผ่าน **Chunked Local LLM (Qwen3:4b)** โดยตรงทีละหน้า/ชิ้นส่วน เพื่อให้โมเดลจัดโครงสร้างตารางเรียนเป็น JSON ตาม Schema ครอบคลุมทั้งรหัสวิชา, ชื่อวิชา, ชั้นปี (Year), ภาคการศึกษา (Semester), และแยกแผนปกติ/สหกิจได้อย่างแม่นยำ โดยแต่ละหลักสูตรใช้เวลาประมวลผลประมาณ 106–410 วินาทีครับ
> 
> 2. **สำหรับข้อบังคับสถาบันฯ ในภาคผนวก ก (คำสั่งที่ 5)**: เนื่องจากเป็นข้อความบรรยายร้อยแก้วยาวๆ ในหน้า 94, 96–99, 101 เราจึงใช้ **Local VLM & LLM Pipeline** โดยใช้ **Typhoon-OCR 1.5** ในการอ่านข้อความจากภาพสแกน และใช้ **Qwen3 (4B)** ในการสกัดเงื่อนไขตัวเลข GPA, หน่วยกิตขั้นต่ำ/สูงสุด, และบทลงโทษการทุจริต ออกมาเป็นโครงสร้าง `regulations.json` พร้อมระบุเลขข้อบังคับและเลขหน้าอ้างอิงจริงครับ
> 
> 3. **สำหรับหมวดวิชาศึกษาทั่วไป (GenEd ในหน้า 154–227) (คำสั่งที่ 6)**: เนื่องจากส่วนนี้เป็นเอกสารสแกนที่มี Font Encoding เสียหายจน Text Extractor ทั่วไปอ่านเป็นภาษาต่างดาว เราจึงพัฒนา Two-Stage Architecture โดยใช้ **Typhoon-OCR 1.5** อ่านภาพเป็น Markdown และใช้ **Qwen3 (4B)** สกัดเป็น JSON ตาม Schema พร้อมเทคนิค **Batch Stage Processing** แยกก้อนประมวลผล OCR และ LLM เพื่อกำจัดปัญหา Ollama Memory Swapping และมี **Page-by-page Caching** ทำให้ได้ข้อมูลหน่วยกิตและคำอธิบายรายวิชาที่สมบูรณ์ 100% ครบทั้ง 266 วิชาครับ"

---

### Phase 4: การนำเข้าข้อมูลสู่ฐานข้อมูล SQLite & ตรวจสอบ 7 กฎ (Lab 8B)

แปลงโครงสร้างและโหลดเข้าสู่ฐานข้อมูลเชิงสัมพันธ์ พร้อมรัน Consistency Check:

```powershell
# รันสคริปต์อัตโนมัติ นำเข้าทั้ง 4 หลักสูตรและข้อบังคับลง SQLite
python run_lab8b.py --program all --skip-eval
```

📁 **ผลลัพธ์ที่ได้**:
* `work/lab8b_run/curriculum.db` (ขนาด ~192 KB บรรจุ 8 ตาราง: `program`, `study_plan`, `course`, `plan_item`, `elective_slot`, `program_course`, `prerequisite`, `regulation` พร้อม views `v_plan` และ `v_semester_credits`)
* `work/lab8b_run/verify.json` (รายงานการตรวจสอบกฎ 7 ข้อ CHK1–CHK7: ผ่านเกณฑ์ความสอดคล้องครบทุกข้อ 100.0%)
* `work/lab8b_run/schema/schema.sql` (ไฟล์ DDL สำหรับสร้างฐานข้อมูลเชิงสัมพันธ์)

🎙️ **สคริปต์บทพูดสำหรับ Phase 4:**
> "เมื่อได้ข้อมูล JSON ครบถ้วน เราจะรันสคริปต์ `run_lab8b.py` ซึ่งจะทำการแปลงและโหลดข้อมูลทั้งหมดเข้าสู่ฐานข้อมูลเชิงสัมพันธ์ SQLite ชื่อ `curriculum.db` โดยเก็บครบทั้งข้อมูลหลักสูตร, แผนการเรียน, รายวิชา, วิชาบังคับก่อน, และข้อบังคับสถาบันฯ
> 
> พร้อมกันนั้น สคริปต์จะทำการตรวจสอบ **Consistency Verification ตามกฎ 7 ข้อ (CHK1–CHK7)** โดยอัตโนมัติ เช่น ผลรวมหน่วยกิตตรงกับหลักสูตร, หน่วยกิตต่อเทอมไม่เกินเกณฑ์, และไม่มีเงื่อนไขวิชาบังคับก่อนที่วนลูป ซึ่งรายงานใน `verify.json` ยืนยันว่าโครงสร้างข้อมูลและเงื่อนไขทั้งหมดผ่านเกณฑ์ความสอดคล้องครบทุกข้อครับ"

---

### Phase 5: การทดสอบ Benchmark ทั้งระบบ 4 ขั้นตอน (Lab 9)

ทดสอบประเมินประสิทธิภาพ End-to-End: สกัด $\rightarrow$ Schema $\rightarrow$ Text-to-SQL $\rightarrow$ ตอบ & อ้างอิงหน้าจริง:

```powershell
# รันการประเมินผลครบทั้ง 4 ขั้นตอน (--live = ถามโมเดลสด 189 ข้อ ประมาณ 5–6 นาที, ต้องเปิด Ollama)
python lab9/run_all_eval.py --live

# วิเคราะห์ผล Step 3 แยกตาม Query Complexity Level 1–5
python lab9/step5_eval_query_complexity.py --labels lab9/query_complexity_labels.json

# รวมคะแนน Extraction แบบ CER/WER/Exact Match ครบทั้ง 7 แผน
python lab9/step1_eval_all_curricula.py
```

📁 **ผลลัพธ์ที่ได้**:
* `lab9/reports/step1_extraction_metrics.json` (ความแม่นยำของการสกัดรายวิชา)
* `lab9/reports/step2_schema_verification.json` (ความสอดคล้อง 7 กฎ CHK1–CHK7)
* `lab9/reports/step3_nl2sql_benchmark.json` (ความถูกต้องของคำสั่ง SQL จากคำถามธรรมชาติ)
* `lab9/reports/step4_groundedness_metrics.json` (ความถูกต้องของคำตอบและการอ้างอิงเลขหน้าจริง)
* `lab9/reports/query_complexity_summary.csv` (สรุป Valid SQL และ Execution Accuracy แยก Level 1–5)
* `lab9/reports/query_complexity_detail.csv` (ผลรายคำถามพร้อมคำตอบที่ระบบให้, เฉลย, Gold Label, SQL และเหตุผลการจัดระดับ)
* `lab9/reports/all_curricula/comparison.csv` (คะแนน Extraction แบบ pooled แยกตามฟิลด์จากทั้ง 7 แผน)

🎙️ **สคริปต์บทพูดสำหรับ Phase 5:**
> "ใน Phase ที่ 5 เราใช้ Automated Evaluation Suite ของ Lab 9 ในการทดสอบ Benchmark ระบบ 4 ขั้นตอนหลัก ตั้งแต่การสกัด, ตรวจสอบ Schema, ประเมิน NL-to-SQL และตรวจสอบ Groundedness จากนั้นวิเคราะห์เพิ่มเติมด้วย Query Complexity Evaluation เพื่อแยกผล Level 1–5 ผลรอบล่าสุด 189 ข้อ SQL รันผ่าน 100% และให้ผลตรงเฉลย 96.30% จุดที่เราปรับแล้วได้ผลชัดคือ Regulation Query ซึ่งเดิมผิดเพราะโมเดลสร้างชื่อ category และ topic ไม่ตรงกับฐานข้อมูล พอเราแนบรายการ category/topic จริงจากตาราง regulation ลงใน Prompt คำถามข้อบังคับก็ถูกครบ 10 จาก 10 ข้อ ส่วนข้อผิดที่เหลือ 7 ข้อมาจากข้อมูลหรือเฉลยทั้งหมด ซึ่งต้องแก้ที่ขั้นสกัดข้อมูล ไม่ใช่ที่โมเดลครับ"

---

### Phase 6: การเปิดใช้งาน Web Application และ API Service (Lab 10)

เปิดบริการ FastAPI Web App เพื่อให้ผู้ใช้สามารถถาม-ตอบผ่านเบราว์เซอร์:

```powershell
# เปิดใช้งานเว็บเซิร์ฟเวอร์
uvicorn lab10_fastapi.curriculum_app.main:app --host 127.0.0.1 --port 8000 --reload
```

* 🌐 **หน้าเว็บสำหรับผู้ใช้งาน**: `http://127.0.0.1:8000`
* 📑 **หน้าแคตตาล็อกรายวิชา**: `http://127.0.0.1:8000/courses`
* 🛠️ **หน้า Interactive API Documentation**: `http://127.0.0.1:8000/docs`

🎙️ **สคริปต์บทพูดสำหรับ Phase 6:**
> "ขั้นตอนสุดท้ายคือการเปิดใช้งานระบบผ่านคำสั่ง `uvicorn` ซึ่งจะสตาร์ท FastAPI Application ขึ้นมาบนเครื่อง เมื่อเปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:8000` ผู้ใช้สามารถพิมพ์ถามคำถามภาษาธรรมชาติ เช่น *'วิชา 06026240 มีกี่หน่วยกิต'* หรือ *'เกียรตินิยมอันดับ 1 ต้องมี GPA สะสมอย่างน้อยเท่าไร'* ระบบจะแปลงคำถามเป็น SQL ดึงข้อมูลจาก `curriculum.db` แล้วสรุปคำตอบภาษาไทยพร้อมแสดง Badge อ้างอิงเลขหน้าจริงในเอกสาร มคอ.2 เช่น เกียรตินิยมอันดับ 1 ตอบ 3.5 อ้างอิงข้อ 27.2.2 หน้า 93 หน้าเว็บเรียกฟังก์ชันเดียวกับที่ใช้วัดผลใน Lab 9 ผลที่วัดได้จึงตรงกับที่ผู้ใช้เห็นจริง ผลทดสอบสดล่าสุด 189 ข้อใช้เวลาเฉลี่ย 1.64 วินาทีต่อข้อ (ต่ำสุด 0.74 วินาที, มัธยฐาน 1.58 วินาที) โดย SQL รันผ่าน 100% และให้ผลตรงเฉลย 96.30% ครับ"

---

## 4. โครงสร้างตารางฐานข้อมูลและการเชื่อมโยง (Database Schema)

ฐานข้อมูล `curriculum.db` ถูกออกแบบให้เป็น Relational Database (Option 2: Full Separation) เพื่อแก้ปัญหา Hallucination ของโมเดลภาษา โดยแยกเป็น 8 ตารางหลัก และ 2 Analytical Views ดังนี้:

```mermaid
erDiagram
    PROGRAM ||--o{ STUDY_PLAN : offers
    PROGRAM ||--o{ PROGRAM_COURSE : offers
    PROGRAM ||--o{ PLAN_ITEM : contextualizes
    STUDY_PLAN ||--o{ PLAN_ITEM : contains
    STUDY_PLAN ||--o{ ELECTIVE_SLOT : defines
    COURSE ||--o{ PLAN_ITEM : referenced_by
    COURSE ||--o{ PROGRAM_COURSE : mapped_to
    COURSE ||--o{ PREREQUISITE : has_prereq
    REGULATION }|..|| PROGRAM : governs

    PROGRAM {
        string program_id PK "รหัสหลักสูตร (DSBA, IT, BIT, AIT)"
        string name_th "ชื่อหลักสูตรภาษาไทย"
        string name_en "ชื่อหลักสูตรภาษาอังกฤษ"
        string degree "ชื่อปริญญา"
        int total_credits "หน่วยกิตรวม (120-132)"
        int years "ระยะเวลาศึกษา (4 ปี)"
    }
    STUDY_PLAN {
        string plan_id PK "รหัสแผน เช่น DSBA_COOP"
        string program_id FK "UQ(plan_id, program_id)"
        string name_th "ชื่อแผนการศึกษาภาษาไทย"
        string name_en "ชื่อแผนการศึกษาภาษาอังกฤษ"
        string plan_type "coop, no_coop, single"
    }
    COURSE {
        string code PK "รหัสวิชา 8 หลัก (06xxxxxx, 90xxxxxx)"
        string name_th "ชื่อวิชาภาษาไทย"
        string name_en "ชื่อวิชาภาษาอังกฤษ"
        int credits "จำนวนหน่วยกิต"
        int lecture_h "ชั่วโมงบรรยาย"
        int lab_h "ชั่วโมงปฏิบัติการ"
        int self_h "ชั่วโมงศึกษาด้วยตนเอง"
        string description_th "คำอธิบายรายวิชาภาษาไทย"
        string pdf_pages "เลขหน้าไฟล์ PDF"
        string printed_pages "เลขหน้าที่พิมพ์ในเอกสาร"
    }
    PLAN_ITEM {
        int id PK "ลำดับรายการ"
        string plan_id FK "Composite FK(plan_id, program_id)"
        string program_id FK "Composite FK(plan_id, program_id)"
        int year "ชั้นปี (1-4)"
        int semester "ภาคการศึกษา (1-2)"
        string code FK "FK ไปยัง course(code)"
        int credits "หน่วยกิตในแผน"
        string alt_group "กลุ่มวิชาทางเลือก"
        string note "หมายเหตุ"
    }
    ELECTIVE_SLOT {
        int id PK "ลำดับสล็อต"
        string plan_id FK "รหัสแผนการศึกษา"
        int year "ชั้นปี (1-4)"
        int semester "ภาคการศึกษา (1-2)"
        string slot_name_th "ชื่อสล็อตภาษาไทย"
        string slot_name_en "ชื่อสล็อตภาษาอังกฤษ"
        string code_pattern "รูปแบบรหัสวิชา"
        int credits "หน่วยกิตของสล็อต"
        string credit_options "ทางเลือกหน่วยกิต"
        string note "หมายเหตุ"
    }
    PROGRAM_COURSE {
        string program_id PK "รหัสหลักสูตร"
        string code PK "รหัสวิชา"
    }
    PREREQUISITE {
        string code PK "รหัสวิชาปลายทาง"
        string requires PK "รหัสวิชาบังคับก่อน"
        string kind PK "ประเภทเงื่อนไข (pre, co)"
    }
    REGULATION {
        int id PK "ลำดับข้อบังคับ"
        string program_id FK "หลักสูตรที่บังคับใช้ (ALL)"
        string category "หมวดหมู่ข้อบังคับ"
        string topic "หัวข้อ"
        string condition_desc "คำอธิบายเงื่อนไข"
        float min_gpa "เกรดเฉลี่ยขั้นต่ำ"
        float max_gpa "เกรดเฉลี่ยสูงสุด"
        int min_credits "หน่วยกิตขั้นต่ำ"
        int max_credits "หน่วยกิตสูงสุด"
        string penalty_action "บทลงโทษ"
        string article_no "เลขข้อบังคับ"
        int source_page "เลขหน้าอ้างอิงภาคผนวก ก"
    }
```

### ตาราง Analytical Views สำคัญ
* `v_plan`: รวมข้อมูลวิชาในแผนพร้อมคำอธิบายรายวิชาและสล็อตวิชาเลือก เชื่อมโยงผ่าน `study_plan` พร้อมแฟล็ก `is_elective_slot`
* `v_semester_credits`: สรุปผลรวมหน่วยกิตและจำนวนวิชาต่อภาคเรียนอย่างถูกต้อง แม่นยำ และไม่นับซ้ำ (คำนวณสล็อตวิชาเลือกและกลุ่มวิชาเลือกสลับ `alt_group`)

### การตรวจสอบความสอดคล้อง 7 กฎ (7-Rule Consistency Check)
ระบบมีฟังก์ชัน `verify_db()` ใน `src/ocr_system/lab8b_curriculum_db.py` ทำการทดสอบทางตรรกะเพื่อให้มั่นใจว่าข้อมูลมีความถูกต้องและสอดคล้องตามเกณฑ์ที่กำหนด:
1. **CHK1 (Total Credits)**: ผลรวมหน่วยกิตในแผนการศึกษาต้องเท่ากับหน่วยกิตรวมที่หลักสูตรประกาศ (เช่น DSBA 132, IT 129, BIT 126, AIT 120)
2. **CHK2 (No Orphan Codes)**: ทุกรหัสวิชาที่ปรากฏในแผน ต้องมีคำอธิบายรายวิชาในตาราง `course`
3. **CHK3 (Valid 8-Digit Codes)**: รหัสวิชาต้องเป็นตัวเลข 8 หลักตามมาตรฐาน สจล. ทุกรายการ
4. **CHK4 (Credit Consistency)**: หน่วยกิตในแผนการศึกษาต้องตรงกับหน่วยกิตในคำอธิบายรายวิชา
5. **CHK5 (Prerequisite Sequence)**: วิชาบังคับก่อน (Prerequisite) ต้องจัดสอนในภาคเรียนก่อนหน้าที่วิชาหลักจะเปิดสอน (ตรวจสอบเจาะจงขอบเขตรายแผนการศึกษา `b.plan_id = a.plan_id` ป้องกันความสับสนระหว่างภาคเรียนของแผนปกติและแผนสหกิจ)
6. **CHK6 (No Duplicate Courses)**: ห้ามมีวิชาซ้ำซ้อนกันในภาคเรียนเดียวกันของหลักสูตรเดียวกัน
7. **CHK7 (Term Credit Limits)**: หน่วยกิตที่ลงทะเบียนต่อภาคการศึกษาปกติ ต้องอยู่ระหว่าง 9 – 22 หน่วยกิต (ยกเว้นภาคสหกิจ/ฝึกงาน และภาคฤดูร้อน)

```powershell
# คำสั่งรันการตรวจสอบความสอดคล้อง (Verification) โดยตรง:
python src/ocr_system/lab8b_curriculum_db.py verify -d work/lab8b_run/curriculum.db
```
*(รายงานผลลัพธ์จะถูกบันทึกลงใน `work/lab8b_run/verify.json` โดยผ่านเกณฑ์ครบทั้ง 7 กฎ 100.0%)*
