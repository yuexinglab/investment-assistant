"""
测试 Step4 v3（双输出：internal_json + meeting_brief_md）
基于 step1_v2_new.txt + step3_v3_bucket.json 运行
"""
import os
import sys
import io

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
print("【Step4 v3 - 双输出版】")
print("=" * 60)

service = Step4Service(call_llm=call_deepseek)
result = service.run(
    step1_text=step1_result,
    step3_json=step3_json,
    bp_text=bp_text,
)

# Part 1: internal_json
internal = result["internal_json"]
print(f"\n【Part 1 - 内部JSON】")
print(f"总缺口数: {internal.total_gaps}")
print(f"会议策略: {internal.meeting_strategy}")
print(f"总结: {internal.summary}")
print(f"决策缺口: {len(internal.decision_gaps)}个")

for gap in internal.decision_gaps:
    print(f"\n  [{gap.gap_id}] {gap.core_issue} | {gap.priority}")

# Part 2: meeting_brief_md
meeting_brief = result["meeting_brief_md"]
print(f"\n【Part 2 - 会议提纲 Markdown】")
print("=" * 60)
print(meeting_brief)

# 保存结果
import json

# 保存 internal_json
internal_output = internal.model_dump_json(indent=2)
with open(os.path.join(PROJECT_DIR_FULL, "step4_v3_internal.json"), "w", encoding="utf-8") as f:
    f.write(internal_output)

# 保存 meeting_brief
with open(os.path.join(PROJECT_DIR_FULL, "step4_v3_meeting_brief.md"), "w", encoding="utf-8") as f:
    f.write(meeting_brief)

print(f"\n[OK] 已保存:")
print(f"  - step4_v3_internal.json ({len(internal_output)} chars)")
print(f"  - step4_v3_meeting_brief.md ({len(meeting_brief)} chars)")
