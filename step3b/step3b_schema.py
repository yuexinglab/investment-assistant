# -*- coding: utf-8 -*-
"""
Step3B Schema 定义
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ConsistencyCheck(BaseModel):
    """一致性检查项"""
    topic: str = Field(description="检查维度，如：商业模式、收入来源、技术壁垒、客户需求")
    claim: str = Field(description="BP中的'说法'（claim）")
    reality: str = Field(description="现实是否支撑这个说法")
    gap: str = Field(description="缺失或问题")
    judgement: str = Field(description="判断：support / contradict / uncertain")
    confidence: str = Field(description="置信度：high / medium / low")


class Tension(BaseModel):
    """关键矛盾"""
    tension: str = Field(description="矛盾描述，如：A vs B")
    why_it_matters: str = Field(description="为什么这个矛盾重要，影响投资判断")
    severity: str = Field(description="严重程度：high / medium / low")


class PackagingSignal(BaseModel):
    """包装/叙事信号"""
    signal: str = Field(description="具体信号描述")
    type: str = Field(description="类型：tech_overstatement / expansion_story / team_overuse / vague_terms")
    severity: str = Field(description="严重程度：high / medium / low")


class Step3BOutput(BaseModel):
    """Step3B 完整输出"""
    consistency_checks: List[ConsistencyCheck] = Field(default_factory=list, description="一致性检查列表")
    tensions: List[Tension] = Field(default_factory=list, description="关键矛盾列表")
    overpackaging_signals: List[PackagingSignal] = Field(default_factory=list, description="包装信号列表")
    summary: str = Field(default="", description="一句话总结最大认知问题")
