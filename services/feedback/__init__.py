# -*- coding: utf-8 -*-
"""
feedback 模块 — BP 反馈标注与学习闭环

职责：
- 保存/加载人工初判（Pre-AI）和人机对比反馈（Post-AI）
- 提供自由输入自动整理（normalizer）
- 从反馈中生成候选知识（knowledge_generator）
"""
from .storage import (
    append_feedback_case,
    load_feedback_cases,
    find_feedback_case,
    find_feedback_by_project,
    generate_feedback_id,
    FEEDBACK_DIR,
    FEEDBACK_FILE,
)
from .normalizer import HumanNoteNormalizer, HUMAN_NOTE_NORMALIZER_PROMPT
from .knowledge_generator import KnowledgeCandidateGenerator, KNOWLEDGE_CANDIDATE_PROMPT

__all__ = [
    "append_feedback_case",
    "load_feedback_cases",
    "find_feedback_case",
    "generate_feedback_id",
    "HumanNoteNormalizer",
    "KnowledgeCandidateGenerator",
    "FEEDBACK_DIR",
    "FEEDBACK_FILE",
]
