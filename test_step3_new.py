"""
快速测试 Step3 新 prompt 是否生效
验证 3 个修改点：
1. relation_to_step1 改为 aligned/caution/gap（无 support/contradict）
2. 必须输出"该公司当前最可能属于哪一类公司"
3. 行业分析绑定到公司（无泛泛而谈）
"""
import sys
import os
import json

# 确保项目根目录在 sys.path
sys.path.insert(0, r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant")

from step3.step3_service import Step3Service, simple_bucket_selector
from step3.project_structure_detector import detect_project_structure
from services.deepseek_service import call_deepseek  # 使用真实 LLM 调用

# 测试项目路径
WORKSPACE = r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace"
PROJECT_ID = "B1_1_0回归测试1_20260504_213218"

step1_path = os.path.join(WORKSPACE, PROJECT_ID, "step1", "step1.txt")
bp_path = os.path.join(WORKSPACE, PROJECT_ID, "materials", "bp_213218.pdf")

print("=" * 60)
print("Step3 新 Prompt 测试")
print("=" * 60)

# 读取 Step1 文本
with open(step1_path, "r", encoding="utf-8") as f:
    step1_text = f.read()

# 读取 BP 文本（用 pdfplumber 简单提取）
import pdfplumber
with pdfplumber.open(bp_path) as pdf:
    bp_text = "\n".join(page.extract_text() or "" for page in pdf.pages[:10])

print(f"\n[Step1 长度]: {len(step1_text)} 字符")
print(f"[BP 文本长度]: {len(bp_text)} 字符")

# 检测 project_structure
print("\n[检测 project_structure...]")
project_structure = detect_project_structure(step1_text, bp_text)
print(f"project_type: {project_structure.get('project_type')}")
print(f"buckets: {project_structure.get('buckets')}")

# 自动选择 buckets
selected_buckets = simple_bucket_selector(step1_text)
print(f"selected_buckets (auto): {selected_buckets}")

# 准备 LLM 调用函数
def call_llm(system: str, user: str) -> str:
    """调用 DeepSeek API"""
    print("\n[调用 DeepSeek API...]")
    return call_deepseek(system, user)

# 运行 Step3
print("\n" + "=" * 60)
print("运行 Step3（使用新 Prompt）...")
print("=" * 60)

service = Step3Service(call_llm=call_llm)
result = service.run(
    step1_text=step1_text,
    bp_text=bp_text,
    industry="新能源汽车",
    selected_buckets=selected_buckets,
    project_structure=project_structure,
)

# 保存结果
output_path = os.path.join(WORKSPACE, PROJECT_ID, "step3_new_test.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✅ Step3 结果已保存至: {output_path}")

# ── 验收检查 ──
print("\n" + "=" * 60)
print("验收检查（3 个修改点）")
print("=" * 60)

bucket_outputs = result.get("bucket_outputs", [])
still_unresolved = result.get("still_unresolved", [])
tensions = result.get("tensions", [])
adjustment_hints = result.get("step1_adjustment_hints", {})

# 检查 1：relation_to_step1 不包含 support/contradict
print("\n【检查 1】relation_to_step1 是否去掉对抗语义")
has_old_semantics = False
for item in bucket_outputs:
    v = item.get("relation_to_step1", "")
    if v in ("support", "contradict"):
        has_old_semantics = True
        print(f"  ❌ 发现旧值: {v} in {item.get('bucket_key')}")
if not has_old_semantics:
    new_vals = set(item.get("relation_to_step1", "") for item in bucket_outputs)
    print(f"  ✅ 无 support/contradict，当前值: {new_vals}")

# 检查 2：是否输出公司类型判断
print("\n【检查 2】是否输出公司类型判断（材料/设备/整机/项目制/平台/服务）")
company_type_found = False
check_texts = []

# 检查 tensions
for t in tensions:
    check_texts.append(("tensions", t))

# 检查 to_step4
for q in adjustment_hints.get("to_step4", []):
    check_texts.append(("to_step4", str(q)))

# 检查 still_unresolved
for q in still_unresolved:
    check_texts.append(("still_unresolved", q.get("question", "")))

type_keywords = ["材料", "设备", "整机", "项目制", "平台", "服务"]
for source, text in check_texts:
    for kw in type_keywords:
        if kw in str(text):
            print(f"  ✅ 在 {source} 中找到公司类型关键词: {kw}")
            print(f"     内容: {str(text)[:120]}...")
            company_type_found = True
            break

if not company_type_found:
    print("  ⚠️  未明确找到公司类型判断，需人工检查输出")
    print("     建议检查 tensions / to_step4 / still_unresolved 字段")

# 检查 3：行业分析是否绑定公司
print("\n【检查 3】行业分析是否绑定到公司（无泛泛而谈）")
unbound_count = 0
for item in bucket_outputs:
    exp = item.get("explanation", "")
    # 简单检查：是否包含公司相关词
    if "公司" not in exp and "该企业" not in exp and "项目" not in exp and "其" not in exp:
        unbound_count += 1

if unbound_count == 0:
    print("  ✅ 所有 bucket_outputs 的 explanation 都绑定到公司")
else:
    print(f"  ⚠️  有 {unbound_count}/{len(bucket_outputs)} 个 bucket_outputs 可能未绑定公司")

# 打印摘要
print("\n" + "=" * 60)
print("Step3 输出摘要")
print("=" * 60)
print(f"selected_buckets: {result.get('selected_buckets')}")
print(f"bucket_outputs 数量: {len(bucket_outputs)}")
print(f"still_unresolved 数量: {len(still_unresolved)}")
print(f"\ntensions:")
for t in tensions:
    print(f"  - {t[:100]}")
print(f"\nstep1_adjustment_hints:")
print(f"  supported: {adjustment_hints.get('supported')}")
print(f"  caution: {adjustment_hints.get('caution')}")
print(f"  to_step4: {json.dumps(adjustment_hints.get('to_step4'), ensure_ascii=False)[:200]}")

print("\n测试完成！请人工检查输出文件确认效果。")
