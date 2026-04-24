"""
测试新版 Step3（桶+行业增强+BP claim警告）
基于 step1_v2_new.txt 运行
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
from step3.step3_service import Step3Service, simple_bucket_selector

print("加载数据...")

# BP原文
bp_path = os.path.join(PROJECT_DIR_FULL, "parsed", "bp_text.txt")
with open(bp_path, "r", encoding="utf-8") as f:
    bp_text = f.read()

# 最新Step1结果
step1_path = os.path.join(PROJECT_DIR_FULL, "step1_v2_new.txt")
with open(step1_path, "r", encoding="utf-8") as f:
    step1_result = f.read()

print(f"BP长度: {len(bp_text)} chars")
print(f"Step1长度: {len(step1_result)} chars")

# 自动选择桶
selected = simple_bucket_selector(step1_result)
print(f"\n自动选中的桶: {selected}")

# 行业
industry = "advanced_materials"

# 运行Step3
print("\n" + "=" * 60)
print("【新版 Step3 - 桶+行业增强版】")
print("=" * 60)

service = Step3Service(call_llm=call_deepseek)
result = service.run(
    step1_text=step1_result,
    bp_text=bp_text,
    industry=industry,
    selected_buckets=selected,
)

print(f"\n选中的桶: {result.selected_buckets}")
print(f"\n桶输出条数: {len(result.bucket_outputs)}")
print(f"公开可补信息条数: {len(result.publicly_resolvable)}")
print(f"仍无法确认问题条数: {len(result.still_unresolved)}")

print("\n--- 桶输出详情 ---")
for item in result.bucket_outputs:
    print(f"\n[{item.bucket_key}] {item.point}")
    print(f"  与Step1关系: {item.relation_to_step1} | 确定性: {item.certainty} | 来源: {item.source_type}")
    print(f"  解释: {item.explanation[:100]}...")

print("\n--- 仍无法确认的关键问题 ---")
for item in result.still_unresolved:
    print(f"\n[{item.bucket_key}] {item.question}")
    print(f"  影响级别: {item.impact_level} | 原因: {item.why_unresolved[:80]}...")

print("\n--- 关键张力（tensions）---")
if result.tensions:
    for t in result.tensions:
        print(f"  ⚡ {t}")
else:
    print("  （无张力输出，需检查）")

print("\n--- Step1校正提示 ---")
print(f"  支持: {result.step1_adjustment_hints.supported}")
print(f"  谨慎: {result.step1_adjustment_hints.caution}")
print(f"  带入Step4: {result.step1_adjustment_hints.to_step4}")

# 保存结果
output_json = result.model_dump_json(indent=2)
with open(os.path.join(PROJECT_DIR_FULL, "step3_v3_bucket.json"), "w", encoding="utf-8") as f:
    f.write(output_json)

print(f"\n[OK] 结构化JSON已保存: step3_v3_bucket.json ({len(output_json)} chars)")
