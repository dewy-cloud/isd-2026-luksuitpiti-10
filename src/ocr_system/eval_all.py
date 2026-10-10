#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eval_all.py
รันประเมินผลความแม่นยำ (CER / WER / Alignment) ของทั้ง 7 แผน
เทียบกับ Ground Truth ใน data/ground_truth/ ด้วย lab7_metrics.py
"""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from lab7b_curriculum import evaluate
import lab7_metrics as M

EVAL_PAIRS = [
    ("DSBA (coop)", "work/lab7b_run/DSBA/pred_text.json", "data/ground_truth/DSBA/DSBA_academic_plan_coop.json", "work/lab7b_run/DSBA"),
    ("DSBA (no_coop)", "work/lab7b_run/DSBA_non_coop/pred_text.json", "data/ground_truth/DSBA/DSBA_academic_plan_no_coop.json", "work/lab7b_run/DSBA_non_coop"),
    ("BIT (coop)", "work/lab7b_run/BIT/pred_text.json", "data/ground_truth/BIT/BIT_academic_plan_coop.json", "work/lab7b_run/BIT"),
    ("BIT (no_coop)", "work/lab7b_run/BIT_non_coop/pred_text.json", "data/ground_truth/BIT/BIT_academic_plan_no_coop.json", "work/lab7b_run/BIT_non_coop"),
    ("IT (coop)", "work/lab7b_run/IT/pred_text.json", "data/ground_truth/IT/IT_academic_plan_coop.json", "work/lab7b_run/IT"),
    ("IT (no_coop)", "work/lab7b_run/IT_non_coop/pred_text.json", "data/ground_truth/IT/IT_academic_plan_no_coop.json", "work/lab7b_run/IT_non_coop"),
    ("AIT (single)", "work/lab7b_run/AIT/pred_text.json", "data/ground_truth/AIT/AIT_academic_plan.json", "work/lab7b_run/AIT"),
]

def main():
    root = Path(__file__).resolve().parent.parent.parent
    print("=" * 105)
    print("  การประเมินผลความแม่นยำ Lab 7B ด้วยโมดูล lab7_metrics.py")
    print("=" * 105)
    header = f"{'หลักสูตร/แผน':<20} | {'Matched':<10} | {'Precision':<10} | {'Recall':<10} | {'F1-score':<10} | {'Code Exact':<11} | {'Name TH CER':<11}"
    print(header)
    print("-" * 105)

    all_results = {}

    for name, p_rel, g_rel, out_rel in EVAL_PAIRS:
        p_path = root / p_rel
        g_path = root / g_rel
        out_dir = root / out_rel

        if not p_path.exists() or not g_path.exists():
            print(f"{name:<20} | ไม่พบไฟล์")
            continue

        pred = json.loads(p_path.read_text(encoding="utf-8"))
        gt = json.loads(g_path.read_text(encoding="utf-8"))

        stats, align = evaluate(pred, gt)
        
        # บันทึก comparison.csv และ evaluation.json
        csv_path = out_dir / "comparison.csv"
        M.save_csv(stats, str(csv_path), extra={"pipeline": "text", "plan": name})
        eval_json_path = out_dir / "evaluation.json"
        eval_summary = {
            "text": {
                **M.stats_to_dict(stats),
                "alignment": align,
            }
        }
        eval_json_path.write_text(json.dumps(eval_summary, ensure_ascii=False, indent=2), encoding="utf-8")

        code_acc = f"{stats['code'].acc * 100:.1f}%"
        name_cer = f"{stats['name_th'].cer:.4f}"
        match_str = f"{align['matched']}/{align['gt_total']}"
        p_str = f"{align['precision']:.3f}"
        r_str = f"{align['recall']:.3f}"
        f1_str = f"{align['f1']:.3f}"

        print(f"{name:<20} | {match_str:<10} | {p_str:<10} | {r_str:<10} | {f1_str:<10} | {code_acc:<11} | {name_cer:<11}")
        all_results[name] = {
            "alignment": align,
            "stats": M.stats_to_dict(stats)
        }

    print("=" * 105)
    print("✓ อัปเดต comparison.csv และ evaluation.json ให้ครบทั้ง 7 แผนเรียบร้อยแล้ว")

if __name__ == "__main__":
    main()
