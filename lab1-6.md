# Lab 1–6: OCR System Setup, Usage, and Evaluation

เอกสารนี้รวบรวมวิธีเตรียมสภาพแวดล้อม ติดตั้ง dependency ใช้ OCR engines สกัดข้อมูลรายวิชา และประเมินผล OCR ในโปรเจกต์นี้

## 1. เปิดโปรเจกต์ด้วย VS Code

แนะนำ VS Code เพราะเปิดดูไฟล์ แก้โค้ด และใช้ Terminal ได้ในที่เดียว

1. แตกไฟล์โปรเจกต์ แล้วเปิด VS Code
2. เลือก **File > Open Folder** และเลือกโฟลเดอร์รากของโปรเจกต์ที่มี `pyproject.toml`
3. เปิด Terminal ด้วย **Terminal > New Terminal**

คำสั่งต่อจากนี้ให้รันจากโฟลเดอร์รากของโปรเจกต์

### Project Structure

```text
ocr_system/
├── README.md
├── requirements.txt
├── pyproject.toml
├── data/
│   ├── input/                 # ไฟล์ภาพหรือ PDF ที่ต้องการ OCR
│   ├── ground_truth/          # ไฟล์เฉลยสำหรับ evaluate
│   └── QA/                    # โฟลเดอร์สำหรับทดสอบ QA
├── outputs/                   # ผลลัพธ์ OCR และ evaluation
└── src/
    └── ocr_system/
        ├── cli.py             # command line interface
        ├── config.py          # config หลักของระบบ
        ├── document_loader.py # โหลดภาพ / แปลง PDF เป็นภาพ
        ├── preprocessing.py   # resize, denoise, contrast, deskew, threshold
        ├── pipeline.py        # OCR pipeline หลัก
        ├── evaluation.py      # CER, WER, exact match
        ├── field_extraction.py# ดึง field เช่น email, date, id, phone
        ├── schemas.py         # dataclass ของผลลัพธ์
        ├── engine_factory.py  # เลือก OCR engine
        ├── engines/           # PaddleOCR, Tesseract, TrOCR, Ensemble
        └── utils/             # ฟังก์ชันช่วยเหลือ เช่น อ่าน/เขียนไฟล์
```

## 2. ติดตั้ง Python packages

โปรเจกต์กำหนด Python ขั้นต่ำเป็น 3.10 ตรวจเวอร์ชันได้ด้วย:

```powershell
python --version
```

ถ้าเครื่องเรียก `python` ไม่ได้ ให้ลอง:

```powershell
py --version
```

สร้าง virtual environment เพื่อแยก packages ของโปรเจกต์:

```powershell
python -m venv .venv
```

ถ้าจำเป็นให้ใช้ `py -m venv .venv` แทน

เปิดใช้งาน environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate
```

ถ้า PowerShell ปฏิเสธการรัน activation script ให้เปิด PowerShell ด้วยบัญชีผู้ใช้ของตน แล้วตั้ง policy ตามคำแนะนำขององค์กรหรือผู้ดูแลเครื่องก่อน

```bash
# macOS / Linux
source .venv/bin/activate
```

เมื่อติดตั้งสำเร็จ prompt จะขึ้นต้นด้วย `(.venv)` จากนั้นติดตั้ง packages และโปรเจกต์:

```bash
pip install -r requirements.txt
pip install -e .
```

การติดตั้งแบบ editable ช่วยให้เรียก CLI ด้วย `python -m ocr_system.cli` จากโฟลเดอร์รากได้

## 3. ติดตั้ง Tesseract และเตรียมไฟล์ทดสอบ

โปรเจกต์ใช้ OCR engines ได้แก่ PaddleOCR, Tesseract และ TrOCR ส่วน `pytesseract` เป็น Python wrapper จึงต้องติดตั้งโปรแกรม Tesseract OCR แยกด้วย

### Windows

ติดตั้ง Tesseract OCR ที่มีภาษา English และ Thai แล้วเปิด Terminal ใหม่ ตรวจสอบด้วย:

```powershell
tesseract --version
tesseract --list-langs
```

รายการภาษาควรมี `eng` และ `tha`

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-tha poppler-utils
```

### macOS

```bash
brew install tesseract poppler
brew install tesseract-lang
```

`poppler` ใช้แปลง PDF เป็นภาพผ่าน `pdf2image`

สร้างโฟลเดอร์ `data/input/` หากยังไม่มี แล้ววางเอกสารทดสอบไว้ข้างใน เช่น:

```text
data/input/sample.pdf
data/input/sample.jpg
data/input/sample.png
```

รองรับ PDF หลายหน้าและไฟล์ภาพ JPG, PNG, TIFF และ BMP

## 4. รัน OCR และสกัดข้อมูลรายวิชา

### Ensemble

Ensemble รวมผลจาก PaddleOCR และ Tesseract เหมาะกับเอกสารที่มีภาษาไทยและอังกฤษปนกัน:

```bash
python -m ocr_system.cli ocr data/input/sample.pdf --engine ensemble
```

### PaddleOCR

```bash
python -m ocr_system.cli ocr data/input/sample.jpg --engine paddle --paddle-lang th
```

เอกสารภาษาอังกฤษเป็นหลักลอง `--paddle-lang en`

### Tesseract

```bash
python -m ocr_system.cli ocr data/input/sample.jpg --engine tesseract --languages tha+eng
```

เลือก `--languages eng` สำหรับภาษาอังกฤษ หรือ `--languages tha` สำหรับภาษาไทย

### TrOCR

```bash
python -m ocr_system.cli ocr data/input/sample.jpg --engine trocr --device cpu
```

ถ้าติดตั้ง PyTorch ที่รองรับ CUDA และมี GPU ให้ใช้ `--device cuda` ได้ TrOCR ในระบบนี้เหมาะกับข้อความสั้นหรือภาพที่ crop เป็นบรรทัด มากกว่าเอกสารยาวทั้งหน้า

### สกัดข้อมูลรายวิชาจากผล OCR

คำสั่ง `ocr` สร้างผล OCR ก่อน จากนั้นใช้ `extract` เพื่อแปลงข้อความเป็นข้อมูลรายวิชา:

```bash
python -m ocr_system.cli extract outputs/sample_ocr.json
```

กำหนดไฟล์ผลลัพธ์เองได้ด้วย `--output`

ผลลัพธ์จะอยู่ใน `outputs/` โดยทั่วไปประกอบด้วย:

```text
outputs/sample_ocr.json       # ข้อความ OCR, confidence, page และข้อมูลบรรทัด
outputs/sample_ocr.txt        # ข้อความ OCR รวม อ่านสะดวก
outputs/sample_fields.json    # fields ทั่วไปที่ระบบตรวจหา เช่น วันที่หรือรหัส
outputs/sample_extracted.json # ข้อมูลรายวิชาหลังสกัดด้วยคำสั่ง extract
outputs/pages/                # ภาพหน้าที่แปลงจาก PDF
```

ชื่อไฟล์จริงจะอิงจากชื่อไฟล์ input

## 5. ประเมินผล OCR (Evaluation)

Ground Truth สำหรับประเมิน raw text ใช้ JSON ที่ map ชื่อไฟล์กับข้อความจริง ตัวอย่าง `data/ground_truth/example_ground_truth.json`:

```json
{
  "sample.pdf": "ข้อความจริงทั้งหมดในเอกสาร sample.pdf",
  "sample.jpg": "ข้อความจริงทั้งหมดในเอกสาร sample.jpg"
}
```

รัน OCR ก่อน แล้วเปรียบเทียบผลกับ Ground Truth:

```bash
python -m ocr_system.cli ocr data/input/sample.pdf --engine ensemble
python -m ocr_system.cli evaluate data/ground_truth/example_ground_truth.json outputs/sample_ocr.json
```

ผลประเมินหลัก:

- **CER (Character Error Rate)**: อัตราความผิดพลาดระดับตัวอักษร ค่ายิ่งต่ำยิ่งดี
- **WER (Word Error Rate)**: อัตราความผิดพลาดระดับคำ ค่ายิ่งต่ำยิ่งดี
- **Exact Match**: ข้อความตรงกันทั้งหมดหรือไม่

ตัวอย่าง CER = 0.05 หมายถึงมีข้อผิดพลาดระดับอักขระประมาณ 5% เมื่อเทียบกับความยาวข้อความอ้างอิง ทั้งนี้ข้อความส่วนเกินอย่างหัวกระดาษที่ไม่มีใน Ground Truth อาจทำให้ CER/WER สูงขึ้น

### ประเมินการสกัดรายวิชา

ถ้ามี prediction แบบ `courses` และ Ground Truth ที่มี `courses` สามารถประเมินผลระดับรายวิชาได้โดยตรง:

```bash
python -m ocr_system.cli ocr data/input/fulldoc_AIT.pdf --engine ensemble
python -m ocr_system.cli extract outputs/fulldoc_AIT_ocr.json
python -m ocr_system.cli evaluate data/ground_truth/AIT/AIT_academic_plan.json outputs/fulldoc_AIT_extracted.json
```

คำสั่ง `filter-gt` ใช้กรองผลที่สกัดให้เหลือรายการที่พบใน Ground Truth ก่อนบันทึกไฟล์ filtered:

```bash
python -m ocr_system.cli filter-gt outputs/fulldoc_AIT_ocr.json data/ground_truth/AIT/AIT_academic_plan.json
```

## 6. คำสั่งที่ใช้บ่อยและ Output JSON

รัน pipeline แบบ end-to-end (OCR แล้วสกัดข้อมูลรายวิชาในคำสั่งเดียว):

```bash
python -m ocr_system.cli run data/input/sample.pdf --engine ensemble
```

กำหนดโฟลเดอร์ output, ภาษา, หรือบันทึกภาพ debug เพิ่มได้ เช่น:

```bash
python -m ocr_system.cli ocr data/input/sample.pdf --engine ensemble --languages tha+eng --paddle-lang th --save-debug-images
```

ตัวอย่างโครงสร้างผล OCR:

```json
{
  "source_path": "data/input/sample.pdf",
  "engine": "ensemble",
  "text": "--- Page 1 ---\nข้อความที่ OCR อ่านได้",
  "pages": [
    {
      "page": 1,
      "text": "ข้อความที่ OCR อ่านได้",
      "lines": [
        {
          "text": "ข้อความหนึ่งบรรทัด",
          "confidence": 0.95,
          "box": [[0, 0], [100, 0], [100, 30], [0, 30]],
          "engine": "paddle",
          "page": 1
        }
      ],
      "image_path": "outputs/pages/sample_page_001.jpg"
    }
  ]
}
```

ถ้า Tesseract อ่านภาพได้ไม่ดี ให้ลองปิด preprocessing เพื่อเปรียบเทียบ:

```bash
python -m ocr_system.cli ocr data/input/sample.jpg --engine tesseract --no-preprocess
```
