# -*- coding: utf-8 -*-
"""services/v2 — 2.0 会后分析模块"""

from .pipeline import PipelineV2
from .schemas import (
    V2Output,
    Step6Output, Step7Output, Step8Output, Step9Output,
    DialogueTurn, UserProfileCandidate,
    QuestionCandidate, IndustryInsightCandidate,
)
from .renderer import render_v2_report

__all__ = [
    "PipelineV2",
    "V2Output",
    "Step6Output", "Step7Output", "Step8Output", "Step9Output",
    "DialogueTurn", "UserProfileCandidate",
    "QuestionCandidate", "IndustryInsightCandidate",
    "render_v2_report",
]
