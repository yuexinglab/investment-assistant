# -*- coding: utf-8 -*-
"""
测试 Step8 v2.2.1 - 规则驱动认知更新

不读 Step6，只看 Step5 + Step7。
"""
import json
import os
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

workspace = r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\测试科技公司_20260424_173519"

# ============================================================
# 1. 读取 Step7 最新结果 + Step6 new_information（用于 info_type 查询）
# ============================================================
step7_dir = os.path.join(workspace, "step7")
step7_files = [f for f in os.listdir(step7_dir)
               if re.match(r"step7_v2_2_\d{3}\.json", f)]
step7_files.sort()
latest_step7 = os.path.join(step7_dir, step7_files[-1])
with open(latest_step7, encoding="utf-8") as f:
    step7_result = json.load(f)
print(f"Step7 最新版本: {step7_files[-1]}")
print(f"问题验证数: {len(step7_result['question_validation'])}")

# 注入 Step6 new_information（v2.2.2 规则引擎需要查 info_type）
step6_dir = os.path.join(workspace, "step6")
step6_files = [f for f in os.listdir(step6_dir)
               if re.match(r"step6_v2_2_\d{3}\.json", f)]
step6_files.sort()
latest_step6 = os.path.join(step6_dir, step6_files[-1])
with open(latest_step6, encoding="utf-8") as f:
    step6_data = json.load(f)
step7_result["_step6_new_information"] = step6_data.get("new_information", [])
print(f"Step6 最新版本: {step6_files[-1]}（已注入 info_type）")

# ============================================================
# 2. 构造 Step5 假设（带 hypothesis_id）
# ============================================================
step5_judgements = [
    {
        "hypothesis_id": "h_001",
        "hypothesis": "AI平台可能构成技术壁垒",
        "view": "AI平台已具备数据飞轮效应，准确率超80%，可显著降低客户研发成本"
    },
    {
        "hypothesis_id": "h_002",
        "hypothesis": "大客户（欧莱雅/宝洁）粘性高，切换成本大",
        "view": "欧莱雅是股东，双方利益深度绑定；宝洁已完成多期合作，切换成本高"
    },
    {
        "hypothesis_id": "h_003",
        "hypothesis": "新能源和食品业务有明确的收入时间表",
        "view": "新能源2025年有收入，食品2025年下半年开始批量出货"
    },
    {
        "hypothesis_id": "h_004",
        "hypothesis": "并购千沐有真实协同效应",
        "view": "并购后可共享研发中台，实现跨行业技术复用"
    },
    {
        "hypothesis_id": "h_005",
        "hypothesis": "专利保护构成有效竞争壁垒",
        "view": "分子结构专利保护力度强，超分子领域无直接竞争对手"
    },
]

print(f"\nStep5 假设数: {len(step5_judgements)}")
for h in step5_judgements:
    print(f"  [{h['hypothesis_id']}] {h['hypothesis'][:40]}...")

print("-" * 60)

# ============================================================
# 3. 运行 Step8（规则驱动）
# ============================================================
from services.v2.services.step8_updater import update, to_dict

output = update(
    step5_judgements=step5_judgements,
    step7_result=step7_result
)

result = to_dict(output)

# ============================================================
# 4. 打印结果
# ============================================================
print(f"\n整体判断变化: {'[YES]' if result['overall_change']['is_judgement_significantly_changed'] else '[NO]'}")

overall = result["overall_change"]
if overall.get("new_risks"):
    print(f"新增风险 ({len(overall['new_risks'])} 条):")
    for r in overall["new_risks"]:
        sev = r.get("severity", "medium")
        tag = "[HIGH]" if sev == "high" else "[MED]"
        print(f"  {tag} [{r['source_question_id']}] {r['risk'][:60]}...")

print(f"\n认知更新 ({len(result['hypothesis_updates'])} 条):")
change_tag = {
    "reinforced":         "[+] reinforced",
    "slightly_reinforced": "[+] slightly_reinforced",
    "weakened":           "[-] weakened",
    "slightly_weakened":  "[-] slightly_weakened",
    "overturned":         "[X] overturned",
    "reframed":           "[~] reframed",
    "uncertain":          "[?] uncertain",
}
for h in result["hypothesis_updates"]:
    ct = change_tag.get(h["change_type"], h["change_type"])
    conf = h.get("confidence_change", "")
    print(f"\n  [{h['hypothesis_id']}] {h['hypothesis'][:40]}...")
    print(f"    变化: {ct} | 信心: {conf}")
    if h.get("source_question_id"):
        print(f"    来源: {h['source_question_id']}")
    if h.get("updated_view"):
        print(f"    更新后: {h['updated_view'][:80]}...")
    if h.get("why_changed"):
        print(f"    原因: {h['why_changed'][:80]}...")
    if h.get("supporting_evidence"):
        print(f"    支持: {', '.join(h['supporting_evidence'])}")
    if h.get("contradicting_evidence"):
        print(f"    反对: {', '.join(h['contradicting_evidence'])}")

if result.get("unchanged_hypotheses"):
    print(f"\n未变化假设 ({len(result['unchanged_hypotheses'])} 条):")
    for u in result["unchanged_hypotheses"]:
        print(f"  [--] {u}")

# ============================================================
# 5. 保存结果
# ============================================================
step8_dir = os.path.join(workspace, "step8")
os.makedirs(step8_dir, exist_ok=True)
existing = [f for f in os.listdir(step8_dir) if re.match(r"step8_v2_2_\d{3}\.json", f)]
max_num = 0
for f in existing:
    m = re.search(r"_(\d{3})\.json", f)
    if m:
        max_num = max(max_num, int(m.group(1)))
next_ver = max_num + 1
out_path = os.path.join(step8_dir, f"step8_v2_2_{next_ver:03d}.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n已保存: {out_path}")
