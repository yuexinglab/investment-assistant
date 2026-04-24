# -*- coding: utf-8 -*-
"""Step5 package - 决策收敛层 v2（探索型投资人版本）

v2 核心变化：
- 从"下结论" → "提出假设 + 设计验证"
- 所有判断保留不确定性（可被推翻）
- 强调"会前验证逻辑"而非"最终结论"

输出结构：
- current_hypothesis: 当前假设（可被推翻）
- why_this_might_be_wrong: 可能错的地方
- investment_logic: 多空逻辑
- key_validation_points: 关键验证点
- deal_breaker_signals: 触发放弃的信号
- meeting_objective: 会前目标
- next_step_strategy: 下一步策略
"""

from step5.step5_service import Step5Service
from step5.step5_schema import (
    Step5Output,
    KeyValidationPoint,
    DealBreakerSignal,
    NextStepStrategy,
    InvestmentLogic,
)

__all__ = [
    "Step5Service",
    "Step5Output",
    "KeyValidationPoint",
    "DealBreakerSignal",
    "NextStepStrategy",
    "InvestmentLogic",
]
