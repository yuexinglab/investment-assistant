"""
Step4 v6.1 - Internal Schema

核心改动：
- QuestionPath 升级为 DeepDivePath（含 deepen_1, deepen_2）
- 新增 backup_path（备用路径）
- 新增 red_flag_question（红线问题）
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Priority = Literal["P1", "P2", "P3"]


class DecisionImpact(BaseModel):
    positive: str = Field(..., min_length=8, description="如果答案偏正面，投资判断如何变化")
    negative: str = Field(..., min_length=8, description="如果答案偏负面，投资判断如何变化")


class DeepDivePath(BaseModel):
    """
    深挖路径（v6.1 升级版）

    - opening: 自然切入问题
    - deepen_1: 第一次追问（具体化）
    - deepen_2: 第二次追问（更深一层）
    - trap: 验证/反问，揭示矛盾
    - signals: 判断标准 {good: [...], bad: [...]}
    """
    opening: str = Field(..., min_length=8, description="自然切入问题")
    deepen_1: str = Field(..., min_length=8, description="第一次追问，具体化")
    deepen_2: str = Field(..., min_length=8, description="第二次追问，更深一层")
    trap: str = Field(..., min_length=8, description="验证/反问，揭示矛盾")
    signals: dict = Field(..., description="判断标准，结构为 {good: [...], bad: [...]}")

    def to_question_paths_format(self) -> dict:
        """兼容旧格式的转换"""
        return {
            "opening": self.opening,
            "deepen": self.deepen_1,  # 旧格式只有一个 deepen
            "trap": self.trap,
            "signals": self.signals
        }


class InternalGap(BaseModel):
    """
    内部决策骨架（v6.1 升级版）

    每个 gap 包含：
    - 主打路径：最自然、最强的提问路径
    - 备用路径：如果对方回避，换角度
    - 红线问题：必须问到的那一句
    """
    gap_id: str = Field(..., min_length=2)
    priority: Priority
    core_issue: str = Field(..., min_length=8)
    from_bucket: str = Field(..., min_length=3)
    why_it_matters: str = Field(..., min_length=10)
    decision_impact: DecisionImpact
    internal_goal: str = Field(..., min_length=10)
    go_if: str = Field(..., min_length=10)
    no_go_if: str = Field(..., min_length=10)

    # v6.1 核心改动：升级为多路径结构
    main_path: DeepDivePath = Field(..., description="主打路径：最自然、最强")
    backup_path: DeepDivePath = Field(..., description="备用路径：如果对方回避，换角度")
    red_flag_question: str = Field(..., min_length=8, description="红线问题：必须问到的那一句")

    def to_v5_question_paths_format(self) -> List[dict]:
        """兼容 v5 格式的转换"""
        return [
            self.main_path.to_question_paths_format(),
            self.backup_path.to_question_paths_format()
        ]


class Step4InternalOutput(BaseModel):
    """
    Step4 Internal 输出结构（v6.1）

    对齐 GPT 建议的 schema 升级
    """
    total_gaps: int = Field(..., ge=1)
    gaps: List[InternalGap] = Field(..., min_length=1)
    internal_summary: str = Field(..., min_length=10, description="内部决策总结")

    # 用于 brief 展示的摘要（可选）
    top_3_priorities: List[str] = Field(..., description="最关键的 3 件事")

    def to_v5_format(self) -> dict:
        """
        转换为 v5 格式（兼容旧展示逻辑）

        v5 格式：candidate_questions 列表
        """
        gaps_v5 = []
        for gap in self.gaps:
            gap_v5 = gap.model_dump()
            # 删除新字段，添加旧字段
            del gap_v5["main_path"]
            del gap_v5["backup_path"]
            del gap_v5["red_flag_question"]
            gap_v5["question_paths"] = gap.to_v5_question_paths_format()
            gaps_v5.append(gap_v5)

        result = self.model_dump()
        result["gaps"] = gaps_v5
        return result
