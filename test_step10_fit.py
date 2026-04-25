# -*- coding: utf-8 -*-
"""
test_step10_fit.py — Step10 Fit 判断测试

测试杉海创新项目在政府基金画像下的 Fit 判断。
"""
import sys
import os
import json

# 添加项目根路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.v2.pipeline import PipelineV2

# 项目路径
project_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "workspace", "测试科技公司_20260424_173519"
)

# 读取 Step9 结果
step9_path = os.path.join(project_dir, "step9", "step9_latest.json")
if not os.path.exists(step9_path):
    step9_path = os.path.join(project_dir, "step9", "step9_v3_001.json")

with open(step9_path, "r", encoding="utf-8") as f:
    step9 = json.load(f)

print("=" * 60)
print("Step10 Fit 判断测试")
print("=" * 60)

print(f"\nStep9 读取成功:")
print(f"  流程决策: {step9.get('overall_decision', {}).get('process_decision', '')}")
print(f"  投资决策: {step9.get('overall_decision', {}).get('investment_decision', '')}")
print(f"  一句话结论: {step9.get('overall_decision', {}).get('one_line_conclusion', '')}")

# 创建 Pipeline
pipeline = PipelineV2(
    project_id="test_shanhai",
    project_name="测试科技公司_20260424_173519",
    workspace_dir=project_dir
)

# Step0: 加载政府基金画像
print("\n>>> Step0: 加载基金画像...")
step0 = pipeline.run_step0(profile_id="government_fund")
print(f"画像: {step0.get('name', '')}")
print(f"硬约束数量: {len(step0.get('hard_constraints', []))}")
print(f"偏好数量: {len(step0.get('preferences', []))}")
print(f"回避项数量: {len(step0.get('avoid', []))}")

# Step10: Fit 判断
print("\n>>> Step10: Fit 判断...")
user_feedback = """
项目方明确表示不愿意在本地落地，也不接受反投要求。
业务模式偏定制化，产量不是主要驱动因素。
新能源业务虽有布局，但尚无收入和订单验证。
"""

# 设置模型
pipeline.model = "deepseek-chat"

step10 = pipeline.run_step10(
    step9_output=step9,
    profile_id="government_fund",
    user_feedback=user_feedback
)

print("\n" + "=" * 60)
print("Step10 Fit 判断结果")
print("=" * 60)

fit_decision = step10.get("fit_decision", "")
final_rec = step10.get("final_recommendation", "")
fit_score = step10.get("fit_score", 0)

fit_display = {
    "fit": "[FIT] 高度匹配",
    "partial_fit": "[PARTIAL] 部分匹配",
    "not_fit": "[NOT FIT] 不匹配"
}
rec_display = {
    "continue": "[CONTINUE] 继续推进",
    "request_materials": "[REQUEST] 补充材料",
    "pass": "[PASS] 放弃"
}

print(f"\n[Fit Decision] {fit_display.get(fit_decision, fit_decision)}")
print(f"[Final Recommendation] {rec_display.get(final_rec, final_rec)}")
print(f"[Fit Score] {fit_score}/100")

# 匹配约束
print("\n--- Matched Constraints ---")
for m in step10.get("matched_constraints", []):
    print(f"  [✓] {m.get('constraint', '')}")
    print(f"      证据: {m.get('evidence', '')[:50]}...")

# 不匹配约束
print("\n--- Mismatched Constraints ---")
for m in step10.get("mismatched_constraints", []):
    severity = m.get("severity", "medium")
    sev_icon = "[HIGH]" if severity == "high" else "[MED]" if severity == "medium" else "[LOW]"
    print(f"  {sev_icon} {m.get('constraint', '')}")
    print(f"      证据: {m.get('evidence', '')[:50]}...")
    print(f"      严重度: {severity}")

# 决策推理
print("\n--- Reasoning ---")
print(step10.get("reasoning", ""))

# 候选沉淀
print("\n--- Candidate Profile Updates ---")
for u in step10.get("candidate_profile_updates", []):
    print(f"  规则: {u.get('candidate_rule', '')}")
    print(f"  证据: {u.get('evidence', '')[:50]}...")

print("\n--- Candidate Case Record ---")
case = step10.get("candidate_case_record", {})
print(f"  项目: {case.get('project_name', '')}")
print(f"  Fit判断: {case.get('fit_judgement', '')}")
print(f"  最终决策: {case.get('final_decision', '')}")
print(f"  原因: {case.get('fit_reason', [])}")

print("\n" + "=" * 60)
print("结果已保存到:")
print(f"  - {project_dir}/step0/step0.json")
print(f"  - {project_dir}/step10/step10.json")
print(f"  - knowledge_base/candidates/fit_feedback_candidates.json")
print("=" * 60)
