# -*- coding: utf-8 -*-
"""
test_step9_v3.py — Step9 v3 双层决策真实数据测试
"""
import sys
import os
import json

# 添加项目根路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.v2.services.step9_decider import decide

# 读取真实数据
project_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "workspace", "测试科技公司_20260424_173519"
)

# 读取 step6, step7, step8 (使用最新版本)
with open(os.path.join(project_dir, "step6", "step6_v2_2_003.json"), "r", encoding="utf-8") as f:
    step6 = json.load(f)

with open(os.path.join(project_dir, "step7", "step7_v2_2_003.json"), "r", encoding="utf-8") as f:
    step7 = json.load(f)

with open(os.path.join(project_dir, "step8", "step8_v2_2_005.json"), "r", encoding="utf-8") as f:
    step8 = json.load(f)

print("=" * 60)
print("Step9 v3 双层决策测试")
print("=" * 60)
print(f"\nStep6: {len(step6.get('new_information', []))} 条新增信息")
print(f"Step7: {len(step7.get('question_validation', []))} 个问题验证")
print(f"Step8: {len(step8.get('hypothesis_updates', []))} 个假设更新")

# 运行 Step9 v3
print("\n>>> Running Step9 v3...")
result = decide(step6=step6, step7=step7, step8=step8, model="deepseek-chat")

print("\n" + "=" * 60)
print("Step9 v3 结果")
print("=" * 60)

# 双层决策
overall = result.get("overall_decision", {})
process_dec = overall.get("process_decision", "")
invest_dec = overall.get("investment_decision", "")
confidence = overall.get("confidence", "")
one_line = overall.get("one_line_conclusion", "")

process_display = {
    "continue_dd": "[Continue] 继续尽调",
    "request_materials": "[Request] 补充材料",
    "pause": "[Pause] 暂缓",
    "stop": "[Stop] 停止"
}
invest_display = {
    "invest_ready": "[Ready] 可投资",
    "not_ready": "[Not Ready] 待验证",
    "reject": "[Reject] 不投资"
}

print(f"\n[Process Decision] {process_display.get(process_dec, process_dec)}")
print(f"[Investment Decision] {invest_display.get(invest_dec, invest_dec)}")
print(f"[Confidence] {confidence}")
print(f"[One-line] {one_line}")

# 四象限分解
breakdown = result.get("decision_breakdown", {})
print("\n--- Decision Breakdown ---")

print(f"\n[Verified Positives] ({len(breakdown.get('verified_positives', []))}):")
for p in breakdown.get("verified_positives", []):
    print(f"  + {p}")

print(f"\n[Unverified Positives] ({len(breakdown.get('unverified_positives', []))}):")
for p in breakdown.get("unverified_positives", []):
    print(f"  ? {p}")

print(f"\n[Confirmed Negatives] ({len(breakdown.get('confirmed_negatives', []))}):")
for n in breakdown.get("confirmed_negatives", []):
    print(f"  - {n}")

print(f"\n[Key Uncertainties] ({len(breakdown.get('key_uncertainties', []))}):")
for u in breakdown.get("key_uncertainties", []):
    print(f"  ! {u}")

# 材料请求
print("\n--- Material Requests ---")
for i, req in enumerate(result.get("material_request_list", []), 1):
    print(f"{i}. [{req['priority'].upper()}] {req['material']}")
    print(f"   Purpose: {req['purpose']}")

# 下一步行动
print("\n--- Next Actions ---")
for i, action in enumerate(result.get("next_actions", []), 1):
    print(f"{i}. [{action['priority'].upper()}] {action['action']} ({action['who']})")

# 关键风险
print("\n--- Key Risks ---")
for r in result.get("key_risks", []):
    print(f"* {r}")

# 决策逻辑
print("\n--- Go/No-Go Logic ---")
print(result.get("go_no_go_logic", ""))

# 保存结果
output_dir = os.path.join(project_dir, "step9")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "step9_v3_001.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n[OK] Result saved: {output_path}")
