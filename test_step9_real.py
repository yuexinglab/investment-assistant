# -*- coding: utf-8 -*-
"""
Step9 v2 真实数据测试
"""
import sys
import os
import json

# 添加项目根路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.v2.services.step9_decider import decide, to_dict
from services.v2.schemas import DecisionType, ConfidenceLevel

# 读取真实 Step8 数据
step8_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "workspace", "测试科技公司_20260424_173519", "step8", "step8_v2_2_005.json"
)

print(f"Reading Step8 data: {step8_path}")
print("=" * 60)

with open(step8_path, "r", encoding="utf-8") as f:
    step8_data = json.load(f)

# 运行 Step9
print("\n>>> Running Step9 v2 rule-based decision...")
output = decide(step8_updates=step8_data, model="deepseek-chat")
result = to_dict(output)

print("\n" + "=" * 60)
print("Step9 v2 Decision Result")
print("=" * 60)

# 打印结果
print(f"\n[Decision] {result['overall_decision']['decision']}")
print(f"[Confidence] {result['overall_decision']['confidence']}")
print(f"[One-line] {result['overall_decision']['one_line_conclusion']}")

print("\n--- Decision Breakdown ---")
print(f"Positives ({len(result['decision_breakdown']['positives'])}):")
for p in result['decision_breakdown']['positives']:
    print(f"   + {p}")

print(f"\nNegatives ({len(result['decision_breakdown']['negatives'])}):")
for n in result['decision_breakdown']['negatives']:
    print(f"   - {n}")

print(f"\nUncertainties ({len(result['decision_breakdown']['uncertainties'])}):")
for u in result['decision_breakdown']['uncertainties']:
    print(f"   ? {u}")

print("\n--- Action Plan ---")
for i, a in enumerate(result['action_plan'], 1):
    print(f"{i}. [{a['priority'].upper()}] {a['action']}")
    print(f"   Reason: {a['reason']}")
    if a['linked_risk']:
        print(f"   Linked Risk: {a['linked_risk']}")

print("\n--- Key Risks ---")
for r in result['key_risks']:
    print(f"* {r}")

print("\n--- Go/No-Go Logic ---")
print(result['go_no_go_logic'])

# 保存结果
output_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "workspace", "测试科技公司_20260424_173519", "step9", "step9_v2_001.json"
)
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n[OK] Result saved: {output_path}")
