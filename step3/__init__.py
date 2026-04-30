# -*- coding: utf-8 -*-
"""
Step3: 基于 Step2 外部约束的 BP 叙事审查层

从"BP 内部一致性检查"升级为"用外部约束审查 BP 叙事"

核心逻辑：
- 使用 Step2 的外部约束（caution / decision_blocker / external_investment_logic）
- 对照 BP 叙事，检查是否：明确回应 / 弱化 / 跳过 / 把未解决说成已解决
- 不允许重新定义公司本质
- 不允许只做语言判断，必须引用 Step2
"""

from .step3_service import run_step3

__all__ = ["run_step3"]
