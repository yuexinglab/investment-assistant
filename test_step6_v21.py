# -*- coding: utf-8 -*-
"""
测试 Step6 v2.2 - 新增信息提取（v2.2: transcript_noise + info_type规则收紧）
"""
import json
import os

# 读取测试数据
workspace = r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\测试科技公司_20260424_173519"

# 读取 Step5 摘要
step5_dir = os.path.join(workspace, "step5")
step5_files = [f for f in os.listdir(step5_dir) if f.endswith(".json")]
step5_file = os.path.join(step5_dir, step5_files[0])
with open(step5_file, encoding="utf-8") as f:
    step5_data = json.load(f)
step5_summary = step5_data.get("summary", str(step5_data)[:3000])

# 读取会议记录
meeting_file = os.path.join(workspace, "v2_context", "meeting_record.txt")
with open(meeting_file, encoding="utf-8") as f:
    meeting_record = f.read()

print(f"Step5 摘要长度: {len(step5_summary)}")
print(f"会议记录长度: {len(meeting_record)}")
print("-" * 40)

# 运行 Step6
from services.v2.services.step6_extractor import extract, to_dict

output = extract(step5_summary=step5_summary, meeting_record=meeting_record)

print(f"meeting_summary: {output.meeting_summary}")
print(f"提取条数: {len(output.new_information)}")
print("-" * 40)

# 检查 v2.2 新字段
for ni in output.new_information:
    print(f"[{ni.id}] {ni.content[:50]}...")
    print(f"  info_type={ni.info_type} | novelty_type={ni.novelty_type} | confidence={ni.confidence}")
    print(f"  affects={ni.affects_judgement}")
    print(f"  related_prior={ni.related_prior_judgement[:40]}..." if ni.related_prior_judgement else "  related_prior=（空）")
    print(f"  follow_up={ni.follow_up_hint[:40]}..." if ni.follow_up_hint else "  follow_up=（空）")
    print(f"  transcript_noise={ni.transcript_noise} | contradicts_bp={ni.contradicts_bp} | is_critical={ni.is_critical}")
    print()

# 统计 info_type 分布
from collections import Counter
info_types = [ni.info_type for ni in output.new_information]
print(f"info_type 分布: {dict(Counter(info_types))}")

# 检查 transcript_noise 字段存在且为 bool
noise_items = [ni for ni in output.new_information if ni.transcript_noise]
print(f"含 transcript_noise=True 的条数: {len(noise_items)}")

# 检查 related_prior 不为空且不是"硬凑"
hard_match = [ni for ni in output.new_information if ni.related_prior_judgement and "未匹配" not in ni.related_prior_judgement]
print(f"匹配到会前判断的条数: {len(hard_match)}")

# 保存结果（版本号文件）
out_dir = os.path.join(workspace, "step6")
os.makedirs(out_dir, exist_ok=True)
# 找最大版本号
import re
existing = [f for f in os.listdir(out_dir) if re.match(r"step6_v2_2_\d{3}\.json", f)]
max_num = 0
for f in existing:
    m = re.search(r"_(\d{3})\.json", f)
    if m:
        max_num = max(max_num, int(m.group(1)))
next_ver = max_num + 1
out_path = os.path.join(out_dir, f"step6_v2_2_{next_ver:03d}.json")
result = to_dict(output)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"已保存: {out_path}")
