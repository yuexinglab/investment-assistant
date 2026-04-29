# -*- coding: utf-8 -*-
"""直接测试下载对比文档，模拟 Flask 请求"""
import json, sys, os

# 直接加载 case
sys.path.insert(0, r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant')
from services.feedback.storage import find_feedback_by_project
from services.pipeline_v1 import load_pipeline_results
import os

WORKSPACE_DIR = r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace'

project_id = 'A1_重测_20260429_141115'
project_dir = os.path.join(WORKSPACE_DIR, project_id)

case = find_feedback_by_project(project_id)
print(f'找到 case: {case is not None}')
print(f'  review_status: {case.get("review_status")}')
print(f'  evaluation keys: {list(case.get("evaluation", {}).keys())}')
print(f'  core_difference keys: {list(case.get("core_difference", {}).keys())}')
print()

# 模拟 _build_comparison_md
from app import _build_comparison_md

meta = {'project_id': project_id, 'company_name': '测试公司'}
pipeline_results = load_pipeline_results(project_dir)

doc = _build_comparison_md(meta, case, pipeline_results)
print('=== 生成文档内容 ===')
print(doc)
