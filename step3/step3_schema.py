# -*- coding: utf-8 -*-
"""
Step3 Schema 定义（v3 增强版）

基于 Step2 外部约束的 BP 叙事审查层

核心变化：
- consistency_checks 新增 related_step2_check, external_constraint, bp_claim_checked
- overpackaging_signals 新增 related_step2_constraint, packaging_type
- tensions 新增 related_step2_logic, conflict_type
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ConsistencyCheck(BaseModel):
    """一致性检查项"""
    # 原有字段
    topic: str = Field(description="检查维度，如：商业模式、收入来源、技术壁垒、客户需求")
    claim: str = Field(description="BP中的'说法'（claim）")
    reality: str = Field(description="现实是否支撑这个说法")
    gap: str = Field(description="缺失或问题")
    judgement: str = Field(description="判断：support / contradict / uncertain")
    confidence: str = Field(description="置信度：high / medium / low")

    # ── v3 新增：Step2 引用 ───────────────────────────────────────────────
    related_step2_check: Optional[str] = Field(
        default="",
        description="关联的 Step2 step1_external_check 条目（引用 step1_field）"
    )
    external_constraint: Optional[str] = Field(
        default="",
        description="对应的外部约束是什么（来自 Step2 external_investment_logic）"
    )
    bp_claim_checked: Optional[str] = Field(
        default="",
        description="BP 中具体哪段话对应这个说法"
    )


class Tension(BaseModel):
    """关键矛盾"""
    # 原有字段
    tension: str = Field(description="矛盾描述，如：A vs B")
    why_it_matters: str = Field(description="为什么这个矛盾重要，影响投资判断")
    severity: str = Field(description="严重程度：high / medium / low")

    # ── v3 新增：Step2 引用 ───────────────────────────────────────────────
    related_step2_logic: Optional[str] = Field(
        default="",
        description="关联的 Step2 external_investment_logic 条目"
    )
    conflict_type: Optional[str] = Field(
        default="",
        description="冲突类型：external_vs_bp / step1_vs_bp"
    )


class PackagingSignal(BaseModel):
    """包装/叙事信号"""
    # 原有字段
    signal: str = Field(description="具体信号描述")
    type: str = Field(
        description="类型：tech_overstatement / expansion_story / team_overuse / vague_terms / "
                    "future_as_present / cooperation_as_revenue / tech_as_capability / platform_narrative"
    )
    severity: str = Field(description="严重程度：high / medium / low")

    # ── v3 新增：Step2 引用 ───────────────────────────────────────────────
    related_step2_constraint: Optional[str] = Field(
        default="",
        description="关联的 Step2 约束（来自 Step2 external_investment_logic 或 step1_external_check）"
    )
    packaging_type: Optional[str] = Field(
        default="",
        description="包装类型细分：future_as_present / cooperation_as_revenue / "
                    "tech_as_capability / platform_narrative / vague_metrics / "
                    "team_overuse / tech_overstatement / expansion_story / vague_terms"
    )


class Step3Output(BaseModel):
    """Step3 v3 完整输出（基于 Step2 外部约束的 BP 叙事审查）"""
    # 原有四大块
    consistency_checks: List[ConsistencyCheck] = Field(
        default_factory=list,
        description="一致性检查列表"
    )
    tensions: List[Tension] = Field(
        default_factory=list,
        description="关键矛盾列表"
    )
    overpackaging_signals: List[PackagingSignal] = Field(
        default_factory=list,
        description="包装信号列表"
    )
    summary: str = Field(
        default="",
        description="一句话总结最大认知问题"
    )

    # ── v3 新增：Step2 引用统计 ────────────────────────────────────────────
    step2_constraints_used: int = Field(
        default=0,
        description="本轮 Step3 引用了多少条 Step2 约束"
    )
    step2_caution_references: int = Field(
        default=0,
        description="引用了多少条 Step2 caution 判断"
    )
    step2_contradict_references: int = Field(
        default=0,
        description="引用了多少条 Step2 contradict 判断"
    )
    # 元数据
    step2_version: Optional[str] = Field(
        default="",
        description="引用的 Step2 schema 版本"
    )
