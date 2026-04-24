"""
测试 Step4（决策缺口层）
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
print("【Step4 - 决策缺口层】")
print("=" * 60)

service = Step4Service(call_llm=call_deepseek)
result = service.run(
    step1_text=step1_result,
    step3_json=step3_json,
    bp_text=bp_text,
)

print(f"\n决策缺口数量: {result.total_gaps}")
print(f"总结: {result.summary}")

for gap in result.decision_gaps:
    print(f"\n{'='*50}")
    print(f"[{gap.gap_id}] {gap.core_issue}")
    print(f"  来源: {gap.from_bucket}")
    print(f"  重要性: {gap.why_it_matters}")
    print(f"  决策分叉:")
    print(f"    ✅ {gap.decision_impact.positive}")
    print(f"    ❌ {gap.decision_impact.negative}")
    print(f"  问题设计:")
    for q in gap.question_design:
        type_icon = {"fact": "📋", "counterfactual": "🔄", "path": "🛤️"}.get(q.question_type, "•")
        print(f"    {type_icon} [{q.question_type}] {q.question}")
        print(f"        意图: {q.intent}")

# 保存结果
output_json = result.model_dump_json(indent=2)
with open(os.path.join(PROJECT_DIR_FULL, "step4_decision_gaps.json"), "w", encoding="utf-8") as f:
    f.write(output_json)

print(f"\n[OK] 结构化JSON已保存: step4_decision_gaps.json ({len(output_json)} chars)")
