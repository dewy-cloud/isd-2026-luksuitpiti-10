<div align="center">
 
![header](https://capsule-render.vercel.app/api?type=transparent&color=0:4B5FBF,100:8B5FA8&height=180&section=header&text=ISD%20Luksuitpiti&fontSize=42&fontColor=cccccc&fontAlignY=35&desc=OCR%20Evaluation%20Pipeline%20For%20School%20of%20Information%20Technology&descAlignY=55&descSize=16)  
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tesseract](https://img.shields.io/badge/Tesseract%20OCR-4B5FBF?style=for-the-badge&logo=google&logoColor=white)

![Semester](https://img.shields.io/badge/Semester-1%2F2569-9b59b6)
![Programs](https://img.shields.io/badge/Programs-AIT%20%7C%20IT%20%7C%20DSBA%20%7C%20BIT-2196f3)
![Language](https://img.shields.io/badge/Language-Python-2196f3)
![Status](https://img.shields.io/badge/Status-Active-4caf50)
 
</div>
# isd-2026-luksuitpiti: Curriculum Assistant & Intelligent OCR System
วิชา 06026240 การพัฒนาระบบอัจฉริยะ (Intelligent System Development)  
คณะเทคโนโลยีสารสนเทศ สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง (KMITL)

## สมาชิกกลุ่ม (Group Members - Luksuitpiti)
| ลำดับ | รหัสนักศึกษา | ชื่อ - นามสกุล | GitHub Username | สาขาวิชา |
|:---:|:---:|:---|:---|:---:|
| 1 | 67070098 | นายปวริศ ปัญสิงห์ | _drews. | DSBA |
| 2 | 67070141 | นายภูวิศ ทรายทอง | babysalmonnn | DSBA |
| 3 | 67070190 | นายสุวิจักขณ์ กุลฉัตรานนท์ | sv_jatm | DSBA |
| 4 | 67070307 | นายปิติ หยาง | pingsensei | DSBA |

---

## README อื่นในโปรเจกต์

ตารางนี้รวม README ที่อยู่ในโฟลเดอร์ย่อย กดชื่อลิงก์เพื่อเปิดอ่านเนื้อหาได้ทันที

| README | ใช้อธิบายอะไร |
| :--- | :--- |
| [lab1-6.md](lab1-6.md) | คู่มือ Lab 1–6: ตั้งค่า VS Code/Python, ติดตั้ง Tesseract, ใช้ OCR engines, สกัดรายวิชา และประเมินผล CER/WER |
| [lab7_final/README.md](lab7_final/README.md) | ภาพรวม Lab 7B: การสกัดข้อมูลหลักสูตรจาก PDF, วิธีทำงานของ pipeline และผล benchmark ของการสกัด |
| [lab9/README.md](lab9/README.md) | คู่มือชุดประเมินผล Lab 9: วิธีรันแต่ละ Step, artifacts ที่ได้ และผล metrics |
| [lab10_fastapi/README.md](lab10_fastapi/README.md) | ภาพรวม Lab 10 และแอป Curriculum/Transcript รวมถึงวิธีเริ่มใช้งาน |
| [lab10_fastapi/curriculum_app/README.md](lab10_fastapi/curriculum_app/README.md) | วิธีวางโฟลเดอร์และเรียกใช้ Curriculum Application ซึ่งตอบคำถามผ่าน Text-to-SQL และ SQLite |

---

## Project Structure

โครงสร้างหลักของ repository และหน้าที่ของแต่ละส่วน:

```text
isd-2026-luksuitpiti/
├── data/                         # ไฟล์ input, ground truth และข้อมูลประกอบ
├── lab6/                         # สคริปต์และผลประเมิน Lab 6
├── lab7_final/                   # OCR/extraction pipeline และ metrics ของ Lab 7B
├── lab9/                         # สคริปต์ประเมิน extraction, NL2SQL และ groundedness
│   └── reports/                  # ผล evaluation และรายงาน CSV/JSON
├── lab10_fastapi/                # FastAPI application และ frontend
│   └── curriculum_app/
├── src/ocr_system/               # CLI, OCR engines, extraction และ SQLite pipeline
│   ├── engines/                  # PaddleOCR, Tesseract, TrOCR และ Ensemble
│   └── lab8b_curriculum_db.py    # แปลง/โหลดข้อมูลหลักสูตรและคำสั่งฐานข้อมูล
├── outputs/                      # ผลลัพธ์ OCR และ artifacts จากการรัน
├── work/                         # ข้อมูลและผลการทดลองระหว่างพัฒนา
├── lab1-6.md                     # คู่มือเตรียมระบบและใช้งาน OCR Labs 1–6
├── run_lab8b.py                  # สคริปต์ช่วยรัน pipeline Lab 8B
├── requirements.txt              # Python dependencies
├── pyproject.toml                # การตั้งค่าแพ็กเกจ Python
├── sysdoc.md                     # เอกสารออกแบบและรายละเอียดระบบ
└── README.md                     # คู่มือหลักและ Quick Start
```

---

## คู่มือการรัน Application สำหรับอาจารย์และผู้ตรวจประเมิน (Quick Start Guide)

โปรเจกต์นี้พัฒนาระบบสกัดข้อมูลเล่มหลักสูตร มคอ.2 (ครอบคลุมทั้ง 4 สาขาวิชา: DSBA, BIT, IT, AIT) เข้าสู่ฐานข้อมูลเชิงสัมพันธ์ SQLite และให้บริการเว็บแอปพลิเคชันถามตอบด้วย Text-to-SQL (NL2SQL) ร่วมกับ Local LLM (Ollama)

### 1. ความต้องการของระบบ (Prerequisites)
- **Python**: เวอร์ชัน 3.10 ขึ้นไป
- **Ollama**: ติดตั้งและเปิด Background Service:
  ```bash
  ollama serve
  ```
  จากนั้นดาวน์โหลดโมเดล LLM สำหรับ Text-to-SQL:
  ```bash
  ollama pull qwen3:4b
  ```
  > 💡 **นโยบายการควบคุมความสุ่ม (Temperature Policy)**:
  > - **`0.0` (Greedy Decoding)**: ใช้ในงาน **OCR**, **Text Pipeline Structuring**, **NL2SQL** และ **Answer Synthesis** (ตามฟังก์ชัน `ollama_generate` ในโค้ดจริงที่ล็อกไว้ที่ 0.0) เพื่อ**ลดความแปรปรวนและเพิ่มความทำซ้ำได้ (Reproducibility)** ช่วยลดโอกาสที่โมเดลจะแต่งข้อมูลนอกเหนือตาราง และให้คำสั่ง SQL และคำตอบมีความคงเส้นคงวาสูงสุด
  > - **`0.1` (Low Stochasticity)**: ใช้เฉพาะใน **Regulation Structuring** และ **GenEd Stage 2** เพื่อช่วยลดการวนลูปของข้อความภาษาไทยที่มีบทยาวร้อยแก้ว

---

### 2. ขั้นตอนการติดตั้ง Dependencies
เปิด Terminal ในโฟลเดอร์โปรเจกต์ และติดตั้งไลบรารีที่จำเป็น:
```bash
pip install -r requirements.txt
```

---

### 3. การเตรียมฐานข้อมูลหลักสูตร (Database Setup)
> **หมายเหตุ**: โปรเจกต์มีฐานข้อมูล SQLite สำเร็จรูปที่ผ่านการสกัดครบทั้ง 504 รายวิชา (268 รายการในแผนการศึกษา, 71 elective slots, 11 regulations, 30 prerequisites) และผ่านการตรวจสอบความสอดคล้อง (Consistency Verification) ครบ 7 กฎ 100% บันทึกไว้ที่ `work/lab8b_run/curriculum.db` (รวมทั้งฐานข้อมูลเดี่ยว 4 สาขาที่ `work/lab8b_run/{DSBA,BIT,IT,AIT}/curriculum.db`) เรียบร้อยแล้ว **สามารถข้ามไปขั้นตอนที่ 4 เพื่อเปิดรันเว็บแอปพลิเคชันได้ทันที**

หากต้องการสั่งรันกระบวนการสกัดใหม่จากเล่มหลักสูตร PDF ต้นฉบับ (Cold-Start Reproduction):

#### ก. สกัดข้อมูลรายวิชาด้วย Lab 7B (แผนการศึกษา + วิชาเลือกเฉพาะ ครบ 4 หลักสูตร):
```bash
python src/ocr_system/lab7b_curriculum.py -i data/input/fulldoc_dsba.pdf --pages 19-25,33-39 -g data/ground_truth/DSBA/DSBA_academic_plan_coop.json -p text -o lab7_final/output/DSBA --program DSBA
python src/ocr_system/lab7b_curriculum.py -i data/input/fulldoc_BIT.pdf --pages 24-25,31-35 -g data/ground_truth/BIT/BIT_academic_plan_coop.json -p text -o lab7_final/output/BIT --program BIT
python src/ocr_system/lab7b_curriculum.py -i data/input/fulldoc_it.pdf --pages 26-30,39-45 -g data/ground_truth/IT/IT_academic_plan_coop.json -p text -o lab7_final/output/IT --program IT
python src/ocr_system/lab7b_curriculum.py -i data/input/fulldoc_AIT.pdf --pages 21-26 -g data/ground_truth/AIT/AIT_academic_plan.json -p text -o lab7_final/output/AIT --program AIT
```

##### 📊 ตารางสรุปผลการสกัดและช่วงหน้าของแต่ละหลักสูตร (Extraction Benchmark & Page Coverage)

| หลักสูตร | ช่วงหน้าที่กำหนด (`--pages`) | เนื้อหาและโครงสร้างในช่วงหน้าดังกล่าว | เวลาสกัดจริง (End-to-End) / เวลา Eval | จำนวนวิชาที่สกัดได้ | มีเลขหน้าอ้างอิงจริง | ความแม่นยำ (F1-Score) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **DSBA** | `19-25, 33-39` | แผนการศึกษาปกติ / สหกิจศึกษา (ปี 1–4) และกลุ่มวิชาเลือกเฉพาะด้าน | 283.9 วินาที / 2.5s (Eval) | 96 วิชา (ตรงเฉลย 86/90) | 79 วิชา | **92.5%** (P=89.6%, R=95.6%) |
| **IT** | `26-30, 39-45` | แผนการศึกษาปกติ (ปี 1–4) และแผนการศึกษาสหกิจศึกษา (ปี 1–4) | 410.0 วินาที / 1.6s (Eval) | 108 วิชา (ตรงเฉลย 102/106) | 101 วิชา | **95.3%** (P=94.4%, R=96.2%) |
| **BIT** | `24-25, 31-35` | โครงสร้างกลุ่มวิชาเลือก และแผนการศึกษาสหกิจศึกษา (ปี 1–4) | 268.7 วินาที / 1.3s (Eval) | 64 วิชา (ตรงเฉลย 62/63) | 57 วิชา | **97.6%** (P=96.9%, R=98.4%) |
| **AIT** | `21-26` | กลุ่มวิชาเลือกเฉพาะ (หน้า 21–22) และแผนการศึกษา ปี 1–4 (หน้า 23–26) | 106.4 วินาที / 1.1s (Eval) | 41 วิชา (ตรงเฉลย 39/57) | 34 วิชา | **79.6%** (P=95.1%, R=68.4%) |
| **GenEd (หมวดศึกษาทั่วไป)** | `154-227` (74 หน้า) | หมวดวิชาศึกษาทั่วไป สจล. ฉบับปรับปรุง 2564 (ภาคผนวก ง) ใช้ร่วมกัน 4 หลักสูตร | 2,827 วินาที (~47 นาที) | **266 วิชา** | 266 วิชา | **100% Schema Valid** (รหัส 8 หลัก, หน่วยกิต, ชั่วโมง L-P-S ครบ 266/266) |

> 📌 **หมายเหตุการวัดเวลาและผลการประเมินเทียบ Lab 9**:
> 1. **เวลาที่ใช้**: เวลาสกัดจริงแบบ End-to-End ของการรัน LLM Chunked บันทึกไว้ใน `_meta.elapsed_sec` ของแต่ละไฟล์ prediction ได้แก่ **AIT (106.4s), BIT (268.7s), DSBA (283.9s), IT (410.0s)** ส่วนตัวเลข **1.1 – 2.5 วินาที** คือเวลาของการคำนวณและประเมินผล (Offline Evaluation & Verification) บนข้อมูล JSON ในหน่วยความจำ
> 2. **ผลการประเมินภาพรวมใน Lab 9 (Step 1)**: เมื่อรันคำสั่ง `python lab9/step1_eval_extraction.py` บนไฟล์ใน `work/lab7b_run/` ได้ **Ground Truth 316 วิชา, สกัดได้ 309 วิชา และจับคู่ถูก 289 วิชา** ส่วนค่าเฉลี่ยรายหลักสูตรแบบ **Macro Average** คือ **Precision 94.0%, Recall 89.7% และ F1-Score 91.3%**
> 3. **Pooled metrics ทั้ง 7 แผน**: รัน `python lab9/step1_eval_all_curricula.py` เพื่อสร้าง `lab9/reports/all_curricula/comparison.csv` ซึ่งสรุป CER, WER และ Exact Match แยกตามฟิลด์ โดยรวมตัวนับจาก DSBA/IT/BIT ทั้งแผน coop และ no-coop รวม AIT; จำนวนรายการเป็นผลรวมข้ามแผน ไม่ใช่จำนวนวิชาไม่ซ้ำกัน

##### 🔬 การประเมินผลไฟล์สกัดย้อนหลัง (Offline Evaluation via `--eval-only`):
หากมีไฟล์ `pred_text.json` อยู่แล้ว สามารถสั่งประเมินผลเทียบกับ Ground Truth ได้ทันทีโดยไม่ต้องสกัดใหม่:
```bash
# IT
python -m src.ocr_system.lab7b_curriculum --eval-only work/lab7b_run/IT/pred_text.json -g data/ground_truth/IT/IT_academic_plan_coop.json
# DSBA
python -m src.ocr_system.lab7b_curriculum --eval-only work/lab7b_run/DSBA/pred_text.json -g data/ground_truth/DSBA/DSBA_academic_plan_coop.json
# BIT
python -m src.ocr_system.lab7b_curriculum --eval-only work/lab7b_run/BIT/pred_text.json -g data/ground_truth/BIT/BIT_academic_plan_coop.json
# AIT
python -m src.ocr_system.lab7b_curriculum --eval-only work/lab7b_run/AIT/pred_text.json -g data/ground_truth/AIT/AIT_academic_plan.json
```
*ระบบจะคำนวณและบันทึกไฟล์สรุปผลอัตโนมัติ:*
- `comparison.csv`: ตารางคะแนน CER, WER (ตัดคำภาษาไทยด้วย PyThaiNLP `newmm`), Exact Match (เข้ารหัส UTF-8 BOM เปิดใน Excel ได้ทันที)
- `evaluation.json`: ข้อมูลความแม่นยำ Alignment (Precision, Recall, F1) และรายการวิชาที่โมเดลอ่านตก

> **หมายเหตุการวิเคราะห์ Alignment (กรณี IT ตก 2, เกิน 6)**:
> 1. **เกิน 4 วิชา (Duplicates)**: วิชา `06016428, 06016430, 06016439, 06016447` ปรากฏอยู่ในตารางวิชาเลือกทั้ง 2 หน้า โมเดลจึงสกัดออกมา 2 ครั้ง ในขณะที่เฉลยมีรายการละ 1 ครั้ง
> 2. **เกิน 2 วิชา / ตก 1 วิชา (Alternative Split)**: สหกิจศึกษา (`06016481` และ `06016482`) ในเฉลยเขียนรวบเป็น 1 แถวเดียวว่า `"06016481 หรือ 06016482"` แต่โมเดลสกัดแยกเป็น 2 แถวเดี่ยวที่ถูกต้องตามโครงสร้างฐานข้อมูล
> 3. **ตก 1 วิชา (Multiple Tracks)**: วิชา `06016418` เปิดสอน 2 แขนง ในเฉลยใส่ไว้ 2 แถว แต่โมเดลสกัดมา 1 แถว
> *(เมื่อนำเข้าสู่ฐานข้อมูล SQLite ใน Lab 8B ระบบมีฟังก์ชัน **Deduplication** ยุบวิชาซ้ำเหลือ 1 รายการ และจัดวิชาคู่สหกิจศึกษาเป็น **Alternative Slot (`alt_group`)** จึงทำให้ฐานข้อมูลสะอาด 100% และผ่านการตรวจครบ 7 กฎ)*


#### ก.2 สกัดข้อบังคับการศึกษา (ภาคผนวก ก) ด้วย Lab 7B (Typhoon-OCR 1.5-3B + Qwen3:4b):
> **หมายเหตุ**: ในเล่มหลักสูตร เนื้อหาภาคผนวก ก (ข้อบังคับ สจล. ว่าด้วยการศึกษาระดับปริญญาตรี พ.ศ. 2564) หน้า 94–101 เป็น**ภาพสแกน (Scanned Bitmap Images)** ที่ไม่มี Text Layer ดั้งเดิม จึงต้องใช้ Local Vision-Language Model (VLM) ในการถอดรหัสข้อความภาษาไทยและแปลงเป็น Structured Data:

```bash
# สกัดข้อบังคับการศึกษาจากเล่ม PDF (บันทึกผลลง work/lab7b_run/)
python src/ocr_system/lab7b_curriculum.py --extract-regulations

# หรือระบุพาธและหน้าที่ต้องการสกัดเอง:
python src/ocr_system/lab7b_curriculum.py --extract-regulations -i data/input/fulldoc_dsba.pdf --pages 94,96,97,98,99,101 -o work/lab7b_run
```
*ผลลัพธ์ที่ได้ (บันทึกใน `work/lab7b_run/`):*
- `intermediate_regulations_vlm.md`: ข้อความภาษาไทยสมบูรณ์จากหน้าสแกน 94, 96, 97, 98, 99, 101 ถอดรหัสด้วย `scb10x/typhoon-ocr1.5-3b`
- `regulations.json`: Structured Data ข้อบังคับ 11 รายการ (เกณฑ์การลงทะเบียน 9–22 หน่วยกิต, บทลงโทษการทุจริตสอบ, เกณฑ์ภาคทัณฑ์ GPA < 2.00, พ้นสภาพนักศึกษา, เกณฑ์เกียรตินิยมอันดับ 1 เหรียญทอง/อันดับ 1/อันดับ 2)

#### ก.3 สกัดคำอธิบายรายวิชาหมวดวิชาศึกษาทั่วไป (GenEd) ด้วย Two-Stage Architecture (Typhoon-OCR 1.5 + Qwen3:4b):
> **หมายเหตุ**: ในเล่มหลักสูตร เนื้อหาหมวดวิชาศึกษาทั่วไป (GenEd ฉบับปรับปรุง พ.ศ. 2564) หน้า 154–227 มีชั้น Text Layer ที่ Font Encoding เสียหายจนเกิดปัญหาข้อความต่างดาว (Mojibake) จึงใช้สถาปัตยกรรม **Two-Stage VLM + LLM Architecture** พร้อม **Batch Stage Execution**:
> 1. **Stage 1 (Batch OCR)**: เรนเดอร์หน้า PDF เป็นภาพแบบ In-memory และให้ `scb10x/typhoon-ocr1.5-3b` สกัดเป็น Markdown ทีละหน้า พร้อมระบบ Page Caching ป้องกันการประมวลผลซ้ำ
> 2. **Stage 2 (Batch LLM Schema)**: นำข้อความ Markdown เข้าสู่ `qwen3:4b` เพื่อแปลงเป็น JSON ตาม Schema ครบถ้วนทั้งชื่อวิชาภาษาไทย (`name_th`), หน่วยกิต, ชั่วโมงบรรยาย-ปฏิบัติ-ศึกษาด้วยตนเอง (lecture_h, lab_h, self_h) และคำอธิบายรายวิชาภาษาไทย (`description_th`)

```bash
# สกัดรายวิชาหมวด GenEd หน้า 154–227 (บันทึกผลลง work/lab7b_run/)
python src/ocr_system/extract_gened.py -i data/input/fulldoc_dsba.pdf --pages 154-227 -o work/lab7b_run/gened_courses.json --out-md work/lab7b_run/gened_combined.md --md-dir work/lab7b_run/markdown_pages
```
*ผลลัพธ์ที่ได้จากการรันจริง (บันทึกใน `work/lab7b_run/`):*
- `markdown_pages/`: ไฟล์แคช Markdown รายหน้า 74 หน้า (หน้า 154–227)
- `gened_combined.md`: เอกสาร Markdown รวมคำอธิบายรายวิชาหมวดวิชาศึกษาทั่วไปทั้งหมด
- `gened_courses.json`: ข้อมูล Structured Data รายวิชา GenEd ทั้งหมด **266 รายวิชา** (ใช้เวลา 2,827.4 วินาที)
  - ความถูกต้องของรหัสวิชา 8 หลัก: **266/266 วิชา (100%)**
  - ความสมบูรณ์ของโครงสร้างชั่วโมงเรียน (lecture_h, lab_h, self_h): **266/266 วิชา (100%)**
  - ความสมบูรณ์ของชื่อวิชาและคำอธิบายภาษาไทย: **266/266 วิชา (100%)**

---

#### ข. แปลงและนำเข้าฐานข้อมูล SQLite ด้วย Lab 8B (Option 2: Full Separation Architecture):
```bash
# 1. สร้าง Schema กลาง
python src/ocr_system/lab8b_curriculum_db.py schema -o work/lab8b_run/schema

# 2. แปลงผลลัพธ์จาก Lab 7B เข้าสู่ Schema Lab 8B (Option 2)
python src/ocr_system/lab8b_curriculum_db.py import-lab7b -i lab7_final/output/DSBA/pred_text.json -o work/lab8b_run/DSBA/curriculum.json --program-id DSBA --program-name "วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ (สหกิจศึกษา)" --name-en "Data Science and Business Analytics (DSBA)" --total-credits 132 --years 4
python src/ocr_system/lab8b_curriculum_db.py import-lab7b -i lab7_final/output/BIT/pred_text.json -o work/lab8b_run/BIT/curriculum.json --program-id BIT --program-name "เทคโนโลยีสารสนเทศทางธุรกิจ (สหกิจศึกษา)" --name-en "Business Information Technology (BIT)" --total-credits 126 --years 4
python src/ocr_system/lab8b_curriculum_db.py import-lab7b -i lab7_final/output/IT/pred_text.json -o work/lab8b_run/IT/curriculum.json --program-id IT --program-name "เทคโนโลยีสารสนเทศ (สหกิจศึกษา)" --name-en "Information Technology (IT)" --total-credits 129 --years 4
python src/ocr_system/lab8b_curriculum_db.py import-lab7b -i lab7_final/output/AIT/pred_text.json -o work/lab8b_run/AIT/curriculum.json --program-id AIT --program-name "เทคโนโลยีปัญญาประดิษฐ์" --name-en "Artificial Intelligence Technology (AIT)" --total-credits 120 --years 4

# 3. โหลดข้อมูลรายวิชาเข้าฐานข้อมูลกลาง (Unified Database: 504 รายวิชา, 7 แผน)
python src/ocr_system/lab8b_curriculum_db.py load -i work/lab8b_run/DSBA/curriculum.json -d work/lab8b_run/curriculum.db --replace
python src/ocr_system/lab8b_curriculum_db.py load -i work/lab8b_run/BIT/curriculum.json -d work/lab8b_run/curriculum.db
python src/ocr_system/lab8b_curriculum_db.py load -i work/lab8b_run/IT/curriculum.json -d work/lab8b_run/curriculum.db
python src/ocr_system/lab8b_curriculum_db.py load -i work/lab8b_run/AIT/curriculum.json -d work/lab8b_run/curriculum.db

# 4. โหลดข้อบังคับการศึกษา (Regulations) เข้าตาราง regulation
python src/ocr_system/lab8b_curriculum_db.py load-regulations -i work/lab7b_run/regulations.json -d work/lab8b_run/curriculum.db

# 5. โหลดคำอธิบายรายวิชาหมวด GenEd เข้าตาราง course (อัปเดตคำอธิบายและชั่วโมงเรียน L-P-S)
python src/ocr_system/extract_gened.py -i data/input/fulldoc_dsba.pdf --pages 154-227 -o work/lab7b_run/gened_courses.json -d work/lab8b_run/curriculum.db

# (ทางเลือก) โหลดฐานข้อมูลเดี่ยวแยกแต่ละสาขาวิชา (Isolated Program Databases)
# python src/ocr_system/lab8b_curriculum_db.py load -i work/lab8b_run/DSBA/curriculum.json -d work/lab8b_run/DSBA/curriculum.db --replace
# python src/ocr_system/lab8b_curriculum_db.py load -i work/lab8b_run/BIT/curriculum.json -d work/lab8b_run/BIT/curriculum.db --replace
# python src/ocr_system/lab8b_curriculum_db.py load -i work/lab8b_run/IT/curriculum.json -d work/lab8b_run/IT/curriculum.db --replace
# python src/ocr_system/lab8b_curriculum_db.py load -i work/lab8b_run/AIT/curriculum.json -d work/lab8b_run/AIT/curriculum.db --replace
```

> **ทางลัด**: สามารถรันกระบวนการทั้งหมดของ Lab 8B ข้างต้น (สร้าง Schema, นำเข้า 4 หลักสูตร, โหลดข้อบังคับ, และตรวจ Verify) อัตโนมัติในคำสั่งเดียวด้วย:
> ```bash
> # รันครบทั้ง 4 หลักสูตรและตรวจ Verify 7 กฎทันที (ข้ามการรัน LLM Eval เพื่อความรวดเร็ว)
> python run_lab8b.py --skip-lab7 --skip-eval
> 
> # หรือรันครบวงจรพร้อมประเมินผลชุดคำถามทองด้วย Qwen (ต้องเปิด Ollama)
> python run_lab8b.py --skip-lab7
> ```

#### ค. ตรวจสอบความถูกต้องของฐานข้อมูล (Consistency Verification 7 กฎ):
```bash
python src/ocr_system/lab8b_curriculum_db.py verify -d work/lab8b_run/curriculum.db -o work/lab8b_run/verify.json
```
**ผลการตรวจสอบ (ผ่านครบ 7 จาก 7 ข้อ 100%):**
```text
  [ผ่าน  ] CHK1  หน่วยกิตรวมของแผน = หน่วยกิตที่หลักสูตรประกาศ
           AIT_SINGLE: 120/120 | BIT_COOP: 126/126 | BIT_NON_COOP: 126/126 | DSBA_COOP: 132/132 | DSBA_NON_COOP: 132/132 | IT_COOP: 129/129 | IT_NON_COOP: 129/129
  [ผ่าน  ] CHK2  ทุกรหัสวิชาในแผน มีคำอธิบายรายวิชา (ครบทุกรหัส 504 วิชา)
  [ผ่าน  ] CHK3  รหัสวิชาเป็นตัวเลข 8 หลักทุกรายการ
  [ผ่าน  ] CHK4  หน่วยกิตในแผน ตรงกับคำอธิบายรายวิชา
  [ผ่าน  ] CHK5  วิชาบังคับก่อน อยู่ภาคเรียนก่อนวิชาที่อ้างถึง
  [ผ่าน  ] CHK6  ไม่มีวิชาซ้ำในภาคเรียนเดียวกัน
  [ผ่าน  ] CHK7  หน่วยกิตต่อภาคเรียนอยู่ระหว่าง 9–22 หน่วยกิต
```

#### ง. การประเมินผลชุดคำถามทดสอบ Text-to-SQL (NL2SQL Benchmark):
ระบบผ่านการประเมินผลชุดคำถาม Gold Questions รวม 189 คำถาม (โครงสร้างหลักสูตร, แผนการเรียน, วิชาเลือก, วิชาบังคับก่อน และข้อบังคับการศึกษา 10 ข้อ):
```bash
# รันการประเมินผล Text-to-SQL อัตโนมัติบนฐานข้อมูลกลาง
python src/ocr_system/lab8b_curriculum_db.py eval -d work/lab8b_run/curriculum.db -q work/lab8b_run/gold_questions.json -o work/lab8b_run/eval_result.json --model qwen3:4b
```
**สรุปผลการประเมิน (Evaluation Metrics):**
- **การตั้งค่า NL2SQL ปัจจุบัน**: Prompt เดียวสำหรับทุกคำถาม (DDL + Few-shot 30 ข้อ + รายการ `category`/`topic` ของข้อบังคับจากฐานข้อมูล), `qwen3:4b` ที่ `temperature = 0.0` และ `num_ctx = 8192`, แก้ SQL 1 ครั้งเมื่อรันไม่ผ่าน และใช้ฟังก์ชัน `ask()` ตัวเดียวกันทั้ง Benchmark และหน้าเว็บ (รายละเอียดใน `sysdoc.md` หัวข้อ 3)
- **ตัวชี้วัดจากคำสั่งประเมิน SQL (`work/lab8b_run/eval_result.json` และ `lab9/reports/step3_nl2sql_benchmark.json`)**:
  - **SQL Syntax Validity**: **100.0%** (189/189 คำถามสร้าง SQL ที่รันผ่านได้)
  - **NL2SQL Execution Accuracy (Unified Database)**: **95.24%** (180/189 คำถามที่ผลลัพธ์ SQL ตรงกับ Ground Truth ในฐานข้อมูล) ข้อผิด 9 ข้อเป็นปัญหาที่ข้อมูลหรือเฉลย 7 ข้อ และโมเดลสร้าง SQL ผิด 2 ข้อ
  - **ผลแยกตาม Query Complexity (Lab 9 Step 5):**

| Level | จำนวนคำถาม | Valid SQL | Execution Accuracy |
| :--- | ---: | ---: | ---: |
| 1 — Simple Lookup | 144 | 100.0% (144/144) | 97.92% (141/144) |
| 2 — Filter & Aggregate | 13 | 100.0% (13/13) | 76.92% (10/13) |
| 3 — Multi-table Relation | 17 | 100.0% (17/17) | 88.24% (15/17) |
| 4 — Regulation Query | 10 | 100.0% (10/10) | 90.00% (9/10) |
| 5 — Ambiguous Query | 5 | 100.0% (5/5) | 100.0% (5/5) |

  - วิธีทำซ้ำ: รัน Step 3 เพื่อสร้าง `work/lab8b_run/eval_result.json` ก่อน แล้วรัน `python lab9/step5_eval_query_complexity.py --labels lab9/query_complexity_labels.json`
  - ผล Step 5: `lab9/reports/query_complexity_summary.csv` สรุปผลราย Level และ `lab9/reports/query_complexity_detail.csv` แสดงคำถาม, คำตอบจาก LLM, เฉลย, SQL และผลถูก/ผิด โดยป้าย Level กำหนดไว้ใน `lab9/query_complexity_labels.json`
  - **Per-Program SQL Execution Accuracy (Isolated Databases; ชุดละ 45 ข้อจาก `work/lab8b_run/{P}/gold_questions.json` รันใหม่ด้วย Prompt ปัจจุบัน 13 ต.ค. 2569)**:
    - **BIT**: **100.0%** (45/45 ข้อ)
    - **IT**: **100.0%** (45/45 ข้อ)
    - **DSBA**: **91.1%** (41/45 ข้อ - คำถามที่ไม่ระบุหลักสูตร/แผนได้ 0 แถว เพราะฐานข้อมูลแยกของ DSBA ไม่มีแผนปกติที่เป็นค่าเริ่มต้น 3 ข้อ และกรองหลักสูตรผิด 1 ข้อ)
    - **AIT**: **88.9%** (40/45 ข้อ - ปัญหาข้อมูล/เฉลยชุดเดียวกับฐานข้อมูลรวม 5 ข้อ)
    - **รวม 4 ฐาน**: Valid SQL **100.0%** (180/180), Execution Accuracy **95.0%** (171/180)
    - สร้างซ้ำได้ด้วย `python src/ocr_system/lab8b_curriculum_db.py eval -d work/lab8b_run/<P>/curriculum.db -q work/lab8b_run/<P>/gold_questions.json -o work/lab8b_run/<P>/eval_result.json` แล้วรัน `python lab9/step3_eval_nl2sql.py --cached`
- **ตัวชี้วัดจากการรันสดล่าสุด (`lab9/reports/live_eval_result.json`)**:
  - **Live Retrieval Correctness**: **95.24%** (180/189 ข้อ โดย `score_one()` ตรวจค่าจาก SQL rows)
  - **Live QA Latency**: **เฉลี่ย 1.69 วินาที/ข้อ** (ต่ำสุด 0.74 วินาที, ค่ามัธยฐาน 1.66 วินาที, สูงสุด 8.00 วินาที, รวม 319.81 วินาที / 189 ข้อ)
  - **ทดสอบผ่าน API จริง (`POST /api/ask` 30 คำถาม)**: HTTP 200 ครบ 30/30 และ SQL ตรงกับ Benchmark ทุกตัวอักษร 30/30 เฉลี่ย 1.92 วินาที/ข้อ (รวม HTTP และการค้นป้ายอ้างอิง)
  - สร้างผลชุดนี้ซ้ำได้ด้วย `python lab9/run_all_eval.py --live` (ต้องใส่ `--live` มิฉะนั้นสคริปต์จะใช้ผลที่บันทึกไว้แทนการถามโมเดลสด)

---

### 4. ขั้นตอนการสั่งรัน Web Application (FastAPI + Modern Web UI)
สั่งรันเว็บเซิร์ฟเวอร์ด้วยคำสั่ง:
```bash
python -m uvicorn lab10_fastapi.curriculum_app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### 5. การเปิดใช้งานหน้าเว็บผ่าน Web Browser
เมื่อเซิร์ฟเวอร์เปิดทำงานแล้ว สามารถเปิดเบราว์เซอร์และเข้าไปที่:
1. **หน้าถามตอบหลักสูตร AI (Assistant Chat UI)**:
   - URL: [http://127.0.0.1:8000/](http://127.0.0.1:8000/) หรือ [http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)
   - ฟีเจอร์: ถามตอบภาษาธรรมชาติเกี่ยวกับโครงสร้างหลักสูตร แผนการเรียน และข้อบังคับการศึกษา พร้อมระบบแสดง SQL และตารางข้อมูล
   - **ระบบ Grounded Citation Badge**: แสดงป้ายเลขหน้าอ้างอิงจริง `[อ้างอิงหน้า x]` วางเคียงข้างป้าย `[Success]` เหนือกล่องคำตอบอย่างเป็นระเบียบ (เช่น รายวิชาอ้างอิงเลขหน้าจากตาราง `course`, ข้อบังคับเกียรตินิยมอันดับ 1 อ้างอิงข้อ 27.2.2 หน้า 93 โดยหากคำถามใดไม่มีเลขหน้าเฉพาะเจาะจงในฐานข้อมูล เช่น หน่วยกิตรวมของหลักสูตรหรือหน่วยกิตต่อเทอม ระบบจะซ่อนป้ายอ้างอิงอัตโนมัติ เพื่อความถูกต้องตามหลัก Grounded Citation และลดความเสี่ยงจากการอ้างอิงคลาดเคลื่อน)
2. **หน้าโครงสร้างหลักสูตรและรายวิชาทั้งหมด (Course Catalog & Regulations)**:
   - URL: [http://127.0.0.1:8000/courses](http://127.0.0.1:8000/courses) หรือ [http://127.0.0.1:8000/static/courses.html](http://127.0.0.1:8000/static/courses.html)
   - ฟีเจอร์: ตรวจสอบรายวิชาทั้งหมด 504 วิชา (วิชาเฉพาะ 238 + GenEd 266) ค้นหารหัส/ชื่อวิชา ตรวจสอบวิชาบังคับก่อน (Prerequisites 30 รายการ) และดูข้อบังคับการศึกษา สจล.
3. **หน้า Interactive API Documentation (Swagger UI)**:
   - URL: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - ฟีเจอร์: ทดสอบเรียกใช้งาน API Endpoint ทุกเส้นได้โดยตรง

---

### 6. ตัวอย่างคำถามทดสอบการทำงานของระบบ (Test Queries)
- **คำถามเชิงโครงสร้าง**:
  - `หลักสูตร DSBA มีกี่หน่วยกิต` $\rightarrow$ ตอบ `132`
  - `วิชา 06026216 คือวิชาอะไร` $\rightarrow$ ตอบ `ปัญญาประดิษฐ์` (`[อ้างอิงหน้า 17]`)
  - `วิชา 06026241 ต้องเรียนวิชาใดมาก่อน`
- **คำถามเชิงความสัมพันธ์และแผนการศึกษา**:
  - `ปี 1 เทอม 1 เรียนกี่หน่วยกิต` $\rightarrow$ ตอบ `18`
  - `ปี 2 เทอม 1 สาขา DSBA เรียนวิชาอะไรบ้าง`
  - `หลักสูตร IT มีวิชากี่ตัว`
- **คำถามเชิงข้อบังคับการศึกษา (Regulations)**:
  - `เกียรตินิยมอันดับ 1 ต้องได้เกรดเท่าไร` $\rightarrow$ ตอบ `3.5` (`[อ้างอิงหน้า 98]`)
  - `ทุจริตในการสอบจะถูกลงโทษอย่างไร` $\rightarrow$ (`[อ้างอิงหน้า 101]`)
  - `ลงทะเบียนเรียนภาคปกติได้สูงสุดกี่หน่วยกิต` $\rightarrow$ ตอบ `22` (`[อ้างอิงหน้า 94]`)

---

---

## Lab 11: Front-End Development & API Contract

### โครงสร้างไฟล์ Frontend
แยกไฟล์ตาม Best Practice (สไลด์หน้า 7 และ 28):
```text
lab10_fastapi/curriculum_app/static/
├── index.html   # หน้า AI Assistant
├── style.css    # รูปแบบและเลย์เอาต์ของหน้าเว็บ
├── app.js       # แชต AI, เรียก API และแสดงสถานะ Idle/Loading/Success/Error
├── courses.html # หน้าแคตตาล็อกรายวิชา แผนการเรียน และข้อบังคับ
└── courses.js   # ค้นหา/กรองรายวิชา แผนการเรียน วิชาบังคับก่อน และข้อบังคับ
```

### การจัดการ 4 สถานะ UI (AI System UX)
1. **Idle**: คำแนะนำการใช้งานพร้อมปุ่มชิปตัวอย่างคำถาม
2. **Loading**: แสดง Spinner และข้อความกำลังประมวลผล พร้อม `disabled` ปุ่มเพื่อป้องกันการกดซ้ำ
3. **Success**: แสดงคำตอบภาษาธรรมชาติจาก AI พร้อมรายละเอียด SQL และตารางข้อมูล (ปลอดภัยจาก XSS ด้วย `textContent`)
4. **Error**: แสดงกล่องเตือนสีแดง แจ้งรายละเอียดข้อผิดพลาดและข้อแนะนำสิ่งที่ผู้ใช้ควรดำเนินการแก้ไข

### API Contract สรุป
| Endpoint | Method | Request Body / Param | Response Success | Response Error |
| :--- | :---: | :--- | :--- | :--- |
| `/api/ask` | POST | `{"question": "string"}` | `200` (`question`, `sql`, `rows`, `answer`, `sources`) | `422` (Request body ไม่ถูกต้อง), `503` (Ollama/DB offline); ถ้าสร้าง SQL ไม่สำเร็จแม้แก้ 1 ครั้ง จะตอบ `200` พร้อม `answer` ปฏิเสธ |
| `/api/courses` | GET | `search`, `program_id`, `limit`, `offset` | `200` (List of CourseResponse + `programs`) | `503` (DB offline) |
| `/api/courses` | POST | `CourseCreate` (พร้อม `plan_id` Dynamic Check) | `201` (CourseResponse + `plan_id`) | `422` (ขาด `plan_id` ในสาขาหลายแผน), `409` (รหัสซ้ำ) |
| `/api/courses/{code}/prerequisites` | GET | `code`: รหัสวิชา 8 หลัก | `200` (`code`, `name_th`, `requires`, `required_by`) | `404` (ไม่พบรายวิชา), `503` (DB offline) |
| `/api/study-plans` | GET | `program_id`, `plan_id` | `200` (List of StudyPlan: `plan_type` = coop/no_coop/single) | `503` (DB offline) |
| `/api/elective-slots` | GET | `plan_id`, `year`, `semester` | `200` (List of ElectiveSlotResponse) | `503` (DB offline) |
| `/api/plan` | GET | `program_id`, `plan_id`, `year`, `semester` | `200` (List of PlanItemResponse จาก `v_plan`) | `503` (DB offline) |
| `/api/plan/summary` | GET | `program_id`, `plan_id`, `year`, `semester` | `200` (List of PlanSummaryResponse จาก `v_semester_credits`) | `503` (DB offline) |
| `/api/program` | GET | - | `200` (ข้อมูลสรุปหลักสูตรแรกที่พบ) | `404` (ไม่พบหลักสูตร), `503` (DB offline) |
| `/api/programs` | GET | - | `200` (List of ProgramResponse ครบทั้ง 4 หลักสูตร) | `503` (DB offline) |
| `/api/stats` | GET | `program_id` | `200` (`total_courses`, `total_plans`, `total_slots`, `total_regulations`) | `503` (DB offline) |
| `/api/regulations` | GET | `category`, `search`, `limit` | `200` (List of RegulationResponse) | `503` (DB offline) |
| `/api/health` | GET | - | `200` (`status`, `database_ready`, `ollama_ready`, `model`) | `200` (Status degraded if not ready) |

> ดูรายละเอียดสัญญา API Contract และตัวอย่าง payload ฉบับสมบูรณ์ได้ที่ [lab10_fastapi/curriculum_app/README.md](lab10_fastapi/curriculum_app/README.md)

