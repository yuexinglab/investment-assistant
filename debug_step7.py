#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试 Step7 执行流程
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json

# 加载测试数据
step6_path = r"C:\Users\86136\Downloads\step6_latest (4).json"
with open(step6_path, "r", encoding="utf-8") as f:
    step6 = json.load(f)

print(f"Step6 new_information 数量: {len(step6.get('new_information', []))}")

# 模拟 step4_questions
step4_questions = [
    "美妆业务的收入规模是多少？",
    "大客户有哪些？粘性如何？",
    "食品业务放量时间表是否可信？",
    "新能源业务收入时间表是什么？",
    "AI平台的准确率和使用场景？",
    "韶关工厂产能利用率如何？",
    "毛利率水平是多少？",
    "并购千沐的协同效应是否真实？",
]

print(f"Step4 questions 数量: {len(step4_questions)}")

# 测试 Step7
print("\n" + "="*50)
print("开始测试 Step7...")
print("="*50)

from services.v2.services.step7_validator import validate

result = validate(
    step4_questions=step4_questions,
    step6_new_information=step6.get("new_information", []),
    meeting_record=None,
    step6_summary=step6.get("meeting_summary", ""),
    model="deepseek-chat"
)

print(f"\nStep7 结果:")
print(f"  question_validation 数量: {len(result.question_validation)}")
print(f"  meeting_quality: {result.meeting_quality}")

if result.question_validation:
    print("\n前3条验证结果:")
    for i, qv in enumerate(result.question_validation[:3]):
        print(f"  {i+1}. {qv.question_id}: status={qv.status}, quality={qv.quality}")
else:
    print("\n❌ question_validation 为空！")

print("\n测试完成!")
