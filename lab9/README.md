# Lab 9: Intelligent System Evaluation & Overfitting Framework
วิชา 06026240 การพัฒนาระบบอัจฉริยะ (Intelligent System Development)  
คณะเทคโนโลยีสารสนเทศ สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง (KMITL)  
**กลุ่ม: Luksuitpiti** (DSBA)

---

##  ที่มาและหลักการประเมินผล (Evaluation Framework)

โฟลเดอร์ `lab9/` นี้ถูกสร้างขึ้นเพื่อรวบรวมสคริปต์ประเมินผลจากทุกแล็บ (Lab 1–8B และ 10) เข้าเป็นชุดทดสอบอัตโนมัติ (Automated Evaluation Suite) โดยวัดประสิทธิภาพแยกตาม 4 ขั้นตอนของระบบ: **สกัด $\rightarrow$ ตรวจ Schema $\rightarrow$ ค้นคืน $\rightarrow$ ตอบ**

---

##  โครงสร้างไฟล์ใน `lab9/`

```text
lab9/
├── README.md                      # คู่มือและคำอธิบายระบบประเมินผล
├── run_all_eval.py                # Master Runner: รันรวดเดียวครบ 4 ขั้นตอน
│
├── step1_eval_extraction.py       # ขั้นที่ 1: การสกัด (Field-level P/R/F1)
├── step1_eval_all_curricula.py    # CER/WER/Exact Match แบบ pooled ครบทั้ง 7 แผน
├── step2_eval_schema.py           # ขั้นที่ 2: ตรวจสอบ Schema & ความสอดคล้อง 7 กฎ (CHK1–CHK7)
├── step3_eval_nl2sql.py           # ขั้นที่ 3: ค้นคืน NL to SQL (Valid SQL Rate, Execution Accuracy)
├── step4_eval_groundedness.py     # ขั้นที่ 4: ตอบ & อ้างอิง (Groundedness, Citation Coverage, EM)
├── step5_eval_query_complexity.py # ขั้นที่ 5: วิเคราะห์ Accuracy แยก Query Complexity Level
├── query_complexity_labels.json   # Gold Labels: Level 5 และ Regulation Level 4
│
└── reports/                       # ผลการประเมินที่ถูกสร้างขึ้นอัตโนมัติ
    ├── step1_extraction_metrics.json
    ├── step2_schema_verification.json
    ├── step3_nl2sql_benchmark.json
    ├── step4_groundedness_metrics.json
    ├── query_complexity_summary.csv
    ├── query_complexity_detail.csv
    └── all_curricula/
        └── comparison.csv          # คะแนน metric รวมแยกตามฟิลด์ ไม่แสดงรายวิชา
```

---

##  วิธีการรันประเมินผล (Quick Start)

### 1. รันประเมินผลรวดเดียวทั้งระบบ (แนะนำ):
```bash
python lab9/run_all_eval.py --live
```
*(ระบบจะประเมินทั้ง 4 ขั้นตอน และแสดงผลสรุปบนหน้าจอทันที ถ้าไม่ใส่ `--live` ขั้นที่ 3 จะใช้ผลที่บันทึกไว้ใน `work/lab8b_run/eval_result.json` แทนการถามโมเดลสด การรันสด 189 ข้อใช้เวลาประมาณ 5–6 นาที และต้องเปิด Ollama ไว้)*

### 2. รันประเมินผลแยกรายขั้นตอน:
```bash
# ขั้นที่ 1: วัดความแม่นยำของการสกัดและ OCR (Lab 7B)
python lab9/step1_eval_extraction.py

# คะแนน CER/WER/Exact Match แบบ pooled จากทั้ง 7 แผน
python lab9/step1_eval_all_curricula.py

# ขั้นที่ 2: ตรวจความถูกต้องของ Schema และความสอดคล้อง 7 กฎ (Lab 8B)
python lab9/step2_eval_schema.py

# ขั้นที่ 3: วัดความแม่นยำ Text-to-SQL (รันสดผ่าน Ollama แบบ Real-time เป็นค่าเริ่มต้น)
python lab9/step3_eval_nl2sql.py             # รันสดครบทุกข้อ
python lab9/step3_eval_nl2sql.py --limit 10  # รันสดตัวอย่าง 10 ข้อ
python lab9/step3_eval_nl2sql.py --cached    # ใช้ผลลัพธ์ที่เคยบันทึกไว้

# ขั้นที่ 4: ตรวจสอบความซื่อสัตย์ต่อฐานข้อมูลและการอ้างอิงเลขหน้าจริง (Groundedness & Citation)
python lab9/step4_eval_groundedness.py            # ประเมินผลสดอัตโนมัติ (ดึงผลสดจาก Step 3 ทันที)
python lab9/step4_eval_groundedness.py --live     # รันถามและประเมินคำตอบภาษาไทยสดผ่าน Ollama
python lab9/step4_eval_groundedness.py --cached   # ใช้ผลลัพธ์ baseline เดิม

# ขั้นที่ 5: วิเคราะห์ Valid SQL และ Execution Accuracy แยกตาม Query Complexity Level
# ต้องรัน Step 3 ก่อน เพื่อให้ work/lab8b_run/eval_result.json เป็นผลล่าสุด
python lab9/step5_eval_query_complexity.py --labels lab9/query_complexity_labels.json
```

ผลของขั้นที่ 5:

- `lab9/reports/query_complexity_summary.csv` — สรุปจำนวนข้อ, Valid SQL และ Execution Accuracy ของ Level 1–5
- `lab9/reports/query_complexity_detail.csv` — รายละเอียดทุกคำถาม พร้อมคำถาม, คำตอบที่ระบบให้ (`llm_answer`), เฉลย (`expected_answer`/`expected_answer_type`), Level, SQL และผลถูก/ผิด
- `lab9/query_complexity_labels.json` — Gold Label ที่กำหนดล่วงหน้า โดยข้อ 180–189 เป็น Regulation Query (Level 4) และคำถามกำกวมที่กำหนดไว้เป็น Level 5

---

## 📊 สรุปผลการประเมิน (Evaluation Metrics Summary)

### ผล Step 1: Extraction Evaluation

| หลักสูตร | Ground Truth | สกัดได้ | จับคู่ถูก | FN | FP | Precision | Recall | F1-Score |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DSBA | 90 | 96 | 86 | 4 | 10 | 89.6% | 95.6% | 92.5% |
| IT | 106 | 108 | 102 | 4 | 6 | 94.4% | 96.2% | 95.3% |
| BIT | 63 | 64 | 62 | 1 | 2 | 96.9% | 98.4% | 97.6% |
| AIT | 57 | 41 | 39 | 18 | 2 | 95.1% | 68.4% | 79.6% |
| **รวมจำนวน / เฉลี่ย Macro** | **316** | **309** | **289** | **27** | **20** | **94.0%** | **89.7%** | **91.3%** |

### คะแนน Extraction แบบรวม 7 แผน (Pooled Metrics)

คำสั่ง `python lab9/step1_eval_all_curricula.py` ประเมิน prediction ทั้ง 7 แผน (DSBA/IT/BIT ทั้ง coop และ no-coop รวม AIT) แล้วรวมตัวนับดิบก่อนคำนวณ metric รายฟิลด์ ผลอยู่ที่ `lab9/reports/all_curricula/comparison.csv` จำนวนรายการเป็นผลรวมของแถวข้ามแผน ไม่ใช่จำนวนวิชาไม่ซ้ำกัน

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

WER แสดงเฉพาะฟิลด์ชื่อที่ประเมินเป็นข้อความ ส่วนวิชาบังคับก่อนและภาคเรียนยืดหยุ่นคิดจากรายการที่จับคู่ได้ตาม evaluator เดิม

| ขั้นตอนของระบบ | Metric ที่ใช้วัด | ความหมายในบริบทของระบบหลักสูตร | ผลลัพธ์ที่ได้ |
| :--- | :--- | :--- | :---: |
| **1. การสกัด (Extraction)** | **Macro Recall** | ค่าเฉลี่ย Recall ของทั้ง 4 หลักสูตร | **89.7%** *(AIT: 68.4%)* |
| | **Macro Precision** | ค่าเฉลี่ย Precision ของทั้ง 4 หลักสูตร | **94.0%** |
| | **Macro F1-Score** | ค่าเฉลี่ย F1-Score ของทั้ง 4 หลักสูตร | **91.3%** |
| **2. ตรวจสอบ Schema** | **Schema Pass Rate** | ข้อมูลผ่าน Pydantic และตาราง Option 2: Full Separation | **100.0%** |
| | **Consistency Pass Rate** | ผ่านกฎความสอดคล้อง **7 จาก 7 ข้อ (CHK1–CHK7)** | **100.0% (7/7 ข้อ)** |
| **3. ค้นคืน (NL to SQL)** | **Valid SQL Rate** | สัดส่วนคำสั่ง SQL ที่สร้างขึ้นแล้วรันผ่านได้ | **100.0%** (189/189 คำถาม) |
| | **Execution Accuracy (SQL)** | รัน SQL แล้วได้ผลลัพธ์ตรงกับ Ground Truth | **96.30%** (182/189 คำถาม) |
| **4. ตอบ & อ้างอิง** | **Faithfulness / Groundedness Proxy** | ใช้ผล `correct` ที่ตรวจจาก SQL rows ใน `step4_groundedness_metrics.json` | **96.30%** (182/189 ข้อ) |
| | **Exact Match (EM)** | คำตอบตรงเฉลยสำหรับชนิด `value` และ `count` | **96.11%** (173/180 ข้อ) |
| | **Course Citation Coverage** | สัดส่วนวิชาที่มีเลขหน้าจริงจากเล่ม มคอ.2 กำกับอยู่ในระบบ | **99.8%** (503/504 รายวิชา) |
| | **Regulation Citation Cov** | สัดส่วนข้อบังคับที่มีเลขหน้าสแกนจริงจากภาคผนวก ก | **100.0%** (11/11 ข้อบังคับ) |

> 📌 **หมายเหตุการรันสดล่าสุด**:
> `lab9/reports/live_eval_result.json` มีผล 189 ข้อจากการรัน `python lab9/run_all_eval.py --live` โดยฟิลด์ `correct` มาจาก `score_one()` ที่ตรวจ SQL rows จึงรายงานเป็น **Live Retrieval Correctness 96.30% (182/189)** ไม่ใช่ Human-rated Final-Answer Correctness ส่วน Latency เฉลี่ย **1.64 วินาที/ข้อ** (มัธยฐาน 1.58 วินาที, ต่ำสุด 0.74 วินาที, สูงสุด 3.75 วินาที, รวม 310.61 วินาที) Step 3 และ Step 4 มาจากการรันรอบเดียวกัน
>
> ข้อผิด 7 ข้อ: ทั้งหมดเป็นปัญหาที่ข้อมูลหรือเฉลย (เช่น วิชา `06016401` ไม่อยู่ในแผน AIT, ไม่มีข้อมูลวิชาบังคับก่อนของ `06046414` และ `06046442`) ไม่มีข้อที่โมเดลสร้าง SQL ผิด รายละเอียดดู `sysdoc.md` หัวข้อ 3.5
>
> ผลแยกตามหลักสูตร (Isolated DB) ใน `step3_nl2sql_benchmark.json` อ่านมาจาก `work/lab8b_run/{BIT,IT,DSBA,AIT}/eval_result.json` ซึ่งรันใหม่ด้วย Prompt ปัจจุบันเมื่อ 16 ต.ค. 2569 (ชุดละ 45 ข้อ): BIT 100.0% (45/45), IT 100.0% (45/45), DSBA 91.1% (41/45), AIT 88.9% (40/45), รวม 95.0% (171/180) และ Valid SQL 100% ทุกฐาน (`run_all_eval.py --live` ไม่ได้รันชุดนี้ใหม่ ต้องรัน `lab8b_curriculum_db.py eval` แยกรายหลักสูตร)

### ผลแยกตาม Query Complexity

| Level | จำนวนคำถาม | Valid SQL | Execution Accuracy |
| :--- | ---: | ---: | ---: |
| 1 — Simple Lookup | 144 | 100.0% (144/144) | 97.92% (141/144) |
| 2 — Filter & Aggregate | 12 | 100.0% (12/12) | 83.33% (10/12) |
| 3 — Multi-table Relation | 17 | 100.0% (17/17) | 88.24% (15/17) |
| 4 — Regulation Query | 10 | 100.0% (10/10) | 100.0% (10/10) |
| 5 — Ambiguous Query | 6 | 100.0% (6/6) | 100.0% (6/6) |

> การจัดระดับใช้ป้ายใน `lab9/query_complexity_labels.json` ร่วมกับลักษณะของ SQL ที่โมเดลสร้าง (เช่น มี `JOIN` หรือใช้ค่าเริ่มต้น DSBA) จำนวนข้อในแต่ละระดับจึงเปลี่ยนได้เมื่อ Prompt เปลี่ยน ควรเทียบข้ามเวอร์ชันเฉพาะตัวเลขรวม

### คำอธิบาย Query Complexity Levels

#### Level 1 — Simple Lookup

คำถามค้นหาค่าจากตารางเดียว โดยระบุรหัสวิชา ชื่อวิชา หรือหลักสูตรไว้อย่างชัดเจน รูปแบบ SQL หลักคือ `SELECT` และ `WHERE`

- ตัวอย่าง: “วิชา 06026200 มีกี่หน่วยกิต”
- ตัวอย่าง: “หลักสูตร IT ใช้เวลาเรียนกี่ปี”

#### Level 2 — Filter & Aggregate

คำถามที่ต้องกรองหลายเงื่อนไข เช่น หลักสูตร แผนการเรียน ชั้นปี และภาคการศึกษา แล้วคำนวณด้วย `COUNT` หรือ `SUM`

- ตัวอย่าง: “หลักสูตร IT ปี 1 เทอม 1 เรียนกี่วิชา”
- ตัวอย่าง: “DSBA ปี 2 เทอม 1 เรียนกี่หน่วยกิต”

#### Level 3 — Multi-table Relation

คำถามที่ต้องเชื่อมความสัมพันธ์ระหว่างหลายตาราง หรือใช้ `JOIN` และ Subquery เช่น การค้นวิชาบังคับก่อนจากตาราง `prerequisite`

- ตัวอย่าง: “วิชาบังคับก่อนของ Data Engineering คืออะไร”
- ตัวอย่าง: “วิชาใดบ้างที่ต้องเรียน 06066300 มาก่อน”

#### Level 4 — Regulation Query

คำถามเกี่ยวกับข้อบังคับ เช่น การลงทะเบียน การภาคทัณฑ์ การทุจริตในการสอบ และเกียรตินิยม โดยต้องจับคู่ความหมายของคำถามกับ `category`, `topic` และฟิลด์คำตอบในตาราง `regulation`

- ตัวอย่าง: “ภาคการศึกษาปกติลงทะเบียนได้สูงสุดกี่หน่วยกิต”
- ตัวอย่าง: “ทุจริตในการสอบครั้งแรกได้รับโทษอะไร”
- ตัวอย่าง: “เกียรตินิยมอันดับ 1 ต้องมี GPA อย่างน้อยเท่าไร”

#### Level 5 — Ambiguous Query

คำถามที่ให้บริบทไม่ครบ เช่น ไม่ระบุหลักสูตรหรือแผนการเรียน ระบบปัจจุบันใช้ `program_id = 'DSBA'` เป็นค่าเริ่มต้นแทนการถามผู้ใช้กลับ

- ตัวอย่าง: “หลักสูตรนี้มีกี่หน่วยกิต”
- ตัวอย่าง: “ปี 1 เทอม 1 เรียนกี่วิชา”
