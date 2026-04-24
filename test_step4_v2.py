"""
测试 Step4 v2（决策缺口层 - 新版内部决策+会议提问）
基于 step1_v2_new.txt + step3_v3_bucket.json 运行
"""
import os
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_DIR = r"D:\复旦文件\Semester3-4\搞事情\论文产品化\投资助手"
PROJECT_NAME = "杉海创新科技6_20260422_162546"
PROJECT_DIR_FULL = os.path.join(PROJECT_DIR, "workspace", PROJECT_NAME)

sys.path.insert(0, PROJECT_DIR)
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from services.deepseek_service import call_deepseek
from step4.step4_service import Step4Service

print("加载数据...")

# BP原文
bp_path = os.path.join(PROJECT_DIR_FULL, "parsed", "bp_text.txt")
with open(bp_path, "r", encoding="utf-8") as f:
    bp_text = f.read()

# 最新Step1结果
step1_path = os.path.join(PROJECT_DIR_FULL, "step1_v2_new.txt")
with open(step1_path, "r", encoding="utf-8") as f:
    step1_result = f.read()

# Step3结果（JSON格式）
step3_path = os.path.join(PROJECT_DIR_FULL, "step3_v3_bucket.json")
with open(step3_path, "r", encoding="utf-8") as f:
    step3_json = f.read()

print(f"BP长度: {len(bp_text)} chars")
print(f"Step1长度: {len(step1_result)} chars")
print(f"Step3 JSON长度: {len(step3_json)} chars")

print("\n" + "=" * 60)
print("【Step4 v2 - 决策缺口层】")
print("=" * 60)

service = Step4Service(call_llm=call_deepseek)
result = service.run(
    step1_text=step1_result,
    step3_json=step3_json,
    bp_text=bp_text,
)

print(f"\n总缺口数: {result.total_gaps}")
print(f"会议策略: {result.meeting_strategy}")
print(f"总结: {result.summary}")

print("\n" + "=" * 60)
print("【决策缺口详情】")
print("=" * 60)

for gap in result.decision_gaps:
    print(f"\n{'='*50}")
    print(f"[{gap.gap_id}] {gap.core_issue}")
    print(f"  优先级: {gap.priority} | 来源: {gap.from_bucket}")
    print(f"  为什么重要: {gap.why_it_matters}")
    print(f"  内部目标: {gap.internal_goal}")
    print(f"  决策影响:")
    print(f"    ✅ 正面: {gap.decision_impact.positive}")
    print(f"    ❌ 负面: {gap.decision_impact.negative}")
    print(f"  决策规则:")
    print(f"    → go_if: {gap.decision_rule.go_if}")
    print(f"    → no_go_if: {gap.decision_rule.no_go_if}")
    print(f"    → next_action: {gap.decision_rule.next_action}")
    print(f"  会议问题 ({len(gap.meeting_questions)}个):")
    for q in gap.meeting_questions:
        stage_icon = {"opening": "🔓", "middle": "🔍", "late": "🔐"}.get(q.ask_stage, "•")
        sens_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(q.sensitivity, "•")
        print(f"    {stage_icon}{sens_icon} [{q.ask_stage}] {q.question}")
        print(f"         意图: {q.intent}")
        print(f"         类型: {q.question_type} | 措辞: {q.why_this_wording}")
        print(f"         正面追问: {q.follow_up_if_positive}")
        print(f"         负面追问: {q.follow_up_if_negative}")

# 保存结果
output_json = result.model_dump_json(indent=2)
with open(os.path.join(PROJECT_DIR_FULL, "step4_v2_decision_gaps.json"), "w", encoding="utf-8") as f:
    f.write(output_json)

print(f"\n[OK] 结构化JSON已保存: step4_v2_decision_gaps.json ({len(output_json)} chars)")
