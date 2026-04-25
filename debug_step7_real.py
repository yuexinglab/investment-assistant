#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟 app.py 中的 Step7 调用
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json

# 加载 step6 数据
step6_path = r"C:\Users\86136\Downloads\step6_latest (4).json"
with open(step6_path, "r", encoding="utf-8") as f:
    step6 = json.load(f)

print(f"Step6 new_information 数量: {len(step6.get('new_information', []))}")

# 模拟 step4_questions（字符串列表格式）
# 这是 _load_step4_questions 返回的格式
step4_questions = [
    "美妆业务的收入规模是多少？",
    "大客户有哪些？粘性如何？",
    "食品业务放量时间表是否可信？",
    "新能源业务收入时间表是什么？",
    "AI平台的准确率和使用场景？",
    "韶关工厂产能利用率如何？",
    "毛利率水平是多少？",
    "并购千沐的协同效应是否真实？",
    "诺奖实验室的具体情况？",
    "竞争对手情况？",
]

print(f"step4_questions 数量: {len(step4_questions)}")
print(f"step4_questions 类型: {type(step4_questions)}")

# 测试 PipelineV2.run_step7
print("\n" + "="*50)
print("测试 PipelineV2.run_step7...")
print("="*50)

from services.v2 import PipelineV2

# 创建临时测试目录
test_project_dir = os.path.join(os.path.dirname(__file__), "temp_test_v2")
os.makedirs(test_project_dir, exist_ok=True)
os.makedirs(os.path.join(test_project_dir, "v2_context"), exist_ok=True)

pipeline = PipelineV2(
    project_id="temp_test",
    project_name="temp_test",
    workspace_dir=os.path.dirname(__file__)
)
pipeline.model = "deepseek-chat"

result = pipeline.run_step7(
    step4_questions=step4_questions,
    step6_new_information=step6.get("new_information", []),
    meeting_record=None,
    step6_summary=step6.get("meeting_summary", "")
)

print(f"\nPipelineV2.run_step7 结果:")
print(f"  question_validation 数量: {len(result.get('question_validation', []))}")
print(f"  meeting_quality: {result.get('meeting_quality', {})}")

if result.get("question_validation"):
    print("\n前3条验证结果:")
    for i, qv in enumerate(result["question_validation"][:3]):
        print(f"  {i+1}. {qv.get('question_id')}: status={qv.get('status')}, quality={qv.get('quality')}")
else:
    print("\n❌ question_validation 为空！")

# 清理测试目录
import shutil
shutil.rmtree(test_project_dir, ignore_errors=True)

print("\n测试完成!")
