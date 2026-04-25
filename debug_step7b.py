#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试 Step7B - 检查问题根源
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json

# 加载 step6 数据
step6_path = r"C:\Users\86136\Downloads\step6_latest (4).json"
with open(step6_path, "r", encoding="utf-8") as f:
    step6 = json.load(f)

step4_questions = [
    "美妆业务的收入规模是多少？",
    "大客户有哪些？粘性如何？",
    "食品业务放量时间表是否可信？",
    "新能源业务收入时间表是什么？",
    "AI平台的准确率和使用场景？",
]

print("="*50)
print("Step 1: 导入必要的模块...")
from services.v2.services.step7_validator import run_step7a, run_step7b, _normalize_questions

print("Step 2: 标准化问题...")
normalized = _normalize_questions(step4_questions)
print(f"  normalized 问题数量: {len(normalized)}")
print(f"  normalized[0]: {normalized[0]}")

print("\nStep 3: 执行 Step7A...")
question_matches = run_step7a(
    questions=normalized,
    new_information=step6.get("new_information", []),
    model="deepseek-chat"
)
print(f"  Step7A 返回数量: {len(question_matches)}")
if question_matches:
    print(f"  Step7A[0]: {question_matches[0]}")

print("\nStep 4: 执行 Step7B...")
question_validations = run_step7b(
    question_matches=question_matches,
    new_information=step6.get("new_information", []),
    model="deepseek-chat"
)
print(f"  Step7B 返回数量: {len(question_validations)}")
if question_validations:
    print(f"  Step7B[0]: {question_validations[0]}")
else:
    print("  ❌ Step7B 返回空！")

print("\n测试完成!")
