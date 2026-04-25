# -*- coding: utf-8 -*-
"""
services.profile — Profile 管理模块

导出核心函数供其他模块使用。
"""

from .profile_loader import (
    DEFAULT_PROFILE_ID,
    get_kb_root,
    list_fund_profiles,
    load_profile,
    load_project_profile,
    save_project_profile,
    get_profile_summary,
    get_fit_questions_for_profile,
    merge_base_and_profile_questions,
    extract_profile_constraints,
)

__all__ = [
    "DEFAULT_PROFILE_ID",
    "get_kb_root",
    "list_fund_profiles",
    "load_profile",
    "load_project_profile",
    "save_project_profile",
    "get_profile_summary",
    "get_fit_questions_for_profile",
    "merge_base_and_profile_questions",
    "extract_profile_constraints",
]
