# -*- coding: utf-8 -*-
"""
knowledge_base/README.md

知识库结构说明

目录结构：
knowledge_base/
  common/           # 通用投资知识库（所有投资人都适用的判断规律）
  profiles/         # 个人/基金画像库（某个人/某只基金的偏好和约束）
  cases/           # 项目案例库（具体项目的最终结果和原因）
  candidates/       # 沉淀候选库（待人工审核的内容）

重要原则：
1. 主判断库（common）和偏好库（profiles）必须分开
2. 偏好只影响"问什么"和"适不适合"，不能污染"事实是什么"
3. 所有沉淀都先进入 candidates，不自动入正式库
"""

# 通用投资知识库 (common/)
industry_insights.json    # 行业认知和规律
question_bank.json        # 问题库
judgment_templates.json   # 判断模板
diligence_actions.json    # 尽调动作清单

# 基金画像库 (profiles/)
fund_profiles/
  government_fund.json    # 政府产业基金
  vc_fund.json            # 风险投资
  industrial_fund.json    # 产业资本
user_profiles/
  default_user.json       # 默认用户画像

# 项目案例库 (cases/)
project_cases.json        # 项目案例记录
fit_feedback.json         # Fit判断反馈

# 沉淀候选库 (candidates/) - 待人工审核
profile_candidates.json           # 画像候选
common_knowledge_candidates.json  # 通用认知候选
question_candidates.json          # 问题候选
fit_feedback_candidates.json       # Fit反馈候选
