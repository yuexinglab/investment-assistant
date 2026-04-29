# -*- coding: utf-8 -*-
"""
Run Step3 -> Step3B -> Step4 end-to-end, save results to project dir.
Reuse existing bp_text and step1.
"""
import sys
import os
import json

ROOT = r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant"
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from services.pipeline_v1 import (
    run_step3,
    run_step3b,
    run_step4,
    _save_step,
    _load_step_text,
)

PROJECT_DIR = os.path.join(ROOT, "workspace", "第一批测试A1_20260428_101520")
os.makedirs(PROJECT_DIR, exist_ok=True)

print("=" * 60)
print("Step3 -> Step3B -> Step4 E2E Test")
print("=" * 60)

# ── Load bp_text and step1 ──────────────────────────────────
bp_text_path = os.path.join(PROJECT_DIR, "parsed", "bp_text.txt")
if not os.path.exists(bp_text_path):
    raise FileNotFoundError("bp_text.txt not found")
with open(bp_text_path, "r", encoding="utf-8") as f:
    bp_text = f.read()
print(f"[OK] bp_text loaded ({len(bp_text)} chars)")

step1_text = _load_step_text(PROJECT_DIR, "step1", "step1.txt")
if not step1_text:
    raise FileNotFoundError("step1.txt not found")
print(f"[OK] step1 loaded ({len(step1_text)} chars)")

# ── Step3 ───────────────────────────────────────────────────
print("\n>> Running Step3 ...")
step3_json = run_step3(bp_text, step1_text)
_save_step(PROJECT_DIR, "step3", "step3.json",
           json.dumps(step3_json, ensure_ascii=False, indent=2))
print("[OK] Step3 done, saved")

has_project_structure = bool(step3_json.get("project_structure"))
print(f"    - project_structure exists: {has_project_structure}")
if has_project_structure:
    kq = step3_json["project_structure"].get("key_uncertainties", [])
    print(f"    - key_uncertainties count: {len(kq)}")

# ── Step3B ───────────────────────────────────────────────────
print("\n>> Running Step3B ...")
step3b_json = run_step3b(bp_text, step3_json)
_save_step(PROJECT_DIR, "step3b", "step3b.json",
           json.dumps(step3b_json, ensure_ascii=False, indent=2))
print("[OK] Step3B done, saved")

step3b_summary = step3b_json.get("summary", "")
print(f"    - summary: {step3b_summary[:100]}...")
checks = step3b_json.get("consistency_checks", [])
tensions = step3b_json.get("tensions", [])
packaging = step3b_json.get("overpackaging_signals", [])
print(f"    - consistency_checks: {len(checks)} items")
print(f"    - tensions: {len(tensions)} items")
print(f"    - overpackaging_signals: {len(packaging)} items")

# ── Step4 ───────────────────────────────────────────────────
print("\n>> Running Step4 ...")
step4_result = run_step4(bp_text, step1_text, step3_json, step3b_json=step3b_json)
_save_step(PROJECT_DIR, "step4", "step4_meeting_brief.md", step4_result.get("meeting_brief_md", ""))
_save_step(PROJECT_DIR, "step4", "step4_internal.json",
           json.dumps(step4_result.get("internal", {}), ensure_ascii=False, indent=2))
_save_step(PROJECT_DIR, "step4", "step4_scan_questions.json",
           json.dumps(step4_result.get("scan_questions", {}), ensure_ascii=False, indent=2))
print("[OK] Step4 done, saved")

# ── Verify Step3B gap integration ───────────────────────────
internal = step4_result.get("internal", {})
gaps = internal.get("gaps", [])
print("\n>> Verifying Step3B -> Step4 gap integration:")
print(f"    - total gaps: {len(gaps)}")

if gaps:
    print("\n    Gap source distribution:")
    source_count = {}
    for g in gaps:
        src = g.get("source", "unknown")
        source_count[src] = source_count.get(src, 0) + 1
    for src, cnt in source_count.items():
        print(f"      {src}: {cnt} items")
    print("\n    Gap details (first 5):")
    for i, g in enumerate(gaps[:5], 1):
        src = g.get("source", "unknown")
        issue = g.get("issue", g.get("description", ""))[:60]
        print(f"      [{i}] [{src}] {issue}")
else:
    print("    WARNING: No gaps found - Step3B may not be flowing into Step4 correctly")

print("\n" + "=" * 60)
print("ALL DONE. Output files in:")
print(f"  {PROJECT_DIR}")
print("=" * 60)
