#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_extract_all.py
รันสกัดแผนการศึกษาทุกหลักสูตร (DSBA, BIT, IT, AIT) ทั้งแบบ coop และ no_coop
โดยใช้ Pure LLM (pipeline=text) และบันทึกลงใน work/lab7b_run/ พร้อมประเมินผล
"""

import sys
import time
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

# เพิ่ม parent directory เข้า sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab7b_curriculum import (
    TEXT_PLAN_PAGE_SPECS,
    run_pipeline,
    load_pages,
    evaluate,
    verify_internal,
)
import lab7_metrics as M

TARGETS = [
    {
        "name": "DSBA (coop)",
        "program": "DSBA",
        "plan": "coop",
        "input": "data/input/fulldoc_dsba.pdf",
        "gt": "data/ground_truth/DSBA/DSBA_academic_plan_coop.json",
        "outdir": "work/lab7b_run/DSBA",
    },
    {
        "name": "DSBA (no_coop)",
        "program": "DSBA",
        "plan": "no_coop",
        "input": "data/input/fulldoc_dsba.pdf",
        "gt": "data/ground_truth/DSBA/DSBA_academic_plan_no_coop.json",
        "outdir": "work/lab7b_run/DSBA_non_coop",
    },
    {
        "name": "BIT (coop)",
        "program": "BIT",
        "plan": "coop",
        "input": "data/input/fulldoc_BIT.pdf",
        "gt": "data/ground_truth/BIT/BIT_academic_plan_coop.json",
        "outdir": "work/lab7b_run/BIT",
    },
    {
        "name": "BIT (no_coop)",
        "program": "BIT",
        "plan": "no_coop",
        "input": "data/input/fulldoc_BIT.pdf",
        "gt": "data/ground_truth/BIT/BIT_academic_plan_no_coop.json",
        "outdir": "work/lab7b_run/BIT_non_coop",
    },
    {
        "name": "IT (coop)",
        "program": "IT",
        "plan": "coop",
        "input": "data/input/fulldoc_it.pdf",
        "gt": "data/ground_truth/IT/IT_academic_plan_coop.json",
        "outdir": "work/lab7b_run/IT",
    },
    {
        "name": "IT (no_coop)",
        "program": "IT",
        "plan": "no_coop",
        "input": "data/input/fulldoc_it.pdf",
        "gt": "data/ground_truth/IT/IT_academic_plan_no_coop.json",
        "outdir": "work/lab7b_run/IT_non_coop",
    },
    {
        "name": "AIT (single)",
        "program": "AIT",
        "plan": "single",
        "input": "data/input/fulldoc_AIT.pdf",
        "gt": "data/ground_truth/AIT/AIT_academic_plan.json",
        "outdir": "work/lab7b_run/AIT",
    },
]

def run_target(target: dict):
    repo_root = Path(__file__).resolve().parent.parent.parent
    print("\n" + "=" * 80)
    print(f"🚀 กำลังประมวลผล: {target['name']}")
    print("=" * 80)
    
    prog = target["program"]
    plan = target["plan"]
    pdf_path = str(repo_root / target["input"])
    gt_path = repo_root / target["gt"]
    outdir = repo_root / target["outdir"]
    outdir.mkdir(parents=True, exist_ok=True)
    
    page_spec = TEXT_PLAN_PAGE_SPECS[prog][plan]
    print(f"  • เอกสาร: {target['input']}")
    print(f"  • ช่วงหน้า: {page_spec}")
    print(f"  • บันทึกที่: {target['outdir']}")

    pages = load_pages(pdf_path, page_spec)
    data = run_pipeline("text", pages, outdir, pdf_path, page_spec, prog_name=prog, plan_name=plan)
    
    if not data or not data.get("courses"):
        print(f"❌ {target['name']} สกัดไม่สำเร็จ")
        return

    # ตรวจความสอดคล้องภายใน
    v = verify_internal(data)
    print(f"\n  ตรวจความสอดคล้องภายใน: {'✓ ผ่าน' if v['ok'] else '✗ มีข้อสังเกต'} ({v['n_courses']} วิชา, {v['total_credits_fixed_terms']} หน่วยกิต)")
    for msg in v["issues"][:4]:
        print(f"    • {msg}")

    # ประเมินผลเทียบ Ground Truth
    if gt_path.exists():
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        stats, align = evaluate(data, gt)
        M.print_table(stats, f"ผลประเมิน: {target['name']}")
        print(f"\n  🎯 สรุปผล: จับคู่ได้ {align['matched']}/{align['gt_total']} "
              f"| ตก {align['missed']} | แต่งเกิน {align['spurious']} "
              f"| P={align['precision']:.3f} R={align['recall']:.3f} F1={align['f1']:.3f}")
        
        # บันทึก CSV และ JSON
        csv_path = outdir / "comparison.csv"
        M.save_csv(stats, str(csv_path), extra={"pipeline": "text", "plan": target["name"]})
        
        eval_json_path = outdir / "evaluation.json"
        eval_summary = {
            "text": {
                **M.stats_to_dict(stats),
                "alignment": align,
                "internal_check": v,
            }
        }
        eval_json_path.write_text(json.dumps(eval_summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ บันทึก {csv_path.name} และ {eval_json_path.name}")

def main():
    start_time = time.time()
    print("=" * 80)
    print("  BATCH EXTRACTION ALL CURRICULA (Lab 7B)")
    print("=" * 80)
    
    selected = sys.argv[1:] if len(sys.argv) > 1 else None
    for target in TARGETS:
        if selected:
            target_key = target["program"].upper()
            if not any(s.upper() in target_key or s.upper() in target["name"].upper() for s in selected):
                continue
        run_target(target)
        
    print("\n" + "=" * 80)
    print(f"🎉 เสร็จสิ้นทุกหลักสูตรในเวลา {time.time() - start_time:.1f} วินาที")
    print("=" * 80)

if __name__ == "__main__":
    main()
