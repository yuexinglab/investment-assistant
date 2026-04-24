# -*- coding: utf-8 -*-
"""
Step5 Schema - 探索型投资人版本 (v2)

核心变化：
- 从"下结论" → "提出假设 + 设计验证"
- 所有判断保留不确定性（可被推翻）
- 强调"会前验证逻辑"而非"最终结论"

输出结构：
- current_hypothesis: 当前假设（可被推翻）
- why_this_might_be_wrong: 可能错的地方（关键！）
- investment_logic: 多空逻辑
- key_validation_points: 关键验证点
- deal_breaker_signals: 触发放弃的信号
- meeting_objective: 会前目标（Step4/5桥梁）
- next_step_strategy: 下一步策略
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class KeyValidationPoint(BaseModel):
    """关键验证点"""
    point: str = Field(description="验证点描述")
    why_it_matters: str = Field(description="为什么重要")
    what_to_look_for: str = Field(description="要观察什么/如何验证")


class DealBreakerSignal(BaseModel):
    """触发放弃的信号"""
    signal: str = Field(description="什么信号出现就放弃")
    implication: str = Field(description="出现后的含义")


class NextStepStrategy(BaseModel):
    """下一步策略"""
    if_validated: str = Field(description="如果验证通过，下一步")
    if_not_validated: str = Field(description="如果验证不通过，下一步")
    current_action: str = Field(description="当前建议动作")


class Step5Output(BaseModel):
    """
    Step5 v2 探索型投资人输出

    核心原则：
    - 不是结论，是假设
    - 不是判断，是对判断的反思
    - 核心是"验证逻辑"而非"表达观点"
    """

    # 1. 当前假设（可被推翻）
    current_hypothesis: str = Field(
        description="当前假设，不是最终结论。必须保留不确定性，用'可能/当前判断/需验证'等表达。"
    )

    # 2. 为什么这个假设可能是错的（关键新增！）
    why_this_might_be_wrong: List[str] = Field(
        description="列出2-4个'你可能是错的地方'，这是防止AI自信过度的关键模块"
    )

    # 3. 投资逻辑
    investment_logic: InvestmentLogic = Field(
        description="多空逻辑，不是结论而是'如果...则...'"
    )

    # 4. 关键验证点（与Step4强关联）
    key_validation_points: List[KeyValidationPoint] = Field(
        description="会议中需要验证的核心点"
    )

    # 5. 放弃信号
    deal_breaker_signals: List[DealBreakerSignal] = Field(
        description="一旦出现就停止跟进的信号"
    )

    # 6. 会前目标（Step4/5的桥梁）
    meeting_objective: str = Field(
        description="本次会议的核心目标：验证哪些假设"
    )

    # 7. 下一步策略
    next_step_strategy: NextStepStrategy = Field(
        description="基于验证结果的下一步"
    )

    def to_markdown(self) -> str:
        """转换为可读的 Markdown 格式"""
        lines = []

        lines.append("# 投资判断框架 v2（探索型）\n")
        lines.append("> ⚠️ 本框架代表「当前阶段的初步假设」，而非最终投资结论。\n")
        lines.append("> 所有判断都可能因新信息被推翻。\n")

        # 1. 当前假设
        lines.append("## 1. 当前假设\n")
        lines.append(f"{self.current_hypothesis}\n")

        # 2. 可能错的地方
        lines.append("## 2. 为什么这个假设可能是错的\n")
        lines.append("> 🔑 这是防止自信过度的关键反思\n")
        for i, reason in enumerate(self.why_this_might_be_wrong, 1):
            lines.append(f"{i}. {reason}")
        lines.append("")

        # 3. 投资逻辑
        lines.append("## 3. 投资逻辑\n")

        lines.append("**看多理由 (Bull Case)**\n")
        for i, item in enumerate(self.investment_logic.bull_case, 1):
            lines.append(f"{i}. {item}")
        lines.append("")

        lines.append("**看空理由 (Bear Case)**\n")
        for i, item in enumerate(self.investment_logic.bear_case, 1):
            lines.append(f"{i}. {item}")
        lines.append("")

        # 4. 关键验证点
        lines.append("## 4. 关键验证点\n")
        lines.append("> 本次会议需要重点验证的内容\n")
        for i, vp in enumerate(self.key_validation_points, 1):
            lines.append(f"**{i}. {vp.point}**")
            lines.append(f"   - 为什么重要: {vp.why_it_matters}")
            lines.append(f"   - 观察什么: {vp.what_to_look_for}")
            lines.append("")
        lines.append("")

        # 5. 放弃信号
        lines.append("## 5. 放弃信号\n")
        lines.append("> 一旦出现以下信号，建议停止跟进\n")
        for i, db in enumerate(self.deal_breaker_signals, 1):
            lines.append(f"**{i}. {db.signal}**")
            lines.append(f"   → {db.implication}")
            lines.append("")
        lines.append("")

        # 6. 会前目标
        lines.append("## 6. 会前目标\n")
        lines.append(f"{self.meeting_objective}\n")

        # 7. 下一步策略
        lines.append("## 7. 下一步策略\n")
        lines.append(f"| 情况 | 建议动作 |\n")
        lines.append(f"|------|----------|\n")
        lines.append(f"| ✅ 验证通过 | {self.next_step_strategy.if_validated} |\n")
        lines.append(f"| ❌ 验证不通过 | {self.next_step_strategy.if_not_validated} |\n")
        lines.append(f"| **当前建议** | **{self.next_step_strategy.current_action}** |\n")

        return "\n".join(lines)


class InvestmentLogic(BaseModel):
    """投资逻辑"""
    bull_case: List[str] = Field(description="看多理由（如果A成立→支持投资）")
    bear_case: List[str] = Field(description="看空理由（如果B成立→不支持投资）")
