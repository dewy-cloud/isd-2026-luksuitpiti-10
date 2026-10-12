# เอกสารสถาปัตยกรรมและการประเมินผลระบบอัจฉริยะ (System Architecture & Evaluation Specification)

**วิชา**: 06026240 การพัฒนาระบบอัจฉริยะ (Intelligent System Development)  
**คณะ**: เทคโนโลยีสารสนเทศ สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง (KMITL)  
**กลุ่ม**: Luksuitpiti  
**หลักสูตรเป้าหมาย**: 4 หลักสูตรระดับปริญญาตรี (DSBA, IT, BIT, AIT) ทั้งแบบปกติและสหกิจศึกษา  
**เอกสารนำเข้า**: เล่มหลักสูตร มคอ.2 (PDF ~150 หน้าต่อเล่ม) และข้อบังคับสถาบันฯ (ภาคผนวก ก)

---

## 1. ภาพรวมสถาปัตยกรรมทั้งระบบ (End-to-End System Architecture)

ระบบถูกออกแบบภายใต้สถาปัตยกรรม **Modular Decoupled Pipeline** โดยแยกแต่ละส่วนการทำงานออกจากกันอย่างชัดเจนตามหลัก **Separation of Concerns** เพื่อป้องกันข้อผิดพลาดต่อเนื่องและลดความเสี่ยงจากการสร้างข้อมูลเท็จ (Hallucination) ของโมเดลภาษาขนาดใหญ่ (LLM)

```mermaid
flowchart TD
    subgraph S1["1. Multimodal Document Processing (Lab 7B)"]
        PDF["เล่มหลักสูตร มคอ.2 (PDF)"] --> P1["PDF Parser & Page Slicer<br/>(PyMuPDF / pdfplumber)"]
        P1 --> P2["VLM Image OCR<br/>(Typhoon-OCR 1.5 3B)"]
        P1 --> P3["Direct Text Extraction"]
        P2 --> P4["Structure & Normalize<br/>(Qwen3:4b + PyThaiNLP)"]
        P3 --> P4
        P4 --> JSON_OUT["Structured JSON<br/>(pred_text.json / regulations.json)"]
    end

    subgraph S2["2. Relational Schema & Integrity (Lab 8B)"]
        JSON_OUT --> P5["Schema Ingestion & Repair<br/>(Pydantic Validation)"]
        P5 --> DB[("SQLite Database (Option 2)<br/>curriculum.db")]
        DB --> CHK["7 Consistency Rules<br/>(CHK1 - CHK7)"]
        CHK --> PASS{"ผ่านทุกกฎ 100%?"}
        PASS -- Yes --> READY[("Clean RDBMS Ready")]
        PASS -- No --> ABSTAIN["Abstain / Data Repair Loop"]
    end

    subgraph S3["3. Natural Language to SQL (Lab 8B / 9)"]
        USER_Q["คำถามภาษาธรรมชาติ (User Query)"] --> PROMPT["Schema-Grounded Prompting<br/>(DDL + Views Injection)"]
        PROMPT --> LLM_SQL["Text-to-SQL Generator<br/>(Qwen3:4b, Temp=0.1)"]
        LLM_SQL --> GUARD["SQL Security Guardrail<br/>(SELECT/WITH only)"]
        GUARD --> EXEC["SQLite Engine Query Execution"]
        EXEC -- "Syntax Error" --> RETRY["Self-Correction Loop<br/>(Max 2 Attempts)"]
        RETRY --> LLM_SQL
        EXEC -- "Success" --> ROWS["SQL Result Rows"]
    end

    subgraph S4["4. Grounded Synthesis & Production (Lab 10)"]
        ROWS --> SYNTH["Grounded Answer Synthesis<br/>(Qwen3:4b)"]
        READY --> CITE["Evidence Citation Engine<br/>(Page Numbers & Articles)"]
        SYNTH --> WEB["Full-Stack Web Application<br/>(FastAPI + Glassmorphic UI)"]
        CITE --> WEB
    end

    subgraph S5["5. Automated Evaluation Framework (Lab 9)"]
        JSON_OUT -.-> E1["Step 1: Extraction Evaluation<br/>(P / R / F1)"]
        READY -.-> E2["Step 2: Schema Verification<br/>(CHK1 - CHK7)"]
        EXEC -.-> E3["Step 3: NL2SQL Benchmark<br/>(Valid Rate & Execution Acc)"]
        SYNTH -.-> E4["Step 4: Groundedness Evaluation<br/>(Faithfulness & Citation Cov)"]
    end
```

---

## 2. รายละเอียดขั้นตอนการทำงานแต่ละส่วน (Pipeline Components Breakdown)

---

### ขั้นตอนที่ 1: การประมวลผลเอกสารและการสกัดข้อมูล (Multimodal Document Processing - Lab 7B)

#### 1.1 กระบวนการทำงาน (Process)
1. **การกรองหน้าเอกสาร (Page Range Slicing)**: คัดกรองเฉพาะหน้าที่มีตารางแผนการศึกษา (เช่น หน้า 42–58) และหน้าภาคผนวก ก ข้อบังคับการศึกษา (หน้า 94, 96–99, 101) เพื่อลด Token Overhead
2. **การสกัดแบบ Multimodal (Triple-Path Extraction)**:
   - **Path A (Text-based)**: สกัดตารางแผนการศึกษาจาก PDF Digital Text โดยตรงผ่าน `PyMuPDF` และ `pdfplumber` ร่วมกับ Regex Code Guard เพื่อให้ได้ความเร็วสูงสุดและลดโอกาสเกิด Hallucination
   - **Path B (VLM-based: ข้อบังคับ)**: แปลงหน้าข้อบังคับการศึกษาที่เป็นภาพสแกนเป็นภาพ PNG (150 DPI) แล้วส่งให้ Vision Language Model (`typhoon-ocr1.5-3b`) แปลงภาพเป็น Markdown ก่อนให้ `Qwen3:4b` สกัดเป็น JSON ข้อบังคับ (`regulations.json`)
   - **Path C (Two-Stage VLM + LLM: หมวด GenEd)**: สกัดคำอธิบายรายวิชาหมวดวิชาศึกษาทั่วไป (หน้า 154–227) ซึ่งมีปัญหาฟอนต์สแกนเสียหาย ผ่าน `extract_gened.py` ด้วยสถาปัตยกรรม Batch Stage Execution (Typhoon-OCR 1.5 $\rightarrow$ Markdown Cache $\rightarrow$ Qwen3 Schema Ingestion) สกัดได้ครบ **266 รายวิชา** พร้อมโครงสร้างชั่วโมงเรียน (lecture_h, lab_h, self_h) และคำอธิบายรายวิชาถูกต้องสมบูรณ์ 100% (266/266 วิชา)
3. **การจับคู่และประเมินเทียบ Ground Truth**: ใช้อัลกอริทึม **Multi-pass Alignment** (จับคู่แบบเข้มงวด `key_strict` และแบบผ่อนปรน `key_loose`) เพื่อคำนวณ Precision, Recall, F1 และวัดค่า CER/WER

```mermaid
flowchart LR
    PDF_FILE["เล่มหลักสูตร PDF"] --> SLICE["parse_page_range()"]
    SLICE -->|ตารางแผนการศึกษา| FITZ["PyMuPDF / pdfplumber"]
    SLICE -->|หน้าข้อบังคับสแกน| RENDER1["Render PNG (150 DPI)"]
    SLICE -->|หน้าวิชา GenEd 154-227| RENDER2["In-Memory PNG Bytes"]
    RENDER1 --> TYPHOON1["Typhoon-OCR 1.5 (VLM)"]
    RENDER2 --> TYPHOON2["Typhoon-OCR 1.5 (Batch Stage 1)"]
    TYPHOON1 --> MD_OUT1["intermediate_regulations_vlm.md"]
    TYPHOON2 --> MD_OUT2["markdown_pages/ (Page Caches)"]
    FITZ --> QWEN_JSON["Qwen3:4b (JSON Structuring)"]
    MD_OUT1 --> QWEN_REG["Qwen3:4b (Regulation Structuring)"]
    MD_OUT2 --> QWEN_GENED["Qwen3:4b (Batch Stage 2 Schema)"]
    QWEN_JSON --> NORM["clean_and_normalize_course()"]
    QWEN_REG --> REG_JSON["regulations.json"]
    QWEN_GENED --> GENED_JSON["gened_courses.json"]
    NORM --> PRED_JSON["pred_text.json"]
```

#### 1.2 โมเดล ไลบรารี และเครื่องมือที่ใช้
- **VLM Model**: `scb10x/typhoon-ocr1.5-3b` (ผ่าน Local Ollama)
- **Text LLM**: `qwen3:4b` (ผ่าน Local Ollama)
- **Libraries**: `pymupdf` (`fitz` 1.24+), `pdfplumber` (0.11+), `pythainlp` (5.0+ สำหรับ Thai word tokenization), `Pillow` (PIL)

#### 1.3 อัลกอริทึมและพารามิเตอร์ (Algorithm & Parameters)
| พารามิเตอร์ | ค่าที่กำหนด | เหตุผลทางเทคนิค |
| :--- | :--- | :--- |
| `DPI` | `150` | ความละเอียดที่สมดุลระหว่างความคมชัดของสระภาษาไทยและขนาดภาพเข้าโมเดล VLM |
| `PAGES_PER_CHUNK` | `1` | ค่าเริ่มต้น (1 หน้า/chunk) เพื่อป้องกัน Context Clutter และไม่ให้โมเดลตกหล่นแถวกลางตาราง |
| `temperature` (OCR, Structuring, NL2SQL, Answer) | `0.0` | อุณหภูมิ 0.0 แบบ Greedy Decoding ตามฟังก์ชัน `ollama_generate()` ในโค้ดจริง (บรรทัด 417) เพื่อลดความแปรปรวน เพิ่มความทำซ้ำได้ และคุมขอบเขตคำตอบ |
| `temperature` (Regulation & GenEd Stage 2) | `0.1` | ลดความสุ่มแต่เปิดความยืดหยุ่นทางภาษาเล็กน้อยสำหรับเนื้อหาร้อยแก้วยาวๆ ในข้อบังคับ และคำอธิบาย GenEd |
| `repeat_penalty` | `1.2` (Reg) / `1.1` (GenEd) | ป้องกันโมเดลเกิดอาการวนลูปข้อความภาษาไทย โดยใช้ 1.2 ในส่วนข้อบังคับ และ 1.1 ใน GenEd Stage 2 |
| `num_ctx` | `8192` | รองรับข้อความจากตารางหลักสูตรทั้งหน้า |
| `num_predict` | `4096` | รองรับ JSON Output ขนาดยาวที่บรรจุ 10–25 วิชาต่อ Chunk |

##### กลยุทธ์การกำหนด Temperature ของระบบ (Greedy Decoding vs Controlled Stochasticity Policy)
ระบบแบ่งนโยบายการควบคุมค่า Temperature ตามการอิมพลีเมนต์ในโค้ดจริงออกเป็น 2 ระดับ:
1. **`temperature = 0.0` (Zero Randomness / Greedy Decoding - ค่าเริ่มต้นหลักของระบบ)**:
   - **ความหมาย**: เป็นการสั่งให้โมเดลเลือกคำ/โทเคนที่ได้คะแนนความน่าจะเป็นสูงสุด (Probability สูงสุด) ในแต่ละตำแหน่งเสมอ เพื่อ**ลดความแปรปรวนและเพิ่มความทำซ้ำได้ (Reproducibility)** ให้ได้คำตอบที่คงเส้นคงวามากที่สุด
   - **จุดที่ระบบนำมาใช้งานจริงในโค้ด**:
     - **OCR Stage** ([`lab7b_curriculum.py`](src/ocr_system/lab7b_curriculum.py)): อ่านตัวอักษรไทย สระลอย วรรณยุกต์ และรหัสวิชา 8 หลักจากภาพสแกนให้ตรงตามเอกสารต้นฉบับมากที่สุด
     - **NL2SQL Engine** ([`lab8b_curriculum_db.py`](src/ocr_system/lab8b_curriculum_db.py)): แปลงคำถามภาษาธรรมชาติเป็นคำสั่ง SQL ที่ต้องมีความแม่นยำด้านไวยากรณ์ตายตัว เช่น การเลือกตาราง/วิว (`v_semester_credits`) และเงื่อนไขฟิลด์ (`program_id = 'IT'`) ป้องกันข้อผิดพลาด Syntax Error
     - **Text Pipeline Structuring** ([`lab7b_curriculum.py`](src/ocr_system/lab7b_curriculum.py)): จัดโครงสร้างตารางเรียนจาก Digital Text Layer เข้า Schema JSON เพื่อลดความแปรปรวนและลดความเสี่ยงจากข้อมูลหลอน
     - **Answer Synthesis** ([`model_service.py`](lab10_fastapi/curriculum_app/model_service.py)): เรียกผ่าน `ollama_generate()` ของ Lab 8B ซึ่งล็อก `temperature: 0.0` เพื่อช่วยควบคุมการสังเคราะห์คำตอบให้อยู่ในขอบเขตของผลลัพธ์จาก SQL
2. **`temperature = 0.1` (Low Stochasticity - กำหนดเฉพาะจุด)**:
   - **ความหมาย**: อนุญาตให้มีความยืดหยุ่นทางภาษาเล็กน้อย เพื่อให้การเรียบเรียงประโยคภาษาไทยมีความเป็นธรรมชาติ และลดการติดลูปคำซ้ำของภาษาไทย
   - **จุดที่ระบบนำมาใช้งานจริงในโค้ด**:
     - **Regulation Structuring** ([`lab7b_curriculum.py`](src/ocr_system/lab7b_curriculum.py)): สกัดข้อบังคับสถาบันฯ ที่เป็นบทร้อยแก้วยาวๆ ในภาคผนวก ก
     - **GenEd Stage 2** ([`extract_gened.py`](src/ocr_system/extract_gened.py)): สกัดคำอธิบายรายวิชาหมวดวิชาศึกษาทั่วไป 74 หน้า

#### 1.4 ระยะเวลาในการรัน (Execution Time)
- **สกัดตารางรายวิชาทั้งหลักสูตร (End-to-End Chunked LLM)**: 106.4 – 410.0 วินาที ต่อหลักสูตร (บันทึกจริงใน `_meta.elapsed_sec`: AIT: 106.4s, BIT: 268.7s, DSBA: 283.9s, IT: 410.0s)
- **สกัดข้อบังคับการศึกษา (VLM Path)**: ~5 – 7 วินาที ต่อหน้า PDF (6 หน้า รวม ~38 วินาที)
- **ประเมินผลเทียบ Ground Truth ในหน่วยความจำ (Step 1 Eval)**: **0.12 วินาที** (คำนวณใน RAM)

#### 1.5 ผลลัพธ์และตัวชี้วัด (Reproducible Extraction Evaluation Metrics - Lab 9 Step 1)
*ผลการรันจริงซ้ำจาก Repository ปัจจุบันผ่านคำสั่ง `python lab9/step1_eval_extraction.py` บนไฟล์ `work/lab7b_run/`:*

| หลักสูตร | Ground Truth | สกัดได้จริง | จับคู่ถูก (Matched) | วิชาตกหล่น (FN) | วิชาเกิน (FP) | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DSBA** | 90 | 96 | 86 | 4 | 10 | **89.6%** | **95.6%** | **92.5%** |
| **IT** | 106 | 108 | 102 | 4 | 6 | **94.4%** | **96.2%** | **95.3%** |
| **BIT** | 63 | 64 | 62 | 1 | 2 | **96.9%** | **98.4%** | **97.6%** |
| **AIT** | 57 | 41 | 39 | 18 | 2 | **95.1%** | **68.4%** | **79.6%** |
| **รวมจำนวน / เฉลี่ย Macro** | **316** | **309** | **289** | **27** | **20** | **94.0%** | **89.7%** | **91.3%** |

ผลด้านล่างเป็นอีกขอบเขตหนึ่งจากตารางข้างต้น: รวมตัวนับดิบของทั้ง 7 แผน (coop/no-coop และ AIT) แล้วคำนวณ CER/WER/Exact Match แยกตามฟิลด์ ไม่ใช่ค่าเฉลี่ย Macro และจำนวนรายการเป็นผลรวมข้ามแผน ไม่ใช่วิชาไม่ซ้ำกัน สร้างซ้ำได้ด้วย `python lab9/step1_eval_all_curricula.py`; CSV อยู่ที่ `lab9/reports/all_curricula/comparison.csv`.

| ฟิลด์ | จำนวนรายการ | CER | WER | Exact Match |
| :--- | ---: | ---: | ---: | ---: |
| รหัสวิชา | 578 | 7.33% | — | 94.12% |
| ชื่อวิชา (ไทย) | 578 | 13.12% | 25.38% | 65.92% |
| ชื่อวิชา (อังกฤษ) | 578 | 12.04% | 14.96% | 89.97% |
| หน่วยกิต | 578 | 13.33% | — | 87.02% |
| ปี/ภาค | 578 | 5.88% | — | 94.12% |
| หมวดวิชา | 578 | 6.02% | — | 93.43% |
| บังคับ/เลือก | 578 | 8.33% | — | 91.70% |
| วิชาบังคับก่อน | 544 | 1.93% | — | 98.53% |
| ภาคเรียนยืดหยุ่น | 544 | 54.23% | — | 73.71% |

WER รายงานเฉพาะฟิลด์ชื่อ ส่วนวิชาบังคับก่อนและภาคเรียนยืดหยุ่นคิดจากแถวที่จับคู่ได้ตาม evaluator เดิม

---

### ขั้นตอนที่ 2: สถาปัตยกรรมฐานข้อมูลและการตรวจความสอดคล้อง (Relational Schema & Consistency - Lab 8B)

#### 2.1 กระบวนการทำงาน (Process)
1. **การออกแบบเชิงสัมพันธ์ (Option 2: Full Separation)**: แยกตารางออกเป็น 8 ตารางเพื่อกำจัด Redundancy, รองรับความสัมพันธ์ Many-to-Many และแยกแผนการศึกษา:
   - `program`: ข้อมูลหลักสูตรภาพรวม (เช่น วท.บ. เทคโนโลยีสารสนเทศ 126 หน่วยกิต)
   - `study_plan`: แผนการศึกษาของแต่ละหลักสูตร เช่น แผนสหกิจศึกษา (`coop`), แผนปกติ (`no_coop`), แผนเดี่ยว (`single`) กำหนดข้อจำกัด `UNIQUE(plan_id, program_id)`
   - `course`: คลังรายวิชาส่วนกลางทั้งหมด พร้อมคำอธิบายรายวิชาและเลขหน้าอ้างอิง
   - `plan_item`: การจัดรายวิชาลงในแต่ละชั้นปี/ภาคเรียนของแต่ละแผนการศึกษา บังคับความถูกต้องด้วย Composite Foreign Key และ Course Foreign Key
   - `elective_slot`: ช่องสำหรับเลือกวิชาเลือกตามหมวดหมู่ พร้อมหน่วยกิตที่กำหนด
   - `program_course`: ตารางเชื่อมโยงระบุว่ารายวิชาใดสังกัดหลักสูตรใดบ้าง
   - `prerequisite`: ตารางความสัมพันธ์รายวิชาบังคับก่อน (Prerequisite / Co-requisite)
   - `regulation`: ข้อบังคับและระเบียบการศึกษาของสถาบัน (เช่น เกณฑ์วิทยาทัณฑ์, เกณฑ์พ้นสภาพ, ลาพัก)
2. **บทบาทสำคัญของตาราง `study_plan` และการบังคับความถูกต้องระดับโครงสร้าง (Structural Referential Integrity)**:
   - เป็นตัวเชื่อม (Bridge) ระหว่าง `program` กับรายวิชาในแผน (`plan_item`) และสล็อตวิชาเลือก (`elective_slot`)
   - แก้ไขปัญหาการซ้อนทับของหลักสูตรที่มีหลายทางเลือก: เช่น สาขา DSBA, IT, BIT มีทั้งแผนสหกิจศึกษา (`plan_type = 'coop'`) และแผนปกติ (`plan_type = 'no_coop'`) ส่วน AIT เป็นแผนเดี่ยว (`plan_type = 'single'`) รวม 7 แผนในระบบ
   - **Composite Foreign Key**: บังคับ `FOREIGN KEY (plan_id, program_id) REFERENCES study_plan(plan_id, program_id)` ในตาราง `plan_item` ป้องกันไม่ให้เกิดการจับคู่ข้ามหลักสูตร (เช่น เอา `plan_id` ของ BIT ไปใส่ `program_id` ของ DSBA)
   - **Course Foreign Key**: บังคับ `FOREIGN KEY (code) REFERENCES course(code)` ในตาราง `plan_item` รับประกันทางสถาปัตยกรรมว่าทุกวิชาในแผนต้องมีคำอธิบายรายวิชาใน `course` จริง 100%
3. **กลไกตรวจสอบรายวิชาบังคับก่อนภายนอก (Prerequisite Audit Engine)**:
   - ตาราง `prerequisite.requires` ไม่ถูกผูก Foreign Key เข้ากับ `course.code` เนื่องจากเล่มหลักสูตร สจล. มีวิชาบังคับก่อนที่เป็นวิชาศึกษาทั่วไปนอกคณะ ซึ่งไม่ได้พิมพ์คำอธิบายรายวิชาไว้ในเล่มของคณะไอที
   - ระบบใช้ **Prerequisite Audit Engine** วิเคราะห์และจำแนกตามมาตรฐานรหัสวิชาของ สจล. ในขั้นตอน Ingestion:
     - `06xxxxxx`: `[WARNING/SUSPICIOUS ANOMALY]` รายวิชาสังกัดคณะเทคโนโลยีสารสนเทศ ที่ไม่พบในคำอธิบายรายวิชา (วิชาตกหล่นหรือ OCR เพี้ยน)
     - `90xxxxxx`: `[INFO/EXTERNAL GENED_THAI]` รายวิชาศึกษาทั่วไป หมวดภาษา/สังคม ของสำนักศึกษาทั่วไป สจล. (ยอมรับเป็นรหัสภายนอกปกติ)
     - `96xxxxxx`: สำหรับหลักสูตร AIT จัดเป็น `[INFO/GENED_INTERNATIONAL]` แต่สำหรับหลักสูตรภาษาไทย จัดเป็น `[WARNING/OCR_TYPO]` เนื่องจากมีความเป็นไปได้สูงที่ OCR อ่านเลข 0 เพี้ยนเป็น 6 จากรหัส 90xxxxxx
4. **การป้องกัน Double Counting และการวิเคราะห์ด้วย Views**:
   - สล็อตวิชาเลือก (เช่น "วิชาเลือก 3 หน่วยกิต") จะถูกแยกเก็บในตาราง `elective_slot` และไม่นำมารวมใน `plan_item` ซ้ำซ้อน
   - `v_plan`: รวมข้อมูลวิชาในแผนพร้อมคำอธิบายรายวิชาและสล็อตวิชาเลือก เชื่อมโยงผ่าน `study_plan` พร้อมแฟล็ก `is_elective_slot`
   - `v_semester_credits`: สรุปผลรวมหน่วยกิตต่อภาคเรียนที่ถูกต้อง แม่นยำ และไม่นับซ้ำ (รองรับกลุ่มวิชาเลือกสลับ `alt_group`)
5. **วงจรตรวจสอบความถูกต้อง 7 ข้อบังคับ (CHK1–CHK7)**: ระบบจะรัน SQL Assertion อัตโนมัติ หากไม่ผ่านเกณฑ์จะสั่ง Abstain หรือเข้า Repair Loop ทันที

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
        string program_id PK
        string name_th
        string name_en
        string degree
        int total_credits
        int years
    }
    STUDY_PLAN {
        string plan_id PK
        string program_id FK "UQ(plan_id, program_id)"
        string name_th
        string name_en
        string plan_type
    }
    COURSE {
        string code PK
        string name_th
        string name_en
        int credits
        int lecture_h
        int lab_h
        int self_h
        string description_th
        string pdf_pages
        string printed_pages
    }
    PLAN_ITEM {
        int id PK
        string plan_id FK "Composite FK(plan_id, program_id)"
        string program_id FK "Composite FK(plan_id, program_id)"
        int year
        int semester
        string code FK "FK to course(code)"
        int credits
        string alt_group
        string note
    }
    ELECTIVE_SLOT {
        int id PK
        string plan_id FK
        int year
        int semester
        string slot_name_th
        string slot_name_en
        string code_pattern
        int credits
        string credit_options
        string note
    }
    PROGRAM_COURSE {
        string program_id PK
        string code PK
    }
    PREREQUISITE {
        string code PK
        string requires PK
        string kind PK
    }
    REGULATION {
        int id PK
        string program_id FK
        string category
        string topic
        string condition_desc
        float min_gpa
        float max_gpa
        int min_credits
        int max_credits
        string penalty_action
        string article_no
        int source_page
    }
```

#### 2.2 กฎความสอดคล้องทั้ง 7 ข้อ (The 7 Consistency Rules)
- **CHK1 (Total Credits)**: ผลรวมหน่วยกิตในแผนการศึกษาต้องเท่ากับหน่วยกิตรวมที่หลักสูตรประกาศ
- **CHK2 (No Orphan Codes)**: ทุกรหัสวิชาที่ปรากฏในแผน ต้องมีคำอธิบายรายวิชาในตาราง `course`
- **CHK3 (Valid 8-Digit Codes)**: รหัสวิชาต้องเป็นตัวเลข 8 หลักตามมาตรฐาน สจล. ทุกรายการ
- **CHK4 (Credit Consistency)**: หน่วยกิตในแผนการศึกษาต้องตรงกับหน่วยกิตในคำอธิบายรายวิชา
- **CHK5 (Prerequisite Sequence)**: วิชาบังคับก่อน (Prerequisite) ต้องจัดสอนในภาคเรียนก่อนหน้าที่วิชาหลักจะเปิดสอน (ตรวจสอบเจาะจงขอบเขตรายแผนการศึกษา `b.plan_id = a.plan_id` ป้องกันความสับสนระหว่างภาคเรียนของแผนปกติและแผนสหกิจ)
- **CHK6 (No Duplicate Courses)**: ห้ามมีวิชาซ้ำซ้อนกันในภาคเรียนเดียวกันของหลักสูตรเดียวกัน
- **CHK7 (Term Credit Limits)**: หน่วยกิตที่ลงทะเบียนต่อภาคการศึกษาปกติ ต้องอยู่ระหว่าง 9 – 22 หน่วยกิต

#### 2.3 โมเดล ไลบรารี และเครื่องมือที่ใช้
- **Database Engine**: `SQLite 3` พร้อมเปิดใช้งาน `PRAGMA foreign_keys = ON;` (ใช้โหมด Journal ปกติของ SQLite ยังไม่ได้เปิดใช้งาน WAL Mode)
- **Validation**: `Pydantic v2` (BaseModel Data Validation)
- **Language**: Python 3.11+ Standard Library (`sqlite3`, `pathlib`)

#### 2.4 ระยะเวลาและประสิทธิภาพในการประมวลผล (Execution & Performance)
- **นำเข้าข้อมูลและสร้างตาราง SQLite ทั้งหมด**: ประมวลผลผ่าน Python Script (`sqlite3`) แบบ Direct Local Transaction เสร็จสิ้นในระดับไม่ถึง 1 วินาที (Sub-second)
- **รันตรวจกฎความสอดคล้อง 7 ข้อ บน 5 ฐานข้อมูล (Step 2 Eval)**: ตรวจสอบความถูกต้องของ Foreign Key, Plan Scope และ Prerequisite Rules ครบ 7 กฎ อย่างรวดเร็วในหน่วยมิลลิวินาที (Sub-second)

#### 2.5 ผลลัพธ์และตัวชี้วัด (Evaluation Metrics)
| ฐานข้อมูล | รายวิชา (course) | แผนการศึกษา (study_plan) | รายการในแผน (plan_item) | สล็อตวิชาเลือก (elective_slot) | Prerequisite | ข้อบังคับ (regulation) | ผลการตรวจ CHK1–CHK7 | สถานะ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **curriculum.db (Unified Main)** | 504 | 7 | 268 | 71 | 30 | 11 | **ผ่าน 7/7 ข้อ (100.0%)** | ✅ สมบูรณ์ |
| **DSBA (Isolated)** | 79 | 1 | 36 | 17 | 5 | 11 | **ผ่าน 7/7 ข้อ (100.0%)** | ✅ สมบูรณ์ |
| **IT (Isolated)** | 99 | 1 | 47 | 6 | 17 | 11 | **ผ่าน 7/7 ข้อ (100.0%)** | ✅ สมบูรณ์ |
| **BIT (Isolated)** | 57 | 1 | 36 | 7 | 5 | 11 | **ผ่าน 7/7 ข้อ (100.0%)** | ✅ สมบูรณ์ |
| **AIT (Isolated)** | 34 | 1 | 34 | 7 | 4 | 11 | **ผ่าน 7/7 ข้อ (100.0%)** | ✅ สมบูรณ์ |

---

### ขั้นตอนที่ 3: ระบบค้นคืนและแปลงภาษาเป็น SQL (Natural Language to SQL Engine - Lab 8B / 9)

#### 3.1 กระบวนการทำงาน (Process)
1. **Schema-Grounded Prompting**: ส่งเฉพาะโครงสร้าง DDL ย่อ, Views สำคัญ และ Few-shot Examples ที่จำเป็นไปยัง Prompt เพื่อป้องกัน Context Clutter
2. **Constrained Output Decoding**: บังคับให้ LLM ส่งคืนเฉพาะ JSON `{"sql": "SELECT ..."}` ผ่าน Ollama Format Schema
3. **Security Guardrail (`guard_sql`)**: ตรวจสอบไวยากรณ์ด้วย Regex บังคับให้คำสั่งขึ้นต้นด้วย `SELECT` หรือ `WITH` เท่านั้น ป้องกัน SQL Injection และคำสั่งแก้ไขข้อมูล (`DROP`, `DELETE`, `UPDATE`, `INSERT`)
4. **Self-Correction Retry Loop**: หากเกิด Runtime หรือ Syntax Error ระบบจะจับ Exception แล้วส่ง Error Message กลับไปให้โมเดลแก้ไขตัวเองอัตโนมัติ (ลองทั้งหมด 2 ครั้ง: ครั้งแรก + แก้ไขซ้ำ 1 ครั้ง / `range(2)`)
5. **Abstain When Empty**: หากรันแล้วผลลัพธ์เป็น 0 แถว ระบบจะตอบปฏิเสธอย่างสุภาพ ("ไม่พบข้อมูลนี้ในเล่มหลักสูตร") เพื่อกำจัดการเดาของ LLM

```mermaid
flowchart TD
    Q["คำถามของผู้ใช้"] --> INJECT["Schema-Grounded Prompting<br/>(DDL + Constraints + Examples)"]
    INJECT --> LLM["Qwen3:4b<br/>(Ollama API, Temp=0.0)"]
    PARSE --> GUARD{"guard_sql()<br/>ตรวจสอบความปลอดภัย"}
    GUARD -- "ไม่ปลอดภัย" --> REJECT["ปฏิเสธคำสั่ง SQL"]
    GUARD -- "ปลอดภัย" --> RUN["Execute บน SQLite"]
    RUN -- "SQL Error" --> RETRY{"Attempt < 2?"}
    RETRY -- Yes --> FEEDBACK["ส่ง Error Message กลับเข้า Prompt"] --> LLM
    RETRY -- No --> FAIL["ยอมแพ้ ไม่เดาคำตอบ (Abstain)"]
    RUN -- "Success" --> ROWS{"แถวข้อมูล > 0?"}
    ROWS -- No --> NO_DATA["ตอบ: 'ไม่พบข้อมูลนี้ในเล่มหลักสูตร'"]
    ROWS -- Yes --> PASS_ROWS["ส่งต่อ Result Rows ให้ Synthesis"]
```

#### 3.2 โมเดล ไลบรารี และเครื่องมือที่ใช้
- **LLM**: `qwen3:4b` (ผ่าน Local Ollama REST API)
- **Directives**: เติม `/no_think` ใน Prompt เพื่อปิด Reasoning CoT ในงานที่ต้องการ Structured SQL Output สั้นและเร็ว
- **Libraries**: `sqlite3`, `requests`, `re`, `json`

#### 3.3 อัลกอริทึมและพารามิเตอร์ (Algorithm & Parameters)
| พารามิเตอร์ | ค่าที่กำหนด | เหตุผลทางเทคนิค |
| :--- | :--- | :--- |
| `model` | `qwen3:4b` | โมเดลขนาดกะทัดรัด (2.5 GB) ที่รองรับภาษาไทยและมีความสามารถด้าน Coding/SQL สูง |
| `temperature` | `0.0` | กำหนด 0.0 แบบ Greedy Decoding เพื่อลดความแปรปรวน เพิ่มความทำซ้ำได้ และให้คำสั่ง SQL คงเส้นคงวาแม่นยำสูงสุด |
| `num_ctx` | `4096` | เพียงพอต่อการใส่ DDL และตัวอย่าง Few-shot ทั้งหมด |
| `num_predict` | `256` | เพียงพอต่อความยาวของคำสั่ง SQL ทั่วไป (เฉลี่ย 40–80 โทเคน) |
| `max_attempts` | `2` (`range(2)`) | ลองทั้งหมด 2 ครั้ง (รอบแรก + Retry ซ่อมแซม 1 ครั้ง) เพื่อควบคุม Latency |

#### 3.4 ระยะเวลาในการรัน (Execution Time)
- **รันสดประเมินผลครบ 189 ข้อ (Live Evaluation Benchmark - `lab9/reports/live_eval_result.json`)**: **เฉลี่ย 1.85 วินาที/ข้อ** (ต่ำสุด 0.77 วินาที, ค่ามัธยฐาน 1.81 วินาที, สูงสุด 10.19 วินาที, เวลารวม 350.03 วินาที)
- **รันจาก Cache Baseline ในหน่วยความจำ (Cached Benchmark)**: **0.05 วินาที**

#### 3.5 ผลลัพธ์และตัวชี้วัด (NL2SQL Evaluation Metrics)
ชุดทดสอบรวมล่าสุด: **Gold Questions 189 ข้อ** ประกอบด้วยคำถามหลักสูตรเดิมที่ตัดรายการซ้ำออก 179 ข้อ และ Regulation Query เพิ่มเติม 10 ข้อ ส่วนผล Isolated DB ด้านล่างเป็น artifact แยกชุดละ 45 ข้อ

| ฐานข้อมูลทดสอบ | จำนวนคำถาม | คำสั่ง SQL รันผ่าน (Valid SQL) | ผลลัพธ์ SQL ตรงเฉลย (Execution Accuracy) | รูปแบบ Error ที่พบ |
| :--- | :---: | :---: | :---: | :--- |
| **BIT (Isolated DB)** | 45 | **100.0%** (45/45) | **100.0%** (45/45) | ไม่มี Error |
| **IT (Isolated DB)** | 45 | **100.0%** (45/45) | **100.0%** (45/45) | ไม่มี Error |
| **DSBA (Isolated DB)** | 45 | **100.0%** (45/45) | **86.7%** (39/45) | ค้นหาชื่อวิชาเลือกทางเลือกอื่น / ผลลัพธ์ว่างเปล่า (6 ข้อ) |
| **AIT (Isolated DB)** | 45 | **100.0%** (45/45) | **88.9%** (40/45) | รหัสวิชาหรือฟิลด์เฉพาะ / ผลลัพธ์ว่างเปล่า (5 ข้อ) |
| **Unified Main DB (รวมล่าสุด)** | **189** | **100.0% (189/189)** | **94.18% (178/189)** | ผลลัพธ์ไม่ตรง 11 ข้อ โดย 4 ข้อเป็น Regulation category/topic mismatch; ไม่มี Syntax Error |

> 📊 **ขอบเขตของตัวชี้วัดรอบล่าสุด**:
> - **NL2SQL Execution Accuracy (94.18% / 178 ข้อ)**: วัดว่าคำสั่ง SQL ให้ผลลัพธ์ตรงกับ Ground Truth (`step3_nl2sql_benchmark.json`)
> - ฟิลด์ `correct` ใน `live_eval_result.json` รอบล่าสุดคำนวณด้วย `score_one()` จาก SQL rows เช่นเดียวกัน จึงไม่รายงานเป็น Human-rated Final-Answer Correctness แยกอีกชุด

---

### ขั้นตอนที่ 4: การสังเคราะห์คำตอบและการอ้างอิงหลักฐาน (Grounded Answer Synthesis & Citations)

#### 4.1 กระบวนการทำงาน (Process)
1. **Grounded Synthesis**: นำแถวข้อมูลที่ได้จาก SQL (`rows`) ส่งเข้า `ANSWER_PROMPT` ของ `qwen3:4b` ให้สรุปเป็นภาษาไทยที่สุภาพ กระชับ และตรงตามตาราง
2. **Strict Groundedness Enforcement**: โมเดลถูกสั่งให้ตอบจากผลลัพธ์ SQL เท่านั้น และห้ามเติมข้อมูลที่ไม่มีอยู่ในตารางอย่างเด็ดขาด
3. **Evidence Citation Retrieval**: สกัด Metadata เลขหน้าและข้อบังคับจากคอลัมน์ `pdf_pages`, `printed_pages` และ `source_page` เพื่อแสดงเป็นป้ายเลขหน้าอ้างอิงกำกับ

```mermaid
flowchart LR
    ROWS["SQL Result Rows"] --> PROMPT["ANSWER_PROMPT<br/>(บังคับสรุปเฉพาะข้อมูลในตาราง)"]
    PROMPT --> QWEN["Qwen3:4b (Thai Synthesis)"]
    QWEN --> THAI_ANS["คำตอบภาษาไทยสละสลวย"]
    ROWS --> META["สกัด pdf_pages / source_page"]
    META --> PILLS["Evidence Citation Badges"]
    THAI_ANS --> FINAL["คำตอบสมบูรณ์พร้อมเลขหน้าอ้างอิง"]
    PILLS --> FINAL
```

#### 4.2 โมเดลและพารามิเตอร์ (Model & Parameters)
- **Model**: `qwen3:4b`
- **Prompt Directive**: `ANSWER_PROMPT` กำหนดรูปแบบ JSON Output `{"answer": "string"}`
- **Parameters**: `temperature = 0.0` (ผ่านฟังก์ชัน `ollama_generate()` ในโค้ดจริง), `num_predict = 256`

#### 4.3 ระยะเวลาในการรัน (Execution Time)
- **สังเคราะห์คำตอบต่อข้อ**: ~0.6 – 1.2 วินาที
- **ประเมินผลความซื่อสัตย์และการอ้างอิงในหน่วยความจำ (Step 4 Eval)**: **0.05 วินาที**

#### 4.4 ผลลัพธ์และตัวชี้วัด (Groundedness Evaluation Metrics)
- **ตัวชี้วัดจาก `lab9/reports/step4_groundedness_metrics.json` (Step 4 In-Memory Benchmark)**:
  - **Faithfulness / Groundedness Proxy**: **94.18%** (178/189 ข้อ โดยอิงฟิลด์ `correct` ที่ตรวจจาก SQL rows)
  - **Exact Match (EM)**: **93.89%** (169/180 ข้อ - วัดคำถามชนิด `value` และ `count`)
  - **Course Citation Coverage**: **99.8%** (503/504 รายวิชา มีเลขหน้าจริงในเล่ม มคอ.2 กำกับ)
  - **Regulation Citation Coverage**: **100.0%** (11/11 ข้อบังคับ มีเลขหน้าสแกนจริงในภาคผนวก ก)
- **ตัวชี้วัดจากการรันสด (`lab9/reports/live_eval_result.json`)**:
  - **Live Retrieval Correctness**: **94.18%** (178/189 ข้อ ตรวจจาก SQL rows)
  - **QA Latency**: เฉลี่ย **1.85 วินาที/ข้อ** (ต่ำสุด 0.77 วินาที, ค่ามัธยฐาน 1.81 วินาที, สูงสุด 10.19 วินาที, รวม 350.03 วินาที)

---

### ขั้นตอนที่ 5: เว็บแอปพลิเคชันและการแสดงผล (Full-Stack Web Application - Lab 10)

#### 5.1 สถาปัตยกรรมและกระบวนการทำงาน (Architecture & Flow)
1. **FastAPI Backend (`lab10_fastapi`)**:
   - เชื่อมต่อกับโมดูลฐานข้อมูลและ LLM โดยตรงผ่าน In-Memory Controller
   - **RESTful API Contract ครอบคลุม 13 Endpoints หลัก**:
     - `GET /api/health`: ตรวจสอบสถานะความพร้อมของฐานข้อมูลและ Ollama LLM
     - `GET /api/program`: ข้อมูลสรุปของหลักสูตรแรกที่พบ
     - `GET /api/programs`: รายการหลักสูตรทั้งหมดพร้อมหน่วยกิตรวมและระยะเวลาศึกษา
     - `GET /api/courses`: ค้นหาและแสดงรายวิชา พร้อมตัวกรอง `search`, `program_id`, `limit`, `offset`
     - `POST /api/courses`: เพิ่มรายวิชาใหม่ พร้อมระบบ **Dynamic Plan Resolution & Validation** (Single-plan เช่น AIT ทำการ Auto-fill `plan_id` ให้อัตโนมัติ; Multi-plan เช่น DSBA, IT, BIT บังคับส่ง `plan_id` มิฉะนั้นจะคืนค่า `422 Unprocessable Entity` ป้องกันการบันทึกผิดแผน)
     - `GET /api/courses/{code}/prerequisites`: กราฟวิชาบังคับก่อน (Prerequisite Graph: `requires` และ `required_by`)
     - `GET /api/study-plans`: รายการแผนการศึกษา (รองรับตัวกรอง `program_id` และ `plan_id`)
     - `GET /api/elective-slots`: รายการสล็อตวิชาเลือกในแต่ละชั้นปี/ภาคเรียน
     - `GET /api/plan`: รายวิชาตามแผนการศึกษาจาก Analytical View `v_plan`
     - `GET /api/plan/summary`: สรุปหน่วยกิตและจำนวนวิชารายเทอมจาก View `v_semester_credits`
     - `GET /api/stats`: สถิติสรุปจำนวนรายวิชา แผนการศึกษา สล็อตวิชาเลือก และข้อบังคับ (รองรับตัวกรอง `program_id`)
     - `GET /api/regulations`: ค้นหากฎระเบียบและข้อบังคับสถาบัน สจล. (หมวดหมู่, เงื่อนไข, บทลงโทษ)
     - `POST /api/ask`: สังเคราะห์คำตอบอัจฉริยะ (Text-to-SQL + Grounded Synthesis + Evidence Citations)
   - รายละเอียด Schema, พารามิเตอร์ และตัวอย่าง Payload ฉบับสมบูรณ์ถูกบันทึกไว้ใน [`lab10_fastapi/curriculum_app/README.md`](lab10_fastapi/curriculum_app/README.md)
2. **Modern Glassmorphic Frontend**:
   - พัฒนาด้วย Native ES6+ JavaScript และ Modern CSS (ไม่มี Dependency ภายนอกขนาดใหญ่)
   - บริหารจัดการหน้าจอด้วย **3-State Finite State Machine**: `IDLE` $\rightarrow$ `LOADING` $\rightarrow$ `SUCCESS` / `EMPTY` / `ERROR`
   - แสดงผลคำตอบด้วย `marked.js` พร้อมกล่อง Accordion แสดงคำสั่ง SQL จริง และป้ายกำกับเลขหน้าอ้างอิง (Citations)

```mermaid
sequenceDiagram
    autonumber
    actor User as ผู้ใช้งาน (Browser)
    participant UI as Glassmorphic UI (Vanilla JS)
    participant API as FastAPI Backend (/api/ask)
    participant LLM as Qwen3:4b (Ollama)
    participant DB as SQLite (curriculum.db)

    User->>UI: พิมพ์คำถาม: "หลักสูตร DSBA มีกี่หน่วยกิต"
    UI->>UI: เปลี่ยนสถานะเป็น LOADING (แสดง Skeleton Spinner)
    UI->>API: POST /api/ask { question }
    API->>LLM: Schema-Grounded Prompting
    LLM-->>API: คืนค่า SQL: SELECT total_credits FROM program...
    API->>DB: รันคำสั่ง SQL ผ่าน guard_sql()
    DB-->>API: คืนแถวข้อมูล: [{ total_credits: 132 }]
    API->>LLM: สังเคราะห์คำตอบภาษาไทยจาก Rows
    LLM-->>API: "หลักสูตร DSBA มีทั้งหมด 132 หน่วยกิต"
    API-->>UI: JSON { answer, sql, rows, sources }
    UI->>UI: เปลี่ยนสถานะเป็น SUCCESS
    UI->>User: แสดงคำตอบภาษาไทย + กล่อง SQL Accordion + เลขหน้าอ้างอิง
```

#### 5.2 ระยะเวลาและประสิทธิภาพ (Performance & Latency)
- **Static Asset & UI Rendering**: พัฒนาด้วย Native Vanilla JS และ Clean CSS ไม่มี External Framework Bundle ขนาดใหญ่ ทำให้โหลดและแสดงผลหน้าเว็บได้ทันที
- **Database Search Queries (`/api/courses`, `/api/regulations`)**: ดึงข้อมูลตรงจาก SQLite ผ่าน Indexed Query และ Limit/Offset Pagination ตอบสนองในระดับ Sub-second
- **Natural Language Question (`/api/ask`) End-to-End**: มีผลประเมินจริงจากชุดทดสอบ 189 คำถาม (`lab9/reports/live_eval_result.json`) ใช้เวลาเฉลี่ย **1.85 วินาที/ข้อ** (ต่ำสุด 0.77s, มัธยฐาน 1.81s, สูงสุด 10.19s, รวม 350.03s) โดยเวลาส่วนใหญ่ขึ้นอยู่กับการประมวลผลของโมเดลภาษา Local LLM (Ollama)

---

## 3. การวิเคราะห์เชิงลึก (In-Depth Technical Analysis)

---

### 3.1 การวิเคราะห์ความเหมาะสมต่อลักษณะเอกสาร (Document Type Suitability)

| ลักษณะเอกสาร | ความสามารถในการจัดการ | การวิเคราะห์และสาเหตุ | แนวทางการจัดการของระบบ |
| :--- | :---: | :--- | :--- |
| **ตารางแผนการศึกษาโครงสร้างมาตรฐาน**<br>*(Grid Table ในเล่ม มคอ.2 เช่น BIT, IT)* | **ดีเลิศ**<br>(F1: BIT 97.6%, IT 95.3%) | ข้อความมีโครงสร้างชัดเจน คอลัมน์รหัสวิชา ชื่อวิชา หน่วยกิต และชั่วโมงบรรยาย/ปฏิบัติแยกบรรทัดเป็นระเบียบ | สกัดผ่าน `PyMuPDF` ดึง Text Layer ตรงและควบคุม Output Schema ด้วย Prompt Constraint ใน `qwen3:4b` |
| **ตารางที่มีข้อความยาวตัดหลายบรรทัด**<br>*(Multi-line Merged Cells เช่น DSBA, AIT)* | **ดีมาก**<br>(F1: DSBA 92.5%, AIT 79.6%) | ชื่อวิชายาวใน PDF มักถูกตัดขึ้นบรรทัดใหม่ หรือมีการแบ่งหน้า ทำให้ Parser ทั่วไปอาจแยกแถวคลาดเคลื่อน | ใช้ฟังก์ชัน `clean_and_normalize_course()` ยุบอักขระ `\n` เป็นช่องว่าง และเชื่อมชื่อวิชาให้สมบูรณ์ตาม Schema |
| **เอกสารข้อบังคับสแกนขาวดำ/ไม่มี Text Layer**<br>*(ภาคผนวก ก หน้า 94, 96–101)* | **ดีมาก**<br>(Citation Coverage 100.0%) | เอกสารสแกนภาษาไทยมีความท้าทายจากสระลอยและวรรณยุกต์ซ้อน จึงเลือกใช้ Visual Language Model โดยตรง | ใช้ **Typhoon-OCR 1.5 3B (VLM)** อ่านภาพเป็น Markdown แล้วส่งต่อ `qwen3:4b` สกัดโครงสร้างข้อบังคับ (11/11 ข้อ) |
| **ตารางวิชาเลือกแบบหลายทางเลือก**<br>*(Elective Slots)* | **ดีเลิศ**<br>(ผ่าน CHK1 100.0%) | หากเก็บเป็นวิชาเดี่ยวจะทำให้หน่วยกิตรวมเบิ้ลเกินจริง (Double Counting) | แยกเก็บในตาราง `elective_slot` และสร้าง View `v_semester_credits` เพื่อคำนวณหน่วยกิตแผนการเรียนแยกต่างหาก |

---

### 3.2 การวิเคราะห์ระดับความซับซ้อนของคำถาม (Query Complexity Levels)

ระบบถูกทดสอบกับคำถามภาษาธรรมชาติหลากหลายระดับความซับซ้อน:

```mermaid
graph LR
    L1["Level 1: Simple Fact Lookup"] --> L2["Level 2: Aggregation & Filter"]
    L2 --> L3["Level 3: Multi-Join & Prereq"]
    L3 --> L4["Level 4: Regulations & Policies"]
    L4 --> L5["Level 5: Ambiguous Queries"]
```

#### ระดับที่ 1: การค้นหาข้อเท็จจริงเดี่ยว (Simple Fact Lookup)
- **ตัวอย่างคำถาม**: *"วิชา 06026200 มีกี่หน่วยกิต"*, *"หลักสูตร DSBA ใช้เวลาเรียนกี่ปี"*
- **SQL ที่สร้าง**: `SELECT credits FROM course WHERE code = '06026200' LIMIT 1`
- **ประสิทธิภาพ**: ไวยากรณ์เรียบง่าย ไม่มีความซับซ้อน สกัดค่าจากคอลัมน์และตารางเดี่ยวได้ตรงเป้าหมาย

#### ระดับที่ 2: การคำนวณรวมและกรองเงื่อนไข (Aggregation & Filter)
- **ตัวอย่างคำถาม**: *"ปี 1 เทอม 1 หลักสูตร IT แผนสหกิจศึกษา เรียนกี่วิชา"*
- **SQL ที่สร้าง**: `SELECT COUNT(*) FROM v_plan p JOIN study_plan sp ON p.plan_id = sp.plan_id WHERE p.program_id = 'IT' AND sp.plan_type = 'coop' AND p.year = 1 AND p.semester = 1 AND p.is_elective_slot = 0`
- **ประสิทธิภาพ**: กรองแผนด้วย `sp.plan_type = 'coop'` แทนการใช้ substring `LIKE '%COOP%'` (เพื่อป้องกันการ match โดน `IT_NON_COOP`) และกรอง `is_elective_slot = 0` เพื่อไม่นับสล็อตวิชาเลือก

#### ระดับที่ 3: ความสัมพันธ์ข้ามตารางและวิชาบังคับก่อน (Multi-Table JOIN & Prerequisites)
- **ตัวอย่างคำถาม**: *"วิชาบังคับก่อนของวิชา Data Engineering คือวิชาอะไร"*
- **SQL ที่สร้าง**: `SELECT requires FROM prerequisite WHERE code = (SELECT code FROM course WHERE name_en LIKE '%Data Engineering%') AND kind = 'pre'`
- **ประสิทธิภาพ**: ผลกลุ่มนี้ **88.24% (15/17 ข้อ)**; รองรับ Subquery และคอลัมน์ `requires` ตาม Schema จริง แต่ยังมีกรณีชื่อหรือเงื่อนไขที่คืนค่าไม่ตรงเฉลย

#### ระดับที่ 4: การค้นหาเกณฑ์และข้อบังคับสถาบัน (Institutional Regulations & Policies)
- **ตัวอย่างคำถาม**: *"ทุจริตในการสอบจะถูกลงโทษอย่างไร"*, *"นักศึกษาที่ได้ GPA ต่ำกว่าเท่าไรถึงจะถูกภาคทัณฑ์"*
- **SQL ที่ถูกต้องตามข้อมูลจริง**: `SELECT penalty_action FROM regulation WHERE category = 'การทุจริตในการสอบ' AND topic = 'ทุจริตครั้งแรก' LIMIT 1`
- **ประสิทธิภาพ**: **60.00% (6/10 ข้อ)** โดย SQL รันผ่าน 10/10 ข้อ แต่ผิด 4 ข้อจากชื่อ `category`/`topic` ที่โมเดลสร้างไม่ตรงค่าจริง เช่น `เกณฑ์การทุจริตในการสอบ` แทน `การทุจริตในการสอบ`

#### ระดับที่ 5: คำถามที่มีความกำกวมหรือไม่ได้ระบุหลักสูตร (Ambiguous / Cross-Curriculum Queries)
- **ตัวอย่างคำถาม**: *"หลักสูตรนี้มีกี่หน่วยกิต"* (โดยไม่บอกชื่อสาขาวิชาในฐานข้อมูลรวม 4 สาขา)
- **พฤติกรรมในโค้ดจริง**: หากผู้ใช้ไม่ได้ระบุชื่อหลักสูตร โค้ดใน [`model_service.py`](lab10_fastapi/curriculum_app/model_service.py) บรรทัด 62 กำหนด System Prompt Rule ไว้อย่างชัดเจนให้ใช้ค่าเริ่มต้น (Default) เป็นหลักสูตร **DSBA** ทันที (`WHERE v.program_id = 'DSBA'`) ระบบจึงไม่ได้สร้าง Dialog ถามกลับ (No Clarification Loop) แต่ตอบโดยสมมติเป็น DSBA ทันที
- **ข้อพิจารณาทางวิศวกรรม**: การ Fallback ไปที่ DSBA ช่วยให้ระบบไม่เกิดข้อผิดพลาดและมีคำตอบให้ผู้ใช้ทันที แต่อาจตอบผิดบริบทหากผู้ใช้มีเจตนาถามถึงสาขาอื่น ในการพัฒนาต่อยอดจึงควรเพิ่ม Ambiguity Detection และส่งสถานะ `needs_clarification` กลับไปยัง Frontend

#### สรุป Accuracy แยกตามระดับจากรอบล่าสุด

| Level | จำนวนคำถาม | Valid SQL | Execution Accuracy |
| :--- | ---: | ---: | ---: |
| 1 — Simple Lookup | 144 | 100.0% (144/144) | 97.92% (141/144) |
| 2 — Filter & Aggregate | 12 | 100.0% (12/12) | 83.33% (10/12) |
| 3 — Multi-table Relation | 17 | 100.0% (17/17) | 88.24% (15/17) |
| 4 — Regulation Query | 10 | 100.0% (10/10) | 60.00% (6/10) |
| 5 — Ambiguous Query | 6 | 100.0% (6/6) | 100.0% (6/6) |

---

## 4. ตารางสรุปครบทุกมิติ (Master Technical Specification Table)

| ขั้นตอน (Step) | กระบวนการหลัก (Process) | โมเดล / เครื่องมือ (Model & Tools) | อัลกอริทึมหลัก (Algorithm) | พารามิเตอร์สำคัญ (Parameters) | ระยะเวลาในการรัน (Runtime) | ตัวชี้วัดสำคัญ (Evaluation Metrics) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Extraction (Lab 7B)** | สกัดรายวิชาและข้อบังคับจาก PDF | - `Typhoon-OCR 1.5 3B`<br>- `Qwen3:4b`<br>- `PyMuPDF`<br>- `pdfplumber` | - Multi-pass Alignment<br>- Dual-path Extraction<br>- Thai Word Tokenization | - DPI = 150<br>- Chunk = 1 หน้า<br>- Temp = 0.0 (OCR/Text)<br>- Temp = 0.1 (Reg/GenEd Stage 2)<br>- Repeat Penalty = 1.2 (Reg) / 1.1 (GenEd)<br>- Num Ctx = 8192 | - ตารางวิชา End-to-End: 106.4–410.0s/เล่ม<br>(AIT 106.4s, BIT 268.7s, DSBA 283.9s, IT 410.0s)<br>- ข้อบังคับ VLM: ~38s (6 หน้า)<br>- ประเมินผลใน RAM: **0.12s** | - **Macro Precision**: 94.0%<br>- **Macro Recall**: 89.7% (AIT Recall: 68.4%)<br>- **Macro F1-Score**: **91.3%** |
| **2. Schema & DB (Lab 8B)** | ตรวจสอบโครงสร้างและความสอดคล้อง | - `SQLite 3`<br>- `Pydantic v2` | - Option 2 Separation<br>- Composite FK Integrity<br>- Prerequisite Audit Engine<br>- 7 Assertion Rules (CHK1–7) | - PRAGMA foreign_keys=ON<br>- (Standard Journal Mode, No WAL)<br>- Unique Constraints | - สร้างและโหลด DB: Sub-second<br>- ตรวจ 7 กฎ: Sub-second | - **Schema Pass Rate**: 100.0%<br>- **Consistency Pass**: 100.0% (7/7 ข้อ) |
| **3. NL to SQL (Lab 8B/9)** | แปลงภาษาธรรมชาติเป็นคำสั่ง SQL | - `Qwen3:4b` (Ollama)<br>- SQLite Engine | - Schema-Grounded Prompting<br>- Self-Correction Loop<br>- Security Guardrail<br>- Abstain on Empty | - Temp = 0.0 (Greedy)<br>- Num Ctx = 4096<br>- Num Predict = 256<br>- Max Attempts = 2 (range(2)) | - รันสด 189 ข้อ: **เฉลี่ย 1.85s/ข้อ** (ต่ำสุด 0.77s, มัธยฐาน 1.81s, สูงสุด 10.19s, รวม 350.03s)<br>- รัน Cached: **0.05s** | - **Valid SQL Rate**: 100.0% (189/189)<br>- **Execution Acc (SQL)**: **94.18%** (178/189) |
| **4. Groundedness (Lab 8B/9)** | ตรวจสอบความซื่อสัตย์และการอ้างอิง | - `Qwen3:4b`<br>- SQLite Metadata | - Grounded Synthesis<br>- Metadata Citation Matching<br>- Strict Grounded Guard | - Temp = 0.0 (ผ่าน `ollama_generate`)<br>- Num Predict = 256<br>- Direct Page Matching | - ตอบคำถามสดรวม: เฉลี่ย 1.85s/ข้อ<br>- ตรวจวัดทั้งชุด (Cached): **0.05s** | - **Faithfulness Proxy**: 94.18% (178/189)<br>- **Exact Match**: 93.89% (169/180)<br>- **Course Citation**: 99.8% (503/504)<br>- **Regulation Citation**: 100.0% (11/11) |
| **5. Web App (Lab 10)** | ให้บริการค้นหาและถามตอบผ่านเว็บ | - `FastAPI` (13 Endpoints)<br>- `Uvicorn`<br>- Vanilla JS / Glassmorphism | - 3-State Finite State Machine<br>- Dynamic Plan Resolution<br>- Default Program: DSBA | - Port = 8000<br>- Max Rows = 100<br>- Async Endpoint Handling | - สืบค้นตรงผ่าน DB: Sub-second<br>- ถามตอบ LLM (Live): **เฉลี่ย 1.85s** (ต่ำสุด 0.77s, สูงสุด 10.19s) | - **RESTful API**: ครบ 13 Endpoints ตาม Contract<br>- **UI Bundle**: Vanilla JS (Zero external overhead) |
| **6. Evaluation (Lab 9)** | รัน 4 ขั้นตอนหลักและวิเคราะห์ Query Complexity | - `run_all_eval.py`<br>- `step5_eval_query_complexity.py` | - Modular Pipeline Aggregation<br>- Gold Labels + Deterministic SQL Classification | - `--live`, `--cached`, `--limit`<br>- `--labels lab9/query_complexity_labels.json` | - แบบ Cached: **0.78s**<br>- แบบ Live (189 ข้อ): **~5.8m** (350.03s)<br>- Complexity Analysis: ใช้ผล Step 3 โดยไม่เรียก LLM ซ้ำ | - JSON Metrics ขั้นที่ 1–4<br>- CSV Summary/Detail สำหรับ Level 1–5; Detail มีคำตอบระบบและเฉลย |

---

## 5. สรุปภาพรวมและจุดเด่นของระบบ (Conclusion & Highlights)

1. **ลดความเสี่ยงจาก Hallucination**: ด้วยการใช้แนวทาง **Text-to-SQL บนฐานข้อมูลเชิงสัมพันธ์** ข้อมูลข้อเท็จจริง (หน่วยกิต, ชื่อวิชา, ข้อบังคับ) จึงถูกดึงมาจากฐานข้อมูลจริงผ่านคำสั่ง SQL โมเดลภาษาทำหน้าที่เพียงแปลงคำถามเป็นคำสั่งสืบค้นและเรียบเรียงภาษาไทยตามผลลัพธ์ที่ได้เท่านั้น
2. **โปร่งใสและตรวจสอบย้อนกลับได้ (Auditability & Trust)**: มีระบบ **Evidence Citation Coverage** อยู่ที่ **99.8% (503/504)** ในรายวิชา และ **100.0% (11/11)** ในข้อบังคับ ระบบแสดงป้ายเลขหน้าอ้างอิงจาก Metadata และเปิดดูคำสั่ง SQL ที่ใช้สืบค้นได้ทันที
3. **เสถียรภาพและความเร็วในการทำงาน**: การประเมินผลระบบผ่านแคชทำงานได้ในเวลาไม่ถึง **1 วินาที (0.78s)** และการสืบค้นข้อมูลทั่วไปผ่าน SQLite / REST API ตอบสนองได้อย่างรวดเร็วในระดับ Sub-second รองรับการใช้งานจริงได้อย่างมีประสิทธิภาพ
4. **ความสมบูรณ์เชิงสถาปัตยกรรม (Architectural Rigor)**: ระบบใช้ Composite Foreign Key `(plan_id, program_id)` และ Course Foreign Key `plan_item.code -> course.code` ในระดับ RDBMS ร่วมกับการตรวจสอบขอบเขตแผนการศึกษา (Plan-scoped assertion) ใน CHK5 และการตรวจสอบ Prerequisite Audit Engine ตามรหัสวิชาของ สจล. ป้องกันข้อผิดพลาดข้ามหลักสูตรอย่างเด็ดขาดและปลอดภัย
