# -*- coding: utf-8 -*-
"""直接测试文档生成"""
import json, os

# 直接读 JSONL 找 case
fb_file = r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\knowledge_base\feedback\bp_review_feedback.jsonl'
target_project = 'A1_重测_20260429_141115'

with open(fb_file, 'r', encoding='utf-8') as f:
    for line in f:
        case = json.loads(line)
        if case.get('project_id') == target_project:
            break

print(f'feedback_id: {case.get("feedback_id")}')
print(f'review_status: {case.get("review_status")}')
print(f'evaluation keys: {list(case.get("evaluation", {}).keys())}')
print(f'core_diff keys: {list(case.get("core_difference", {}).keys())}')
print()

evaluation = case.get("evaluation", {})
core_diff = case.get("core_difference", {})

print('=== 3.1 核心差异记录 ===')
print(f'ai_main_thesis: {core_diff.get("ai_main_thesis")}')
print(f'human_main_thesis: {core_diff.get("human_main_thesis")}')
print(f'missed_key_issues: {core_diff.get("missed_key_issues")}')
print()
print('=== 3.2 一句话学习 ===')
print(core_diff.get("one_sentence_learning"))
print()
print('=== 3.3 对齐评估 ===')
print(f'essence_score: {evaluation.get("essence_score")}')
print(f'meeting_judgement_alignment: {evaluation.get("meeting_judgement_alignment")}')
print(f'ai_bias_direction: {evaluation.get("ai_bias_direction")}')
print(f'reasoning_score: {evaluation.get("reasoning_score")}')
print(f'question_coverage_score: {evaluation.get("question_coverage_score")}')
print(f'overall_usefulness_score: {evaluation.get("overall_usefulness_score")}')
print()
print('=== 3.4 错误归因 ===')
print(f'error_types: {evaluation.get("error_types")}')
print(f'wrong_steps: {evaluation.get("wrong_steps")}')
print(f'brief_error_summary: {evaluation.get("brief_error_summary")}')
