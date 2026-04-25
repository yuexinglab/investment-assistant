# -*- coding: utf-8 -*-
"""
测试 Step7 v2.2 - 问题对齐 & 回答质量判断（两步架构）
"""
import json
import os
import re

workspace = r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\测试科技公司_20260424_173519"

# 读取最新 Step6 输出
step6_dir = os.path.join(workspace, "step6")
step6_files = [f for f in os.listdir(step6_dir)
               if re.match(r"step6_v2_2_\d{3}\.json", f)]
step6_files.sort()
latest_step6 = os.path.join(step6_dir, step6_files[-1])
with open(latest_step6, encoding="utf-8") as f:
    step6_data = json.load(f)

new_information = step6_data.get("new_information", [])
print(f"Step6 最新版本: {step6_files[-1]}")
print(f"新增信息条数: {len(new_information)}")

# 会前问题列表（从 step4/5 推断的真实场景问题）
step4_questions = [
    "AI平台是否已形成闭环？准确率和实际应用效果如何？",
    "大客户（欧莱雅/宝洁）的粘性来源是什么？切换成本是否真的高？",
    "新能源和食品业务的收入时间表是什么？是否存在重大延期风险？",
    "并购千沐的协同效应是否真实？整合进展如何？",
    "专利保护是否真正构成竞争壁垒？与欧莱雅共有专利的范围有多大？",
]

print(f"\n会前问题数: {len(step4_questions)}")
for i, q in enumerate(step4_questions, 1):
    print(f"  Q{i}: {q[:50]}...")

print("-" * 50)

# 运行 Step7（两步架构）
from services.v2.services.step7_validator import validate, run_step7a, run_step7b, to_dict

output = validate(
    step4_questions=step4_questions,
    step6_new_information=new_information
)

result = to_dict(output)

print(f"\n会议整体评估:")
mq = result["meeting_quality"]
print(f"  规则计数: answered={mq.get('answered_count',0)} / partial={mq.get('partially_count',0)} / weak={mq.get('weak_count',0)} / missing_evidence={mq.get('missing_evidence_count',0)}")
print(f"  回答直接性: {mq['answer_directness']}")
print(f"  证据强度: {mq['evidence_strength']}")
print(f"  回避程度: {mq['evasion_level']}")
print(f"  整体可信度: {mq['overall_confidence']}")
print(f"  回避信号数: {len(mq['evasion_signals'])}")

print(f"\n问题验证 ({len(result['question_validation'])} 个):")
status_tag = {
    "answered": "[OK]",
    "partially_answered": "[~]",
    "indirectly_answered": "[~]",
    "evaded": "[X]",
    "not_answered": "[—]",
}
impact_tag = {
    "strengthens": "^",
    "slightly_strengthens": "^-",
    "weakens": "v",
    "slightly_weakens": "v-",
    "no_change": "=",
    "unclear": "?",
}
for v in result["question_validation"]:
    st = status_tag.get(v["status"], "[—]")
    im = impact_tag.get(v["impact"], "?")
    matched = ", ".join(v["matched_information_ids"]) if v["matched_information_ids"] else "—"
    print(f"\n  [{v['question_id']}] {v['original_question'][:50]}...")
    print(f"    状态: {st} {v['status']} | 质量: {v['quality']} | 影响: {im} {v['impact']}")
    print(f"    匹配: {matched}")
    if v.get("matched_information_summary"):
        for sm in v["matched_information_summary"]:
            print(f"    > {sm[:80]}...")
    print(f"    总结: {v['answer_summary'][:80]}...")
    if v.get("missing_evidence"):
        print(f"    缺失: {v['missing_evidence']}")
    if v.get("follow_up_question"):
        print(f"    追问: {v['follow_up_question'][:80]}...")

# 保存结果
step7_dir = os.path.join(workspace, "step7")
os.makedirs(step7_dir, exist_ok=True)
existing = [f for f in os.listdir(step7_dir) if re.match(r"step7_v2_2_\d{3}\.json", f)]
max_num = 0
for f in existing:
    m = re.search(r"_(\d{3})\.json", f)
    if m:
        max_num = max(max_num, int(m.group(1)))
next_ver = max_num + 1
out_path = os.path.join(step7_dir, f"step7_v2_2_{next_ver:03d}.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n已保存: {out_path}")
