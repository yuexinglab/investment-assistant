"""Step4 package — v6.1 完整版

v6.1 架构：
- 基础扫描层（会话式）：7 个维度 × {opening, follow_up, best_question}
- 深挖层（多路径）：3 个缺口 × {main_path + backup_path + red_flag_question}
- 会前提纲：scan 只显示 best_question，deep dive 完整展开
"""

from step4.step4_service import Step4Service
from step4.step4_internal_schema import (
    Step4InternalOutput,
    InternalGap,
    DecisionImpact,
    DeepDivePath,  # v6.1: 升级版路径结构
)
from step4.context_builder import build_step4_context

__all__ = [
    "Step4Service",
    "Step4InternalOutput",
    "InternalGap",
    "DecisionImpact",
    "DeepDivePath",  # v6.1
    "build_step4_context",
]
