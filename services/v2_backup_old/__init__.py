"""
v2 package — 2.0尽调更新系统

包含：
- schemas.py: 数据结构定义
- prompts.py: Prompt构建器
- pipeline.py: 执行链
- renderer.py: 报告渲染器
"""

from .schemas import (
    # 枚举
    FieldStatus, QAJudgment, ValueAssessment,
    RiskImpact, DecisionImpact,
    RiskStatus, Recommendation, RiskSignal,
    # V1结构化
    V1StructuredOutput, FieldState, Question, Risk,
    # 2.0模块输出
    V2PipelineResult, DeltaResult, QAResult, QASummary,
    RiskUpdate, RiskUpdateSummary,
    DecisionUpdate, AlphaSignal,
)
from .pipeline import run_v2_pipeline
from .renderer import render_markdown, render_ui_card

__all__ = [
    # 枚举
    "FieldStatus",
    "QAJudgment",
    "ValueAssessment",
    "RiskImpact",
    "DecisionImpact",
    "RiskStatus",
    "Recommendation",
    "RiskSignal",
    # V1结构化
    "V1StructuredOutput",
    "FieldState",
    "Question",
    "Risk",
    # 2.0模块输出
    "V2PipelineResult",
    "DeltaResult",
    "QAResult",
    "QASummary",
    "RiskUpdate",
    "RiskUpdateSummary",
    "DecisionUpdate",
    "AlphaSignal",
    # 函数
    "run_v2_pipeline",
    "render_markdown",
    "render_ui_card",
]
