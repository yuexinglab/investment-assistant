# -*- coding: utf-8 -*-
"""测试新 Step5：决策收敛版本"""
import sys
import os
import json

ROOT = r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant"
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from services.deepseek_service import call_deepseek
from step5.step5_service import run_step5
from services.pipeline_v1 import _load_step_text, _load_step_json, _save_step

PROJECT_DIR = os.path.join(ROOT, "workspace", "第一批测试A1_20260428_101520")

print("=" * 60)
print("Step5 New Schema Test")
print("=" * 60)

# Load all inputs
bp_text_path = os.path.join(PROJECT_DIR, "parsed", "bp_text.txt")
with open(bp_text_path, "r", encoding="utf-8") as f:
    bp_text = f.read()
print(f"[OK] bp_text loaded ({len(bp_text)} chars)")

step1_text = _load_step_text(PROJECT_DIR, "step1", "step1.txt")
step3_json = _load_step_json(PROJECT_DIR, "step3", "step3.json")
step3b_json = _load_step_json(PROJECT_DIR, "step3b", "step3b.json")
step4_internal = _load_step_json(PROJECT_DIR, "step4", "step4_internal.json")
step4_brief = _load_step_text(PROJECT_DIR, "step4", "step4_meeting_brief.md")

if not step3b_json:
    print("[ERROR] step3b.json not found - run Step3B first")
    sys.exit(1)

print(f"[OK] step1: {len(step1_text)} chars")
print(f"[OK] step3: {len(str(step3_json))} chars")
print(f"[OK] step3b: {len(str(step3b_json))} chars")
print(f"[OK] step4_internal: {len(str(step4_internal))} chars")

# Build step4_output (full)
step4_output = {
    "internal_json": step4_internal,
    "meeting_brief_md": step4_brief,
}

# Run Step5
print("\n>> Running Step5 (new schema) ...")
result = run_step5(
    step1_text=step1_text,
    step3_json=step3_json,
    step3b_json=step3b_json,
    step4_output=step4_output,
    call_llm=call_deepseek,
)

# Save
_save_step(PROJECT_DIR, "step5", "step5_output.json",
           json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
_save_step(PROJECT_DIR, "step5", "step5_decision.md", result.to_markdown())
print("[OK] Step5 output saved")

# Print key fields
print("\n>> Core Judgement:")
j = result.core_judgement
print(f"    decision: {j.decision}")
print(f"    confidence: {j.confidence}")
print(f"    one_liner: {j.one_liner}")

print("\n>> Reasons to meet:")
for r in result.reasons_to_meet:
    print(f"    - {r.point}")

print("\n>> Reasons to pass:")
for r in result.reasons_to_pass:
    print(f"    - {r.point}")

print("\n>> Must-ask questions:")
for i, q in enumerate(result.must_ask_questions, 1):
    print(f"    [{i}] {q.question}")
    print(f"        purpose: {q.purpose}")

print("\n>> Investment logic:")
il = result.investment_logic
print(f"    primary: {il.primary_type}")
print(f"    secondary: {il.secondary_types}")
print(f"    risk_type: {il.risk_type}")

print("\n" + "=" * 60)
print("DONE. Check step5/step5_output.json and step5_decision.md")
print("=" * 60)
