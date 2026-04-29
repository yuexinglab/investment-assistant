# -*- coding: utf-8 -*-
"""Step5 package - 决策收敛版本

Step5 的定位：
- 不是分析层（那是 Step1/3/3B/4 的事）
- 而是"决策收敛层"：把看懂 + 拆穿 + 提问，收敛成"投不投"

输出结构：
- core_judgement: 核心判断（decision: meet/pass/maybe）
- reasons_to_meet: 值得继续看的决策理由
- reasons_to_pass: 不投的决策理由
- key_risks: 核心风险
- must_ask_questions: 必问问题（来自 Step4 gaps）
- investment_logic: 投资逻辑归因
"""

from step5.step5_service import Step5Service, run_step5
from step5.step5_schema import (
    Step5Output,
    CoreJudgement,
    ReasonItem,
    RiskItem,
    QuestionItem,
    InvestmentLogic,
)

__all__ = [
    "Step5Service",
    "run_step5",
    "Step5Output",
    "CoreJudgement",
    "ReasonItem",
    "RiskItem",
    "QuestionItem",
    "InvestmentLogic",
]
